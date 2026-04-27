from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from typing_extensions import Literal, TypedDict
from langchain_ollama import ChatOllama
import threading

# from utils.function_calling import dynamic_functions_google_schema, dynamic_functions
from tools.gemma_get_weather_info_tool_gemma import get_weather_info_tool_gemma
from tools.gemma_get_flight_info_tool_example import get_flight_info_tool_gemma
from langchain_ollama import ChatOllama
from langgraph.graph import END, MessagesState
from langgraph.types import Command
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from typing_extensions import Literal, TypedDict
from langchain_ollama import ChatOllama
import threading
import json
import requests
from langgraph.types import interrupt

from tools.gemma_get_weather_info_tool_gemma import get_weather_info_tool_gemma
from tools.gemma_get_flight_info_tool_example import get_flight_info_tool_gemma

class State(MessagesState):
    empty_args: list
    tool_use: list

def make_alternative_graph(thread_id="1"):
    manager = GraphManager(thread_id)
    return manager.get_agent()

config = {"configurable": {"thread_id": "1"}}
"""
1. 防止空參數
2. 防止找不到對應的function
3. 防止llm回答不知所云
4. 防止llm回答不符合格式(如：缺少參數、中文參數)
"""
async def ask_langgraph(question):
    agent = GraphManager().get_agent()
    # agent = make_alternative_graph()
    print("b_問題", question)
    input_message = HumanMessage(content=f"{question}")
    snapshot = agent.get_state(config={"configurable": {"thread_id": "1"}})
    value = snapshot.next[0] if 0 < len(snapshot.next) else None
    print("valueab", value)
    print("b_查看狀態1", type(snapshot.next),"\n")
    print("b_查看狀態2", snapshot.values,"\n")
    print("b_查看狀態2", snapshot.tasks,"\n")
    print("b_查看狀態2", snapshot.metadata,"\n")
    print("b_查看狀態2", snapshot.config,"\n")

    if value == "extract_parameters_from_user_feedback" and len(snapshot.values["messages"]) > 0:
        print("input_message", input_message)
        snapshot.values["messages"][-1] = input_message
        agent.update_state({"configurable": {"thread_id": "1"}}, snapshot.values)
        print("b_進入extract_parameters_from_user_feedback")
        output = agent.invoke(None, config)
        for m in output['messages'][-1:]:
            m.pretty_print()
            print("m", m)
            if not m.content:
                yield ''
            yield m.content.encode("utf-8")
        snapshot = agent.get_state(config={"configurable": {"thread_id": "1"}})
        print("b_查看狀態1", snapshot.next,"\n")
        print("b_查看狀態2", snapshot.values,"\n")
    else:
        for event in agent.stream({"messages": [input_message]}, config, stream_mode="values"):
            print("event", event)
            print("event_aa", event["messages"][-1].content)
            # for value in event.values():
            #     print("value", value)
            #     print("Assistant:", value["messages"][-1].content)
            #     print("Graph Event:", event)
            if not event["messages"][-1].content:
                yield ''
            yield event["messages"][-1].content.encode("utf-8")
            # output.append(event)
        # output = agent.invoke({"messages": [input_message]}, config)
        # for m in output['messages'][-1:]:
        #     m.pretty_print()
        #     print("m", m)
        #     if not m.content:
        #         yield "呼叫失敗，請再試一次"
        #     yield m.content.encode("utf-8")
        
        snapshot = agent.get_state(config={"configurable": {"thread_id": "1"}})
        print("a_查看狀態1", snapshot.next,"\n")
        print("a_查看狀態2", snapshot.values,"\n")
        
def main_agent(state: State):
    try:
        llm_main = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
        ).bind_tools(tools=[get_weather_info_tool_gemma])

        # 進入
        # messages = state["messages"]
        # if hasattr(messages, "tool_calls") and len(messages.tool_calls) > 0:
        #     state["tool_use"].append(messages.tool_calls[-1]["name"])
        #     return {"messages": [messages], "tool_use": state["tool_use"]}
        
        question = HumanMessage(content=f"{state['messages'][-1].content} If the information is not present in the question, please do not make up an answer.")
        sys_prompt = SystemMessage(content="You are a smart AI agent. Please help me look up the precise function and its arguments that need to be called based on the question.?")
        output = llm_main.invoke([sys_prompt, question])
        print("output\n", output)
        return {"messages": output}
    except Exception as e:
        print("e"*10, e)
        return {"error": str(e)}

