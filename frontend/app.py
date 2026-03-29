import streamlit as st
import requests
import json
import plotly.graph_objects as go
import pandas as pd

if "saved_graphs" not in st.session_state:
    st.session_state.saved_graphs = []
    
st.set_page_config(
    page_title="AI Data Analyst",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background-color: #636EFA;
        /*color: white;
        border: none;
        padding: 8px;
        font-weight: bold;
    }
    .stButton>button:hover { background-color: #4a54c9; }
    .block-container { padding-top: 1rem; }

    /* Tabs text fix (IMPORTANT) */
    button[data-baseweb="tab"] {
        
        font-weight: 600;
    }

    /* Active tab */
    button[aria-selected="true"] {
        background-color: #636EFA !important;
        
        border-radius: 8px;
    }

    /* Hover */
    button[data-baseweb="tab"]:hover {
        color: #636EFA !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar — File Upload ──
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/combo-chart.png", width=60)
    st.title("AI Data Analyst")
    st.divider()

    st.subheader("📁 Upload Data")
    files = st.file_uploader(
        "CSV or Excel",
        accept_multiple_files=True,
        type=["csv", "xlsx"]
    )

if not files:
    st.markdown("""
    <div style='text-align:center; padding: 80px 0;'>
        <h1> AI Data Analyst</h1>
        <p style='color: gray; font-size: 18px;'>
            Upload a CSV or Excel file from the sidebar to get started
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── First load — data fetch karo ──
file_data = []
for f in files:
    f.seek(0)
    file_data.append(("files", (f.name, f.read())))

with st.spinner("Loading data..."):
    res = requests.post(
        "http://127.0.0.1:8000/analyze/",
        files=file_data,
        data={"query": "", "chart_type": "None", "column": ""}
    )

if res.status_code != 200:
    st.error(res.text)
    st.stop()

data = res.json()

if "error" in data:
    st.error(data["error"])
    st.stop()

all_columns      = data["summary"].get("columns_list", [])
numeric_cols     = data["summary"].get("numeric_cols", [])
categorical_cols = data["summary"].get("categorical_cols", [])
datetime_cols    = data["summary"].get("datetime_cols", [])
filter_values    = data["summary"].get("filter_values", {})

# ── Sidebar — Baaki controls real data ke saath ──
with st.sidebar:
    st.success(f"{len(files)} file(s) loaded")
    for f in files:
        st.caption(f"{f.name}")

    st.divider()

    st.subheader("Column")
    selected_col = st.selectbox("Select column", all_columns)

    st.divider()

    st.subheader("Filters")
    filter_col = st.selectbox("Filter by", ["None"] + categorical_cols)
    filter_val = None
    if filter_col != "None":
        filter_val = st.selectbox(
            "Value",
            filter_values.get(filter_col, [])
        )

    st.divider()

    st.subheader("Groupby")
    groupby_col    = st.selectbox("Group by", ["None"] + categorical_cols)
    groupby_metric = st.selectbox("Metric", ["mean", "sum", "count", "max", "min"])

    st.divider()

    st.subheader("Chart")
    chart_type = st.selectbox("Chart type",
                   ["None", "Bar", "Line", "Pie",
                    "Histogram", "Box", "Area", "Scatter", "Heatmap"])

    st.divider()

    st.subheader("Date/Time")
    date_col = st.selectbox("Date column", ["None"] + datetime_cols)
    date_value_col = None
    date_freq = "M"
    if date_col != "None":
        date_value_col = st.selectbox("Value column", numeric_cols)
        date_freq = st.selectbox(
            "Frequency",
            ["D", "W", "M", "Q", "Y"],
            format_func=lambda x: {
                "D": "Daily", "W": "Weekly", "M": "Monthly",
                "Q": "Quarterly", "Y": "Yearly"
            }[x]
        )

    st.divider()

    show_insights = st.toggle("Show Insights", value=True)

    st.divider()

    run = st.button("▶ Run Analysis", width='stretch')

# ── Tabs ──
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Data", "Analysis", "Calculated Columns", "Query", "Saved Graphs"])

# ── Tab 1 — Data ──
with tab1:
    st.subheader("Data Summary")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Rows", data["summary"].get("rows"))
    with c2:
        st.metric("Columns", data["summary"].get("columns"))
    with c3:
        st.metric("Duplicates", data["summary"].get("duplicates"))
    with c4:
        st.metric("Numeric Cols", len(numeric_cols))

    st.divider()

    st.subheader("Data Preview")
    c1, c2 = st.columns([3, 1])
    with c1:
        search_term = st.text_input("Search", placeholder="Type to search...")
    with c2:
        rows_to_show = st.selectbox("Rows", [10, 25, 50, 100, "All"])

    if "table_data" in data:
        df_preview = pd.DataFrame(data["table_data"])
        if search_term:
            mask = df_preview.astype(str).apply(
                lambda x: x.str.contains(search_term, case=False, na=False)
            ).any(axis=1)
            df_preview = df_preview[mask]
        if rows_to_show != "All":
            df_preview = df_preview.head(int(rows_to_show))
        st.dataframe(df_preview, width='stretch', height=400)
        st.caption(f"Showing {len(df_preview)} rows")

    st.divider()

    st.subheader("Null Values")
    null_df = pd.DataFrame(
        data["summary"].get("null_values", {}).items(),
        columns=["Column", "Null Count"]
    )
    null_df = null_df[null_df["Null Count"] > 0]
    if null_df.empty:
        st.success("No null values found!")
    else:
        st.dataframe(null_df, width='stretch')

# ── Tab 2 — Analysis ──
with tab2:
    if run:
        if chart_type == "None":
            st.warning("Please select a chart type")
            st.stop()

        file_data2 = []
        for f in files:
            f.seek(0)
            file_data2.append(("files", (f.name, f.read())))

        with st.spinner("Running analysis..."):
            res2 = requests.post(
                "http://127.0.0.1:8000/analyze/",
                files=file_data2,
                data={
                    "query": "",
                    "chart_type": chart_type.lower(),  # ✅ FIXED
                    "column": selected_col,
                    "filter_col": filter_col if filter_col != "None" else "",
                    "filter_val": filter_val or "",
                    "groupby_col": groupby_col if groupby_col != "None" else "",
                    "groupby_metric": groupby_metric,
                    "date_col": date_col if date_col != "None" else "",
                    "date_value_col": date_value_col or "",
                    "date_freq": date_freq
                }
            )

        if res2.status_code != 200:
            st.error(res2.text)
            st.stop()

        data2 = res2.json()

        if "error" in data2:
            st.error(data2["error"])
            st.stop()

        # ------------------ DATE/TIME ------------------
        if data2.get("datetime_result"):
            st.subheader("📅 Date/Time Trend")
            dt = data2["datetime_result"]
            fig = go.Figure(json.loads(dt["plotly_json"]))
            st.plotly_chart(fig, width = 'stretch')

        # ------------------ GROUPBY ------------------
        if data2.get("groupby_result"):
            st.subheader("📊 Groupby Result")

            gb_df = pd.DataFrame(data2["groupby_result"])
            st.dataframe(gb_df, width = 'stretch')

            # ✅ Always show graph for groupby
            if len(gb_df.columns) == 2:
                fig = go.Figure(go.Bar(
                    x=gb_df.iloc[:, 0],
                    y=gb_df.iloc[:, 1]
                ))
                fig.update_layout(
                    title=f"{groupby_metric} of {selected_col} by {groupby_col}",
                    template="plotly_dark"
                )
                st.plotly_chart(fig, width='stretch')

                if st.button("💾 Save this graph", key="save_groupby_graph"):
                    st.session_state.saved_graphs.append({
                        "fig": fig.to_json(),
                        "custom_title": "Groupby Graph"
                    })
                    st.success("✅ Graph saved!")
                    
                    st.session_state.saved_graphs.append({
                        "fig": g["plotly_json"],
                        "custom_title": g.get("title", "My Graph")
                    })
        # ------------------ GRAPHS ------------------
        # ✅ Show only when no groupby
        DEBUG = []
        #st.write("DEBUG:", data2.get("graphs"))
        
        if groupby_col == "None":
            if data2.get("graphs"):
                st.subheader("📈 Graphs")
                cols = st.columns(2)

                for i, g in enumerate(data2["graphs"]):   # ✅ i yaha defined hai
                    with cols[i % 2]:
                        if "plotly_json" in g:
                            fig = go.Figure(json.loads(g["plotly_json"]))
                            st.plotly_chart(fig, width='stretch')

                            # ✅ SAVE BUTTON (yahi hona chahiye)
                            if st.button("💾 Save this graph", key=f"save_graph_{i}"):
                                if "saved_graphs" not in st.session_state:
                                    st.session_state.saved_graphs = []

                                st.session_state.saved_graphs.append(g)
                                st.success("✅ Graph saved!")
            else:
                st.warning("No graph generated for this selection")
        else:
            st.info("📊 Graph is shown in Groupby section above")
        st.divider()
        
        st.subheader("Saved Graphs")

        if "saved_graphs" in st.session_state and st.session_state.saved_graphs:
            for i, g in enumerate(st.session_state.saved_graphs):
                with cols[i % 2]:
                    fig = go.Figure(json.loads(g["plotly_json"]))
                    st.plotly_chart(fig, width='stretch')
        else:
            st.info("No saved graphs yet")
    
        # ------------------ INSIGHTS ------------------
        if show_insights and data2.get("insights"):
            st.subheader("🧠 Insights")
            cols = st.columns(2)

            for i, insight in enumerate(data2["insights"]):
                with cols[i % 2]:
                    st.info(insight)

    else:
        st.info("👉 Sidebar se options select karo aur ▶ Run Analysis dabao")
        
# ── Tab 3 — Calculated Columns ──
with tab3:
    st.subheader("Calculated Columns")
    st.caption("Format: new_column = expression")
    st.caption("Example: profit = sale_price - market_price")

    calc_formula = st.text_input(
        "Enter formula",
        placeholder="profit = sale_price - market_price"
    )

    if st.button("Add Column"):
        if calc_formula:
            file_data_calc = []
            for f in files:
                f.seek(0)
                file_data_calc.append(("files", (f.name, f.read())))

            with st.spinner("Adding column..."):
                calc_res = requests.post(
                    "http://127.0.0.1:8000/analyze/",
                    files=file_data_calc,
                    data={
                        "query": "",
                        "chart_type": "None",
                        "column": "",
                        "calculated_formula": calc_formula
                    }
                )

            if calc_res.status_code == 200:
                calc_data = calc_res.json()
                if calc_data.get("calc_message"):
                    if "successfully" in calc_data["calc_message"]:
                        st.success(calc_data["calc_message"])
                    else:
                        st.error(calc_data["calc_message"])
                if "table_data" in calc_data:
                    st.subheader("Updated Preview")
                    df_calc = pd.DataFrame(calc_data["table_data"])
                    st.dataframe(df_calc, width='stretch', height=300)
        else:
            st.warning("Formula likhna zaroori hai")

# ── Tab 4 — Query ──
with tab4:
    st.subheader("🔍 Query")
    query = st.text_input(
        "Enter your query",
        placeholder="average sale_price"
    )

    if st.button("🔎 Run Query"):
        if query:
            file_data_q = []
            for f in files:
                f.seek(0)
                file_data_q.append(("files", (f.name, f.read())))

            with st.spinner("Running query..."):
                res_q = requests.post(
                    "http://127.0.0.1:8000/analyze/",
                    files=file_data_q,
                    data={
                        "query": query,
                        "chart_type": "None",
                        "column": selected_col
                    }
                )

            if res_q.status_code == 200:
                q_data = res_q.json()
                if q_data.get("query_result"):
                    st.subheader("Result")
                    st.write(q_data["query_result"])
                else:
                    st.warning("Koi result nahi mila")
        else:
            st.warning("Query likhna zaroori hai")
            
with tab5:
    st.subheader("💾 Saved Graphs")

    if not st.session_state.saved_graphs:
        st.info("No graphs saved yet")

    else:
        cols = st.columns(2)

        for i, g in enumerate(st.session_state.saved_graphs):
            with cols[i % 2]:

                # ✅ Rename
                new_title = st.text_input(
                    "Rename",
                    value=g["custom_title"],
                    key=f"title_{i}"
                )
                st.session_state.saved_graphs[i]["custom_title"] = new_title

                # ✅ Delete
                if st.button("Remove", key=f"delete_{i}"):
                    st.session_state.saved_graphs.pop(i)
                    st.rerun()

                # ✅ Graph show
                fig = go.Figure(json.loads(g["fig"]))
                fig.update_layout(title=new_title)

                st.plotly_chart(fig, width='stretch')

                # ✅ Download (optional)
                try:
                    img_bytes = fig.to_image(format="png")
                    st.download_button(
                        f"⬇ Download {i}",
                        data=img_bytes,
                        file_name=f"{new_title}.png",
                        mime="image/png"
                    )
                except:
                    pass