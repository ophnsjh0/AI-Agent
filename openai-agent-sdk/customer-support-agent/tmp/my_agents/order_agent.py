import streamlit as st
from agents import Agent, RunContextWrapper
from agents import Agent, RunContextWrapper, handoff
from models import UserAccountContext, HandoffData
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters
from tools import (
    lookup_order_status,
    initiate_return_process,
    schedule_redelivery,
    expedite_shipping,
    AgentToolUsageLoggingHooks,
)
from output_guardrails import order_output_guardrail
# from my_agents.account_agent import account_agent
# from my_agents.technical_agent import technical_agent
# from my_agents.billing_agent import billing_agent
# from my_agents.triage_agent import triage_agent

def dynamic_order_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}
    
    You are an Order Management specialist helping {wrapper.context.name}.
    Customer tier: {wrapper.context.tier} {"(Premium Shipping)" if wrapper.context.tier != "basic" else ""}
    
    YOUR ROLE: Handle order status, shipping, returns, and delivery issues.
    
    ORDER MANAGEMENT PROCESS:
    1. Look up order details by order number
    2. Provide current status and tracking information
    3. Resolve shipping or delivery issues
    4. Process returns and exchanges
    5. Update shipping preferences if needed
    
    ORDER INFORMATION TO PROVIDE:
    - Current order status (processing, shipped, delivered)
    - Tracking numbers and carrier information
    - Expected delivery dates
    - Return/exchange options and policies
    
    RETURN POLICY:
    - 30-day return window for most items
    - Free returns for premium customers
    - Exchange options available
    - Refund processing time: 3-5 business days
    
    {"PREMIUM PERKS: Free expedited shipping and returns, priority processing." if wrapper.context.tier != "basic" else ""}
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


order_agent = Agent(
    name="Order Management Agent",
    instructions=dynamic_order_agent_instructions,
    tools=[
        lookup_order_status,
        initiate_return_process,
        schedule_redelivery,
        expedite_shipping,
    ],
    hooks=AgentToolUsageLoggingHooks(),
        output_guardrails=[
        order_output_guardrail,
    ],
    # handoffs=[
    #     make_handoff(triage_agent),
    #     make_handoff(billing_agent),
    #     make_handoff(account_agent),
    #     make_handoff(technical_agent),
    # ]
)