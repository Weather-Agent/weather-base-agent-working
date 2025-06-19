from google.adk.agents import Agent
from google.adk.tools import google_search

searcher = Agent(
    name="searcher",
    model="gemini-2.0-flash",
    description="Search agent",
    instruction="""
    You are a search agent that can look up information on the web.
    
    When asked to search for something that you can't answer directly, use the google_search tool to find relevant information.
    """,
    tools=[google_search],
)
