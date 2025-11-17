from pydantic import BaseModel

class UserAccountContext(BaseModel):
    customer_id: int
    name: str
    tier: str = "basic"  # premium entreprise
    email: str

class InputGuardRailOutput(BaseModel):

    is_off_topic: bool
    reason: str
    
class HandoffData(BaseModel):
    to_agent_name: str
    issue_type: str
    issue_description: str
    reason: str

class TechnicalOutputGuardRailOutput(BaseModel): # Agent별로 생성 필요 

    contains_off_topic: bool
    contains_billing_data: bool
    contains_account_data: bool
    contains_order_data: bool
    reason: str
    
class AccountOutputGuardRailOutput(BaseModel): # Agent별로 생성 필요 

    contains_off_topic: bool
    contains_billing_data: bool
    contains_technical_data: bool
    contains_order_data: bool
    reason: str
    
class OrderlOutputGuardRailOutput(BaseModel): # Agent별로 생성 필요 

    contains_off_topic: bool
    contains_billing_data: bool
    contains_account_data: bool
    contains_technical_data: bool
    reason: str
    
class BillingOutputGuardRailOutput(BaseModel): # Agent별로 생성 필요 

    contains_off_topic: bool
    contains_technical_data: bool
    contains_account_data: bool
    contains_order_data: bool
    reason: str