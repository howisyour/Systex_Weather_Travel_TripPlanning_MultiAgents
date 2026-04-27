import requests
import datetime
import re
from dotenv import load_dotenv
import os
from utill.Locale_tran import LOCATION_ALIASES, STATE_ALIASES
from pathlib import Path

# from configs.configs import WEATHER_API_KEY, WEATHER_BASE_URL
from model.requset import WeatherRequest


class Weather():
    GEO_BASE_URL = "https://api.openweathermap.org/geo/1.0/direct"
    ZIP_BASE_URL = "https://api.openweathermap.org/geo/1.0/zip"
    ZIP_PATTERN = re.compile(r"^(?=.*\d)[A-Za-z0-9\-\s]+,[A-Za-z]{2}$")

    
    def __init__(self):
        env_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(dotenv_path=env_path, override=False)
        self.api_key = os.getenv("WEATHER_API_KEY")
        self.url = os.getenv("WEATHER_BASE_URL")
        # self.api_key = WEATHER_API_KEY
        # self.url = WEATHER_BASE_URL

    def _normalize_search_state(self, search_state: str | None) -> str | None:
        if not search_state:
            return None
        normalized_state = search_state.strip().lower()
        return STATE_ALIASES.get(normalized_state, normalized_state)

    def _normalize_location(self, location: str | None) -> str | None:
        if not location:
            return None
        normalized_location = location.strip()
        return LOCATION_ALIASES.get(normalized_location, normalized_location)

    def _normalize_date(self, date_value: str | None) -> str | None:
        if not date_value:
            return None
        normalized_date = date_value.strip()
        if "T" in normalized_date:
            normalized_date = normalized_date.split("T", 1)[0]
        return normalized_date or None

    def _normalize_days(self, days: int | None, default: int) -> int:
        if days is None:
            return default
        return max(1, days)

    def _request_json(self, url: str, params: dict) -> dict:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def _resolve_location(self, location: str) -> dict:
        normalized_location = self._normalize_location(location)
        if not normalized_location:
            raise ValueError("請提供 location")

        if self.ZIP_PATTERN.match(normalized_location):
            zip_data = self._request_json(
                self.ZIP_BASE_URL,
                {
                    "zip": normalized_location,
                    "appid": self.api_key,
                },
            )
            return {
                "name": zip_data.get("name", normalized_location),
                "lat": zip_data["lat"],
                "lon": zip_data["lon"],
                "country": zip_data.get("country", ""),
            }

        geo_data = self._request_json(
            self.GEO_BASE_URL,
            {
                "q": normalized_location,
                "limit": 5,
                "appid": self.api_key,
            },
        )
        if not geo_data:
            raise ValueError(f"找不到地點：{location}")
        return geo_data[0]

    def _get_current_weather(self, location_info: dict) -> dict:
        return self._request_json(
            f"{self.url}/weather",
            {
                "lat": location_info["lat"],
                "lon": location_info["lon"],
                "units": "metric",
                "lang": "zh_tw",
                "appid": self.api_key,
            },
        )

    def _get_forecast_weather(self, location_info: dict) -> dict:
        return self._request_json(
            f"{self.url}/forecast",
            {
                "lat": location_info["lat"],
                "lon": location_info["lon"],
                "units": "metric",
                "lang": "zh_tw",
                "appid": self.api_key,
            },
        )
        
    def weather_summary_forecast(self, data: dict, days: int = 3, start_date: str = None) -> str:
        city = data['city']['name']
        country = data['city']['country']
        forecast_by_day = {}

        for entry in data['list']:
            date = entry['dt_txt'].split(" ")[0]
            forecast_by_day.setdefault(date, []).append(entry)

        sorted_dates = sorted(forecast_by_day.keys())
        if start_date:
            sorted_dates = [d for d in sorted_dates if d >= start_date]

        summaries = []
        for date in sorted_dates[:days]:
            entries = forecast_by_day[date]
            temps = [e['main']['temp'] for e in entries]
            avg_temp = sum(temps) / len(temps)
            conditions = list(set(e['weather'][0]['description'] for e in entries))
            condition_summary = "，".join(conditions)
            summaries.append(f"{date}：{condition_summary}，平均溫度 {avg_temp:.1f}°C。")

        return f"地點：{city}, {country}\n" + "\n".join(summaries)


    def weather_summary_current(self, data: dict) -> str:
        city = data['name']
        country = data.get('sys', {}).get('country', '')
        temp = data['main']['temp']
        condition = data['weather'][0]['description']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']

        return (
            f"地點：{city}{', ' + country if country else ''}，"
            f"目前天氣：{condition}，溫度 {temp}°C，"
            f"濕度：{humidity}%，風速：{wind_speed} m/s"
        )
    
    def get_history_weather(self, request):
        normalized_date = self._normalize_date(request.date)
        if not normalized_date:
            return "[錯誤] 查詢歷史天氣需要 date，格式為 YYYY-MM-DD。"

        return (
            f"[歷史天氣目前不支援] 目前 agent_tool 已統一使用 OpenWeather。"
            f"現有設定未包含可用的歷史天氣端點，無法查詢 {normalized_date} 的歷史資料。"
        )
    
    def wheather(self, request: WeatherRequest) -> str:
        results = []
        normalized_state = self._normalize_search_state(request.search_state)

        if not normalized_state:
            return "[錯誤] 請提供 search_state，可用值為 current、forecast、history。"

        if not request.location:
            return "[錯誤] 請提供 location。"

        try:
            if normalized_state == "current":
                location_info = self._resolve_location(request.location)
                current_data = self._get_current_weather(location_info)
                results.append(f"[即時天氣]\n{self.weather_summary_current(current_data)}")

                forecast_days = self._normalize_days(request.days, 1)
                if request.days is not None and forecast_days > 0:
                    forecast_data = self._get_forecast_weather(location_info)
                    summary = self.weather_summary_forecast(
                        forecast_data,
                        days=forecast_days,
                        start_date=self._normalize_date(request.date),
                    )
                    results.append(f"[未來 {forecast_days} 天天氣預報]\n{summary}")

            elif normalized_state == "forecast":
                location_info = self._resolve_location(request.location)
                forecast_data = self._get_forecast_weather(location_info)
                forecast_days = self._normalize_days(request.days, 3)
                summary = self.weather_summary_forecast(
                    forecast_data,
                    days=forecast_days,
                    start_date=self._normalize_date(request.date),
                )
                results.append(f"[未來 {forecast_days} 天天氣預報]\n{summary}")

            elif normalized_state == "history":
                results.append(self.get_history_weather(request))

            else:
                return "[錯誤] search_state 僅支援 current、forecast、history。"
        except requests.exceptions.HTTPError as exc:
            return f"[錯誤] 天氣查詢失敗：{exc.response.status_code} {exc.response.reason}"
        except Exception as exc:
            return f"[錯誤] 天氣查詢失敗：{str(exc)}"

        return "\n\n".join(results)


    
if __name__ == "__main__":
    # 可使用 "python3 -m utill.weather" 進行測試
    
    tdx_service = Weather()
    
    current_request = WeatherRequest(search_state="current", location="taipei")
    
    history_request = WeatherRequest(search_state="history", location="taipei", date="2025-03-22", days=3)
    
    forecast_request = WeatherRequest(search_state="forecast", location="taipei", days=3)
    
    international_flights = tdx_service.wheather(history_request)
    print(international_flights)