from langchain_community.tools.tavily_search import TavilySearchResults

def generate_tavily():
    return TavilySearchResults(max_results=3)