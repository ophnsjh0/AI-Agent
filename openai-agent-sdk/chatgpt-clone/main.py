import dotenv

dotenv.load_dotenv()
import re
from openai import OpenAI
import asyncio
import base64
import streamlit as st
from agents import (Agent, Runner, SQLiteSession, WebSearchTool, FileSearchTool, ImageGenerationTool, CodeInterpreterTool, HostedMCPTool,)
from agents.mcp.server import MCPServerStdio

client = OpenAI()

VECTOR_STORE_ID = "vs_6901a0235f1881918cea7adbd1d6cef1"

DEFAULT_MODEL = "gpt-5-mini"

FINANCE_KEYWORDS = [
    r"\b(stock|stocks|etf|price|prices|ticker|ohlc|chart|dividend|yield|pe|eps)\b",
    r"\b(주가|주식|ETF|가격|시가|종가|배당|수익률|티커)\b",
]
TICKER_LIKE = r"\b[A-Z]{1,5}\b"  # 간단한 티커 패턴 (AAPL, MSFT 등)

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history",
        "chat-gpt-clone-memory.db",
    )
session = st.session_state["session"]

def is_finance_query(msg: str) -> bool:
    if not isinstance(msg, str):
        return False
    msg_low = msg.lower()
    if re.search(TICKER_LIKE, msg):
        return True
    return any(re.search(p, msg_low) for p in FINANCE_KEYWORDS)

async def paint_history():
    messages = await session.get_items()

    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    content = message["content"]
                    if isinstance(content, str):
                        st.write(content)
                    elif isinstance(content, list):
                        for part in content:
                            if "image_url" in part:
                                st.image(part["image_url"])

                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"].replace("$", "\$"))
        if "type" in message:
            message_type = message["type"]
            if message_type == "web_search_call":
                with st.chat_message("ai"):
                    st.write("🔍 Searched the web...")
            elif message_type == "file_search_call":
                with st.chat_message("ai"):
                    st.write("🗂️ Searched your files...")
            elif message_type == "image_generation_call":
                image = base64.b64decode(message["result"])
                with st.chat_message("ai"):
                    st.image(image)
            elif message_type == "code_interpreter_call":
                with st.chat_message("ai"):
                    st.code(message["code"])
            elif message_type == "mcp_list_tools":
                with st.chat_message("ai"):
                    st.write(f"Listed {message['server_label']}'s tools")
            elif message_type == "mcp_call":
                with st.chat_message("ai"):
                    st.write(
                        f"Called {message['server_label']}'s {message['name']} with args {message['arguments']}"
                    )


def update_status(status_container, event):

    status_messages = {
        "response.web_search_call.completed": ("✅ Web search completed.", "complete"),
        "response.web_search_call.in_progress": (
            "🔍 Starting web search...",
            "running",
        ),
        "response.web_search_call.searching": (
            "🔍 Web search in progress...",
            "running",
        ),
        "response.file_search_call.completed": (
            "✅ File search completed.",
            "complete",
        ),
        "response.file_search_call.in_progress": (
            "🗂️ Starting file search...",
            "running",
        ),
        "response.file_search_call.searching": (
            "🗂️ File search in progress...",
            "running",
        ),
        "response.image_generation_call.generating": (
            "🎨 Drawing image...",
            "running",
        ),
        "response.image_generation_call.in_progress": (
            "🎨 Drawing image...",
            "running",
        ),
        "response.code_interpreter_call_code.done": (
            "🤖 Ran code.",
            "complete",
        ),
        "response.code_interpreter_call.completed": (
            "🤖 Ran code.",
            "complete",
        ),
        "response.code_interpreter_call.in_progress": (
            "🤖 Running code...",
            "complete",
        ),
        "response.code_interpreter_call.interpreting": (
            "🤖 Running code...",
            "complete",
        ),
        "response.mcp_call.completed": (
            "⚒️ Called MCP tool",
            "complete",
        ),
        "response.mcp_call.failed": (
            "⚒️ Error calling MCP tool",
            "complete",
        ),
        "response.mcp_call.in_progress": (
            "⚒️ Calling MCP tool...",
            "running",
        ),
        "response.mcp_list_tools.completed": (
            "⚒️ Listed MCP tools",
            "complete",
        ),
        "response.mcp_list_tools.failed": (
            "⚒️ Error listing MCP tools",
            "complete",
        ),
        "response.mcp_list_tools.in_progress": (
            "⚒️ Listing MCP tools",
            "running",
        ),
        "response.completed": (" ", "complete"),
    }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)

