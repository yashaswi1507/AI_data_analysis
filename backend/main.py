from fastapi import FastAPI, UploadFile, File, Form
import os
from utils import *
from typing import List
import pandas as pd
import time

app = FastAPI()

@app.post("/analyze/")
async def analyze(
    files: List[UploadFile] = File(...),
    query: str = Form(None),
    chart_type: str = Form(None),
    column: str = Form(None),
    filter_col: str = Form(None),
    filter_val: str = Form(None),
    groupby_col: str = Form(None),
    groupby_metric: str = Form(None),
    date_col: str = Form(None),
    date_value_col: str = Form(None),
    date_freq: str = Form(None),
    calculated_formula: str = Form(None)
):
    try:
        query = query or ""
        chart_type = (chart_type or "none").lower()
        column = column if column else None
        filter_col = filter_col if filter_col else None
        filter_val = filter_val if filter_val else None
        groupby_col = groupby_col if groupby_col else None
        groupby_metric = groupby_metric or "mean"
        date_col = date_col if date_col else None
        date_value_col = date_value_col if date_value_col else None
        date_freq = date_freq or "M"
        calculated_formula = calculated_formula if calculated_formula else None

        os.makedirs("uploads", exist_ok=True)

        dfs = []
        file_labels = []

        for file in files:
            file_path = f"uploads/{int(time.time())}_{file.filename}"
            contents = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(contents)
            df_temp = load_file(file_path)
            file_label = os.path.splitext(file.filename)[0]
            dfs.append(df_temp)
            file_labels.append(file_label)

        # Universal conflict fix
        if len(dfs) > 1:
            all_col_sets = [set(d.columns) for d in dfs]
            common_cols = set.intersection(*all_col_sets)
            if common_cols:
                renamed_dfs = []
                for df_temp, label in zip(dfs, file_labels):
                    rename_map = {}
                    for c in common_cols:
                        try:
                            all_unique_vals = [
                                set(d[c].dropna().astype(str).unique())
                                for d in dfs
                            ]
                            first = all_unique_vals[0]
                            all_same = all(first == other for other in all_unique_vals[1:])
                            if not all_same:
                                rename_map[c] = f"{c}_{label}"
                        except:
                            rename_map[c] = f"{c}_{label}"
                    df_temp = df_temp.rename(columns=rename_map)
                    renamed_dfs.append(df_temp)
                dfs = renamed_dfs

        df = pd.concat(dfs, ignore_index=True, sort=False)
        df = clean_data(df)

        calc_message = None
        if calculated_formula:
            df, calc_message = add_calculated_column(df, calculated_formula)

        numeric, categorical = classify_columns(df)
        datetime_cols = detect_datetime_cols(df)
        df = convert_datetime_cols(df, datetime_cols)

        summary = data_summary(df)
        summary["numeric_cols"] = numeric
        summary["categorical_cols"] = categorical
        summary["datetime_cols"] = datetime_cols
        summary["filter_values"] = {
            col: df[col].dropna().unique().tolist()[:50]
            for col in categorical
        }

        if filter_col and filter_val:
            df = df[df[filter_col].astype(str) == str(filter_val)]

        graphs = []
        if chart_type != "none" and column:
            graphs = generate_graphs(df, numeric, categorical, chart_type, column)
        else:
            graphs = auto_generate_graphs(df, numeric, categorical)

        insights = generate_insights(df, numeric)

        query_result = None
        if query:
            query_result = handle_query(df, query)

        groupby_result = None
        if groupby_col and column:
            groupby_result = perform_groupby(df, groupby_col, column, groupby_metric)

        datetime_result = None
        if date_col and date_value_col:
            datetime_result = datetime_analysis(df, date_col, date_value_col, date_freq)

        return {
            "graphs": graphs,
            "insights": insights,
            "summary": summary,
            "query_result": query_result,
            "groupby_result": groupby_result,
            "datetime_result": datetime_result,
            "calc_message": calc_message,
            "table_data": df.head(100).to_dict(orient="records"),
            "message": f"{len(files)} file(s) processed."
        }

    except Exception as e:
        return {"error": str(e)}