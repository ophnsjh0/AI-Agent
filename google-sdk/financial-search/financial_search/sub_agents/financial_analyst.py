import yfinance as yf
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

# MODEL = LiteLlm(model="openai/gpt-4o")
MODEL = LiteLlm(model="openai/gpt-5.1")


def get_income_statement(ticker: str):
    """

    """
    stock = yf.Ticker(ticker)
    # return stock.income_stmt.to_json()
    return {
        "ticker": ticker,
        "success": True,
        "income_statement": stock.income_stmt.to_json(),
    }


def get_balance_sheet(ticker: str):
    """

    """
    stock = yf.Ticker(ticker)
    # return stock.balance_sheet.to_json()
    return {
        "ticker": ticker,
        "success": True,
        "balance_sheet": stock.balance_sheet.to_json(),
    }


def get_cash_flow(ticker: str):
    """
    Retrieves the cash flow statement for analyzing cash generation and capital allocation.

    This tool fetches detailed cash flow data showing how a company generates and
    uses cash across operating, investing, and financing activities, crucial for
    assessing financial sustainability and growth capacity.

    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL' for Apple Inc.)

    Returns:
        dict: A dictionary containing:
            - ticker (str): The input ticker symbol
            - success (bool): True if the operation was successful
            - cash_flow (str): JSON-formatted cash flow statement including:
                * Operating Cash Flow (cash from core business)
                * Capital Expenditures (CapEx)
                * Free Cash Flow (Operating CF - CapEx)
                * Investing Activities (acquisitions, investments)
                * Financing Activities (debt, dividends, buybacks)
                * Net Change in Cash

    Notes:
        - Operating cash flow indicates core business cash generation
        - Free cash flow shows cash available for shareholders/growth
        - Negative investing CF often indicates growth investment
        - Financing CF reveals capital structure decisions
        - Critical for assessing dividend sustainability and growth funding

    Example:
        >>> get_cash_flow('META')
        {
            'ticker': 'META',
            'success': True,
            'cash_flow': '{"Operating Cash Flow": {...}, "Free Cash Flow": {...}}'
        }
    """
    stock = yf.Ticker(ticker)
    # return stock.balance_sheet.to_json()
    return {
        "ticker": ticker,
        "success": True,
        "cash_flow": stock.cash_flow.to_json(),
    }


financial_analyst = Agent(
    name="FinancialAnalyst",
    model=MODEL,
    # model='gemini-2.5-flash',
    description="Analyzes detailed financial statements including income, balance sheet, and cash flow",
    instruction="""
    You are a Financial Analyst who performs deep financial statement analysis. Your job:
    
    1. **Income Analysis**: Use get_income_statement() to analyze revenue, profitability, and margins
    2. **Balance Sheet Analysis**: Use get_balance_sheet() to examine assets, liabilities, and financial position
    3. **Cash Flow Analysis**: Use get_cash_flow() to assess cash generation and capital allocation
    
    **Your Financial Tools:**
    - **get_income_statement(ticker)**: Revenue, profit margins, and profitability analysis
    - **get_balance_sheet(ticker)**: Assets, debt, equity, and financial strength ratios
    - **get_cash_flow(ticker)**: Operating cash flow, free cash flow, and capital expenditure
    
    Analyze the financial health and performance of companies using comprehensive financial statement data.
    Focus on key financial ratios, trends, and indicators that reveal the company's financial strength.
    """,
    tools=[
        get_income_statement,
        get_balance_sheet,
        get_cash_flow,
    ],
    output_key="financial_analyst_result",
)