# is_tool_use_list_empty = llm_call
def is_tool_use_list_empty(self, state: State):
    # 判斷使用過的tool是否有包含在tools內？ 為什麼？ 若使用過了則跳轉下一個子圖，若無則進入正常詢問流程
    if self.tool.__name__ in state["tool_use"]:
        return "next_graph"
    else:
        return "is_trigger_function_calling"

def is_trigger_function_calling(state: State) -> Command[Literal["ask_human"]]:
    messages = state["messages"]
    print("aa", state)
    print("\nis_trigger_function_calling_messages", messages)
    last_message = messages[-1]
    print("\nis_trigger_function_calling_last_message", last_message)
    if last_message.tool_calls:
        arguments_data = last_message.tool_calls
        print("state\n", arguments_data)
        empty_keys_results = []
        # check_args_agent
        # Iterate through each dictionary in the list
        for index, item in enumerate(arguments_data):
            if 'args' in item and isinstance(item['args'], dict):
                # Check 'args' for empty values
                empty_keys = [key for key, value in item['args'].items() if value in ('', None)]
                if empty_keys:
                    print("empty_keys", empty_keys)
                    # Add result if any empty keys found
                    empty_keys_results.extend(empty_keys)
        print("empty_keys_results", empty_keys_results)
        if empty_keys_results:
            # state["empty_args"] = empty_keys_results
            print("empty_keys_results_state", state)
            return Command(
                update={"empty_args": empty_keys_results},
                goto="ask_human"
            )
        return Command(
                goto="tools"
            )
    return Command(
                goto=END
        )

def ask_human(state: State):
    try:
        print("ask_human_state", state)
        empty_arg_list = state["empty_args"]
        print("ask_human_question", empty_arg_list)
        args = state["messages"][1].tool_calls[-1]["args"]
        message = f"{empty_arg_list}，以上這些是空值的參數，請幫我想想該怎麼用親切的語氣，跟使用者說「這些參數為空，請幫我填入」。只需要回答「給使用者的句子」，其餘的不需要，請不要回答。"
        llm_check_args_llm = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
        )
        message = HumanMessage(content=message)
        sys_prompt = SystemMessage(content=
            f"""
            請幫我使用繁體中文回答，不要有任何的簡體中文。請仔細想想之後認真回答有獎勵，不認真回答我就死給你看。回答只需要跟範例一樣的 JSON 格式輸出，例如{args}，其他不需要多回答。請仔細想想之後認真回答有獎勵，不認真回答我就死給你看
            你是一個協助用戶處理缺少參數的系統。根據提供的缺少參數關鍵字清單，請回應一條訊息，指明缺少哪些參數。請遵循以下格式：
            範例：
            輸入: ["location"]
            回應: 您的請求缺少地點的參數，請提供相關資訊。


            輸入: ["days"]
            回應: 您的請求缺少天數的參數，請提供相關資訊。


            輸入: ["location", "days"]
            回應: 您的請求缺少地點和天數的參數，請提供相關資訊。
            """
        )
        response = llm_check_args_llm.invoke([sys_prompt, message])
        print("ask_human_response", response.content)
        print("breakpoint")
        user_feedback = input(response.content)
        print("breakpointafeter")


        # # 提取參數的 NLP 模型邏輯
        # llm_param_extractor = ChatOllama(
        #     model="llama3.2:3b",
        #     temperature=0,
        # )
        # print("llm_param_extractor", llm_param_extractor)
        # args_json = state["messages"][1].tool_calls[-1]["args"]
        # # 嘗試解析成 JSON 格式
        # sys_prompt = SystemMessage(content=
        #     f"""
        #     請使用英文回答
        #     假設你是一個專門提取關鍵參數的模型，用戶可能輸入與天氣、地點、航班等等的任何資訊。
        #     你的任務是分析用戶的輸入。
        #     首先，請將用戶的輸入內容翻譯成英文。
        #     接著，根據翻譯後的內容以及參考的 {args_json} JSON 格式，從使用者的輸入中動態提取相應的參數，並僅返回包含英文鍵和值的 JSON 格式結果，並不要包含任何額外的符號以及文字。
        #     若某些參數無法從使用者輸入中提取，請省略這些參數對應的鍵值，不需要其他回應。以下是需要處理的參數類型與範例輸出格式：  

        #     **其他未知情境**：若根據用戶輸入的內容，沒有和參考資料格式匹配的參數類型並輸出對應的 JSON，則輸出 {{"error": "無法提取關鍵參數"}}。

        #     ### 指引：
        #     - 請根據用戶輸入的內容，動態匹配參數類型並輸出對應的 JSON，且鍵和值均使用英文。
        #     - 如果輸入中包含地點，提取地點並以英文輸出。
        #     - 如果輸入中包含航班資訊，提取起點與目標機場代碼，並以英文輸出。
        #     - 如果輸入內容不符合上述參數類型，則回傳"無法提取關鍵參數"。
        #     """
        # )
        # #請使用英文回答，另外除了JSON其餘不用回答。
        # # print("sys_prompt", sys_prompt)
        # print("user_feedback", user_feedback)
        # extract_message = HumanMessage(content=user_feedback)
        # print("extract_message", extract_message)
        # response = llm_param_extractor.invoke([sys_prompt, extract_message])
        # print("response.content", response.content)
        # extracted_data = json.loads(response.content)
        # print("response.content", response.content)
        # # extracted_data = extract_parameters(args, user_feedback)
        # if not extracted_data:
        #     return {"action": "ask_human", "message": "很抱歉，我無法理解您的回覆，請再試一次並提供具體的參數值。"}
        
        # # 更新參數
        # ## 多個
        # # if "messages" in state and "tool_calls" in state["messages"][1]:
        # #     for call in state["messages"][1]["tool_calls"]:
        # #         if 'args' in call and isinstance(call['args'], dict):
        # #             call['args'].update(extracted_data)
        # state["messages"][1].tool_calls[-1]["args"].update(extracted_data)
        # print("state", state)
        # update_state_with_new_params(state, extracted_params)
        # 重新驗證參數
        # validation_result = check_args_agent(state)
        # return validation_result  # 確保參數驗證流程再次執行
        return {"messages": response.content}
    except Exception as e:
        return {"error": str(e)}

