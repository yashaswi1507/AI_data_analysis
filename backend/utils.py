import os
import time
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_file(file_path):
    try:
        if file_path.endswith(".csv"):
            try:
                df = pd.read_csv(file_path, sep=None, engine="python", encoding="latin1")
            except pd.errors.EmptyDataError:
                raise ValueError("Uploaded CSV file is empty")
            except Exception:
                df = pd.read_csv(file_path, encoding="latin1")
        elif file_path.endswith(".xlsx"):
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format")

        if df is None or df.empty:
            raise ValueError("Uploaded file is empty")

        return df

    except Exception as e:
        raise ValueError(f"Error loading file: {str(e)}")


def clean_data(df):
    df = df.drop_duplicates()
    df = df.dropna(how='all')

    # IMPORTANT (numeric fix)
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except:
            pass

    # ✅ FIX inplace issue
    for col in df.select_dtypes(include='number').columns:
        df[col] = df[col].fillna(df[col].mean())

    for col in df.select_dtypes(include='object').columns:
        if not df[col].mode().empty:
            df[col] = df[col].fillna(df[col].mode()[0])

    return df


def data_summary(df):
    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "columns_list": df.columns.tolist(),
        "null_values": df.isnull().sum().to_dict(),
        "duplicates": int(df.duplicated().sum())
    }


def classify_columns(df):
    numeric = df.select_dtypes(include='number').columns.tolist()
    categorical = df.select_dtypes(include='object').columns.tolist()
    return numeric, categorical


def detect_datetime_cols(df):
    datetime_cols = []

    for col in df.select_dtypes(include='object').columns:  # ✅ FIX
        try:
            converted = pd.to_datetime(df[col], errors='coerce', format='mixed')
            if converted.notna().sum() / len(df) > 0.7:
                datetime_cols.append(col)
        except:
            continue

    return datetime_cols

def convert_datetime_cols(df, datetime_cols):
    for col in datetime_cols:
        try:
            df[col] = pd.to_datetime(df[col], format='mixed', errors='coerce')
        except:
            pass
    return df

def auto_generate_graphs(df, numeric, categorical):
    graphs = []

    for col in numeric[:3]:
        fig = px.histogram(
            df, x=col,
            title=f"Distribution of {col}",
            template="plotly_dark",
            color_discrete_sequence=["#636EFA"]
        )
        graphs.append({
            "title": f"Histogram of {col}",
            "plotly_json": fig.to_json()
        })

    for col in categorical[:3]:
        counts = df[col].value_counts().head(10).reset_index()
        counts.columns = [col, "count"]
        fig = px.bar(
            counts, x=col, y="count",
            title=f"Top categories in {col}",
            template="plotly_dark",
            color_discrete_sequence=["#EF553B"]
        )
        fig.update_layout(xaxis_tickangle=-45)
        graphs.append({
            "title": f"Bar chart of {col}",
            "plotly_json": fig.to_json()
        })

    if len(numeric) >= 2:
        fig = px.scatter(
            df, x=numeric[0], y=numeric[1],
            title=f"{numeric[0]} vs {numeric[1]}",
            template="plotly_dark",
            color_discrete_sequence=["#00CC96"]
        )
        graphs.append({
            "title": f"Scatter: {numeric[0]} vs {numeric[1]}",
            "plotly_json": fig.to_json()
        })

    if len(numeric) > 1:
        corr = df[numeric].corr()
        fig = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.columns.tolist(),
            colorscale="RdBu",
            zmid=0
        ))
        fig.update_layout(title="Correlation Heatmap", template="plotly_dark")
        graphs.append({
            "title": "Correlation Heatmap",
            "plotly_json": fig.to_json()
        })

    return graphs


