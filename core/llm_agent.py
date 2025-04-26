from typing import Dict, List, TypedDict, Annotated, Sequence, Any
import pandas as pd
import json

from langgraph.graph import START, END, MessagesState, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_deepseek import ChatDeepSeek
from core.database import HerbDatabase



class State(TypedDict):
    """State for the agent."""
    messages: Annotated[List[BaseMessage], "messages"]


class ConfigSchema(TypedDict):
    """Config for the agent."""
    model: str
    max_tokens: int
    temperature: float


class WorkFlow(StateGraph):
    def __init__(self):
        super().__init__(state_schema=State, config_schema=ConfigSchema)
        self._build()

    @staticmethod
    @tool("query_herbs", description="根据用户提供的药材名称列表，返回药材信息。")
    def query_herbs(names: List[str]):
        results = []
        for name in names:
            db = HerbDatabase()
            df = db.query_herbs(name=name)
            if not df.empty:
                for _, row in df.iterrows():
                    herb_info = {
                        "id": int(row["id"]),
                        "name": row["name"],
                        "price": float(row["price"]),
                        "effect": row["effect"],
                        "usage": row["usage"]
                    }
                    results.append(herb_info)
        return results
    
    @staticmethod
    @tool("calculate_total_price", description="根据用户输入的药材名称和数量，返回总价")
    def calculate_total_price(names: List[str], quantities: List[int]):
        # 查询每种药材的价格，然后计算并返回总价
        total_price = 0
        results = []
        for name, quantity in zip(names, quantities):
            db = HerbDatabase()
            df = db.query_herbs(name=name)
            if not df.empty:
                price = float(df.iloc[0]["price"])
                total_price += price * quantity
                herb_info = {
                    "id": int(df.iloc[0]["id"]),
                    "name": df.iloc[0]["name"], 
                    "price": price,
                    "effect": df.iloc[0]["effect"],
                    "usage": df.iloc[0]["usage"],
                    "quantity": quantity
                }
                results.append(herb_info)
        return {"results": results, "total_price": total_price}

    def _agent(self, state: State, config: RunnableConfig):
        """
        首要Agent，调用LLM判断用户输入是否与药材检索相关，选择检索或计算总价工具
        """
        llm = ChatDeepSeek(
            model="deepseek-chat",
            max_tokens=config["configurable"].get("max_tokens", 1000),
            temperature=config["configurable"].get("temperature", 0.0)  
        )
        llm_with_tools = llm.bind_tools([self.query_herbs, self.calculate_total_price], tool_choice="auto")
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}
    
    def _generate(self, state: State, config: RunnableConfig):
        """
        根据工具的返回结果，用LLM生成用户回复
        """
        llm = ChatDeepSeek(
            model="deepseek-chat",
            max_tokens=config["configurable"].get("max_tokens", 1000),
            temperature=config["configurable"].get("temperature", 0.0)  
        )
        last_message = state["messages"][-1]
        # 判断last_message是哪个工具的返回结果，选用不同的prompt
        if isinstance(last_message, ToolMessage):
            if last_message.name == "query_herbs":
                prompt_template = PromptTemplate.from_template(
                    """
                    # 任务
                    根据检索到的药材信息，生成用户回复。
                    使用markdown表格形式列举药材信息
                    # 数据库语义：
                    1. 药材名称：{{name}}
                    2. 药材价格（单位：元/克）：{{price}}
                    3. 药材功效：{{effect}}
                    4. 药材用法：{{usage}}

                    <药材信息>
                    {herbs}
                    </药材信息>
                    """
                )
                prompt = prompt_template.invoke({"herbs": last_message.content})
            elif last_message.name == "calculate_total_price":
                msg_result = json.loads(last_message.content)
                prompt_template = PromptTemplate.from_template(
                    """
                    # 任务
                    根据药材信息，生成用户回复。
                    1. 首先，用markdown表格形式列举药材信息
                    2. 然后，输出计算好的药材总价：{total_price}
                    # 数据库语义
                    1. 药材名称：{{name}}
                    2. 药材价格（单位：元/克）：{{price}}
                    3. 药材功效：{{effect}}
                    4. 药材用法：{{usage}}
                    5. 药材数量：{{quantity}}

                    <药材信息>
                    {herbs}
                    </药材信息>
                    """
                )
                prompt = prompt_template.invoke({"herbs":msg_result["results"], "total_price": msg_result["total_price"]})
        else:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "根据用户输入，生成用户回复"),
                MessagesPlaceholder(variable_name="messages")
            ]).invoke({"messages": state["messages"]})
        response = llm.invoke(prompt)
        return {"messages": [response]}

    def _build(self):
        self.add_node("agent", self._agent)
        self.add_node("generate", self._generate)
        self.add_node("tools", ToolNode(tools=[self.query_herbs, self.calculate_total_price]))
        self.add_edge(START, "agent")
        self.add_conditional_edges(
            "agent",
            tools_condition
        )
        self.add_edge("tools", "generate")
        self.add_edge("generate", END)
