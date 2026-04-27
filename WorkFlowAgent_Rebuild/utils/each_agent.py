
from langchain_core.messages import SystemMessage, HumanMessage
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

from utils.function_calling import dynamic_functions_google_schema, dynamic_functions
from utils.langgraph_function_calling import graph_manager
from tools.gemma_get_weather_info_tool_gemma import get_weather_info_tool_gemma
from tools.gemma_get_flight_info_tool_example import get_flight_info_tool_gemma

config = {"configurable": {"thread_id": "1"}}

def get_weather_info(location: str, days: str) -> list:
    """
    Returns weather information based on the provided request.

    Args:
        location: The city to get the weather for.
        days: The number of days for the weather forecast (e.g. 1).

    Returns:
        list: A list of flight information dictionaries matching the request criteria.
    """
    url = "https://davinci-weather.nutc-imac.com/api/v1/weather"
    body = {
        "q": location,
        "days": days
    }

    try:
        # 發送 POST 請求
        response = requests.post(url, json=body)
        response.raise_for_status()  # 檢查回應狀態碼

        # 解析 JSON 回應
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        print(f"請求失敗，錯誤: {e}")
        return []

def get_flight_info(DepartureAirportID: str, ArrivalAirportID: str, ScheduleStartDate: str, ScheduleEndDate: str) -> list:
    """
    Returns flight information based on the provided request.

    Args:
        ScheduleStartDate: The schedule start date in the format 'YYYY-MM-DD'.
        ScheduleEndDate: The schedule end date in the format 'YYYY-MM-DD'.
        DepartureAirportID: The departure airport code.
        ArrivalAirportID: The question should refer to the airport code for a single destination, not the code for all airports in a region.

    Returns:
        list: A list of flight information dictionaries matching the request criteria.
    """
    return "中華航空: 2021-09-01 08:00, 2021-09-01 10:00 ,長榮航空: 2021-09-01 08:00, 2021-09-01 10:00"

all_tools = {
    "get_weather_info": get_weather_info,
    "get_flight_info": get_flight_info,
}

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
    # 沒有先上傳檔案詢問會有問題
    agent = graph_manager.get_agent()
    input_message = HumanMessage(content=f"{question}")
    if agent != None:
        snapshot = agent.get_state(config=config)
        value = snapshot.next[0] if 0 < len(snapshot.next) else None
        if len(snapshot.next) >= 1 and len(snapshot.values["messages"]) > 0:
            feed_back = question
            for event in agent.stream(Command(resume=feed_back), config=config, stream_mode="values"):
                if not event["messages"][-1].content:
                    yield ''
                yield event["messages"][-1].content.encode("utf-8")
        else:
            for event in agent.stream({"messages": [input_message]}, config=config, stream_mode="values"):
                # for value in event.values():
                #     print("value", value)
                #     print("Assistant:", value["messages"][-1].content)
                #     print("Graph Event:", event)
                if not event["messages"][-1].content:
                    yield ''
                elif event["messages"][-1].content == []:
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

# class Graph:
#     def __init__(self, tools):
#         # all_tools 就是我的痊癒列表 調整順序的tool必須包含在痊癒列表中 否則會報錯
#         self.tools = [dynamic_functions[tool] for tool in tools]
#         self.agent = self.build_graph(0)

#     def build_graph(self, start_index):
#         tool = self.tools[start_index]
#         sub_graph = SubGraph(tool)
#         # Build graph
#         builder = StateGraph(State)
#         #  Node
#         # tool_node = ToolNode([get_weather_info_tool_gemma])

#         builder.add_node(sub_graph.main_agent)
#         # builder.add_node(sub_graph.first_ask)
#         builder.add_node(sub_graph.is_trigger_function_calling)
#         builder.add_node(sub_graph.ask_human)
#         builder.add_node(sub_graph.extract_parameters_from_user_feedback)
#         builder.add_node("tools", ToolNode([tool]))
#         if start_index != len(self.tools) - 1:
#             builder.add_node("next_graph", self.build_graph(start_index+1))
#             # builder.add_conditional_edges("main_agent", sub_graph.llm_call, ["is_trigger_function_calling", "next_graph"])
#             builder.add_conditional_edges("main_agent", sub_graph.llm_call, ["ask_human", "tools", END, "next_graph"])
#         else:
#             pass
#             # builder.add_conditional_edges("main_agent", sub_graph.llm_call_to_end, ["is_trigger_function_calling", END])
#             builder.add_conditional_edges("main_agent", sub_graph.llm_call_to_end, ["ask_human", "tools", END])
#         # Edge
#         builder.add_edge(START, "main_agent")
#         # builder.add_conditional_edges("is_trigger_function_calling", ,["ask_human", "tools", END])
#         # builder.add_edge("main_agent", "is_trigger_function_calling")
#         # builder.add_edge("first_ask", "is_trigger_function_calling")
#         # builder.add_edge("ask_human", "extract_parameters_from_user_feedback")
#         builder.add_edge("ask_human", "extract_parameters_from_user_feedback")
#         builder.add_edge("extract_parameters_from_user_feedback", "tools")
#         builder.add_edge("tools", "main_agent")
#         # Compile graph
#         memory = MemorySaver()
#         self.graph = builder.compile(checkpointer=memory)
        
