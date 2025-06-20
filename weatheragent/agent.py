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
    After getting the agent response search the web using the searcher tool to get check the information is correct or not. If the result is not corrent response with the most relevant information you found through the web.

    You are responsible for delegating tasks to the following agent:
    - earthquake_agent
    - flood_agent
    - meterologist
     You also have access to the following tools:
    - searcher: Use this tool to search for information on the web when you cannot answer a question directly or you are ordered to do so. like getting the number of cities in a country, or the current weather in a city.

    """,
    sub_agents=[earthquake_agent, flood_agent,meterologist],
    tools=[
        AgentTool(searcher),
    #     get_current_time,
    ],
)
