from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph,START,END
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import ToolNode,tools_condition
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
import json
import os
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("BASE_URL")
MODEL = os.getenv("MODEL")
TAVILY_PAY_KEY=os.getenv("TAVILY_API_KEY")


class State(TypedDict):
    messages: Annotated[list,add_messages]
    
class BasicToolNode:
    def __init__(self,tools:list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}
    def __call__(self,inputs:dict):
        if messages := inputs.get("messages",[]):
            message = messages[-1]
        else:
            raise ValueError("No messages found in inputs")
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(tool_call["args"])
            outputs.append(
                content=json.dumps(tool_result),
                name = tool_call["name"],
                tool_call_id = tool_call["id"]
            )
        return {"messages":outputs}    
    
graph_builder = StateGraph(State)
memory = MemorySaver()
config = {"configurable":{"thread_id":"1"}}

# tools
tool = TavilySearchResults(api_key=TAVILY_PAY_KEY,max_results=2)
tool_node = BasicToolNode(tools=[tool])
# llm
llm = ChatOpenAI(base_url=BASE_URL,api_key=OPENAI_API_KEY,model=MODEL)
llm_with_tools = llm.bind_tools(tools=[tool])

# def route_tool(state:State):
#     if isinstance(state,list):
#         ai_message = state[-1]
#     elif messages := state.get("messages",[]):
#         ai_message = messages[-1]
#     else:
#         raise ValueError(f"No messages found in state: {state}")    
#     if hasattr(ai_message,"tool_calls") and len(ai_message.tool_calls) > 0:
#         return "tools"
#     return END

def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# graph
graph_builder.add_node("chatbot",chatbot)
tool_node = ToolNode(tools=[tool])
graph_builder.add_node("tools",tool_node)
graph_builder.add_conditional_edges("chatbot",tools_condition)
graph_builder.add_edge("tools","chatbot")
graph_builder.set_entry_point("chatbot")
graph = graph_builder.compile(checkpointer=memory)

def stream_graph_updates(user_input: str):
    # print param type
    for event in graph.stream({"messages": [("user", user_input)]},config):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)

while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        stream_graph_updates(user_input)
    except Exception as e:
        # fallback if input() is not available
        # user_input = "What do you know about LangGraph?"
        # print("User: " + user_input)
        # stream_graph_updates(user_input)
        print(e)
        break