#         self.save_graph(self.graph, tool.__name__)
#         return self.graph
    
#     def save_graph(self,graph, name):
#         try:
#             png_data = graph.get_graph().draw_mermaid_png()
#             output_file = name+  ".png"
#             with open(output_file, "wb") as f:
#                 f.write(png_data)
#             print(f"圖形已保存到: {output_file}")
#         except Exception as e:
#             print(f"無法保存圖形：{str(e)}")

# class SubGraph:
#     def __init__(self, tool):
#         self.tool = tool
#         self.querys = {tool.__name__ : querys[tool.__name__]}
#         self.llm = ChatOllama(
#                 model="llama3.2:3b",
#                 temperature=0,
#             ).bind_tools([tool], parallel_tool_calls=False)
#         self.sys_msg = SystemMessage(
#             content="""
#             You are an AI Agent equipped with various tools to help you complete tasks. You should automatically determine whether these tools are needed based on the user's request. 
#             If you can directly answer the question, do not generate a tool message.
            
#             Based on the context provided, follow these steps to determine if a tool call is necessary:

#             1. Summarize the Direction: Analyze the user's question and summarize the direction of the inquiry (e.g., issue resolution, information retrieval, decision-making) to confirm if it aligns with the functionality of the tool.
#             2. Parameter Validation: Ensure that all parameters required for the tool call can be directly extracted from the user's question.
            
#             If either condition is not met, do not proceed with the tool call.
#             Instead, provide a response through regular question-and-answer logic
                
#             """)

#     def main_agent(self, state: State):
#         try:
#             output = []
#             state["tool_use"] = []
#             if state["messages"] and isinstance(state["messages"][-1], ToolMessage):
#                 state["tool_use"].append(state["messages"][-1].name)
#             # 如果tool_use不包含當前tool檔案的名稱，代表尚未執行，詢問使用者題目。
#             if self.tool.__name__  not in state["tool_use"]:
#                 print("abc", state)
#                 user_question = state["messages"][0].content
#                 question = HumanMessage(content=f"{user_question} If the information is not present in the question, please do not make up an answer.")
#                 sys_prompt = SystemMessage(content="You are a smart AI agent. Please help me look up the precise function and its arguments that need to be called based on the question.?")
#                 output = self.llm.invoke([sys_prompt, question])
#                 return {"messages": output, "empty_args": [], "tool_use": state["tool_use"]}
#             #     print("a"*10)
#                 # prompt = self.querys[self.tool.__name__]
#                 # question = state["messages"][-1].content
#             return {"messages": [], "empty_args": [], "tool_use": state["tool_use"]}
#         except Exception as e:
#             print("e"*10, e)
#             return {"error": str(e)}

#     def is_trigger_function_calling(self, state: State) -> Command[Literal["ask_human", "tools", END]]:
        
#         messages = state["messages"]
#         print("aa", state)
#         # answer = interrupt("test")
#         # print("aws", answer)
#         print("\nis_trigger_function_calling_messages", messages)
#         last_message = messages[-1]
#         print("\nis_trigger_function_calling_last_message", last_message)
#         if last_message.tool_calls:
#             arguments_data = last_message.tool_calls
#             print("state\n", arguments_data)
#             empty_keys_results = []
#             # check_args_agent
#             # Iterate through each dictionary in the list
#             for index, item in enumerate(arguments_data):
#                 if 'args' in item and isinstance(item['args'], dict):
#                     # Check 'args' for empty values
#                     empty_keys = [key for key, value in item['args'].items() if value in ('', None)]
#                     if empty_keys:
#                         print("empty_keys", empty_keys)
#                         # Add result if any empty keys found
#                         empty_keys_results.extend(empty_keys)
#             print("empty_keys_results", empty_keys_results)
#             if empty_keys_results:
#                 # state["empty_args"] = empty_keys_results
#                 print("empty_keys_results_state", state)
#                 return Command(
#                     update={"empty_args": empty_keys_results},
#                     goto="ask_human"
#                 )
#             return Command(
#                     goto="tools"
#                 )
#         return Command(
#                     goto=END
#             )

