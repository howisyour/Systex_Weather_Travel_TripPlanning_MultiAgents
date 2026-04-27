from langchain_ollama import ChatOllama
from datetime import datetime
import pytz
from lang_graph.main.about_file import dynamic_functions_google_schema
from lang_graph.main.state import State
from lang_graph.main.config import thread, initial_input
from typing_extensions import TypedDict, Annotated
from pydantic import BaseModel
import json
import re
from typing import Literal
from langchain_core.messages import SystemMessage, HumanMessage


# Supervisor負責導向到不同的子圖Agent
class Supervisor:
    def __init__(self):
        # self.tool = tool
        # self.llm = ChatOllama(
        #     model="llama3.2:3b",
        #     temperature=0,
        # ).bind_tools([tool], parallel_tool_calls=False)
        self.llm_with_no_tool = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
        )
        # self.members = graph_instance.tools_str + ["FINISH"]        
        self.sys_prompt = """
            You are a Supervisor Agent responsible for assigning the most suitable subgraph Agent based on user input.
            If you respond seriously, you will be rewarded; if you do not respond seriously, you will be scolded.

            Your primary task is to use your reasoning ability to identify the most appropriate subgraph Agent for the given user input.
            The currently available subgraph Agents are:
            {tool}

            Instructions:

            STAGE 1: Input Validation (Highest Priority)
            Validate whether there is any user input. If there is no input, reply with "not found" immediately.

            STAGE 2: Input Analysis
            Analyze the user input to identify keywords and intent.

            STAGE 3: Match Input with Each Agent's Capability
            Select the Agent that matches the description of the subgraph based on the question.

            STAGE 4: Select an Agent Only When Input Clearly Matches Its Domain
            Select an Agent only if the input clearly matches the domain of that Agent.

            STAGE 5: Choose an Agent Only When the Query Is Relevant to the Agent's Domain
            Only assign an Agent if the user’s query is “highly relevant” to that subgraph Agent’s scope of functionality.
            
            Carefully analyze the user’s request and choose the most suitable subgraph Agent. If no relevant subgraph Agent is available, reply with “None.”
            
            Important Notes:
                If there is ambiguity or you cannot make a determination, always reply with “None.”
                Do not arbitrarily assign an unrelated subgraph Agent just to provide an answer.
                Carefully analyze the user’s request and choose the most suitable subgraph Agent. If no relevant subgraph Agent is available, reply with “None.”
            
            System time: {system_time}
            """
                    
    def gateway(self, question,  subgraphs_list, rule="normal", current_agent=None): #-> Command[Literal[*members, "__end__"]]
        
        print("-"*50)
        """
        如果問題為空值，假設為初始化或者是觸發graph
        若不為空值，則有可能是問問題或者是使用回饋
        """
        agent = None
        result = []
        print("dynamic_functions_google_schema",dynamic_functions_google_schema)
        pattern = r"<<(.*?)>>"
        matches = re.findall(pattern, question)
        agent_name_list = list(subgraphs_list.keys())
        print("--------------------------------agnet name list--------------------------")
        print(agent_name_list)
        
        if not matches:
            q = (question or "").strip()
            if not q:
                return None

            # Deterministic keyword routing (avoid expensive/fragile LLM routing for clear intents)
            q_lower = q.lower()

            # Weather intent
            if any(k in q for k in ["天氣", "溫度", "下雨", "降雨", "濕度"]):
                return subgraphs_list.get("weather_info")

            # Flight schedule intent (highest priority when user mentions schedule/time)
            if any(k in q for k in ["航班時刻", "時刻表", "時刻", "班表", "航班", "起飛", "抵達"]):
                return subgraphs_list.get("flight_info")

            # Flight discount intent
            if any(k in q for k in ["優惠", "折扣", "特價", "促銷", "便宜", "機票"]):
                return subgraphs_list.get("discount")

            # Sticky follow-up: if we already have a current agent but no clear routing keywords
            # were found (often user is just supplying arguments), keep the current agent.
            if current_agent is not None:
                return current_agent

            # **** Newest Fixed Order Process ****
            for i, item in enumerate(dynamic_functions_google_schema, 1):
                # 獲取函數名稱和描述
                name = item['function']['name']
                description = item['function']['description']
                
                # 創建格式化的字符串並添加到列表中
                formatted_string = f"{i}. {name} - {description}"
                result.append(formatted_string)

            data = "\n".join(result)
            sys_prompt = self.sys_prompt.format(
                tool = data,
                system_time=datetime.now(tz=pytz.utc).astimezone(pytz.timezone('Asia/Taipei')).isoformat(),
                
            )
            sys_prompt = SystemMessage(content=sys_prompt)
            question = HumanMessage(content=f"Based on the user's input, precisely determine which subgraph agent should be used. \n User Input: {question}")
            
            # print("self------\n", sys_prompt)
            # print("question-----------\n", question)
            # 有回饋就使用當前的實例
            # if graph_instance.current_ins:
            #     agent = graph_instance.current_ins
            # 沒有就使用透過llm做決策導向該導向的子圖
            # BUG: 目前有llm會無法精確做出導向子圖的決策
            # else:
            response = self.llm_with_no_tool.with_structured_output(Router).invoke([sys_prompt, question])

            # If model cannot confidently map to any domain, stop routing.
            if response.agent == "None":
                return current_agent

            # Guard against schema/config drift between Router literals and subgraph keys.
            if response.agent not in subgraphs_list:
                return current_agent

            # agent = graph_instance.subgraphs_list[response["agent"]]
            # supervisor 需要目前子圖Agent的列表 ，基本上這個東西再構建原本的圖的時候應該就會固定了，至於如果要分多個人用我後續再想看看
            agent = subgraphs_list[response.agent]
            # matched_dicts = list(filter(lambda item: item.get('function', {}).get('name') == agent_name_list[agent_list_index], dynamic_functions_google_schema))
            # agent = subgraphs_list[agent_name_list[agent_list_index]]
            
            return agent
            # for data in graph_instance.ask_graph(agent=agent, question=question):
            #     print("graph_instance.ask_grap", data)
            #     if data:
            #         print("data", data)
            #         yield data
                    # chatbot_history[-1] = gr.ChatMessage(
                    #     role="assistant",
                    #     content = data
                    #     # content=event["messages"][-1].content
                    # )
                    # yield (
                    #     gr.update(value=""),
                    #     chatbot_history
                    # )
            # goto = response["next"]
            # if goto == "FINISH":
            #     goto = END

            # return Command(goto=goto)
            # print("test")
        else:
            agent_tail = list(matches)[0]
            if(not (agent_tail=="skip" or agent_tail=="previous" or agent_tail=="stop" or agent_tail=="restart")):
                matched_dicts = list(filter(lambda item: item.get('function', {}).get('name') == agent_tail, dynamic_functions_google_schema))
                if matched_dicts:
                    return subgraphs_list[matched_dicts[0]["function"]["name"]]
            else:
                current_agent_name = next((k for k, v in subgraphs_list.items() if v == current_agent), None)
                current_step_index = agent_name_list.index(current_agent_name)
                if (agent_tail=="skip"):
                    print("skipping agent")
                    if(current_step_index < len(agent_name_list)):
                        current_step_index+=1
                        next_ageent_name = agent_name_list[current_step_index]
                        matched_dicts = list(filter(lambda item: item.get('function', {}).get('name') == next_ageent_name, dynamic_functions_google_schema))
                        if matched_dicts:
                            return subgraphs_list[matched_dicts[0]["function"]["name"]]
                    # 我要怎麼知道現在處理的agent是?
                elif(agent_tail=="pervious"):
                    if(current_step_index > 0):
                        current_step_index-=1
                        pervious_ageent_name = agent_name_list[current_step_index]
                        matched_dicts = list(filter(lambda item: item.get('function', {}).get('name') == pervious_ageent_name, dynamic_functions_google_schema))
                        if matched_dicts:
                            return subgraphs_list[matched_dicts[0]["function"]["name"]]
                elif(agent_tail=="stop"):
                    print("stop")
                elif(agent_tail=="restart"):
                    current_step_index=0
                    restart_agent_name = agent_name_list[current_step_index]
                    matched_dicts = list(filter(lambda item: item.get('function', {}).get('name') == restart_agent_name, dynamic_functions_google_schema))
                    if matched_dicts:
                        return subgraphs_list[matched_dicts[0]["function"]["name"]]


class Router(BaseModel):
    """
    precisely determine which subgraph agent should be used. 
    If no relevant subgraph agent is found, reply with None.
    Do not arbitrarily assign an unrelated subgraph Agent just to provide an answer.
    """
    
    agent: Literal["attraction_info", "weather_info", "discount", "flight_info", "None"]

# supervisor = graph_instance.create_supvisor()
supervisor = Supervisor()