from model.requset import FlightRequest, WeatherRequest, ChatRequest,Air_TicketRequest,attraction_info_Request
from model.response import FlightResponse, WeatherResponse, LangFlowWeatherResponse
from utill.transport import TDXInternationalFlight
from utill.weather import Weather
from utill.chat import Chat
from utill.attraction import Attraction

import traceback
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或指定你的前端 URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/flightinformation/", response_model=FlightResponse)
async def create_item(request: FlightRequest):
    try:
        tdx_service = TDXInternationalFlight()
        flight_schedule = tdx_service.get_international_schedule(request=request)
        
        api_response = FlightResponse(response=flight_schedule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        # Only treat as error when an exception really happened.
        traceback.print_exc()
        api_response = FlightResponse(response="Error Response")
    
    return api_response

@app.post("/weather/", response_model=WeatherResponse)
async def weather_item(request:WeatherRequest):
    # try:
    print(f"request: {request}")
    try:
        service = Weather()
        weather_response = service.wheather(request)
        api_response = WeatherResponse(response=weather_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # except:
    #     api_response = WeatherResponse(response="Error Response")
        
    return api_response

@app.post("/langflow_weather/")
async def langflow_weather_item(request:WeatherRequest):
    # try:
    print(f"request: {request}")
    try:
        service = Weather()
        weather_response = service.wheather(request)
        api_response = LangFlowWeatherResponse(response=weather_response, text=weather_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # except:
    #     api_response = WeatherResponse(response="Error Response")
    
    return {
        "text": weather_response
    }

@app.post("/attraction_info/")
async def attraction_info(request:attraction_info_Request):
    print(f"request: {request}")
    try:
        attraction_response = Attraction().get_attraction_info(request)
        return {"response": attraction_response}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.middleware("http")
async def log_request_data(request: Request, call_next):
    body = await request.body()
    print(f"Request path: {request.url.path}")
    print(f"Request body: {body.decode('utf-8')}")
    response = await call_next(request)
    return response


@app.post("/chat/")
async def chat(request:ChatRequest):
    # try:
    chat = Chat()
    # except:
    #     api_response = WeatherResponse(response="Error Response")
    
    return {
        "response": chat.chat(request)
    }

@app.post("/air_ticket/")
async def air_ticket(request:Air_TicketRequest):
    return "目前沒有這個功能"