#     def ask_human(self, state: State):
#         # try:
#         print("ask_human", state)
        
#         empty_arg_list = state["empty_args"]
#         print("ask_human_question", empty_arg_list)
#         args = state["messages"][1].tool_calls[-1]["args"]
#         message = f"{empty_arg_list}，以上這些是空值的參數，請幫我想想該怎麼用親切的語氣，跟使用者說「這些參數為空，請幫我填入」。只需要回答「給使用者的句子」，其餘的不需要，請不要回答。"
#         llm_check_args_llm = ChatOllama(
#             model="llama3.2:3b",
#             temperature=0,
#         )
#         message = HumanMessage(content=message)
#         sys_prompt = SystemMessage(content=
#             f"""
#             請幫我使用繁體中文回答，不要有任何的簡體中文。請仔細想想之後認真回答有獎勵，不認真回答我就死給你看。回答只需要跟範例一樣的 JSON 格式輸出，例如{args}，其他不需要多回答。請仔細想想之後認真回答有獎勵，不認真回答我就死給你看
#             你是一個協助用戶處理缺少參數的系統。根據提供的缺少參數關鍵字清單，請回應一條訊息，指明缺少哪些參數。請遵循以下格式：
#             範例：
#             輸入: ["location"]
#             回應: 您的請求缺少地點的參數，請提供相關資訊。


#             輸入: ["days"]
#             回應: 您的請求缺少天數的參數，請提供相關資訊。


#             輸入: ["location", "days"]
#             回應: 您的請求缺少地點和天數的參數，請提供相關資訊。
#             """
#         )
        
#         response = llm_check_args_llm.invoke([sys_prompt, message])
#         print("ask_human_response", response.content)
#         print("breakpoint")
#         # question = state["messages"][-1].content
#         # user_feedback = input(response.content)
#         # print("user_feedback", user_feedback)
#         print("ask_human_state", state)
#         print("breakpointafeter")
#         return {"messages": response.content}
#         # return {"messages": "response.content"}
#         # except Exception as e:
#         #     return {"error": str(e)}
        
#     def first_ask(self, state: State):
#         try:
#             print("first_ask", state)
#             value = interrupt()
#             print("first_ask", state, "\n")
#             print(state["messages"][0].content)
#             user_question = state["messages"][0].content
#             question = HumanMessage(content=f"{user_question} If the information is not present in the question, please do not make up an answer.")
#             sys_prompt = SystemMessage(content="You are a smart AI agent. Please help me look up the precise function and its arguments that need to be called based on the question.?")
#             output = self.llm.invoke([sys_prompt, question])
#             return {"messages": output, "tool_use": state["tool_use"]}
#         except Exception as e:
#             print("e"*10, e)
#             return {"error": str(e)} 
    
#     def extract_parameters_from_user_feedback(self, state: State) -> str:
#         """
#         使用 LLM 提取參數，回傳 dict 格式的參數鍵值對
#         """
#         # try:
#         print("extract_parameters_from_user_feedback_state_1", state)
#         answer = interrupt("test")
#         print("answer", answer)
#         del state["messages"][-1]
#         print("aws", answer)
#         print("extract_parameters_from_user_feedback_state_2", state)
#         print("extract_parameters_state\n", state)
#         llm_param_extractor = ChatOllama(
#             model="llama3.2:3b",
#             temperature=0,
#         )
#         ref_args = state["messages"][-2].tool_calls[-1]["args"]
#         print("ref_args", ref_args)
#         sys_prompt = SystemMessage(content=
#             f"""
#             請使用英文回答
#             假設你是一個專門提取關鍵參數的模型，用戶可能輸入與天氣、地點、航班等等的任何資訊。你的任務是分析用戶的輸入，根據內容以及參考的 {ref_args} JSON 格式，動態提取參數，並輸出結果。
#             要求：
#             1. 請根據用戶輸入的內容，動態匹配參數類型並輸出對應的 JSON。所有結果必須嚴格遵循模板格式{ref_args}
#             2. 若根據用戶輸入的內容，沒有和參考資料格式匹配的參數類型並輸出對應的 JSON，則輸出 {{"error": "無法提取關鍵參數"}}。
#             3. 禁止在輸出中增加模板未定義的字段。例如，不能多出 "error": null 或其他額外資訊。
#             4. 禁止輸出任何多餘的文字說明或解釋，只輸出 JSON 格式。
#             5. 僅輸出用戶提供的資料，若用戶未提供某些參數，則不要在輸出中包含這些參數。
#             """
#         )
#         #請使用英文回答，另外除了JSON其餘不用回答。
#         print("sys_prompt\n", sys_prompt)
#         question = state["messages"][-1].content
#         # question = "Taipei"
#         extract_message = HumanMessage(content=f"{question}")
#         print("extract\n", extract_message)
#         response = llm_param_extractor.invoke([sys_prompt, extract_message])
#         print("a"*10)
#         print("a"*10, "\n")
#         print(response.content)
#         data = response.content.replace("'", '"')
#         extracted_data = json.loads(data)
#         print("bbbb")
#         print("extract_parameters\n", extracted_data)
#         state["messages"][1].tool_calls[-1]["args"].update(extracted_data)
#         # print("state", state["messages"][1])
#         state["messages"][1].response_metadata["message"]["tool_calls"][0]["function"]["arguments"].update(extracted_data)
        
