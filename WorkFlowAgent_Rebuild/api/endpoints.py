import os
import asyncio
from fastapi import APIRouter, File, UploadFile, Body
from fastapi.responses import StreamingResponse
from typing import List
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser

from utils.function_calling import (
    remove_tools_files,
    upload_tools_files,
    send_message_to_gemma,
    send_message_to_llama_use_Ollama,
)
from utils.langgraph_function_calling import ask_langgraph
# from utils.each_agent import ask_langgraph

# from lang_graph.trip_a import ask_langgraph

router = APIRouter()

@router.get("/get_files_in_folder")
def get_files_in_folder():
    """從資料夾中獲取檔案清單"""
    folder_path = "/home/ubuntu/bowei/function_calling_prod/tools"
    try:
        files = os.listdir(folder_path)
        return [f for f in files if os.path.isfile(os.path.join(folder_path, f))]
    except Exception as e:
        return [f"Error: {e}"]


@router.delete("/remove_tools")
def remove_tools(payload: dict = Body(...)):
    """刪除選中的檔案"""
    try:        
        files = payload["selected_files"]
        remove_tools_files(files)
        return "OK"
    except Exception as e:
        print("remove_tools_ERROR\n", e)


@router.post("/upload_tools")
async def upload_tools(files: list[UploadFile] = File(...)):
    try:
        upload_tools_files(files)
        # BUG: 預期加入藉由dynamic_functions長度，來判斷讀取tool是否成功(可能還需要進度條？)，但是不負責判斷程式碼內的內容
        # return {"message": "Functions generated successfully", "functions": list(dynamic_functions.keys())}
    except Exception as e:
        return {"generate_function_error": str(e)}


@router.post("/generate_function_not_file")
async def generate_function(payload: dict = Body(...)):
    try:
        functions = mutiple_plugin_generate_function_code(payload)
        for function_code, function_name in functions:
            print("function_code", function_code)
            # 動態執行生成的函數代碼
            exec(function_code, globals())
            # 將函數添加到動態函數字典中
            dynamic_functions[function_name] = globals()[function_name]
        return {"message": f"Function {function_name} generated successfully", "function_code": function_code}
    except Exception as e:
        return {"error": str(e)}

@router.post("/ask")
async def stream_chat(payload: dict = Body(...)):
    """
        測試case:s
        Case 1 今天台中天氣如何?(O)
        Case 2 今天東京天氣如何(O)
        Case 3 今天天氣如何(X)
        Case 4 幫我查詢2024年10月28號台北到大阪的航班(O)
        Case 5 幫我查詢2024年10月28號到大阪的航班(X)
        Case 6 幫我查詢2024年10月28號台北起飛的航班(X)
        Case 7 幫我查詢台北到大阪的航班(X)
        case 8 明天會放颱風假嗎？(X)
    """
    try:
        print("問題：", payload)
        # 達哥 payload
        # query = payload["query"][-1]["content"]
        # 非達哥 payload
        query = payload["content"]
        model_type = payload.get("model_type", "llama")  # 默認使用llama模型
        if model_type == "gemma":
            print("gemma問題：", query)
            generator = send_message_to_gemma(query)
            # result = send_message_to_gemma_with_tgi(query)
        elif model_type == "langgraph":
            generator = ask_langgraph(query)
        else:
            generator = send_message_to_llama_use_Ollama(query)
        return StreamingResponse(generator, media_type="application/json")
    except Exception as e:
        print("e"*10, e)
        return {"error": str(e)}

@router.post("/ask_not_streaming")
async def process_string(payload: dict = Body(...)):
    try:
        query = payload["query"]
        available_tools = list(dynamic_functions.values())
        PROMPT = "You are a smart AI agent. Please help me look up the precise function and its arguments that need to be called based on the question.?"
        prompt_template = f"""{PROMPT}
            # 使用者問題
            Question: {{question}}
        """
        llm_main = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
        ).bind_tools(available_tools)

        llm_normal = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
            keep_alive="0s"
        )
        chain = (
            {"content": lambda x: """
            As a proficient AI, your task is to analyze the user's request and identify the most suitable function to execute. Subsequently, extract the necessary arguments for the function from the user's input. Provide your response in JSON format, including the keys 'function' and 'arguments'. Within 'function', specify the 'name' of the function. Under 'arguments', present a dictionary where keys represent the function's parameters and values are extracted from the user's input.
            """, "question": RunnablePassthrough()}
            | ChatPromptTemplate.from_template(prompt_template)
            | llm_main
        )
        # 動態更新可用的工具
        translated = llm_normal.invoke(
            f"「{query}」 請將括號中的文字轉換成英文，除了翻譯不要回答任何文字，包含上下引號")
        print("translated", translated)
        # 如果不懂問題的內容就回答不知道，不要亂回答
        response = chain.invoke(
            f"{translated} If the information is not present in the question, please do not make up an answer.")

        # BUG: 需加上如何判斷llm是否要做function calling
        """
        有tool_calls，就做function calling
        沒有tool_calls，就直接回傳response.content
        """
        if response.response_metadata["message"].get("tool_calls") is not None:
            for tool in response.response_metadata["message"]["tool_calls"]:
                function_to_call = dynamic_functions.get(
                    tool['function']['name'])
                if function_to_call:
                    # --- not stream
                    function_args = tool['function']['arguments']
                    function_response = function_to_call.func(**function_args)
                    print("function_response", function_response)
                    if function_response is None:
                        return {f"[ERROR] Function {tool['function']['name']} returned None"}
                    result = llm_normal.invoke(
                        f"{function_response} 請根據上述資料整理之後使用繁體中文回答，千萬不要使用簡體中文")
                    return result.content
                else:
                    return {"error": f"Function {tool['function']['name']} not found"}
        else:
            return response.content
    except Exception as e:
        print("error", e)
        return {"error": str(e)}

from fastapi import FastAPI, Request
@router.post("/run_graph")
async def run_graph(payload: dict = Body(...)):
    # 获取 API 输入数据
    input_data = payload["content"]
    print("Received API input:", input_data)

    # 将 API 接收的数据作为初始输入给图
    # initial_input = {"input": input_data.get("input", "default input")}
    # print("Initial input to graph:", initial_input)
    generator = ask_langgraph(input_data)
    return StreamingResponse(generator, media_type="application/json")