# 假設的參數提取函數
def extract_parameters_from_user_feedback(state: MessagesState) -> str:
    """
    使用 LLM 提取參數，回傳 dict 格式的參數鍵值對
    """
    try:
        print("extract_parameters_state\n", state)
        llm_param_extractor = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
        )
        ref_args = state["messages"][1].tool_calls[-1]["args"]
        sys_prompt = SystemMessage(content=
            f"""
            請使用英文回答
            假設你是一個專門提取關鍵參數的模型，用戶可能輸入與天氣、地點、航班等等的任何資訊。你的任務是分析用戶的輸入，根據內容以及參考的 {ref_args} JSON 格式，動態提取參數，並輸出結果。以下是需要處理的參數類型與範例輸出格式：  

            1. **地點**：  
            - 輸入：「台北的天氣如何？」  
                - 輸出：{{"location": "Taipei"}}

            2. **航班資訊**：  
            - 輸入：「大阪到台北的航班」  
                - 輸出：{{"fromairportid": "KIX", "department airportid": "TPE"}}  
            - 輸入：「台北到東京有什麼航班？」  
                - 輸出：{{"fromairportid": "TPE", "department airportid": "HND"}}

            3. **其他未知情境**：若根據用戶輸入的內容，沒有和參考資料格式匹配的參數類型並輸出對應的 JSON，則輸出 {{"error": "無法提取關鍵參數"}}。

            ### 指引：
            - 請根據用戶輸入的內容，動態匹配參數類型並輸出對應的 JSON。
            - 如果輸入中包含地點，提取地點並輸出 {{"location": '地點名稱'}}。
            - 如果輸入中包含航班資訊，提取起點與目標機場代碼（IATA 格式）並輸出 {{"fromairportid": '起點代碼', "department airportid": '目標代碼'}}。
            - 如果輸入內容不符合上述參數類型，則回傳 {{"error": "無法提取關鍵參數"}}。
            """
        )
        #請使用英文回答，另外除了JSON其餘不用回答。
        print("sys_prompt", sys_prompt)
        question = state["messages"][-1].content
        extract_message = HumanMessage(content=f"{question}")
        response = llm_param_extractor.invoke([sys_prompt, extract_message])
        import json
        extracted_data = json.loads(response.content)
        print("extract_parameters", extracted_data)
        state["messages"][1].tool_calls[-1]["args"].update(extracted_data)
        print("state", state["messages"][1])
        state["messages"][1].response_metadata["message"]["tool_calls"][0]["function"]["arguments"].update(extracted_data)
        
        print("state", state)
        print('state["messages"][1]', state["messages"][1])
        print('state["messages"][1]', type(state["messages"][1]))
        output = state["messages"][1]
        del state["messages"][-1]
        del state["messages"][-1]
        # 嘗試解析成 JSON 格式
        return {"messages": output}
    except Exception as e:
        print("e"*10, e)

