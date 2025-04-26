import streamlit as st
import uuid

from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import ToolMessage

from core.database import HerbDatabase
from core.llm_agent import WorkFlow



st.header("🤖 智能查询")
st.markdown("""
在这里，您可以使用自然语言查询数据库。系统会自动理解您的意图并生成相应的SQL查询。
""")
# 模型配置
model_config = {"configurable": {"max_tokens": 1000, "temperature": 1.0, "thread_id": str(uuid.uuid4())}}

# 初始化数据库和LLM
@st.cache_resource
def init_agent():
    workflow = WorkFlow()
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 用户输入
if prompt := st.chat_input("请输入您的问题..."):
    # 添加用户消息到历史
    st.session_state.messages.append({"role": "human", "content": prompt})
    with st.chat_message("human"):
        st.markdown(prompt)
    
    # 显示系统响应
    def output_wrapper(response):
        for chunk, _ in response:
            if not isinstance(chunk, ToolMessage) and chunk.content:
                yield chunk.content
    
    with st.chat_message("ai"):
        try:
            agent = init_agent()
            response = agent.invoke(
                {"messages": [prompt]},
                config=model_config,
                stream_mode="messages"
                )
            msg_placeholder = st.empty()
            with msg_placeholder:
                with st.status("思考中...", expanded=True):
                    msg = st.write_stream(output_wrapper(response))
            msg_placeholder.empty()
            st.session_state.messages.append({"role": "ai", "content": msg})
            st.rerun()
        except Exception as e:
            st.info(agent.get_state(config=model_config))
            raise e