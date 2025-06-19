from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .sub_agents.earthquake_agent.agent import earthquake_agent
from .sub_agents.flood_agent.agent import flood_agent
from .sub_agents.meterologist.agent import meterologist
#from .sub_agents.stock_analyst.agent import stock_analyst
from .tools.tools import get_current_time

root_agent = Agent(
    name="weatheragent",
    model="gemini-2.0-flash",
    description="Weather Manager agent",
    instruction="""
    You are a weather manager agent that is responsible for overseeing the work of the other weather agents.

    Always delegate the task to the appropriate agent. Use your best judgement 
    to determine which agent to delegate to.

    You are responsible for delegating tasks to the following agent:
    - earthquake_agent
    - flood_agent
    - meterologist

    """,
    sub_agents=[earthquake_agent, flood_agent,meterologist],
    # tools=[
    #     AgentTool(news_analyst),
    #     get_current_time,
    # ],
)
