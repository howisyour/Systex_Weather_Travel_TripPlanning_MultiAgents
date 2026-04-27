import requests
import json
from datetime import datetime


from configs.configs import (
    TRAINSPORT_SEARCH_TOOLS,
    WEATHER_DAYS_MAPPING,
    WEATHER_LOCATION_MAPPING,
    WEATHER_SEARCH_TOOLS,
)

today = datetime.today().strftime('%Y-%m-%d')

def weather_info(location: str, date: str, days: str) -> list:
    """
    Retrieves weather details, including temperature and conditions, for a specified location.

    Args:
        location: The city to get the weather for. type must be string.
        date: The date of day for start weather forecast.
        days: The number of days for the weather forecast.

    Returns:
        list: A list of flight information dictionaries matching the request criteria.
    """
    
    search_state = "current"
    if date:
        today_str = datetime.today().strftime('%Y-%m-%d')
        today = datetime.strptime(today_str, '%Y-%m-%d')
        input_date = datetime.strptime(date, '%Y-%m-%d')

        if input_date < today:
            search_state = "history"
        elif input_date == today:
            search_state = "current"
        else:
            search_state = "forecast"
    
    if location:
        location = WEATHER_LOCATION_MAPPING.get(location, location)
    
    # date is expected to be in YYYY-MM-DD format; do NOT map it via location mapping.
    
    if days:
        mapped_days = WEATHER_DAYS_MAPPING.get(days)
        if mapped_days is not None:
            days = mapped_days
        else:
            try:
                days = int(str(days).strip())
            except Exception:
                days = None
    
    body = {
        "search_state": search_state,
        "location": location,
        "date": date,
        "days": days
    }
    print("=====================Weather body===============================")
    print(body)
    try:
        # 發送 POST 請求
        response = requests.post(WEATHER_SEARCH_TOOLS, json=body, timeout=20)
        response.raise_for_status()  # 檢查回應狀態碼

        # 解析 JSON 回應
        result = json.loads(response.content)
        return result.get("response")
    except requests.exceptions.RequestException as e:
        print(f"請求失敗，錯誤: {e}")
        return ""

_AIRPORT_ALIAS_TO_IATA = {
    # Taiwan
    "台北": "TPE",
    "臺北": "TPE",
    "桃園": "TPE",
    "松山": "TSA",
    "taipei": "TPE",
    "tpe": "TPE",
    "tsa": "TSA",
    # Taichung
    "台中": "RMQ",
    "臺中": "RMQ",
    "rmq": "RMQ",
    # Japan (Tokyo area)
    "東京": "NRT",
    "成田": "NRT",
    "羽田": "HND",
    "tokyo": "NRT",
    "nrt": "NRT",
    "hnd": "HND",
}


def _normalize_airport_id(value: str) -> str:
    if not value:
        return value
    key = value.strip()
    if not key:
        return value
    # Preserve IATA codes (3 letters) as-is (uppercased)
    if len(key) == 3 and key.isalpha():
        return key.upper()
    mapped = _AIRPORT_ALIAS_TO_IATA.get(key)
    if mapped:
        return mapped
    mapped = _AIRPORT_ALIAS_TO_IATA.get(key.lower())
    return mapped or key


def flight_info(
    DepartureAirportID: str,
    ArrivalAirportID: str,
    ScheduleStartDate: str,
    ScheduleEndDate: str | None = None,
) -> list:
    """
    Retrieves flight schedule (航班時刻/班表) data based on departure and arrival airports,
    filtering results by the specified start and end dates.

    Args:
        DepartureAirportID: The departure airport (IATA code like "TPE") or common city/airport alias like "台北".
        ArrivalAirportID: The arrival airport (IATA code like "NRT") or common city/airport alias like "東京".
        ScheduleStartDate: The schedule start date in the format 'YYYY-MM-DD'.
        ScheduleEndDate: The schedule end date in the format 'YYYY-MM-DD'. If omitted, defaults to ScheduleStartDate.

    Returns:
        list: A list of flight information dictionaries matching the request criteria.
    """
    DepartureAirportID = _normalize_airport_id(DepartureAirportID)
    ArrivalAirportID = _normalize_airport_id(ArrivalAirportID)
    if not ScheduleEndDate:
        ScheduleEndDate = ScheduleStartDate

    body = {
        "DepartureAirportID": DepartureAirportID,
        "ArrivalAirportID": ArrivalAirportID,
        "ScheduleStartDate": ScheduleStartDate,
        "ScheduleEndDate": ScheduleEndDate,
    }
    # 發送 POST 請求
    response = requests.post(TRAINSPORT_SEARCH_TOOLS, json=body)
    # 檢查回應狀態碼
    if response.status_code == 200 and response != "":
        # 解析 JSON 回應
        result = json.loads(response.content)
        print("============================ flight_info Response================================")
        
        print(body)
        resp = result.get("response")
        print(resp)
        print("="*25)
        # Normalize service-level error payloads into a structured error.
        if isinstance(resp, str) and ("Error" in resp or "error" in resp):
            return {"error": resp, "request": body}
        return resp
    else:
        flight_info = response.text
    return flight_info

def attraction_info() -> list:
    
    # location: str, days: int
    # Args:
    #     location: The city to get the tourist attractions for.
    #     days: The number of days for the trip.
    
    """
    Suggest popular tourist destinations and local attractions based on the specified location and trip duration.    

    Returns:
        list: A list of tourist attractions in the specified location for the given duration.
    """
    return "日本大阪 /5天: 大阪城公園、大阪海遊館、八坂神社、北野異人館、日本橋電器街"


def discount(departure: str, arrival: str, ScheduleEndDate: str) -> list:
    """
    Retrieves applicable flight promotions, including discounts and special offers, 
    for flights between the given departure and arrival locations within the specified timeframe.

    Args:
        departure: The departure airport or city.
        arrival: The destination airport or city.
        ScheduleEndDate: The schedule end date in the format 'YYYY-MM-DD'.

    Returns:
        list: A list of flight information dictionaries matching the request criteria.
    """
    return "中華航空 大阪在2026/10/15訂票享87折優惠  "
    # url = "http://10.20.1.97:54088/rag/retrieval"
    # headers = {
    #     "accept": "application/json",
    #     "Content-Type": "application/json"
    # }

    # data = {
    #     "embed_model": "imac/zpoint_large_embedding_zh",
    #     "category": "INKS",
    #     "user_question": "什麼是CNC?",
    #     "topk": 5,
    #     "score_threshold": 0
    # }

    # response = requests.post(url, headers=headers, data=json.dumps(data))
    # if response.status_code == 200 and response != "":
    #     flight_info = response.json()
    # else:
    #     flight_info = response.text
    # return flight_info
    


querys = {
    "flight_info": "(Flight Schedule Agent)請根據以下內容輸入你想查詢的航班: 出發地, 目的地, 起飛日",
    "discount": "(Flight Discounts Agent)請輸入以下內容輸入你想查詢航班優惠: 起點, 目的地, 起飛日",
    "weather_info": "(Travel Weather Agent)請根據以下內容輸入你想查詢的天氣: 地名, 日期, 天數",
    "attraction_info": "(Travel Spot Agent)請根據以下內容輸入你想查詢的景點: 地名, 天數",
}

all_tools = {
    "flight_info": flight_info,
    "discount" : discount,
    "weather_info": weather_info,
    "attraction_info": attraction_info,
}
