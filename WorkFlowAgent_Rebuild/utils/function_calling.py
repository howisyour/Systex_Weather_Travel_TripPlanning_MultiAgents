import importlib.util
import time
import types
import os

import ollama
from fastapi import UploadFile
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import BaseTool, StructuredTool
from langchain_ollama import ChatOllama
from openai import OpenAI
from transformers import pipeline

from tools.gemma_tools import *
from tools.langchain_tools import *
from utils.convert_to_tool import *
from utils.model_loader import loader
from utils.langgraph_function_calling import graph_manager


# NEW FETURE: 新增上傳plugin機制
dynamic_functions_google_schema = []
dynamic_functions = {}


def mutiple_plugin_generate_function_code(api_input_payload):
    functions = []

    for data in api_input_payload['data']:
        # 檢查字典是否為空
        if not data:
            continue
        function_name = data['name']
        description = data['descrition']
        arguments = data['argument']
        function_content = data['function_content']

        # 生成函數定義
        function_def = f"@tool\ndef {function_name}({', '.join([f'{arg}: str' for arg in arguments])}) -> list:"

        # 生成文檔字符串
        docstring = f'''    """{description}

    Args:
{chr(10).join([f"        {arg} (str): The {arg.replace('ID', '')} {arg.replace('ID', '').lower()}." for arg in arguments])}

    Returns:
        list: A list of flight information dictionaries matching the request criteria.
    """'''

        print("function_content.strip()", function_content.strip())
        # 生成函數主體
        function_body = textwrap.indent(textwrap.dedent(f'''\
            {function_content.strip()}
            
            if response.status_code == 200:
                return response.json()
            else:
                return f"Request failed with status code: {{response.status_code}}"
        '''), '    ')

        # 組合完整的函數代碼
        full_function = f"{function_def}\n{docstring}\n{function_body}"
        functions.append((full_function, function_name))

        with open('new_file2.txt', 'w') as file:
            file.write(full_function)
    return functions

def save_uploaded_file(uploaded_file: UploadFile, destination: str):
    with open(destination, "wb") as buffer:
        buffer.write(uploaded_file.file.read())

def dynamic_import(module_name, module_path):
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if callable(attr) and isinstance(attr, types.FunctionType):
                schema = create_schema_from_function(attr)
                dynamic_functions_google_schema.append(schema)
                dynamic_functions[attr_name] = attr
        return module
    except Exception as e:
        print("dynamic_import_ERROR\n", e)

def remove_tools_files(files):
    folder_path = "/home/ubuntu/bowei/systex-local-rag-system-poc/backend/tools"
    for file_name in files:
        print("file_name", file_name)
        file_path = os.path.join(folder_path, file_name)
        if os.path.exists(file_path):
            spec = importlib.util.spec_from_file_location(file_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and isinstance(attr, types.FunctionType):
                    schema = create_schema_from_function(attr)
                    dynamic_functions_google_schema.remove(schema)
                    del dynamic_functions[attr_name]
        os.remove(file_path)

def upload_tools_files(files):
    global graph_manager
    global dynamic_functions_google_schema
    global dynamic_functions
    try:
        print("upload_tools", files)
        for uploaded_file in files:
            file_path = f"/home/ubuntu/bowei/systex-local-rag-system-poc/backend/tools/{uploaded_file.filename}"
            with open(file_path, "wb") as buffer:
                buffer.write(uploaded_file.file.read())
            file_name = os.path.splitext(uploaded_file.filename)[0]
            spec = importlib.util.spec_from_file_location(file_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and isinstance(attr, types.FunctionType):
                    schema = create_schema_from_function(attr)
                    print("a"*10)
                    dynamic_functions_google_schema.append(schema)
                    print("a"*10)
                    dynamic_functions[attr_name] = attr
        print("a"*10)
        # langgraph 暫放
        config_2 = {
            "tool_function_list": ["get_weather_info_tool","get_flight_info_tool"]
        }

        graph_manager.create_graph(config_2["tool_function_list"])
        print("graph_instance\n", graph_manager)
    except Exception as e:
        print("upload_tools_ERROR\n", e)

async def send_message_to_llama_use_Ollama(question: str):
    try:
        translated_question = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant with access to the following functions. Use them if required -"},
                {"role": "user", "content": f"Please help me translate the following sentence into English, and do not respond with any other text, including quotation marks.\n\n {question}"},
            ],
            stream=False,
        )
        translated_question = translated_question['message']['content']
        print("dynamic_functions", dynamic_functions_google_schema)
        start_time = time.time()
        response = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant with access to the following functions. Use them if required -"},
                {"role": "user", "content": f"{translated_question} If the information is not present in the question, please do not make up an answer."},
            ],
            stream=False,
            tools=dynamic_functions_google_schema
        )
        end_time = time.time()
        print(f"LLM 回答問題耗時: {end_time - start_time} 秒")
        if 'tool_calls' in response['message'].keys():
            for tool in response["message"]["tool_calls"]:
                function_args = tool['function']['arguments']
                if "" in function_args.values():
                    yield "缺少參數"
                print("tool", tool)
                print("dynamic_functions", dynamic_functions)
                function_to_call = dynamic_functions.get(tool['function']['name'], "")
                if function_to_call == "":
                    yield "找不到對應的function"
                print("function_to_call", function_to_call)
                function_response = function_to_call(**function_args)
                print("function_response", function_response)
                if type(function_response) == list:
                    function_response = function_response[:5]
                # BUG :請llm整理資料如果prompt沒下好，回答會有問題
                # --- streaming ---  若要改成非串流，以下astream改成invoke、return改用yield
                """
                llm_normal.invoke(f"{function_response} 請根據上述資料整理之後使用繁體中文回答，千萬不要使用簡體中文"):
                """
                data_response = ollama.chat(
                    model="llama3.2:3b",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant with access to the following functions. Use them if required -"},
                        {"role": "user", "content": f"{function_response} 請根據上述資料整理之後使用繁體中文回答，千萬不要使用簡體中文"},
                    ],
                    stream=True,
                    keep_alive=0
                )
                for chunk in data_response:
                    yield chunk['message']['content'].encode('utf-8')
        else:
            yield response['message']['content']
    except Exception as e:
        print("send_message_to_llama_use_Ollama_ERROR", e)

