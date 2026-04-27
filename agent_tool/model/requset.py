from typing import Optional
from pydantic import BaseModel


class FlightRequest(BaseModel):
    AirlineID: Optional[str] = None
    FlightNumber: Optional[str] = None
    DepartureTime: Optional[str] = None
    ArrivalTime: Optional[str] = None
    DepartureAirportID: Optional[str] = None
    ArrivalAirportID: Optional[str] = None
    ScheduleStartDate: Optional[str] = None
    ScheduleEndDate: Optional[str] = None
    Monday: Optional[bool] = None
    Tuesday: Optional[bool] = None
    Wednesday: Optional[bool] = None
    Thursday: Optional[bool] = None
    Friday: Optional[bool] = None
    Saturday: Optional[bool] = None
    Sunday: Optional[bool] = None


class WeatherRequest(BaseModel):
    search_state: Optional[str] = None  # "current", "forecast", "history"; 相容 "now", "future"
    location: Optional[str] = None
    date: Optional[str] = None
    days: Optional[int] = None



class ChatRequest(BaseModel):
    model: Optional[str] = None  
    prompt: Optional[str] = None
    system_prompt: Optional[str] = None

class Air_TicketRequest(BaseModel):
    pass

class attraction_info_Request(BaseModel):
    engine: Optional[str] = "google_local"  # 必要。指定使用 Google 在地搜尋引擎。
    q: Optional[str] = None  # 必要。搜尋關鍵字（Query）。例如："日本大阪 景點"
    location: Optional[str] = None  # 建議。幫助 API 定位搜尋區域（更精準）。例如："Osaka, Japan"
    num: Optional[int] = 20  # 回傳結果的數量。預設 20。
    api_key: Optional[str] = None  # 必要。你在 SerpApi 註冊後取得的私密金鑰。
    hl: Optional[str] = "zh-tw"  # 回傳結果的語言（繁體中文）。
    gl: Optional[str] = "jp"  # 搜尋的國家代碼（例如日本為 jp），影響排序邏輯。