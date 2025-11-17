# my_agents/agent_graph.py

"""
에이전트 간 의존성을 한 곳에서만 정의하는 배선/그래프 모듈.

- 각 *_agent.py 파일은 자기 Agent만 정의하고
  다른 agent를 import 하지 않는다.
- 이 파일에서만 triage/technical/account/billing/order 사이 handoff를 구성한다.
"""

from agents import Agent

# triage 쪽에서 쓰던 handoff 팩토리를 재사용한다고 가정
# (triage_agent.py 안에 `make_handoff` 함수가 있다고 가정)
from my_agents.triage_agent import triage_agent, make_handoff

# leaf agents: 서로는 절대 import 하지 않음 (이 파일에서만 모아줌)
from my_agents.technical_agent import technical_agent
from my_agents.account_agent import account_agent
from my_agents.billing_agent import billing_agent
from my_agents.order_agent import order_agent


# --- Triage Agent의 handoff 구성 ---
triage_agent.handoffs = [
    # 사용자가 처음 질문했을 때 분기
    make_handoff(technical_agent),
    make_handoff(billing_agent),
    make_handoff(account_agent),
    make_handoff(order_agent),
]

# --- Technical Agent의 handoff 구성 ---
# Tech 대화 중에 계정/결제/주문/다시 Triage로 넘길 수 있도록 구성
technical_agent.handoffs = [
    # # 필요하면 다시 triage로 되돌리기
    # make_handoff(triage_agent),
    # # Tech에서 바로 다른 전문 에이전트로 handoff
    # make_handoff(billing_agent),
    # make_handoff(account_agent),
    # make_handoff(order_agent),
]

account_agent.handoffs = [
    # # 필요하면 다시 triage로 되돌리기
    # make_handoff(triage_agent),
    # # Tech에서 바로 다른 전문 에이전트로 handoff
    # make_handoff(billing_agent),
    # make_handoff(technical_agent),
    # make_handoff(order_agent),
]

billing_agent.handoffs = [
    # # 필요하면 다시 triage로 되돌리기
    # make_handoff(triage_agent),
    # # Tech에서 바로 다른 전문 에이전트로 handoff
    # make_handoff(account_agent),
    # make_handoff(technical_agent),
    # make_handoff(order_agent),
]

order_agent.handoffs = [
    # 필요하면 다시 triage로 되돌리기
    # make_handoff(triage_agent),
    # # Tech에서 바로 다른 전문 에이전트로 handoff
    # make_handoff(account_agent),
    # make_handoff(technical_agent),
    # make_handoff(billing_agent),
]

__all__ = [
    "triage_agent",
    "technical_agent",
    "account_agent",
    "billing_agent",
    "order_agent",
]
