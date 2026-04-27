import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from model.requset import attraction_info_Request


class Attraction:
    API_ENDPOINT = "https://serpapi.com/search"

    def __init__(self):
        env_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(dotenv_path=env_path, override=False)
        self.default_api_key = os.getenv("SERPAPI_API_KEY")

    def get_attraction_info(self, request: attraction_info_Request) -> dict:
        if not request.q:
            raise ValueError("請提供 q（搜尋關鍵字）")

        api_key = request.api_key or self.default_api_key
        if not api_key:
            raise ValueError("請提供 api_key 或設定環境變數 SERPAPI_API_KEY")

        params: dict = {
            "engine": request.engine or "google_local",
            "q": request.q,
            "num": request.num or 20,
            "api_key": api_key,
            "hl": request.hl or "zh-tw",
            "gl": request.gl or "jp",
        }
        if request.location:
            params["location"] = request.location

        response = requests.get(self.API_ENDPOINT, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
