from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv
import os
load_dotenv()

api_key=os.getenv("TAVILY_API_KEY")

tool = TavilySearchResults(api_key=api_key,max_results=2)
tools = [tool]
rs= tool.invoke("韩国发布戒严令")
print(rs)