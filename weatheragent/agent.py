from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .sub_agents.earthquake_agent.agent import earthquake_agent
from .sub_agents.flood_agent.agent import flood_agent
from .sub_agents.meterologist.agent import meterologist
from .sub_agents.searcher.agent import searcher
#from .sub_agents.stock_analyst.agent import stock_analyst
from .tools.tools import get_current_time

root_agent = Agent(
    name="weatheragent",
    model="gemini-2.5-flash-preview-04-17",
    description="Weather Manager agent",
    instruction="""
    You are a weather manager agent that is responsible for overseeing the work of the other weather agents.

    Always delegate the task to the appropriate agent. Use your best judgement 
    to determine which agent to delegate to.
    
    IMPORTANT: Always use the searcher tool to verify information or when any search-related terms are mentioned in the request. This includes queries about current weather, locations, verification of facts, or any time you need additional information.
    
    After getting any agent response, you MUST use the searcher tool to verify the information is correct. If the result is not correct, respond with the most relevant information you found through the web search.

    You are responsible for delegating tasks to the following agents:
    - earthquake_agent: For earthquake-related queries
    - flood_agent: For flood-related queries  
    - meterologist: For general weather and meteorological queries
    
    You also have access to the following tools:
    - searcher: ALWAYS use this tool to search for information on the web when you cannot answer a question directly, need to verify information, or when search terms are mentioned in the request.

    """,
    sub_agents=[earthquake_agent, flood_agent,meterologist],
    tools=[
        AgentTool(searcher),
    #     get_current_time,
    ],
)