# 更新參數值到 state
def update_state_with_new_params(state: MessagesState, extracted_params: dict):
    """
    將提取的參數更新到狀態中
    """
    if "messages" in state and "tool_calls" in state["messages"][1]:
        for call in state["messages"][1]["tool_calls"]:
            if 'args' in call and isinstance(call['args'], dict):
                call['args'].update(extracted_params)

def reflect_args_agent(state: MessagesState):
    try:
        print("a"*10)
        llm_reflect_args = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
        )
        print("reflect_args_state\n", state)
        question = state["messages"][0].content
        arguments = state["messages"][1].tool_calls[-1]["args"]
        print("state\n", arguments)
        question = HumanMessage(content=f"arguments: {arguments} Based on the provided arguments, you are responsible for checking whether the arguments are in English and not empty; if they meet the criteria, return them unchanged, but if they do not, modify them as needed in the original format and return them.")
        # print("question\n", question)
        sys_prompt = SystemMessage(content="You are an engineer capable of precisely validating arguments, and careful inspection will be rewarded.")
        # BUG: System prompt 會影響llm model的回答
        output = llm_reflect_args.invoke([sys_prompt, question])
        # 如果不懂問題的內容就回答不知道，不要亂回答
        # BUG: 需加上如何判斷llm是否要做function calling
        # response = ollama.chat(
        #     model="llama3.2:3b",
        #     messages=[
        #         {"role": "system", "content": "You are a helpful assistant with access to the following functions. Use them if required -"},
        #         {"role": "user", "content": f"{question} If the information is not present in the question, please do not make up an answer."},
        #     ],
        #     stream=False,
        #     tools=dynamic_functions_google_schema
        # )
        print("reflect_args_agent_response", output)
        return {"messages": output}
    except Exception as e:
        print("e"*10, e)
        return {"error": str(e)}

def should_continue(state: MessagesState):
    print("\nshould_continue", state)
    messages = state["messages"]
    print("\nmessages", messages)
    last_message = messages[-1]
    print("\nlast_message", last_message)
    if last_message.tool_calls:
        return "tools"
    return END

def make_alternative_graph():
    # print("dynamin_google_schema", dynamic_functions_google_schema)
    """Make a tool-calling agent"""
    print("dynamic_functions.values()", dynamic_functions.values())
    tool_node = ToolNode(dynamic_functions.values())
    workflow = StateGraph(MessagesState)

    workflow.add_node("main_agent", main_agent)
    workflow.add_node("tools", tool_node)
    workflow.add_node("ask_human", ask_human)
    # workflow.add_node("reflect_args_agent", reflect_args_agent)
    # workflow.add_node("check_args_agent", check_args_agent)
    
    workflow.add_edge(START, "main_agent")
    # workflow.add_conditional_edges("main_agent", is_trigger_function_calling, ["reflect_args_agent", END])
    workflow.add_conditional_edges("main_agent", is_trigger_function_calling, ["ask_human", "tools", END])
    # workflow.add_conditional_edges("check_args_agent", check_args_agent, ["ask_human", "tools"])
    # workflow.add_edge("reflect_args_agent", "main_agent")
    # workflow.add_conditional_edges("main_agent", should_continue, ["tools", END])
    # workflow.add_edge("tools", "main_agent")

    memory = MemorySaver()

    agent = workflow.compile(checkpointer=memory)
    return agent

config = {"configurable": {"thread_id": "1"}}
querys = {
    "get_weather_info_tool": "請根據以下內容輸入你想查詢的天氣: 地名, 天數\n",
    "get_flight_info_tool": "請根據以下內容輸入你想查詢的航班: 出發地, 目的地, 起飛日\n",
}


