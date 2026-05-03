
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_ollama import ChatOllama
from langgraph.types import interrupt

from lang_graph.main.about_file import dynamic_functions_google_schema
from lang_graph.main.state import State
from lang_graph.main.config import initial_input
from lang_graph.main.tools import querys
from langgraph.graph import END

class SubGraph:
    def __init__(self, graph_instance, tool):
        self.graph = graph_instance
        self.tool = tool
        print("-----------------SubGraph tool-------------------------")
        print(tool)
        print("------------------------------------------")
        
        self.llm = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
        ).bind_tools(tools=[tool])
        self.llm_with_no_tool = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
        )
        self.sys_msg = SystemMessage(
            content="""
                You are an AI Agent equipped with various tools to help you complete tasks. 
                Please Follow below steps to think, and do the decision in the end.
                1. If you can directly answer the question, do not generate a tool message.
                2. You should automatically determine whether these tools are needed based on the user's request. 
                3. When calling a tool, first extract arguments from the user's natural language.
                4. You MAY normalize aliases into API-friendly values (e.g., "台北" -> "TPE", "東京" -> "NRT").
                5. If an argument is truly missing from the user's input, do not guess; ask a short clarifying question.
                6. Allowed default: if a single flight date is provided, treat it as both start and end date.
                
                Here are the tools you have access to:
                    Flight Status Query: For retrieving real-time flight information.
                    Weather Query: For executing weather-related queries.
            """)
        # 1. Determine if you can directly answer the user's question. just give an answer. and don't do above steps.
        # 2. If you cannot, decide which tool can most effectively help you complete the task.
        # 3. Only generate the corresponding tool message when necessary.
        # 4. You have to check every ToolCall argument is missing or not, if missing you should ask the user for the missing arguments.and don't according the tool call result to generate response.
        # 5. Remember to always provide the best answer based on the user's needs and avoid unnecessary tool calls.
        self.sys_args_msg = SystemMessage(
            content="""
                You are an AI Agent and response short and precise messages to the user.
                If user query is about weather :check get_weather_info argument
                If user query is about flight :check get_flight_info argument
                Here are the tools Argument have to be set:
                    get_weather_info: location, date, days
                    get_flight_info: DepartureAirportID, ArrivalAirportID, ScheduleStartDate, ScheduleEndDate
                     
                If all arguments key have value,you shoud regenerate a new complete query as output with "Argument is complete" in the end.
                Or    
                Please According to the missing arguments for the tool call.
                And follow below example to ask user for the missing arguments.Don't Give any code, just give a question.
                Example:
                    Please provide the day for the weather query.
                    Please provide the destination for the flight query.
                    
                    
            """)
        # Current arguments: {"date": "2024-12-05"}
        
        
        self.querys = {tool.__name__: querys[tool.__name__]}
        
    def human_feedback(self, state: State):
        """
        如果有缺少或沒缺少回傳模板並取得使用者回饋
        """
        try:
            # print("human_feedback----------------------------\n", state)
            print("human_feedback----------------------------\n")
            state["args_missing_funcname"] = state.get("args_missing_funcname", "")
            state["tool_calls_args"] = state.get("tool_calls_args", {})
            state["empty_args"] = state.get("empty_args", [])
            state["tool_use"] = state.get("tool_use", [])
            state["condition"] = state.get("condition", "") 
            output = ""

            # One-shot: if caller already provided a query (feedback) for this subgraph,
            # skip the template and proceed to get_user_input -> assistant.
            # IMPORTANT: do NOT skip when a ToolMessage is pending – it must be processed
            # so that condition is set to "next_graph_or_end" and the graph ends correctly.
            _last_msg = (state.get("messages") or [None])[-1]
            if (
                state.get("condition") == "direct_input"
                and str(state.get("feedback", "")).strip()
                and not isinstance(_last_msg, ToolMessage)
            ):
                return {
                    "messages": [AIMessage(content="")],
                    "tool_use": state["tool_use"],
                    "args_missing_funcname": state["args_missing_funcname"],
                    "tool_calls_args": state["tool_calls_args"],
                    "empty_args": state["empty_args"],
                    "condition": "direct_input",
                }
            # 詢問補參數的模板
            if state["args_missing_funcname"] != "" and state["condition"] == "lack_args" and state["empty_args"] != []:
                message = f"{state['empty_args']}，以上這些是空值的參數，請幫我想想該怎麼用親切的語氣，跟使用者說「這些參數為空，請幫我填入」。只需要回答「給使用者的句子」，其餘的不需要，請不要回答。"
                question = HumanMessage(content=message)
                sys_prompt = SystemMessage(content=
                    f"""
                    請幫我使用繁體中文回答，不要有任何的簡體中文。請仔細想想之後認真回答有獎勵，不認真回答我就死給你看。
                    你是一個協助用戶處理缺少參數的系統。根據提供的缺少參數關鍵字清單，請回應一條訊息，指明缺少哪些參數。
                    """
                )
                response = self.llm_with_no_tool.invoke([sys_prompt, question])
                print("response", response)
                output = AIMessage(content=f"{response.content}")
                state["condition"] = "parse_args"
                # return self.handle_tool_use(state, missing_message=response.content)
            # 回傳tool call的結果
            elif state.get("messages") and isinstance(state["messages"][-1], ToolMessage):
                print("is_toolmessage", state["messages"][-1])
                # state["tool_use"].append(statemessages.tool_calls[-1]["name"])
                state["condition"] = "next_graph_or_end"
                last_tool_message = state["messages"][-1]
                tool_name = getattr(last_tool_message, "name", "") or ""
                tool_func_data = last_tool_message.content
                # If tool returned an error-like payload, respond deterministically instead of
                # asking the LLM to "summarize" (which often produces unrelated greetings).
                tool_text = str(tool_func_data).strip()
                if "Error Response" in tool_text or tool_text.lower().startswith("error"):
                    if tool_name == "weather_info":
                        output = AIMessage(
                            content=(
                                "天氣查詢服務回傳錯誤（Error Response）。\n"
                                "可能原因：後端 tools service（/weather/）暫時不可用、參數不被接受，或 OpenWeather API 沒有回應。\n"
                                "你可以先改用：地點（例如 台北/東京）、日期（YYYY-MM-DD）、天數（1~5）再試一次。"
                            )
                        )
                    elif tool_name == "flight_info":
                        output = AIMessage(
                            content=(
                                "航班查詢服務回傳錯誤（Error Response）。\n"
                                "可能原因：後端 tools service（/flightinformation/）暫時不可用、參數不被接受，或資料源沒有回應。\n"
                                "你可以先改用：`RMQ` → `NRT`，日期 `2026-03-20` 再試一次；若仍失敗，我可以幫你一起看 tools service 的回應內容。"
                            )
                        )
                    else:
                        output = AIMessage(
                            content=(
                                "工具服務回傳錯誤（Error Response）。\n"
                                "可能原因：後端 tools service 暫時不可用、參數不被接受，或資料源沒有回應。"
                            )
                        )
                elif not tool_text:
                    if tool_name == "flight_info":
                        output = AIMessage(
                            content=(
                                "查無符合條件的航班班表（查無資料）。\n"
                                "你可以嘗試：更換日期、改查其他機場組合，或縮小/放寬條件（例如不指定航空公司/航班號）。"
                            )
                        )
                    else:
                        output = AIMessage(
                            content=(
                                "查無符合條件的資料（查無資料）。\n"
                                "你可以嘗試：更換查詢條件後再試一次。"
                            )
                        )
                else:
                    # Weather 工具本身已回傳可直接呈現的中文摘要，
                    # 避免再交給 LLM 二次整理（偶爾會誤補「查無資料」等無關句子）。
                    if tool_name == "weather_info":
                        output = AIMessage(content=tool_text)
                        return {
                            "messages": [output],
                            "tool_use": state["tool_use"],
                            "args_missing_funcname": state["args_missing_funcname"],
                            "tool_calls_args": state["tool_calls_args"],
                            "empty_args": state["empty_args"],
                            "condition": state["condition"],
                        }
                    message = (
                        f"{tool_func_data}\n"
                        "請根據上述資料整理後用繁體中文回答。\n"
                        "重要限制：\n"
                        "1) 不要自行補出『實際出發日期/抵達日期』，班表時間可能只是每日時間。\n"
                        "2) 只能使用工具輸出中已提供的欄位（航空公司/航班/班表起飛時間/班表抵達時間/有效期間/營運日）。\n"
                        "3) 若資料為空，請回覆查無資料（不要說是錯誤）。"
                    )
                    question = HumanMessage(content=message)
                    sys_prompt = SystemMessage(content=
                        f"""
                        You are a helpful assistant. Return a concise Traditional Chinese answer.
                        """
                    )
                    response = self.llm_with_no_tool.invoke([sys_prompt, question])
                    output = AIMessage(content=f"{response.content}")
            elif state["condition"] == "output" and state.get("messages"):
                # print("is_toolmessage", state["messages"][-1])
                # # state["tool_use"].append(statemessages.tool_calls[-1]["name"])
                # state["condition"] = "next_graph_or_end"
                # tool_func_data = state["messages"][-1].content
                # message = f"{tool_func_data} 請根據上述資料整理之後使用繁體中文回答，千萬不要使用簡體中文"
                # question = HumanMessage(content=message)
                # sys_prompt = SystemMessage(content=
                #     f"""
                #     You are a helpful assistant with access to the following functions. Use them if required -
                #     """
                # )
                # response = self.llm_with_no_tool.invoke([sys_prompt, question])
                state["condition"] = "next_graph_or_end"
                data = state["messages"][-1].content
                output = AIMessage(content=f"{data}")
            # 詢問一般問問題的模板
            else:
                for tool, prompt in self.querys.items():
                    if self.tool.__name__ not in state["tool_use"]:
                        print(
                            f"now is {self.tool.__name__} Agent----------------------------------------------------------------------------------------------------")
                        # user_input = input(prompt)
                        output = AIMessage(content=f"{prompt}")
                        state["condition"] = "assistant"
                    
            return {
                "messages": [output],
                "tool_use": state["tool_use"],
                "args_missing_funcname": state["args_missing_funcname"],
                "tool_calls_args": state["tool_calls_args"],
                "empty_args": state["empty_args"],
                "condition": state["condition"]
            }
        except Exception as e:
            print("e"*10, e)

    # 目前沒用到
    def handle_tool_use(self, state: State, missing_message=""):
        print("handle_tool_use_state----------------------------\n", state)
        state["tool_calls_args"] = state.get("tool_calls_args", {})
        state["empty_args"] = state.get("empty_args", [])
        state["tool_use"] = state.get("tool_use", [])
        state["args_missing_funcname"] = state.get("args_missing_funcname", "") 
        state["condition"] = state.get("condition", "") 
        output = ""
        if missing_message.strip() != "":
            # print("aa"*10)
            # user_input = input(missing_message)
            output = HumanMessage(content=f"{missing_message}")
            state["condition"] = "parse_args"
            # return {"messages": self.get_user_input(missing_message, state["args_missing_funcname"], state["tool_calls_args"]), "args_missing_funcname": state["args_missing_funcname"]}
        else:
            for tool, prompt in self.querys.items():
                if tool not in state["tool_use"]:
                    print(
                        f"now is {self.tool.__name__}  Agent----------------------------------------------------------------------------------------------------")
                    # user_input = input(prompt)
                    output = HumanMessage(content=f"{prompt}")
                    state["condition"] = "assistant"
                    # return {"messages": self.get_user_input(prompt), "args_missing_funcname": state["args_missing_funcname"]}
        print("userinput", output)
        return {
            "messages": [output],
            "tool_use": state["tool_use"],
            "args_missing_funcname": state["args_missing_funcname"],
            "tool_calls_args": state["tool_calls_args"],
            "empty_args": state["empty_args"],
            "condition": state["condition"]
        }
        # return {"messages": [], "args_missing_funcname": state["args_missing_funcname"], "tool_calls_args": state["tool_calls_args"]}

    def get_user_input(self, state: State):
        print("get_user_input_state----------------------------\n")
        existing_feedback = state.get("feedback")
        if state.get("condition") == "direct_input" and existing_feedback is not None and str(existing_feedback).strip():
            return {"feedback": existing_feedback, "condition": "assistant"}
        feedback = interrupt("Please provide feedback:")
        return {"feedback": feedback}

    @staticmethod
    def get_empty_args(arguments_data):
        print("get_empty_args_state----------------------------\n", arguments_data)
        empty_keys_results = []
        for index, item in enumerate(arguments_data):
            if 'args' in item and isinstance(item['args'], dict):
                # Check 'args' for empty values
                empty_keys = [key for key, value in item['args'].items() if value in ('', None)]
                if empty_keys:
                    print("empty_keys", empty_keys)
                    # Add result if any empty keys found
                    empty_keys_results.extend(empty_keys)
        print("empty_keys", empty_keys_results)
        return empty_keys_results

    """
    負責parse_args
    如果沒有missing_function的數值 或者是 根本沒有tool_calls代表根本沒有觸發過func call
    如果有missing function數值 代表是需要重組的狀況
    """
    def assistant(self, state: State):
        # System message
        print("assistant_state--------------\n")
        if state["args_missing_funcname"] == "" and state["condition"] == "assistant":
            # question = HumanMessage(content=f"{state['messages'][-1].content} If the information is not present in the question, please do not make up an answer.")
            feeback_data = state["feedback"]
            question = HumanMessage(content=f"{feeback_data} If the information is not present in the question, please do not make up an answer.")
            sys_prompt = SystemMessage(
                content=(
                    "You are a helpful assistant with access to the following functions. Use them if required.\n"
                    "Extract the precise function name and arguments from the user question.\n"
                    "Important: If the user provides airport IATA codes (exactly 3 letters like RMQ, TPE, NRT, HND), "
                    "DO NOT change them to other codes. Preserve them exactly (case-insensitive; output uppercase).\n"
                    "If an argument is missing, do not guess; request clarification via missing-args flow."
                )
            )
            messages = self.llm.invoke([sys_prompt, question])
            print("=============----------------------Response-------------------------------------==========================")
            print(messages)
            print("-"*50)
            # 第一次問 觸發funcall 而且有缺
            # 如果tool_calls["args"]為空值且message有tools
            if hasattr(messages, "tool_calls"):
                print("state", messages)
                state["condition"] = "lack_args" if self.check_args_null_or_blank(messages.tool_calls[-1]["args"]) else "satisfied_args"
                state["args_missing_funcname"] = messages.tool_calls[-1]["name"] if self.check_args_null_or_blank(
                    messages.tool_calls[-1]["args"]) else ""
                state["empty_args"] = self.get_empty_args(messages.tool_calls)
                # 確定沒有缺參數應該才算？可是觸發之後不會再回來？
                # state["tool_use"].append(messages.tool_calls[-1]["name"]) if not self.check_args_null_or_blank(messages.tool_calls[-1]["args"]) else state["tool_use"]
                print("aaa", state["empty_args"])
                state["tool_calls_args"] = messages.tool_calls[-1]["args"]
                    # return {
                    #     "condition": "lack_args",
                    #     "args_missing_funcname": state["args_missing_funcname"],
                    #     "empty_args": state["empty_args"],
                    #     "tool_calls_args": state["tool_calls_args"]
                    # }
                    # return Command(
                    #             update={
                    #                 "condition": "lack_args",
                    #                 "args_missing_funcname": state["args_missing_funcname"],
                    #                 "empty_args": state["empty_args"],
                    #                 "tool_calls_args": state["tool_calls_args"]
                    #             },
                    #             goto="human_feedback"
                    #         )
                # return {"messages": state['messages'], "args_missing_funcname": state["args_missing_funcname"], "tool_calls_args": state["tool_calls_args"], "empty_args": state["empty_args"]}
            return {
                "messages": [messages],
                "args_missing_funcname": state["args_missing_funcname"],
                "tool_use": state["tool_use"],
                "tool_calls_args": state["tool_calls_args"],
                "empty_args": state["empty_args"],
                "condition": state["condition"]
            }

        # Fallback: keep state shape stable even if conditions don't match.
        return {
            "messages": state.get("messages", []) or [],
            "args_missing_funcname": state.get("args_missing_funcname", ""),
            "tool_use": state.get("tool_use", []),
            "tool_calls_args": state.get("tool_calls_args", {}),
            "empty_args": state.get("empty_args", []),
            "condition": state.get("condition", ""),
        }

    def normal_llm(self, state: State):
        feeback_data = state["feedback"]
        question = HumanMessage(content=f"{feeback_data} If the information is not present in the question, please do not make up an answer.")
        sys_prompt = SystemMessage(content="You are a helpful assistant with access to the following functions. Use them if required - \n You are a smart AI agent. Please help me look up the precise function and its arguments that need to be called based on the question.")
        messages = self.llm_with_no_tool.invoke([sys_prompt, question])
        state["condition"] = "output"
        return {"messages": [messages], "condition": state["condition"]}
    
    def no_func_llm(self, state: State):
        feeback_data = state["feedback"]
        question = HumanMessage(content=f"{feeback_data} If the information is not present in the question, please do not make up an answer.")
        sys_prompt = SystemMessage(content="Answer the question and give some suggest in chinese")
        messages = self.llm_with_no_tool.invoke([sys_prompt, question])
        state["condition"] = "output"
        return {"messages": [messages], "condition": state["condition"]}

    def check_args_null_or_blank(self, json):
        for key, value in json.items():
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return True
        return False
 
    @staticmethod
    def modify_function_dict(function_list, function_name, keep_keys):
        
        # Limit: 只限一個Tool時使用
        for function_dict in function_list:
            if function_dict['function']['name'] == function_name:
                # 過濾 properties
                new_properties = {key: value for key, value in function_dict['function']['parameters']['properties'].items() if key in keep_keys}
                
                # 更新 required
                new_required = [key for key in function_dict['function']['parameters']['required'] if key in keep_keys]
                
                # 修改 function_dict
                function_dict['function']['parameters']['properties'] = new_properties
                function_dict['function']['parameters']['required'] = new_required
                return function_dict

    # 
    def arg_assistant(self, state: State):
        """
        取參數並回填
        """
        # print("abc"*10, dynamic_functions_google_schema)
        ref_args = state.get("tool_calls_args")
        sys_prompt = SystemMessage(content=
            f"""
            請使用英文回答
            假設你是一個專門提取關鍵參數的模型，用戶可能輸入與天氣、地點、航班等等的任何資訊。你的任務是分析用戶的輸入，根據內容以及參考的 {ref_args} JSON 格式，動態提取參數，並輸出結果。
            要求：
            1. 請根據用戶輸入的內容，動態匹配參數類型並輸出對應的 JSON。所有結果必須嚴格遵循模板格式{ref_args}
            2. 若根據用戶輸入的內容，沒有和參考資料格式匹配的參數類型並輸出對應的 JSON，則輸出 {{"error": "無法提取關鍵參數"}}。
            3. 禁止在輸出中增加模板未定義的字段。例如，不能多出 "error": null 或其他額外資訊。
            4. 禁止輸出任何多餘的文字說明或解釋，只輸出 JSON 格式。
            5. 僅輸出用戶提供的資料，若用戶未提供某些參數，則不要在輸出中包含這些參數。
            6. 嚴格按照上述要求，只輸出 JSON 格式的內容，禁止輸出任何其他文字。
            """
        )
        print("======================================Subgraph arg_assistant================================================")
        print("system\n")
        print(sys_prompt)
        print("-----------------------------question------------------------------")
        print(state['feedback'])
        
        
        # question = HumanMessage(content=f"{state['messages'][-1].content}")
        question = HumanMessage(content=f"{state['feedback']}")

        # BUG:預期回傳json格式回傳，有可能不是json，後續要修改
        print("-----------------------------modified_function_dict------------------------------")
        modified_function_dict = self.modify_function_dict(dynamic_functions_google_schema, state["args_missing_funcname"], state["empty_args"])
        print("-----------------------------modified_function_dict success------------------------------")
        print("-----------------------------arg_assistant_llm------------------------------")
        arg_assistant_llm = self.llm_with_no_tool.with_structured_output(modified_function_dict)
        print("-----------------------------arg_assistant_llm success------------------------------")
        print("-----------------------------arg_assistant_llm.invoke------------------------------")
        messages = arg_assistant_llm.invoke([sys_prompt, question])
        print("-----------------------------arg_assistant_llm.invoke success------------------------------")
        # 如果再次產生的參數還是空直會報錯
        print("messages", messages)
        print("messages.content", type(messages))
        for message in reversed(state["messages"]):
            print("message", message)
            print("message", hasattr(message, "tool_calls"))
            if isinstance(message, AIMessage) and hasattr(message, "tool_calls") and len(message.tool_calls) > 0:
                print("last"*10)
                break
            state["messages"].pop()
        print("args_assistant", state)
        state["messages"][-1].tool_calls[-1]["args"].update(messages)
        """
        利用倒序尋找最後一個AIMessage且觸發func call的
        若非則所有訊息刪除, 直到最後一個是func call的
        """
        # print(type(state["messages"][2].tool_calls))
        # for message in reversed(state["messages"]):
        #     print(dir(message))
        #     if isinstance(message, AIMessage) and hasattr(message, "tool_calls"):
        #         print("last"*10)
        #         break
        #     state["messages"].pop()
        
        # messages = self.llm_with_no_tool.invoke([self.sys_args_msg] + [state["messages"][-1]])
        if not self.check_args_null_or_blank(state["messages"][-1].tool_calls[-1]["args"]):
            state["args_missing_funcname"] = ""
            state["tool_calls_args"] = {}
        return {"args_missing_funcname": state["args_missing_funcname"], "tool_calls_args": state["tool_calls_args"]}

    def go_to_subgraph_or_get_user_input(self, state: State):
        print("go_to_subgraph_or_get_user_input--------------\n", state)
        if state["condition"] == "next_graph_or_end":
            state["tool_use"] = []
            state["args_missing_funcname"] = ""
            state["tool_calls_args"] = {}
            state["empty_args"] = []
            state["condition"] = ""
            # Do not auto-jump to the next subgraph; pause for the next user input.
            return "get_user_input"
            
        # if self.tool.__name__ in state["tool_use"]:
            # print("go_to_subgraph_or_get_user_input")
            # and isinstance(state["messages"][-1], ToolMessage)
            # state["tool_use"] = []
        return "get_user_input"
    
    def go_to_end_or_get_user_input(self, state: State):
        # if self.tool.__name__ in state["tool_use"]:
        if state["condition"] == "next_graph_or_end":
            print("go_to_end_or_get_user_input")
            # and isinstance(state["messages"][-1], ToolMessage)
            # state["tool_use"] = []
            return END
        return "get_user_input"
    
    def llm_call(self, state: State):
        print("llm_call", state)
        if state["args_missing_funcname"] != "" and state["condition"] == "parse_args":
            return "arg_assistant"
        # elif self.tool.__name__ in state["tool_use"]:
        #     # and isinstance(state["messages"][-1], ToolMessage)
        #     state["tool_use"] = []
        #     return "next_graph"
        elif state["condition"] == "assistant":
            return "assistant"

    def llm_call_to_end(self, state: State):
        if state["args_missing_funcname"] != "" and state["condition"] == "lack_args":
            return "arg_assistant"
        elif self.tool.__name__ in state["tool_use"]:
            return END
        else:
            return "assistant"

    def tools_condition_edge(self, state: State):
        print("tools_condition_edge", state)
        if isinstance(state, list):
            ai_message = state[-1]
        elif isinstance(state, dict) and (messages := state.get("messages", [])):
            ai_message = messages[-1]
        elif messages := getattr(state, "messages", []):
            ai_message = messages[-1]
        else:
            raise ValueError(
                f"No messages found in input state to tool_edge: {state}")
        if state["args_missing_funcname"] != "" and state["condition"] == "lack_args":
            return "human_feedback"
        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            print("inside_tools_before")
            return "tools"
        return "human_feedback"

    # 沒用到
    def is_arg_complete(self, state: State):
        if state["args_missing_funcname"] != "":
            return "human_feedback"
        return "assistant"