def generate_graphs(df, numeric, categorical, chart_type, selected_col):
    fig = None

    if chart_type == "histogram":
        try:
            df[selected_col] = pd.to_numeric(df[selected_col])
        except:
            return []
        fig = px.histogram(df, x=selected_col, template="plotly_dark",
                           title=f"Histogram of {selected_col}",
                           color_discrete_sequence=["#636EFA"])

    elif chart_type == "box":
        if selected_col not in numeric:
            return []
        fig = px.box(df, y=selected_col, template="plotly_dark",
                     title=f"Box Plot of {selected_col}",
                     color_discrete_sequence=["#AB63FA"])

    elif chart_type == "line":
        if selected_col not in numeric:
            return []
        fig = px.line(df, y=selected_col, template="plotly_dark",
                      title=f"Line Chart of {selected_col}",
                      color_discrete_sequence=["#FFA15A"])

    elif chart_type == "area":
        if selected_col not in numeric:
            return []
        fig = px.area(df, y=selected_col, template="plotly_dark",
                      title=f"Area Chart of {selected_col}",
                      color_discrete_sequence=["#19D3F3"])

    elif chart_type == "bar":
        if selected_col in categorical:
            counts = df[selected_col].value_counts().head(10).reset_index()
            counts.columns = [selected_col, "count"]
            fig = px.bar(counts, x=selected_col, y="count",
                         template="plotly_dark",
                         title=f"Bar Chart of {selected_col}",
                         color_discrete_sequence=["#EF553B"])
            fig.update_layout(xaxis_tickangle=-45)
        elif selected_col in numeric:
            if df[selected_col].nunique() <= 50:
                counts = df[selected_col].value_counts().reset_index()
                counts.columns = [selected_col, "count"]
                fig = px.bar(counts, x=selected_col, y="count",
                             template="plotly_dark",
                             title=f"Bar Chart of {selected_col}",
                             color_discrete_sequence=["#EF553B"])
            else:
                return []
        else:
            return []

    elif chart_type == "pie":
        if selected_col in categorical:
            counts = df[selected_col].value_counts().head(10).reset_index()
            counts.columns = [selected_col, "count"]
        elif selected_col in numeric:
            if df[selected_col].nunique() <= 10:
                counts = df[selected_col].value_counts().reset_index()
                counts.columns = [selected_col, "count"]
            else:
                return []
        else:
            return []
        fig = px.pie(counts, names=selected_col, values="count",
                     template="plotly_dark",
                     title=f"Pie Chart of {selected_col}",
                     hole=0.3)

    elif chart_type == "scatter":
        if len(numeric) < 2:
            return []
        fig = px.scatter(df, x=numeric[0], y=numeric[1],
                         template="plotly_dark",
                         title=f"Scatter: {numeric[0]} vs {numeric[1]}",
                         color_discrete_sequence=["#00CC96"])

    elif chart_type == "heatmap":
        if len(numeric) < 2:
            return []
        corr = df[numeric].corr()
        fig = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.columns.tolist(),
            colorscale="RdBu",
            zmid=0
        ))
        fig.update_layout(title="Heatmap", template="plotly_dark")

    else:
        return []

    if fig is None:
        return []

    return [{
        "title": f"{chart_type.capitalize()} of {selected_col}",
        "plotly_json": fig.to_json()
    }]


def generate_insights(df, numeric):
    insights = []
    for col in numeric:
        mean = df[col].mean()
        median = df[col].median()
        insights.append(f"{col} Mean: {mean:.2f}")
        insights.append(f"{col} Max: {df[col].max()}")
        if mean > median:
            insights.append(f"{col} is right-skewed")
        elif mean < median:
            insights.append(f"{col} is left-skewed")
    return insights


def perform_groupby(df, groupby_col, value_col, metric="mean"):
    try:
        if groupby_col not in df.columns or value_col not in df.columns:
            return None

        num_cols = df.select_dtypes(include='number').columns.tolist()

        if metric == "count":
            result = df.groupby(groupby_col)[value_col].count().reset_index()
        elif value_col in num_cols:
            if metric == "mean":
                result = df.groupby(groupby_col)[value_col].mean().reset_index()
            elif metric == "sum":
                result = df.groupby(groupby_col)[value_col].sum().reset_index()
            elif metric == "max":
                result = df.groupby(groupby_col)[value_col].max().reset_index()
            elif metric == "min":
                result = df.groupby(groupby_col)[value_col].min().reset_index()
            else:
                result = df.groupby(groupby_col)[value_col].mean().reset_index()
        else:
            result = df.groupby(groupby_col)[value_col].count().reset_index()

        result = result.sort_values(by=value_col, ascending=False)

        if value_col in num_cols:
            result[value_col] = result[value_col].round(2)

        return result.to_dict(orient="records")

    except Exception as e:
        return None


def datetime_analysis(df, date_col, value_col, freq="M"):
    try:
        df_temp = df[[date_col, value_col]].copy()
        df_temp[date_col] = pd.to_datetime(df_temp[date_col])
        df_temp = df_temp.set_index(date_col)
        df_temp = df_temp.sort_index()

        freq_map = {"D": "Daily", "W": "Weekly", "M": "Monthly",
                    "Q": "Quarterly", "Y": "Yearly"}
        title = freq_map.get(freq, "Monthly") + " Trend"

        resampled = df_temp.resample(freq).mean().dropna()

        if resampled.empty:
            return None

        fig = px.line(
            resampled, y=value_col,
            title=f"{title} of {value_col}",
            template="plotly_dark",
            color_discrete_sequence=["#636EFA"]
        )
        fig.update_layout(xaxis_title="Date", yaxis_title=value_col,
                          hovermode="x unified")

        stats = {
            "highest": {
                "value": round(float(resampled[value_col].max()), 2),
                "date": str(resampled[value_col].idxmax().date())
            },
            "lowest": {
                "value": round(float(resampled[value_col].min()), 2),
                "date": str(resampled[value_col].idxmin().date())
            },
            "overall_trend": "📈 Upward" if resampled[value_col].iloc[-1] > resampled[value_col].iloc[0] else "📉 Downward"
        }

        return {
            "plotly_json": fig.to_json(),
            "title": f"{title} of {value_col}",
            "stats": stats
        }

    except Exception as e:
        return None


