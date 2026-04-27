from pydantic import BaseModel


# 定義 Response Model
class FlightResponse(BaseModel):
    response: str
    
# 定義 Response Model
class WeatherResponse(BaseModel):
    response: str

    
class LangFlowWeatherResponse(BaseModel):
    response: str
    text: str = None  # 可選的文字描述欄位，默認為 None