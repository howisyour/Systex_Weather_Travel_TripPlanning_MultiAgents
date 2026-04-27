import gradio as gr
import requests
import json
import os
import re, time
import subprocess
import signal
import copy

from langgraph.types import interrupt, Command
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from configs.configs import FAST_UPLOAD_PARH, FAST_GETTOOLS_PARH, FAST_REMOVEDTOOLS_PARH

from lang_graph.main.graph import graph_instance
from lang_graph.main.supervisor import supervisor
from lang_graph.main.config import initial_input
from lang_graph.main.question_control import qc_instance
# from lang_graph.main.app import main
chatbot_history = []
agent_step_index = 0

def start(question, model, chatbot_history):
    # chatbot_history = []
    if question == "":
        return (
            gr.Info("請輸入問題"),
        )

    chatbot_history.append(
        gr.ChatMessage(
            role="user",
            content=question.replace("<", "&lt;").replace(">", "&gt;")
        )
    )
    
    agent = supervisor.gateway(question=question, subgraphs_list=graph_instance.subgraphs_list, rule="normal", current_agent=graph_instance.current_ins)
    question = re.sub(r"<<.*?>>\s*", "", question).strip()

    if agent is None: # TODO:可以串完成的Chat使用ollama做回覆
        # Do not continue previous graph state when supervisor intentionally returns None.
        chatbot_history.append(
            gr.ChatMessage(
                role="assistant",
                content="目前沒有對應的 Agent，可再補充需求（例如：出發地、目的地、日期）。"
            )
        )
        yield gr.update(value=""), gr.update(value=chatbot_history)
        return

    if agent == graph_instance.current_ins:
        print("the same agent")
        # Only resume if this graph is actually waiting for an interrupt.
        try:
            snapshot = agent.get_state(config=graph_instance.thread)
            waiting_for_input = bool(getattr(snapshot, "next", None)) and (snapshot.next[0] == "get_user_input")
        except Exception:
            waiting_for_input = False

        if waiting_for_input and question:
            question = Command(resume=question)
        else:
            one_shot_input = copy.deepcopy(initial_input)
            one_shot_input["feedback"] = question
            one_shot_input["condition"] = "direct_input"
            question = one_shot_input
    else:
        # One-shot: first message should be used as the subgraph query, not only for routing.
        one_shot_input = copy.deepcopy(initial_input)
        one_shot_input["feedback"] = question
        one_shot_input["condition"] = "direct_input"
        question = one_shot_input
    
    
    for data in graph_instance.ask_graph(agent=agent, question=question):
        split_pattern = r"(\((?:航班優惠 Agent|航班查詢 Agent|天氣 Agent|旅遊規劃 Agent)\).*)"
        parts = re.split(split_pattern, data.strip())
        
        for part in parts:
            if part.strip():
                chatbot_history.append(gr.ChatMessage(
                    role="assistant",
                    content=part.strip()
                ))
                
                yield gr.update(value=""), gr.update(value=chatbot_history)

async def stop():
    print("stop")
    await graph_instance.stop_ask_graph()
    print("stop2")
    # yield (gr.update(interactive=False))
    

def upload_file(files: list):
    """
    Upload a list of files to a server with retry logic.

    Parameters:
    files (list): A list of file paths to be uploaded.

    Returns:
    None
    """
    try:
        # print("Uploading file(s):", files)
        if files:
            session = requests.Session()
            retries = Retry(total=5, backoff_factor=0.1)
            session.mount('http://', HTTPAdapter(max_retries=retries))

            with open(str(files[0]), 'rb') as f:
                files_data = [
                    ('files', (os.path.basename(str(file)), open(str(file), "rb")))
                    for file in files
                ]                
                response = session.post(
                    FAST_UPLOAD_PARH,
                    files=files_data
                )
            print("Upload successful")
    except Exception as e:
        print("Upload error:", e)

def get_files_in_folder():
    try:
        # url path 要修改
        response = requests.get(FAST_GETTOOLS_PARH)
        if response.status_code == 200:
            print("檔案清單:", response.json())
            print("檔案清單類型:", type(response.json()))
        else:
            print("獲取檔案清單失敗:", response.json())
        return gr.Dropdown(choices=response.json(), interactive=True) 
    except Exception as e:
        return [f"Error: {e}"]

def restart_fastapi():
    try:
        process = subprocess.Popen(
            ["python", "fastapi_app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ FastAPI 已啟動 fastapi_app.py")
        return process
    except Exception as e:
        print(f"FastAPI 啟動失敗: {e}")
        return None

def remove_selected_files(selected_files: list):
    try:
        print("selected_files:", selected_files)
        print("type(selected_files):", type(selected_files))
        if selected_files:
            # 測試刪除選中的檔案
            print("selected_files:", selected_files)
            response = requests.delete(FAST_REMOVEDTOOLS_PARH, json={'selected_files': selected_files})
            if response.status_code == 200:
                print("刪除結果:", response.json())
                return gr.update(value=[])
            else:
                print("刪除檔案失敗:", response.json())
        else:
            gr.Info("請選擇檔案")
    except Exception as e:
        return [f"Error: {e}"]

with gr.Blocks(title="Demo") as gradio:
    with gr.Tab("Function_Calling"):
        with gr.Row():
            with gr.Column():
                model_type = gr.Dropdown(
                    ["default", "llama", "gemma", "langgraph"], label="選擇模型", info="可不選擇模型，預設為llama3.2:3b（llama: 使用llama3.2:3b模型, gemma: 使用gemma模型）"
                )

                fc_qa_textbox = gr.Textbox(label="輸入問題")
                
                send_question_button = gr.Button(
                    value="送出"
                )
                
                stop_btn = gr.Button(value="停止", interactive=True)
        with gr.Row():
            fc_qa_chatbot = gr.Chatbot(
                height=700,
                layout="bubble",
                type="messages",
                label="聊天文字框",
                group_consecutive_messages=False
            )

    send_question_button.click(
        start,
        inputs=[
            fc_qa_textbox,
            model_type,
            fc_qa_chatbot
        ],
        outputs=[
            fc_qa_textbox,
            fc_qa_chatbot
        ],
    )

    stop_btn.click(
        stop,
        inputs=None,
        outputs=None
    )

    

if __name__ == "__main__":
    
    fastapi_process = restart_fastapi()
    
    gradio.queue(max_size=None).launch(share=False, ssl_verify=False,
        debug=True, server_name="0.0.0.0", server_port=5469)

    if fastapi_process:
        fastapi_process.terminate()
    
