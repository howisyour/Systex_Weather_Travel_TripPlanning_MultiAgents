# 這個檔案暫時沒用到
import os
import getpass
import json

# from lang_graph.main.about_file import upload_tools_files


def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

import os
import getpass
import json
import threading
# import time
from concurrent.futures import ThreadPoolExecutor, Future
# import gradio as gr

# from langgraph.types import Command
from lang_graph.main.graph import graph_instance
# from lang_graph.main.supervisor import graph_instance, supervisor
from lang_graph.main.config import thread, initial_input

# task_stop = threading.Event()
class Main:
    def __init__(self):
        # self.now_graph_index = graph.now_graph_index
        self.now_compile_graph = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.current_task: Future = None
        self.future = None
        self.task_stop = threading.Event()

    def __del__(self):
        self.executor.shutdown(wait=True)

    # 將詢問的function 用一個thread去執行
    # chatbot, tools_hints, state
    def start(self, agent, question): #, prompt, tools_hints, messageList=[]
        self.task_stop.clear()
        # current_task = self.executor.submit(getResponse, prompt, tools_hints, messageList)
        self.current_task = self.executor.submit(graph_instance.ask_graph, self.task_stop, agent, question)
        for data in self.current_task.result():
            # if self.task_stop.is_set():
            #     break
            print("data:", data)
            yield data
        # return current_task.result()[0], current_task.result()[1], current_task.result()[2]
        

    async def stop(self):
        try:
            if self.current_task:
                self.task_stop.set()
                self.current_task.cancel()  # 盡可能嘗試取消線程
            self.current_task = None
        except:
            print('thread timeout')
        # global task_stop
        # global current_task
        
        # if current_task and not current_task.done():
        #     print("取消中")
        #     task_stop = True
        #     return "Task canceled"
        # return "No Task can be canceled"


    def start_graph(self, _input, graph):
        global task_stop
        for event in graph.stream(_input, thread, stream_mode="values", subgraphs=True):
            if not task_stop:
                event[1]["messages"][-1].pretty_print()
                print("message type:", event[1]["messages"][-1].type)
                if event[1]["messages"][-1].type == "ai" and len(event[1]["messages"][-1].tool_calls) == 0:
                    print("AI Message:"+event[1]["messages"][-1].content)
                    state = graph.get_state(thread, subgraphs=True)
                    task_state = state.tasks
                    return event[1]
            else:
                task_stop = False
                return "Task canceled"

main = Main()

# if __name__ == "__main__":
    # _set_env("OPENAI_API_KEY")
    # _set_env("TAVILY_API_KEY")
    # save_graph(app, "workflow")
    # test()



# 為什麼要初始化？      
# def initialize(index, _input={"messages": ""}, messageList=[], is_canceled=False):
#     global graph
#     global now_graph_index
#     global now_compile_graph

#     now_compile_graph = graph.all_compile_graphs[index]
#     now_compile_graph_state = now_compile_graph.get_state(thread).values
#     # 判斷是否有缺少參數
#     if is_canceled and now_compile_graph_state['args_missing_funcname'] != "":
#         # 有缺參數的話，將缺少的參數從tool_use中移除
#         now_compile_graph_state['tool_use'].remove(now_compile_graph_state['args_missing_funcname'])
#         now_compile_graph_state['args_missing_funcname'] = ""
#         # 更新當前的graph狀態
#         now_compile_graph.update_state(thread, now_compile_graph_state)
#     else:
#         now_compile_graph.update_state(thread, _input)    
#     now_graph_index = index
#     event = start(initial_input, now_compile_graph)
#     responeMessage = event["messages"][-1].content
#     return responeMessage


# 什麼時候要把訊息存到messageList
# def updateMessageList(message, role, messageList):
#     try:
#         messageList.append({
#             "role": role,
#             "content": message,
#         })
#     except Exception as e:
#         print(f"Error: {e}")

#     return messageList

# 呼叫子圖Agent
# def getResponse(prompt, tools_hints, messageList=[]):
#     global graph
#     global now_graph_index
#     global now_compile_graph
#     # 使用者輸入
#     # updateMessageList(prompt, "user", messageList)
#     # 取得當前graph實例的狀態
#     state = now_compile_graph.get_state(thread, subgraphs=True)

#     # 判斷"next_graph" 不存在 state.next
#     if "next_graph" not in state.next:
#         # 不存在就代表已經到最後一個節點
#         event = start_graph(Command(resume=prompt), now_compile_graph)
#         responeMessage = event["messages"][-1].content if not isinstance(event, str) else event
#         updateMessageList(responeMessage, "assistant", messageList)
        
#         state = now_compile_graph.get_state(thread, subgraphs=True)
#         if isinstance(event, str):
#             tools_hints = initialize(now_graph_index, messageList=messageList, is_canceled=True)
#         elif "next_graph" in state.next:
#             tools_hints = initialize(now_graph_index + 1, event, messageList)
#     # 存在就代表還有下一個graph，回傳下一個graph的提示
#     return messageList, tools_hints, ""

# 請給我Taipei 2024/12/05的天氣
# 請給我2024/12/05 台灣前往東京的航班
# 請給我一天的天氣

# if __name__ == "__main__":
#     config = json.load(open("config.json", "r", encoding="utf-8"))
    # # graph = Graph(config["tool_function_list"]).build_graph(0)


    # thread = {"configurable": {"thread_id": "2"}}

    # # Initial input
    # initial_input = {"messages": "",
    #                  "tool_use": []}

    # # graph.invoke(initial_input, thread, stream_mode="values")

    # for event in graph_instance.stream(initial_input, thread, stream_mode="values"):
    #     # print("Event:", event)
    #     event["messages"][-1].pretty_print()

    # for event in graph.stream(initial_input, thread, stream_mode="values", interrupt_after=["human_feedback"]):
    #     # print("Event:", event)
    #     event["messages"][-1].pretty_print()