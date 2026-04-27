from langgraph.graph import MessagesState


class State(MessagesState):
    tool_use: list
    args_missing_funcname: str
    tool_calls_args: dict
    empty_args: list
    condition: str
    feedback :str
    web_search: str
    documents: list[str]
    question: str
    arg_parse_attempts: int