import streamlit as st
import pandas as pd
from core.database import HerbDatabase



st.header("📊 数据库管理")

# 创建数据库实例
db = HerbDatabase()

# 查询表单
with st.form("查询表单"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        herb_id = st.number_input("药材ID", min_value=0, step=1)
    with col2:
        herb_name = st.text_input("药材名称")
    with col3:
        min_price = st.number_input("最低价格", min_value=0.0, step=0.01)
    with col4:
        max_price = st.number_input("最高价格", min_value=0.0, step=0.01)
    
    submitted = st.form_submit_button("查询")

# 执行查询
if submitted:
    df = db.query_herbs(
        id=herb_id if herb_id > 0 else None,
        name=herb_name if herb_name else None,
        min_price=min_price if min_price > 0 else None,
        max_price=max_price if max_price > 0 else None
    )
else:
    df = db.get_all_herbs()

# 数据编辑器
st.subheader("药材数据")
main_col, side_col = st.columns([0.9, 0.1])
with main_col:
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
    column_config={
        "id": st.column_config.NumberColumn("药材ID", disabled=True),
        "name": st.column_config.TextColumn("名称", required=True),
        "price": st.column_config.NumberColumn("价格/克", format="%.2f", required=True),
        "effect": st.column_config.TextColumn("功效"),
        "usage": st.column_config.TextColumn("用法用量")
    }
)

# 导出对话框函数
@st.dialog("确认导出")
def export_dialog():
    st.warning("即将导出当前所有药材数据为CSV文件。")
    tmp_col1, tmp_col2 = st.columns(2)
    with tmp_col1:
        csv = db.export_to_csv(edited_df)
        st.download_button(
            label="下载CSV文件",
            data=csv,
            file_name="herbs.csv",
            mime="text/csv",
            use_container_width=True
        )
    with tmp_col2:
        if st.button("取消", use_container_width=True):
            st.rerun()

# 导入对话框函数
@st.dialog("确认导入")
def import_dialog():
    st.error("⚠️ 警告：导入CSV将覆盖当前所有药材数据！")
    uploaded_file = st.file_uploader("选择CSV文件", type=['csv'])
    import_placeholder = st.container()
    tmp_col1, tmp_col2 = st.columns(2)
    if uploaded_file is not None:
        try:
            # 尝试不同的编码方式
            encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']
            new_df = None
            
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)  # 重置文件指针
                    new_df = pd.read_csv(uploaded_file, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if new_df is None:
                import_placeholder.error("无法识别文件编码，请确保文件使用UTF-8或GBK编码")
                
            # 验证数据格式
            required_columns = ['id', 'name', 'price', 'effect', 'usage']
            if all(col in new_df.columns for col in required_columns):
                import_placeholder.success("CSV文件格式正确")
                if tmp_col1.button("确认导入", use_container_width=True):
                    db.save_changes(new_df)
                    import_placeholder.success("数据导入成功！")
                    st.rerun()
            else:
                import_placeholder.error("CSV文件格式不正确，请确保包含所有必要列：id, name, price, effect, usage")
        except Exception as e:
            import_placeholder.error(f"导入失败：{str(e)}")
    if tmp_col2.button("取消导入", use_container_width=True):
        st.rerun()

if side_col.button("", icon=":material/save:", help="保存修改"):
    db.save_changes(edited_df)
    st.success("数据已保存！")
if side_col.button("", icon=":material/download:", help="导出当前所有药材数据为CSV文件"):
    export_dialog()
if side_col.button("", icon=":material/upload:", help="导入CSV文件"):
    import_dialog() 