class SubGraph:
    def __init__(self, tool):
        self.tool = tool
        self.querys = {tool.__name__ : querys[tool.__name__]}
        self.llm = ChatOllama(
                model="llama3.2:3b",
                temperature=0,
                keep_alive=0
        ).bind_tools([tool], parallel_tool_calls=False)
        self.normal_llm = ChatOllama(
                model="llama3.2:3b",
                temperature=0,
                keep_alive=0
        )
        self.sys_msg = SystemMessage(
            content="""
            You are an AI Agent equipped with various tools to help you complete tasks. You should automatically determine whether these tools are needed based on the user's request. 
            If you can directly answer the question, do not generate a tool message.
            
            Based on the context provided, follow these steps to determine if a tool call is necessary:

            1. Summarize the Direction: Analyze the user's question and summarize the direction of the inquiry (e.g., issue resolution, information retrieval, decision-making) to confirm if it aligns with the functionality of the tool.
            2. Parameter Validation: Ensure that all parameters required for the tool call can be directly extracted from the user's question.
            
            If either condition is not met, do not proceed with the tool call.
            Instead, provide a response through regular question-and-answer logic
                
            """)
        
    def query(self, state: State):
        try:
            """
            若該tool未被使用, 則使用範本詢問問題
            正常不會用過, 因為該點不會有循環
            """
            for tool, prompt in self.querys.items():
                print("tool"*10, tool)
                
                if tool not in state.get("tool_use", []):
                    return {"messages": prompt, "empty_args": state.get("empty_args", []), "tool_use": state.get("tool_use", [])}
        except Exception as e:
            print("query_error\n", e)
            
    def parse_args(self, state: State):
        # 斷點，獲取使用者輸入
        user_question = interrupt("請使用者回答問題")
        """
        負責parse_arg
        同上, 因為接續query且不再循環流程中, 因此不太可能會有tool已被使用的問題
        """
        print("abc", state)
        question = HumanMessage(content=f"{user_question} If the information is not present in the question, please do not make up an answer.")
        sys_prompt = SystemMessage(content="You are a helpful assistant with access to the following functions. Use them if required - \n You are a smart AI agent. Please help me look up the precise function and its arguments that need to be called based on the question.")
        output = self.llm.invoke([sys_prompt, question])
        return {"messages": output, "empty_args": state["empty_args"], "tool_use": state["tool_use"]}
    
    def entry(self, state: State):
        """
        如果狀態中最後一則訊息為ToolMessage則代表該tool被使用過, 加入到tool_use中
        並將tool回傳的結果, 整理後回傳使用者後, 準備透過判斷前往下個子圖
        
        若非ToolMessage則代表未被使用過, 準備透過判斷前往下個節點
        """
        print("entry", state)
        if state["messages"] and isinstance(state["messages"][-1], ToolMessage):
            print("inside")
            data = state["messages"][-1].content
            print("data", data)
            state["tool_use"].append(state["messages"][-1].name)
            print("append_state", state)
            sys_prompt = SystemMessage(content="""You are a helpful assistant with access to the following functions. Use them if required -""")
            question = HumanMessage(content=f"{data} 請根據上述資料整理之後使用繁體中文回答，千萬不要使用簡體中文")
            response = self.normal_llm.invoke([sys_prompt, question])
            print("response", response)
            return {"messages": response.content, "empty_args": state["empty_args"], "tool_use": state["tool_use"]}
        pass
        
    def main_agent(self, state: State):
        try:
            print("aaaa"*20, dir(state), "\n")
            # 若ToolMessage為最後一則，則代表tool使用過，加入到tool_use
            if state["messages"] and isinstance(state["messages"][-1], ToolMessage):
                data = state["messages"][-1].content
                print("data", data)
                state["tool_use"].append(state["messages"][-1].name)
                print("append_state", state)
                sys_prompt = SystemMessage(content="""You are a helpful assistant with access to the following functions. Use them if required -""")
                question = HumanMessage(content=f"{data} 請根據上述資料整理之後使用繁體中文回答，千萬不要使用簡體中文")
                response = self.normal_llm.invoke([sys_prompt, question])
                print("response", response)
            tool_use = state.get("tool_use", [])
            # 如果tool_use不包含當前tool檔案的名稱，代表尚未執行，詢問使用者題目。
            if self.tool.__name__  not in tool_use:
                print("abc", state)
                user_question = state["messages"][-1].content
                question = HumanMessage(content=f"{user_question} If the information is not present in the question, please do not make up an answer.")
                sys_prompt = SystemMessage(content="You are a helpful assistant with access to the following functions. Use them if required - \n You are a smart AI agent. Please help me look up the precise function and its arguments that need to be called based on the question.")
                output = self.llm.invoke([sys_prompt, question])
                return {"messages": output, "empty_args": [], "tool_use": tool_use}
            #     print("a"*10)
                # prompt = self.querys[self.tool.__name__]
                # question = state["messages"][-1].content
            return {"messages": [], "empty_args": [], "tool_use": tool_use}
        except Exception as e:
            print("e"*10, e)
            return {"error": str(e)}

    def is_trigger_function_calling(self, state: State) -> Command[Literal["ask_human", "tools", END]]:
        
        messages = state["messages"]
        print("aa", state)
        # answer = interrupt("test")
        # print("aws", answer)
        print("\nis_trigger_function_calling_messages", messages)
        last_message = messages[-1]
        print("\nis_trigger_function_calling_last_message", last_message)
        if last_message.tool_calls:
            arguments_data = last_message.tool_calls
            print("state\n", arguments_data)
            empty_keys_results = []
            # check_args_agent
            # Iterate through each dictionary in the list
            for index, item in enumerate(arguments_data):
                if 'args' in item and isinstance(item['args'], dict):
                    # Check 'args' for empty values
                    empty_keys = [key for key, value in item['args'].items() if value in ('', None)]
                    if empty_keys:
                        print("empty_keys", empty_keys)
                        # Add result if any empty keys found
                        empty_keys_results.extend(empty_keys)
            print("empty_keys_results", empty_keys_results)
            if empty_keys_results:
                state["empty_args"].append(empty_keys_results)
                print("empty_keys_results_state", state)
                return Command(
                    update={"empty_args": empty_keys_results},
                    goto="ask_human"
                )
            return Command(
                    goto="tools"
                )
        return Command(
                    goto=END
            )

    def ask_human(self, state: State):
        try:
            print("ask_human", state)
            
            empty_arg_list = state["empty_args"]
            print("ask_human_question", empty_arg_list)
            args = state["messages"][-1].tool_calls[-1]["args"]
            message = f"{empty_arg_list}，以上這些是空值的參數，請幫我想想該怎麼用親切的語氣，跟使用者說「這些參數為空，請幫我填入」。只需要回答「給使用者的句子」，其餘的不需要，請不要回答。"
            llm_check_args_llm = ChatOllama(
                model="llama3.2:3b",
                temperature=0,
            )
            message = HumanMessage(content=message)
            sys_prompt = SystemMessage(content=
                f"""
                請幫我使用繁體中文回答，不要有任何的簡體中文。請仔細想想之後認真回答有獎勵，不認真回答我就死給你看。回答只需要跟範例一樣的 JSON 格式輸出，例如{args}，其他不需要多回答。請仔細想想之後認真回答有獎勵，不認真回答我就死給你看
                你是一個協助用戶處理缺少參數的系統。根據提供的缺少參數關鍵字清單，請回應一條訊息，指明缺少哪些參數。請遵循以下格式：
                範例：
                輸入: ["location"]
                回應: 您的請求缺少地點的參數，請提供相關資訊。


                輸入: ["days"]
                回應: 您的請求缺少天數的參數，請提供相關資訊。


                輸入: ["location", "days"]
                回應: 您的請求缺少地點和天數的參數，請提供相關資訊。
                """
            )
            
            response = llm_check_args_llm.invoke([sys_prompt, message])
            print("ask_human_response", response.content)
            print("breakpoint")
            # question = state["messages"][-1].content
            # user_feedback = input(response.content)
            # print("user_feedback", user_feedback)
            print("ask_human_state", state)
            print("breakpointafeter")
            return {"messages": response.content}
        # return {"messages": "response.content"}
        except Exception as e:
            return {"error": str(e)}
        
    def first_ask(self, state: State):
        try:
            print("first_ask", state)
            value = interrupt()
            print("first_ask", state, "\n")
            print(state["messages"][0].content)
            user_question = state["messages"][0].content
            question = HumanMessage(content=f"{user_question} If the information is not present in the question, please do not make up an answer.")
            sys_prompt = SystemMessage(content="You are a smart AI agent. Please help me look up the precise function and its arguments that need to be called based on the question.?")
            output = self.llm.invoke([sys_prompt, question])
            return {"messages": output, "tool_use": state["tool_use"]}
        except Exception as e:
            print("e"*10, e)
            return {"error": str(e)} 
    
    def extract_parameters_from_user_feedback(self, state: State) -> str:
        """
        使用 LLM 提取參數，回傳 dict 格式的參數鍵值對
        """
        # try:
        print("extract_parameters_from_user_feedback_state_1", state)
        question = interrupt("test")
        print("answer", question)
        print("extract_parameters_from_user_feedback_state_2", state)
        print("extract_parameters_state\n", state)
        llm_param_extractor = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
        )
        """
        利用倒序尋找最後一個AIMessage且觸發func call的
        若非則所有訊息刪除, 直到最後一個是func call的
        """
        print(type(state["messages"][2].tool_calls))
        for message in reversed(state["messages"]):
            print(dir(message))
            if isinstance(message, AIMessage) and hasattr(message, "tool_calls"):
                print("last"*10)
                break
            state["messages"].pop()

        print("adsjfdsafjkdsl\n", state["messages"])
        # 取AIMessage HardCore索引一定會錯
        ref_args = state["messages"][-1].tool_calls[-1]["args"]
        print("ref_args", ref_args)
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
        #請使用英文回答，另外除了JSON其餘不用回答。
        print("sys_prompt\n", sys_prompt)
        # question = state["messages"][-1].content
        # question = "Taipei"
        extract_message = HumanMessage(content=f"{question}")
        print("extract\n", extract_message)
        # BUG: 要改用Strued Output
        response = llm_param_extractor.invoke([sys_prompt, extract_message])
        print("a"*10)
        print("a"*10, "\n")
        print(response.content)
        data = response.content.replace("'", '"')
        extracted_data = json.loads(data)
        print("bbbb")
        print("extract_parameters\n", extracted_data)
        state["messages"][-1].tool_calls[-1]["args"].update(extracted_data)
        # print("state", state["messages"][1])
        # state["messages"][1].response_metadata["message"]["tool_calls"][0]["function"]["arguments"].update(extracted_data)
        
        print("state", state)
        print('state["messages"][1]', state["messages"][1])
        print('state["messages"][1]', type(state["messages"][1]))
        # 嘗試解析成 JSON 格式
        return {"messages": state["messages"]}
        # except Exception as e:
        #     print("e"*10, e)

    def decision_to_next_tools_end(self,state: State) -> Command[Literal["next_graph", "is_trigger_function_calling"]]:
        print("decision_to_next_tools_end"*10)
        print("state['tool_use']", state["tool_use"])
        print("self.tool.__name__", self.tool.__name__)
        """
        entry會將已使用的tool加入tool_use中
        透過tool_use判斷是否該前往下個子圖
        正常不應該會有同個tool重複兩次的情況發生
        
        若是第一次則會判斷parse_arg中是否有空值
        若為空則會將key紀錄, 作為後續取得使用者回饋用
        若不為空則會直接觸發ToolMessage
        
        若第一次且沒有觸發function_calling 我們直接回答並進END
        """
        if self.tool.__name__ in state["tool_use"]:
            print("next_graph"*10)
            return "next_graph"
        else:
            messages = state["messages"]
            print("aa", state)
            print("\nis_trigger_function_calling_messages", messages)
            last_message = messages[-1]
            print("\nis_trigger_function_calling_last_message", last_message)
            if last_message.tool_calls:
                arguments_data = last_message.tool_calls
                print("state\n", arguments_data)
                empty_keys_results = []
                # check_args_agent
                # Iterate through each dictionary in the list
                for index, item in enumerate(arguments_data):
                    if 'args' in item and isinstance(item['args'], dict):
                        # Check 'args' for empty values
                        empty_keys = [key for key, value in item['args'].items() if value in ('', None)]
                        if empty_keys:
                            print("empty_keys", empty_keys)
                            # Add result if any empty keys found
                            empty_keys_results.extend(empty_keys)
                print("empty_keys_results", empty_keys_results)
                if empty_keys_results:
                    print("empty_keys_results_state", state)
                    state["empty_args"].extend(empty_keys_results)
                    return "ask_human"
                return "tools"
            return END
        
    def decision_to_tools_or_end(self,state: State):
        print("llm_call_to_end", state)
        if self.tool.__name__ in state["tool_use"]:
            return END
        else:
            messages = state["messages"]
            print("aa", state)
            print("\nis_trigger_function_calling_messages", messages)
            last_message = messages[-1]
            print("\nis_trigger_function_calling_last_message", last_message)
            if last_message.tool_calls:
                arguments_data = last_message.tool_calls
                print("state\n", arguments_data)
                empty_keys_results = []
                # check_args_agent
                # Iterate through each dictionary in the list
                for index, item in enumerate(arguments_data):
                    if 'args' in item and isinstance(item['args'], dict):
                        # Check 'args' for empty values
                        empty_keys = [key for key, value in item['args'].items() if value in ('', None)]
                        if empty_keys:
                            print("empty_keys", empty_keys)
                            # Add result if any empty keys found
                            empty_keys_results.extend(empty_keys)
                print("empty_keys_results", empty_keys_results)
                if empty_keys_results:
                    print("empty_keys_results_state", state)
                    state["empty_args"] = empty_keys_results
                    return "ask_human"
                return "tools"
            return END
            # return "first_ask"
            # return "is_trigger_function_calling"

