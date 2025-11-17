import streamlit as st
from agents import Agent, RunContextWrapper
from agents import Agent, RunContextWrapper, handoff
from models import UserAccountContext, HandoffData
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters
from tools import (
    lookup_billing_history,
    process_refund_request,
    update_payment_method,
    apply_billing_credit,
    AgentToolUsageLoggingHooks,
)
from output_guardrails import billing_output_guardrail
# from my_agents.account_agent import account_agent
# from my_agents.order_agent import order_agent
# from my_agents.technical_agent import technical_agent
# from my_agents.triage_agent import triage_agent


def dynamic_billing_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}
    
    You are a Billing Support specialist helping {wrapper.context.name}.
    Customer tier: {wrapper.context.tier} {"(Premium Billing Support)" if wrapper.context.tier != "basic" else ""}
    
    YOUR ROLE: Resolve billing, payment, and subscription issues.
    
    BILLING SUPPORT PROCESS:
    1. Verify account details and billing information
    2. Identify the specific billing issue
    3. Check payment history and subscription status
    4. Provide clear solutions and next steps
    5. Process refunds/adjustments when appropriate
    
    COMMON BILLING ISSUES:
    - Failed payments or declined cards
    - Unexpected charges or billing disputes
    - Subscription changes or cancellations
    - Refund requests
    - Invoice questions
    
    BILLING POLICIES:
    - Refunds available within 30 days for most services
    - Premium customers get priority processing
    - Always explain charges clearly
    - Offer payment plan options when helpful
    
    {"PREMIUM BENEFITS: Fast-track refund processing and flexible payment options available." if wrapper.context.tier != "basic" else ""}
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

billing_agent = Agent(
    name="Billing Support Agent",
    instructions=dynamic_billing_agent_instructions,
    tools=[
        lookup_billing_history,
        process_refund_request,
        update_payment_method,
        apply_billing_credit,
    ],
    hooks=AgentToolUsageLoggingHooks(),
        output_guardrails=[
        billing_output_guardrail,
    ],
    # handoffs=[
    #     make_handoff(triage_agent),
    #     make_handoff(technical_agent),
    #     make_handoff(account_agent),
    #     make_handoff(order_agent),
    # ]
)