import streamlit as st
from agents import Agent, RunContextWrapper, handoff
from models import UserAccountContext, HandoffData
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters
from tools import (
    run_diagnostic_check,
    provide_troubleshooting_steps,
    escalate_to_engineering,
    AgentToolUsageLoggingHooks,
)
from output_guardrails import technical_output_guardrail
# from my_agents.account_agent import account_agent
# from my_agents.order_agent import order_agent
# from my_agents.billing_agent import billing_agent
# from my_agents.triage_agent import triage_agent


def dynamic_technical_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}
    
    You are a Technical Support specialist helping {wrapper.context.name}.
    Customer tier: {wrapper.context.tier} {"(Premium Support)" if wrapper.context.tier != "basic" else ""}
    
    YOUR ROLE: Solve technical issues with our products and services.
    
    TECHNICAL SUPPORT PROCESS:
    1. Gather specific details about the technical issue
    2. Ask for error messages, steps to reproduce, system info
    3. Provide step-by-step troubleshooting solutions
    4. Test solutions with the customer
    5. Escalate to engineering if needed (especially for premium customers)
    
    INFORMATION TO COLLECT:
    - What product/feature they're using
    - Exact error message (if any)
    - Operating system and browser
    - Steps they took before the issue occurred
    - What they've already tried
    
    TROUBLESHOOTING APPROACH:
    - Start with simple solutions first
    - Be patient and explain technical steps clearly
    - Confirm each step works before moving to the next
    - Document solutions for future reference
    
    {"PREMIUM PRIORITY: Offer direct escalation to senior engineers if standard solutions don't work." if wrapper.context.tier != "basic" else ""}
    """

# def handle_handoff(
#     wrapper : RunContextWrapper[UserAccountContext],
#     input_data: HandoffData
# ):
#     with st.sidebar:
#         st.write(
#             f"""
#             Handing off to {input_data.to_agent_name}
#             Reason: {input_data.reason}
#             Issue Type: {input_data.issue_type}
#             Description: {input_data.issue_description}
#         """
#         )
    

# def make_handoff(agent):
#     return handoff(
#         agent=agent,
#         on_handoff=handle_handoff,
#         input_type=HandoffData,
#         input_filter=handoff_filters.remove_all_tools,
#     )

technical_agent = Agent(
    name="Technical Support Agent",
    instructions=dynamic_technical_agent_instructions,
    tools=[
        run_diagnostic_check,
        provide_troubleshooting_steps,
        escalate_to_engineering,
    ],
    hooks=AgentToolUsageLoggingHooks(),
       output_guardrails=[
        technical_output_guardrail,
    ],
    
    # handoffs=[
    #     make_handoff(triage_agent),
    #     make_handoff(billing_agent),
    #     make_handoff(account_agent),
    #     make_handoff(order_agent),
    # ]
)