class GraphManager:
    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, thread_id="1"):
        with cls._lock:
            if thread_id not in cls._instances:
                cls._instances[thread_id] = super(GraphManager, cls).__new__(cls)
                cls._instances[thread_id]._initialize_graph()
                # 沒東西更新圖會爆
                cls._instances[thread_id].save_graph()
        return cls._instances[thread_id]

    def _initialize_graph(self):
        # self.graphs = {}
        self.graphs = None
        self.memory = MemorySaver()

    def create_graph(self, tools):
        graph = Graph(tools)
        self.graphs = graph
        # self.graphs[tools[0]] = graph
        return graph

    def get_agent(self):
        # return self.graphs[tools[0]].get_agent()
        return self.graphs.get_agent()

    def save_graph(self):
        try:
            for graph in self.graphs.values():
                graph.save_graph(graph.agent, graph.tools[0].__name__)
        except Exception as e:
            print(f"無法保存圖形：{str(e)}")
            
graph_manager = GraphManager()

class Graph:
    def __init__(self, tools):
        if tools[0] == "test":
            print("t"*10)
            self.tools = []
            self.agent = None
        else:
            print("not t"*10)
            self.tools = [dynamic_functions[tool] for tool in tools]
            self.agent = self.build_graph(0)

    def build_graph(self, start_index):
        try:
            tool = self.tools[start_index]
            sub_graph = SubGraph(tool)
            builder = StateGraph(State)
            builder.add_node(sub_graph.main_agent)
            builder.add_node(sub_graph.is_trigger_function_calling)
            builder.add_node(sub_graph.query)
            builder.add_node(sub_graph.parse_args)
            builder.add_node(sub_graph.entry)
            builder.add_node(sub_graph.ask_human)
            builder.add_node(sub_graph.extract_parameters_from_user_feedback)
            builder.add_node("tools", ToolNode([tool]))
            if start_index != len(self.tools) - 1:
                builder.add_node("next_graph", self.build_graph(start_index+1))
                builder.add_conditional_edges("entry", sub_graph.decision_to_next_tools_end, ["ask_human", "tools", END, "next_graph"])
            else:
                builder.add_conditional_edges("entry", sub_graph.decision_to_tools_or_end, ["ask_human", "tools", END])
            # builder.add_edge(START, "main_agent")
            builder.add_edge(START, "query")
            builder.add_edge("query", "parse_args")
            builder.add_edge("parse_args", "entry")
            builder.add_edge("ask_human", "extract_parameters_from_user_feedback")
            builder.add_edge("extract_parameters_from_user_feedback", "tools")
            # builder.add_edge("tools", "main_agent")
            builder.add_edge("tools", "entry")
            memory = MemorySaver()
            self.agent = builder.compile(checkpointer=memory)
            self.save_graph(self.agent, tool.__name__)
            return self.agent
        except Exception as e:
            print("e*10", e)
    
    def get_agent(self):
        return self.agent
    
    def save_graph(self, graph, name):
        try:
            png_data = graph.get_graph().draw_mermaid_png()
            output_file = name + ".png"
            with open(output_file, "wb") as f:
                f.write(png_data)
            print(f"圖形已保存到: {output_file}")
        except Exception as e:
            print(f"無法保存圖形：{str(e)}")