asyncio.run(paint_history())

async def run_agent(message):
    use_mcp_fin = is_finance_query(message)

    # yfinance MCP는 "필요할 때만" 띄운다
    yfinance_server = None
    if use_mcp_fin:
        yfinance_server = MCPServerStdio(
            params={
                "command": "uvx",
                "args": ["mcp-yahoo-finance"],
            },
            cache_tools_list=True,
            # 아래 2개 인자가 라이브러리에 있는 경우에만 유효 (없어도 안전)
            # startup_timeout=20.0,   # 서버 부팅 대기 시간 (기본 5s → 20s)
            # request_timeout=30.0,   # 요청 응답 대기 시간 (기본 5s → 30s)
        )

    async def build_agent(mcp_ctx=None):
        return Agent(
            mcp_servers=[mcp_ctx] if mcp_ctx else [],
            name="ChatGPT Clone",
            instructions="""
            You are a helpful assistant.

            You have access to the followign tools:
                - Web Search Tool: Use this when the user asks a questions that isn't in your training data. Use this tool when the users asks about current or future events, when you think you don't know the answer, try searching for it in the web first.
                - File Search Tool: Use this tool when the user asks a question about facts related to themselves. Or when they ask questions about specific files.
                - Code Interpreter Tool: Use this tool when you need to write and run code to answer the user's question.
            """,
            tools=[
                WebSearchTool(),
                FileSearchTool(
                    vector_store_ids=[VECTOR_STORE_ID],
                    max_num_results=3,
                ),
                ImageGenerationTool(
                    tool_config={
                        "type": "image_generation",
                        "quality": "high",
                        "output_format": "jpeg",
                        "partial_images": 1,
                    }
                ),
                CodeInterpreterTool(
                    tool_config={
                        "type": "code_interpreter",
                        "container": {"type": "auto"},
                    }
                ),
                HostedMCPTool(
                    tool_config={
                        "server_url": "https://mcp.context7.com/mcp",
                        "type": "mcp",
                        "server_label": "Context7",
                        "server_description": "Use this to get the docs from software projects.",
                        "require_approval": "never",
                    }
                ),
            ],
        )

    # --- Streamlit UI 영역 그대로 ---
    with st.chat_message("ai"):
        status_container = st.status("⏳", expanded=False)
        code_placeholder = st.empty()
        image_placeholder = st.empty()
        text_placeholder = st.empty()
        response = ""
        code_response = ""

        st.session_state["code_placeholder"] = code_placeholder
        st.session_state["image_placeholder"] = image_placeholder
        st.session_state["text_placeholder"] = text_placeholder

        # --- [핵심] yfinance MCP를 띄우되, 실패/지연 시 우아하게 폴백 ---
        agent = None
        if yfinance_server:
            try:
                # Python 3.11+: asyncio.timeout / 3.10 이하면 wait_for 사용
                try:
                    # 선호
                    from asyncio import timeout
                    async with timeout(25):  # 전체 부팅+tool-list 25초 제한
                        async with yfinance_server:
                            agent = await build_agent(yfinance_server)
                            # 아래 스트리밍 실행 (yfinance 포함)
                            stream = Runner.run_streamed(agent, message, session=session)
                            async for event in stream.stream_events():
                                if event.type == "raw_response_event":
                                    update_status(status_container, event.data.type)
                                    if event.data.type == "response.output_text.delta":
                                        response += event.data.delta
                                        text_placeholder.write(response.replace("$", "\$"))
                                    if event.data.type == "response.code_interpreter_call_code.delta":
                                        code_response += event.data.delta
                                        code_placeholder.code(code_response)
                                    elif event.data.type == "response.image_generation_call.partial_image":
                                        img = base64.b64decode(event.data.partial_image_b64)
                                        image_placeholder.image(img)
                            return
                except ImportError:
                    # Python 3.10 호환: wait_for
                    import asyncio as _asyncio
                    async def _boot_and_stream():
                        async with yfinance_server:
                            _agent = await build_agent(yfinance_server)
                            _stream = Runner.run_streamed(_agent, message, session=session)
                            async for event in _stream.stream_events():
                                if event.type == "raw_response_event":
                                    update_status(status_container, event.data.type)
                                    if event.data.type == "response.output_text.delta":
                                        nonlocal response
                                        response += event.data.delta
                                        text_placeholder.write(response.replace("$", "\$"))
                                    if event.data.type == "response.code_interpreter_call_code.delta":
                                        nonlocal code_response
                                        code_response += event.data.delta
                                        code_placeholder.code(code_response)
                                    elif event.data.type == "response.image_generation_call.partial_image":
                                        img = base64.b64decode(event.data.partial_image_b64)
                                        image_placeholder.image(img)

                    await _asyncio.wait_for(_boot_and_stream(), timeout=25)
                    return

            except Exception as e:
                # MCP가 뜨지 않거나, 툴 리스트가 안 오거나, 요청이 느려 터지면 폴백
                status_container.update(
                    label=f"⚒️ yfinance MCP 비활성(사유: {type(e).__name__}) — 일반 에이전트로 계속합니다.",
                    state="complete",
                )

        # 여기로 오면: (1) 애초에 금융 질의가 아니거나 (2) MCP가 실패한 경우
        agent = await build_agent(None)
        stream = Runner.run_streamed(agent, message, session=session)
        async for event in stream.stream_events():
            if event.type == "raw_response_event":
                update_status(status_container, event.data.type)
                if event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response.replace("$", "\$"))
                if event.data.type == "response.code_interpreter_call_code.delta":
                    code_response += event.data.delta
                    code_placeholder.code(code_response)
                elif event.data.type == "response.image_generation_call.partial_image":
                    img = base64.b64decode(event.data.partial_image_b64)
                    image_placeholder.image(img)