async def send_message_to_llama_use_langchain(question: str):
    try:
        print("send_message_to_llama")
        llm_main = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
        ).bind_tools(tools=list(dynamic_functions.values()))
        llm_normal = ChatOllama(
            model="llama3.2:3b",
            temperature=0,
        )
        # BUG: System prompt 會影響llm model的回答
        PROMPT = "You are a smart AI agent. Please help me look up the precise function and its arguments that need to be called based on the question.?"
        prompt_template = f"""{PROMPT}
            # 使用者問題
            Question: {{question}}
        """
        chain = (
            {"content": lambda x: """
            As a proficient AI, your task is to analyze the user's request and identify the most suitable function to execute. Subsequently, extract the necessary arguments for the function from the user's input. Provide your response in JSON format, including the keys 'function' and 'arguments'. Within 'function', specify the 'name' of the function. Under 'arguments', present a dictionary where keys represent the function's parameters and values are extracted from the user's input.
            """, "question": RunnablePassthrough()}
            | ChatPromptTemplate.from_template(prompt_template)
            | llm_main
        )
        translated = llm_normal.invoke(
            f"Please help me translate the following sentence into English, and do not respond with any other text, including quotation marks.\n\n {question}")
        # 如果不懂問題的內容就回答不知道，不要亂回答
        response = chain.invoke(
            f"{translated.content} If the information is not present in the question, please do not make up an answer.")
        # BUG: 需加上如何判斷llm是否要做function calling
        if response.response_metadata["message"].get("tool_calls") is not None:
            if response.response_metadata["message"]:
                # available_functions = {
                #     'validate_user': validate_user,
                #     'get_temperature_humidity_tool': get_temperature_humidity_data,
                #     'get_flight_info_tool': get_flight_info_tool,
                #     'get_weather_info_tool': get_weather_info_tool
                # }
                # BUG: 使用者把tool寫錯了怎麼辦？ or 參數有幻覺？ or 有些參數是不需要的？
                for tool in response.response_metadata["message"]["tool_calls"]:
                    print("tool", tool)
                    print("dynamic_functions", dynamic_functions)
                    function_to_call = dynamic_functions[tool['function']['name']]
                    print("function_to_call", function_to_call)
                    function_args = tool['function']['arguments']
                    function_response = function_to_call.func(**function_args)
                    print("function_response", function_response)
                    if type(function_response) == list:
                        function_response = function_response[:5]
                    # BUG :請llm整理資料如果prompt沒下好，回答會有問題
                    # --- streaming ---  若要改成非串流，以下astream改成invoke、return改用yield
                    """
                    llm_normal.invoke(f"{function_response} 請根據上述資料整理之後使用繁體中文回答，千萬不要使用簡體中文"):
                    """
                    start_time = time.time()
                    async for chunk in llm_normal.astream(f"{function_response} 請根據上述資料整理之後使用繁體中文回答，千萬不要使用簡體中文"):
                        print("chunk.content\n", chunk.content)
                        if chunk.content:
                            yield chunk.content
                    end_time = time.time()
                    print(f"LLM 回答問題耗時: {end_time - start_time} 秒")
            else:
                yield response.content
        else:
            print(f"Unexpected response type: {response}")
            yield response.content
    except Exception as e:
        print("e"*10, e)

