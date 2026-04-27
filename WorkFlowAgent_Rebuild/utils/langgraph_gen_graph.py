from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
import threading

# from utils.function_calling import dynamic_functions_google_schema, dynamic_functions
from utils.langgraph_function_calling import main_agent, is_trigger_function_calling, ask_human, extract_parameters_from_user_feedback
from tools.gemma_get_weather_info_tool_gemma import get_weather_info_tool_gemma


class State(MessagesState):
    empty_args: list

# # older
# class GraphManager:
#     _instances = {}
#     _lock = threading.Lock()

#     def __new__(cls, thread_id="1"):
#         with cls._lock:
#             if thread_id not in cls._instances:
#                 cls._instances[thread_id] = super(GraphManager, cls).__new__(cls)
#                 cls._instances[thread_id]._initialize_graph()
#                 cls._instances[thread_id].save_graph()
#         return cls._instances[thread_id]

#     def _initialize_graph(self):
#         builder = StateGraph(State)
#         builder.add_edge(START, "main_agent")
#         builder.add_edge("main_agent", "is_trigger_function_calling")
#         builder.add_edge("ask_human", "extract_parameters_from_user_feedback")
#         builder.add_edge("extract_parameters_from_user_feedback", "tools")
#         builder.add_edge("tools", "main_agent")

#         tool_node = ToolNode([get_weather_info_tool_gemma])
#         builder.add_node(main_agent)
#         builder.add_node(is_trigger_function_calling)
#         builder.add_node(ask_human)
#         builder.add_node(extract_parameters_from_user_feedback)
#         builder.add_node("tools", tool_node)


#         memory = MemorySaver()
#         self.agent = builder.compile(
#             checkpointer=memory,
#             # This is new!
#             interrupt_before=["extract_parameters_from_user_feedback"],
#             # Note: can also interrupt __after__ tools, if desired.
#             # interrupt_after=["tools"]
#         )

#         self.workflow = StateGraph(MessagesState)

#         # self.workflow.add_node("main_agent", main_agent)
#         # self.workflow.add_node("tools", tool_node)
#         # self.workflow.add_node("ask_human", ask_human)
#         # # 根據需要添加其他節點
#         # self.workflow.add_edge(START, "main_agent")
#         # self.workflow.add_conditional_edges("main_agent", is_trigger_function_calling, ["ask_human", "tools", END])

#         # self.memory = MemorySaver()
#         # self.agent = self.workflow.compile(checkpointer=self.memory)

#     def get_agent(self):
#         return self.agent

#     def update_graph(self, new_nodes=None, new_edges=None):
#         with self._lock:
#             if new_nodes:
#                 for node_name, node in new_nodes.items():
#                     self.workflow.add_node(node_name, node)
#             if new_edges:
#                 for edge in new_edges:
#                     self.workflow.add_edge(*edge)
#             # 重新編譯 agent
#             self.agent = self.workflow.compile(checkpointer=self.memory)

#     def save_graph(self):
#         try:
#             png_data = self.agent.get_graph().draw_mermaid_png()
#             output_file = "graph.png"
#             with open(output_file, "wb") as f:
#                 f.write(png_data)
#             print(f"圖形已保存到: {output_file}")
#         except Exception as e:
#             print(f"無法保存圖形：{str(e)}")
