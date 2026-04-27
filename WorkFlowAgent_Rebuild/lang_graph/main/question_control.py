import os
import getpass
import json
import threading
# import time
from concurrent.futures import ThreadPoolExecutor, Future
# import gradio as gr

# from langgraph.types import Command
# from lang_graph.main.graph import graph_instance
# from lang_graph.main.supervisor import graph_instance, supervisor
from lang_graph.main.config import thread, initial_input

# task_stop = threading.Event()
class QuestionControl:
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
        # self.current_task = self.executor.submit(graph_instance.ask_graph, self.task_stop, agent, question)
        # return self.current_task
        # return self.executor.submit(graph_instance.ask_graph, self.task_stop, agent, question)
        # for data in self.current_task.result():
        #     # if self.task_stop.is_set():
        #     #     break
        #     print("data:", data)
        #     yield data
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


    # def start_graph(self, _input, graph):
    #     global task_stop
    #     for event in graph.stream(_input, thread, stream_mode="values", subgraphs=True):
    #         if not task_stop:
    #             event[1]["messages"][-1].pretty_print()
    #             print("message type:", event[1]["messages"][-1].type)
    #             if event[1]["messages"][-1].type == "ai" and len(event[1]["messages"][-1].tool_calls) == 0:
    #                 print("AI Message:"+event[1]["messages"][-1].content)
    #                 state = graph.get_state(thread, subgraphs=True)
    #                 task_state = state.tasks
    #                 return event[1]
    #         else:
    #             task_stop = False
    #             return "Task canceled"
    
qc_instance = QuestionControl()