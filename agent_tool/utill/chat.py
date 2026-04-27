import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()
from model.requset import ChatRequest
# from configs.configs import OLLAMA_BASE_URL, OPENAI_API_KEY


class Chat:

    def __init__(self):
        self.ollama_url = f"{os.getenv('OLLAMA_BASE_URL')}/api/generate"
        self.openai_url = "https://api.openai.com/v1/chat/completions"
        self.openai_key = os.getenv("OPENAI_API_KEY")

    def chat(self, chat_request: ChatRequest) -> str:
        if chat_request.model == "gpt-4o":
            return self.call_openai(chat_request)
        else:
            return self.call_ollama(chat_request)

    def call_openai(self, chat_request: ChatRequest) -> str:
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "gpt-4o",
            "messages": []
        }
        if chat_request.system_prompt:
            body["messages"].append({"role": "system", "content": chat_request.system_prompt})
        if chat_request.prompt:
            body["messages"].append({"role": "user", "content": chat_request.prompt})

        response = requests.post(self.openai_url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']

    def call_ollama(self, chat_request: ChatRequest) -> str:
        payload = {
            "model": chat_request.model or "llama3.1:8b",
            "prompt": chat_request.prompt or "",
            "system": chat_request.system_prompt or "",
            "stream": False
        }
        response = requests.post(self.ollama_url, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")
