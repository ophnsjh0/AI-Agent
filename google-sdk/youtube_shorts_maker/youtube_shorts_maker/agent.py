from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm
from .sub_agents.content_planner.agent import content_planner_agent
from .sub_agents.asset_generator.agent import asset_generator_agent
from .sub_agents.video_assembler.agent import video_assembler_agent
from .prompt import SHORTS_PRODUCER_DESCRIPTION, SHORTS_PRODUCER_PROMPT

# MODEL = LiteLlm(model="openai/gpt-4o")
# MODEL = LiteLlm(model="openai/gpt-5.2")


shorts_producer_agent = Agent(
    name="ShortsProducerAgent",
    # model=MODEL,
    # model="gemini-3-pro-preview",
    model="gemini-2.5-flash", 
    description=SHORTS_PRODUCER_DESCRIPTION,
    instruction=SHORTS_PRODUCER_PROMPT,
    tools=[
        AgentTool(agent=content_planner_agent),
        AgentTool(agent=asset_generator_agent),
        AgentTool(agent=video_assembler_agent),
    ],
)

root_agent = shorts_producer_agent