from agents import (
    Agent,
    output_guardrail,
    Runner,
    RunContextWrapper,
    GuardrailFunctionOutput,
)
from models import (
    TechnicalOutputGuardRailOutput,
    AccountOutputGuardRailOutput,
    OrderlOutputGuardRailOutput,
    BillingOutputGuardRailOutput,
    UserAccountContext,
)


technical_output_guardrail_agent = Agent(
    name="Technical Support Guardrail",
    instructions="""
    Analyze the technical support response to check if it inappropriately contains:
    
    - Billing information (payments, refunds, charges, subscriptions)
    - Order information (shipping, tracking, delivery, returns)
    - Account management info (passwords, email changes, account settings)
    
    Technical agents should ONLY provide technical troubleshooting, diagnostics, and product support.
    Return true for any field that contains inappropriate content for a technical support response.
    """,
    output_type=TechnicalOutputGuardRailOutput,
)

account_output_guardrail_agent = Agent(
    name="Account Support Guardrail",
    instructions="""
    Analyze the Account support response to check if it inappropriately contains:
    
    - Billing information (payments, refunds, charges, subscriptions)
    - Order information (shipping, tracking, delivery, returns)
    - Technical management info (troubleshooting, diagnostics, product support)
    
    Account agents should ONLY provide account passwords, email changess, and account settings.
    Return true for any field that contains inappropriate content for a account support response.
    """,
    output_type=AccountOutputGuardRailOutput,
)

order_output_guardrail_agent = Agent(
    name="Order Support Guardrail",
    instructions="""
    Analyze the order support response to check if it inappropriately contains:
    
    - Billing information (payments, refunds, charges, subscriptions)
    - Account management info (passwords, email changes, account settings)
    - Technical management info (troubleshooting, diagnostics, product support)
    
    Order agents should ONLY provide Order shipping, tracking, delivery and returns.
    Return true for any field that contains inappropriate content for a order support response.
    """,
    output_type=OrderlOutputGuardRailOutput,
)

billing_output_guardrail_agent = Agent(
    name="Billing Support Guardrail",
    instructions="""
    Analyze the billing support response to check if it inappropriately contains:
    
    - Order information (shipping, tracking, delivery, returns)
    - Account management info (passwords, email changes, account settings)
    - Technical management info (troubleshooting, diagnostics, product support)
    
    Billing agents should ONLY provide billing payments, refunds, charges and subscriptions.
    Return true for any field that contains inappropriate content for a billing support response.
    """,
    output_type=BillingOutputGuardRailOutput,
)



@output_guardrail
async def technical_output_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent,
    output: str,
):
    result = await Runner.run(
        technical_output_guardrail_agent,
        output,
        context=wrapper.context,
    )

    validation = result.final_output

    triggered = (
        validation.contains_off_topic
        or validation.contains_billing_data
        or validation.contains_account_data
        or validation.contains_order_data
    )

    return GuardrailFunctionOutput(
        output_info=validation,
        tripwire_triggered=triggered,
    )
    
@output_guardrail
async def account_output_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent,
    output: str,
):
    result = await Runner.run(
        account_output_guardrail_agent,
        output,
        context=wrapper.context,
    )

    validation = result.final_output

    triggered = (
        validation.contains_off_topic
        or validation.contains_billing_data
        or validation.contains_technical_data
        or validation.contains_order_data
    )

    return GuardrailFunctionOutput(
        output_info=validation,
        tripwire_triggered=triggered,
    )

@output_guardrail
async def order_output_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent,
    output: str,
):
    result = await Runner.run(
        order_output_guardrail_agent,
        output,
        context=wrapper.context,
    )

    validation = result.final_output

    triggered = (
        validation.contains_off_topic
        or validation.contains_billing_data
        or validation.contains_account_data
        or validation.contains_technical_data
    )

    return GuardrailFunctionOutput(
        output_info=validation,
        tripwire_triggered=triggered,
    )

@output_guardrail
async def billing_output_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent,
    output: str,
):
    result = await Runner.run(
        billing_output_guardrail_agent,
        output,
        context=wrapper.context,
    )

    validation = result.final_output

    triggered = (
        validation.contains_off_topic
        or validation.contains_account_data
        or validation.contains_technical_data
        or validation.contains_order_data
    )

    return GuardrailFunctionOutput(
        output_info=validation,
        tripwire_triggered=triggered,
    )