async def send_message_to_gemma(question: str):
    try:
        print("dynamic_functions", dynamic_functions_google_schema)
        print("send_message_gemma", question)
        # 若模型未載入，則載入模型
        if loader.status == False:
            loader.load_model("DiTy/gemma-2-9b-it-function-calling-GGUF")
            print("model", loader.status)
        print("model_loader", loader.status)
        model = loader.model
        tokenizer = loader.tokenizer
        print("model\n", model)

        # define pipeline
        generation_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

        translated_question = generation_pipeline(
            [
                {"role": "system", "content": "You are a professional translation engine. Please help me translate my questions into English."},
                {"role": "user", "content": f"{question}"},
            ],
            max_new_tokens=256        
        )[0]["generated_text"][-1]["content"]

        # Step 1: Apply chat template
        history_messages = [
            {"role": "system", "content": "You are a helpful assistant with access to the following functions. Use them if required -  and If the information is not present in the question, please do not make up an answer."},
            {"role": "user", "content": f"{translated_question}"},
        ]
        inputs = tokenizer.apply_chat_template(
            history_messages,
            tokenize=False,
            add_generation_prompt=True,  # adding prompt for generation
            tools=dynamic_functions_google_schema,
        )

        terminator_ids = [
            tokenizer.eos_token_id,
            tokenizer.convert_tokens_to_ids("<end_of_turn>"),
        ]

        outputs = generation_pipeline(
            inputs,
            max_new_tokens=512,
            eos_token_id=terminator_ids,
        )
        print("outputs", outputs)
        print("output", outputs[0]["generated_text"][len(inputs):])

        # 使用正則表達式匹配字典部分
        match = re.search(r'Function call: ({.*})', outputs[0]["generated_text"][len(inputs):])
        
        if match:
            dict_str = match.group(1)
            print("Extracted dict string:", dict_str)
            # 將字串轉換為字典
            tool = json.loads(dict_str)
            if "" in tool.values():
                yield "缺少參數"
            print("tool", tool)
            function_to_call = dynamic_functions[tool["name"]]
            print("function_to_call", function_to_call)
            function_args = tool["arguments"]
            function_response = function_to_call(**function_args)
            print("function_response", len(function_response))
            if type(function_response) == list and len(function_response) != 0:
                function_response = function_response[0]
                print("function_response", function_response)
            elif type(function_response) == dict:
                function_response = function_response["current"]
            response = generation_pipeline(
                [
                    {"role": "system", "content": "Please provide a comprehensive and professional response in Traditional Chinese characters only. Do not use Simplified Chinese characters in your answer."},
                    {"role": "user", "content": f"{function_response}"},
                ],
                max_new_tokens=256,
                batch_size=64
            )[0]["generated_text"][-1]["content"]
            for i in response:
                yield i
        else:
            yield outputs[0]["generated_text"][len(inputs):]
        loader.unload_model_and_tokenizer()
    except Exception as e:
        print("e"*10, e)
        yield {"error": str(e)}

def send_message_to_gemma_with_tgi(question: str):
    try:
        client = OpenAI(
            base_url="http://10.20.1.97:8080/v1/",
            api_key="-"
        )
        start_time = time.time()
        chat_completion = client.chat.completions.create(
            model="tgi",
            messages=[
                {"role": "system", "content": "You are a helpful assistant with access to the following functions. Use them if required -"},
                {"role": "user", "content": f"{question}"}
            ],
            tools=dynamic_functions_google_schema,
        )
        end_time = time.time()
        print(f"LLM 回答問題耗時: {end_time - start_time:.4f} 秒")
    except Exception as e:
        print("send_message_to_gemma_with_tgi ERROR\n"*10, e)