prompt = st.chat_input(
    "Write a message for your assistant",
    accept_file=True,
    file_type=[
        "txt",
        "jpg",
        "jpeg",
        "png",
    ],
)

if prompt:

    if "code_placeholder" in st.session_state:
        st.session_state["code_placeholder"].empty()
    if "image_placeholder" in st.session_state:
        st.session_state["image_placeholder"].empty()
    if "text_placeholder" in st.session_state:
        st.session_state["text_placeholder"].empty()

    for file in prompt.files:
        if file.type.startswith("text/"):
            with st.chat_message("ai"):
                with st.status("⏳ Uploading file...") as status:
                    uploaded_file = client.files.create(
                        file=(file.name, file.getvalue()),
                        purpose="user_data",
                    )
                    status.update(label="⏳ Attaching file...")
                    client.vector_stores.files.create(
                        vector_store_id=VECTOR_STORE_ID,
                        file_id=uploaded_file.id,
                    )
                    status.update(label="✅ File uploaded", state="complete")
        elif file.type.startswith("image/"):
            with st.status("⏳ Uploading image...") as status:
                file_bytes = file.getvalue()
                base64_data = base64.b64encode(file_bytes).decode("utf-8")
                data_uri = f"data:{file.type};base64,{base64_data}"
                asyncio.run(
                    session.add_items(
                        [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_image",
                                        "detail": "auto",
                                        "image_url": data_uri,
                                    }
                                ],
                            }
                        ]
                    )
                )
                status.update(label="✅ Image uploaded", state="complete")
            with st.chat_message("human"):
                st.image(data_uri)

    if prompt.text:
        with st.chat_message("human"):
            st.write(prompt.text)
        asyncio.run(run_agent(prompt.text))


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))