#         print("state", state)
#         print('state["messages"][1]', state["messages"][1])
#         print('state["messages"][1]', type(state["messages"][1]))
#         output = state["messages"][-2]
#         # del state["messages"][-1]
#         # del state["messages"][-1]
#         # 嘗試解析成 JSON 格式
#         return {"messages": output}
#         # except Exception as e:
#         #     print("e"*10, e)

#     def llm_call(self,state: State) -> Command[Literal["next_graph", "is_trigger_function_calling"]]:
#         # 如果執行過就不要再執行了
#         if self.tool.__name__ in state["tool_use"]:
#             return "next_graph"
#         else:
#             messages = state["messages"]
#             print("aa", state)
#             print("\nis_trigger_function_calling_messages", messages)
#             last_message = messages[-1]
#             print("\nis_trigger_function_calling_last_message", last_message)
#             if last_message.tool_calls:
#                 arguments_data = last_message.tool_calls
#                 print("state\n", arguments_data)
#                 empty_keys_results = []
#                 # check_args_agent
#                 # Iterate through each dictionary in the list
#                 for index, item in enumerate(arguments_data):
#                     if 'args' in item and isinstance(item['args'], dict):
#                         # Check 'args' for empty values
#                         empty_keys = [key for key, value in item['args'].items() if value in ('', None)]
#                         if empty_keys:
#                             print("empty_keys", empty_keys)
#                             # Add result if any empty keys found
#                             empty_keys_results.extend(empty_keys)
#                 print("empty_keys_results", empty_keys_results)
#                 if empty_keys_results:
#                     print("empty_keys_results_state", state)
#                     state["empty_args"] = empty_keys_results
#                     return "ask_human"
#                 return "tools"
#             return END
#             # return "first_ask"
#             # return "is_trigger_function_calling"
        
#     def llm_call_to_end(self,state: State):
#         if self.tool.__name__ in state["tool_use"]:
#             return END
#         else:
#             messages = state["messages"]
#             print("aa", state)
#             print("\nis_trigger_function_calling_messages", messages)
#             last_message = messages[-1]
#             print("\nis_trigger_function_calling_last_message", last_message)
#             if last_message.tool_calls:
#                 arguments_data = last_message.tool_calls
#                 print("state\n", arguments_data)
#                 empty_keys_results = []
#                 # check_args_agent
#                 # Iterate through each dictionary in the list
#                 for index, item in enumerate(arguments_data):
#                     if 'args' in item and isinstance(item['args'], dict):
#                         # Check 'args' for empty values
#                         empty_keys = [key for key, value in item['args'].items() if value in ('', None)]
#                         if empty_keys:
#                             print("empty_keys", empty_keys)
#                             # Add result if any empty keys found
#                             empty_keys_results.extend(empty_keys)
#                 print("empty_keys_results", empty_keys_results)
#                 if empty_keys_results:
#                     print("empty_keys_results_state", state)
#                     state["empty_args"] = empty_keys_results
#                     return "ask_human"
#                 return "tools"
#             return END
#             # return "first_ask"
#             # return "is_trigger_function_calling"

if __name__=="__main__":
    dynamic_functions = {
        "get_weather_info_tool": get_weather_info_tool,
        "get_flight_info_tool": get_flight_info_tool
    }

    config_2 = {
        "tool_function_list": ["get_weather_info_tool","get_flight_info_tool"]
    }
    agent = Graph(config_2["tool_function_list"]).build_graph(0)

    for event in agent.stream({"messages": ["這兩天天氣如何？"]}, config=config, stream_mode="values"):
        print("event", event)
        print("event_aa", event["messages"][-1].content)

