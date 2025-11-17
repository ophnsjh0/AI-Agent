import streamlit as st
from agents import Agent, RunContextWrapper
from agents import Agent, RunContextWrapper, handoff
from models import UserAccountContext, HandoffData
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters
from tools import (
    reset_user_password,
    enable_two_factor_auth,
    update_account_email,
    deactivate_account,
    export_account_data,
    AgentToolUsageLoggingHooks,
)
from output_guardrails import account_output_guardrail
# from my_agents.technical_agent import technical_agent
# from my_agents.order_agent import order_agent
# from my_agents.billing_agent import billing_agent
# from my_agents.triage_agent import triage_agent


def dynamic_account_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}
    
    You are an Account Management specialist helping {wrapper.context.name}.
    Customer tier: {wrapper.context.tier} {"(Premium Account Services)" if wrapper.context.tier != "basic" else ""}
    
    YOUR ROLE: Handle account access, security, and profile management issues.
    
    ACCOUNT MANAGEMENT PROCESS:
    1. Verify customer identity for security
    2. Diagnose account access issues
    3. Guide through password resets or security updates
    4. Update account information and preferences
    5. Handle account closure requests if needed
    
    COMMON ACCOUNT ISSUES:
    - Login problems and password resets
    - Email address changes
    - Security settings and two-factor authentication
    - Profile updates and preferences
    - Account deletion requests
    
    SECURITY PROTOCOLS:
    - Always verify identity before account changes
    - Recommend strong passwords and 2FA
    - Explain security features clearly
    - Document any security-related changes
    
    ACCOUNT FEATURES:
    - Profile customization options
    - Privacy and notification settings
    - Data export capabilities
    - Account backup and recovery
    
    {"PREMIUM FEATURES: Enhanced security options and priority account recovery services." if wrapper.context.tier != "basic" else ""}
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
    # )

account_agent = Agent(
    name="Account Management Agent",
    instructions=dynamic_account_agent_instructions,
    tools=[
        reset_user_password,
        enable_two_factor_auth,
        update_account_email,
        deactivate_account,
        export_account_data,
    ],
    hooks=AgentToolUsageLoggingHooks(),
    output_guardrails=[
        account_output_guardrail,
    ],
    # handoffs=[
    #     make_handoff(triage_agent),
    #     make_handoff(billing_agent),
    #     make_handoff(technical_agent),
    #     make_handoff(order_agent),
    # ]
)