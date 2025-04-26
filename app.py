import streamlit as st

st.set_page_config(
    page_title="HerbStat - 中药数据库管理系统",
    page_icon="🌿",
    layout="wide"
)

pg = st.navigation(
    [
        st.Page("pages/home.py", title="首页", icon="🏠"),
        st.Page("pages/assistant.py", title="智能查询", icon="🔍"),
        st.Page("pages/dbm.py", title="数据库管理", icon="📊")
    ]
)
pg.run()