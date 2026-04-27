from collections import OrderedDict
import threading
import json, os
from concurrent.futures import ThreadPoolExecutor, Future

from configs.configs import GRAPH_SAVED_DIR

from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from lang_graph.main.tools import all_tools
from lang_graph.main.subgraph import SubGraph
from lang_graph.main.state import State
from lang_graph.main.supervisor import Supervisor
from lang_graph.main.config import initial_input, thread
from lang_graph.main.rag_subgraph import RagSubGraph

class Graph:
    def __init__(self, tools, agent_type, checkpointer=MemorySaver()):
        self.tools = [all_tools[tool] for tool in tools]         # self.tools = [dynamic_functions[tool] for tool in tools]
        self.tools_str = tools
        self.current_ins = None
        self.subgraphs_list = OrderedDict() 
        self.checkpointer = checkpointer
        self.agent_type = agent_type
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.task_stop = threading.Event()
        self.current_task: Future = None
        
    def __del__(self):
        self.executor.shutdown(wait=True)

    def create_supvisor(self):
        builder = StateGraph(State)
        # 建構子圖中邏輯需要graph的一些狀態，因此傳給底下的
        supervisor = Supervisor()
        builder.add_node("supervisor", supervisor.gateway)
        builder.add_edge(START, "supervisor")
        for subgraph_key, subgraph_ins in self.subgraphs_list.items():
            builder.add_node(subgraph_key, subgraph_ins)

        memory = MemorySaver()
        graph = builder.compile(checkpointer=memory)
        self.save_graph(graph)
        return graph

    def build_graph(self, start_index):
        tool = self.tools[start_index]
        tool_str = self.tools_str[start_index]
        print("tool_str------\n", tool_str)
        agent_type = self.agent_type[start_index]
        print("agent_type----\n", agent_type)
        next_tool_str = self.tools_str[start_index+1] if start_index + 1 < len(self.tools_str) else END
        sub_graph = SubGraph(self, tool)
        rag_instance = RagSubGraph()
        # Build graph
        # 先建立langgrpah需要的點
        builder = StateGraph(State)
        builder.add_node("human_feedback", sub_graph.human_feedback)
        builder.add_node("get_user_input", sub_graph.get_user_input)
        if agent_type==0:
            # builder.add_node("normal_llm", sub_graph.normal_llm) # Origin function
            builder.add_node("normal_llm", sub_graph.no_func_llm)
        elif agent_type==1:
            builder.add_node("assistant", sub_graph.assistant)
            builder.add_node("tools", ToolNode([tool]))
            builder.add_node("arg_assistant", sub_graph.arg_assistant)
        elif agent_type==2:
            builder.add_node("retrieve", rag_instance.rag_node)  # retrieve
            builder.add_node("grade_documents", rag_instance.grade_documents)  # grade documents
            builder.add_node("generate", rag_instance.generate)  # generatae
            # builder.add_node("transform_query", rag_instance.transform_query)  # transform_query
            builder.add_node("keyword_search_node", rag_instance.web_search)  # web search
        
        # 根據不同類型連結不同的點
        builder.add_edge(START, "human_feedback")
        if agent_type==0:
            builder.add_edge("get_user_input", "normal_llm")
            builder.add_edge("normal_llm", "human_feedback")
        elif agent_type==1:
            builder.add_conditional_edges("get_user_input", sub_graph.llm_call, ["assistant", "arg_assistant"])
            builder.add_conditional_edges(
                "assistant",
                sub_graph.tools_condition_edge,
                ["tools", "human_feedback"]
            )
            builder.add_edge("arg_assistant", "assistant")
            builder.add_edge("tools", "human_feedback")

        elif agent_type==2:
            # Build graph
            builder.add_edge("get_user_input", "retrieve")
            builder.add_edge("retrieve", "grade_documents")
            builder.add_conditional_edges(
                "grade_documents",
                rag_instance.decide_to_generate,
                {
                    "keyword_search_node": "keyword_search_node",
                    "generate": "generate",
                },
            )
            builder.add_edge("keyword_search_node", "generate")
            builder.add_edge("generate", "human_feedback")
            
        # 迭代建立子圖
        if start_index != len(self.tools) - 1:
            print("迭代建立子圖")
            print(f"next_tool_str: {next_tool_str}")
            print("-"*15)
            builder.add_node(next_tool_str, self.build_graph(start_index+1))
            # Do not auto-advance to the next subgraph. After producing an answer/tool result,
            # end this run and wait for the next user message to be routed by Supervisor.
            builder.add_conditional_edges("human_feedback", sub_graph.go_to_end_or_get_user_input, [END, "get_user_input"])
        else:
            builder.add_conditional_edges("human_feedback", sub_graph.go_to_end_or_get_user_input, [END, "get_user_input"])
        
        
        # Compile graph
        graph = builder.compile(checkpointer=MemorySaver())
        
        self.subgraphs_list[tool_str] = graph
        self.save_graph(graph, tool.__name__)
        return graph

    def save_graph(self, graph, name="langgrph"):
        # 儲存 graph
        try:
            output_dir = GRAPH_SAVED_DIR
            os.makedirs(output_dir, exist_ok=True)  # 確保資料夾存在
            png_data = graph.get_graph(xray=1).draw_mermaid_png()
            output_file = os.path.join(output_dir, f"{name}.png")
            print(f"Graph output path: {output_file}")
            with open(output_file, "wb") as f:
                f.write(png_data)
        except Exception as e:
            print(f"無法保存圖形：{str(e)}")

    def ask_graph(self, agent=None, question=None):
        self.current_ins = agent
        # 後續有instance時，都給當前的
        """
        values example:

        updates example:
            ((), {'human_feedback': {'messages': [AIMessage(content='請根據以下內容輸入你想查詢的天氣: 地名, 天數\n', additional_kwargs={}, response_metadata={}, id='51df0f83-db5a-4f30-b641-4f6383096250')], 'tool_use': [], 'args_missing_funcname': '', 'tool_calls_args': {}, 'empty_args': {}, 'condition': 'assistant'}})
        """
        # ----updates
        snapshot = agent.get_state(config=thread)
        print("agent_state", snapshot)
        value, task = "", ""
        if snapshot:
            if snapshot.next and snapshot.tasks:
                value, task = snapshot.next[0], snapshot.tasks[0]            
        self.task_stop.clear()
        self.current_task = self.executor.submit(self._stream_graph, agent, question)
        for data in self.current_task.result():
            yield data
    
    def _stream_graph(self, agent, question): # 新增一個執行緒執行的函數
        for data in agent.stream(question, thread, stream_mode="updates", subgraphs=True):
            output = ""
            if self.task_stop.is_set():
                break
            if data[1].get("human_feedback", ""):
                messages = data[1]["human_feedback"].get("messages") or []
                if messages and messages[-1].type == "ai" and len(messages[-1].tool_calls) == 0:
                    output = messages[-1].content
            yield output
        
    async def stop_ask_graph(self):
        try:
            if self.current_task:
                self.task_stop.set()
                self.current_task.cancel()  # 盡可能嘗試取消線程
            self.current_task = None
        except:
            print('thread timeout')
            
    def get_agent_state(self):
        if self.current_ins:
            return self.current_ins.get_state(config=self.thread)
                
    @staticmethod
    def get_subgraphs(self):
        return self.subgraphs_list

_HERE = os.path.dirname(__file__)
config = json.load(open(os.path.join(_HERE, "config.json"), "r", encoding="utf-8"))
graph_instance = Graph(config["tool_function_list"], config["type"])
graph_instance.build_graph(0)