def add_calculated_column(df, formula):
    try:
        if "=" not in formula:
            return df, "Formula mein '=' hona chahiye. Example: profit = sale_price - market_price"

        col_name, expression = formula.split("=", 1)
        col_name = col_name.strip()
        expression = expression.strip()

        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col_name):
            return df, "Column naam mein sirf letters, numbers aur underscore allowed hain"

        df[col_name] = df.eval(expression)

        return df, f"Column '{col_name}' successfully add hua!"

    except Exception as e:
        return df, f"Formula error: {str(e)}"


def handle_query(df, query):
    query = re.sub(r'[^\w\s]', '', query).lower().strip()

    num_cols = df.select_dtypes(include='number').columns.tolist()
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    all_cols = df.columns.tolist()

    if len(all_cols) == 0:
        return {"message": "No columns found in dataset"}

    detected_col = None

    for c in all_cols:
        c_clean = c.lower().replace("_", " ").replace("-", " ")
        q_clean = query.replace("_", " ")
        if c_clean in q_clean or q_clean in c_clean:
            detected_col = c
            break

    if not detected_col:
        query_words = query.split()
        for c in all_cols:
            col_words = c.lower().replace("_", " ").split()
            if any(w in query_words for w in col_words):
                detected_col = c
                break

    if not detected_col:
        query_words = query.split()
        for c in all_cols:
            for qw in query_words:
                if len(qw) > 3 and qw in c.lower():
                    detected_col = c
                    break
            if detected_col:
                break

    if not detected_col:
        detected_col = num_cols[0] if num_cols else all_cols[0]

    col = detected_col

    avg_kw = ["average", "mean", "avg"]
    sum_kw = ["total", "sum"]
    top_kw = ["top", "highest", "maximum", "max", "best", "most"]
    low_kw = ["lowest", "minimum", "min", "worst", "least", "bottom"]
    cnt_kw = ["count", "how many", "number of"]
    unq_kw = ["unique", "distinct", "different"]
    nul_kw = ["missing", "null", "empty", "nan"]
    dst_kw = ["distribution", "spread", "range", "describe", "summary",
              "stats", "statistics", "overview", "analysis", "breakdown"]

    if any(k in query for k in dst_kw):
        if col in num_cols:
            return {
                f"{col} - Mean"   : round(float(df[col].mean()), 2),
                f"{col} - Median" : round(float(df[col].median()), 2),
                f"{col} - Std Dev": round(float(df[col].std()), 2),
                f"{col} - Min"    : round(float(df[col].min()), 2),
                f"{col} - Max"    : round(float(df[col].max()), 2),
                f"{col} - 25%"    : round(float(df[col].quantile(0.25)), 2),
                f"{col} - 75%"    : round(float(df[col].quantile(0.75)), 2),
            }
        else:
            return {f"Distribution of {col}": df[col].value_counts().head(10).to_dict()}

    if any(k in query for k in top_kw):
        if col in num_cols:
            return {f"Top 5 by {col}": df.nlargest(5, col)[col].reset_index(drop=True).tolist()}
        else:
            return {f"Top 5 in {col}": df[col].value_counts().head(5).to_dict()}

    if any(k in query for k in low_kw):
        if col in num_cols:
            return {f"Bottom 5 by {col}": df.nsmallest(5, col)[col].reset_index(drop=True).tolist()}
        else:
            return {f"Bottom 5 in {col}": df[col].value_counts().tail(5).to_dict()}

    if any(k in query for k in avg_kw):
        if col in num_cols:
            return {f"Average {col}": round(float(df[col].mean()), 2)}
        else:
            return {"message": f"'{col}' is not numeric"}

    if any(k in query for k in sum_kw):
        if col in num_cols:
            return {f"Total {col}": round(float(df[col].sum()), 2)}
        else:
            return {"message": f"'{col}' is not numeric"}

    if any(k in query for k in cnt_kw):
        return {f"Count of {col}": int(df[col].count())}

    if any(k in query for k in unq_kw):
        return {
            f"Unique values in {col}": df[col].nunique(),
            "Values": df[col].unique()[:20].tolist()
        }

    if any(k in query for k in nul_kw):
        return {f"Missing values in {col}": int(df[col].isnull().sum())}

    if col in num_cols:
        return {
            f"{col} - Mean": round(float(df[col].mean()), 2),
            f"{col} - Max" : round(float(df[col].max()), 2),
            f"{col} - Min" : round(float(df[col].min()), 2),
        }
    else:
        return {f"Top values in {col}": df[col].value_counts().head(5).to_dict()}