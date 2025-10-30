status_messages = {
        "response.web_search_call.completed": ("✅ Web search completed.", "complete"),
        "response.web_search_call.in_progress": ("🔍 Starting web search...","running",),
        "response.web_search_call.searching": ("🔍 Web search in progress...","running",),
        "response.completed": (" ", "complete"),
    }


label, state = status_messages["response.web_search_call.completed"]
    
print(label)
print(state)