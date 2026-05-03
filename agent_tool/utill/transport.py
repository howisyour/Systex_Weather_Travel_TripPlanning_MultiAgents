import json
import os
from pathlib import Path
import re

import requests
from dotenv import load_dotenv

# from configs.configs import *

from model.requset import FlightRequest


class TDXInternationalFlight:
    def __init__(self):
        # Ensure .env is loaded regardless of current working directory.
        env_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(dotenv_path=env_path, override=False)

        # self.client_id = TDX_CLIENT_ID
        # self.client_secret = TDX_CLIENT_SECRET
        # self.token_url = TDX_TOKEN_URL
        self.client_id = os.getenv("TDX_CLIENT_ID")
        self.client_secret = os.getenv("TDX_CLIENT_SECRET")
        self.token_url = os.getenv("TDX_TOKEN_URL")
        self.api_url = "https://tdx.transportdata.tw/api/basic/v2/Air/GeneralSchedule/International"

    def get_access_token(self):
        if not self.token_url:
            raise ValueError("TDX_TOKEN_URL 未設定（請確認 agent_tool/.env 或環境變數）。")
        if not self.client_id or not self.client_secret:
            raise ValueError("TDX_CLIENT_ID/TDX_CLIENT_SECRET 未設定（請確認 agent_tool/.env 或環境變數）。")
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        response = requests.post(self.token_url, headers=headers, data=data, timeout=20)
        response.raise_for_status()
        return response.json()['access_token']

    def get_international_schedule(self, request: FlightRequest) -> str:
        token = self.get_access_token()
        print("TDX token 取得成功")
        filter_list = list()
        filter_query = ""
        
        filter_list = []

        if request.AirlineID:
            filter_list.append(f"AirlineID eq \'{request.AirlineID}\'")  # 航空公司代碼

        if request.FlightNumber:
            filter_list.append(f"FlightNumber eq \'{request.FlightNumber}\'")  # 航班號碼

        if request.DepartureTime:
            filter_list.append(
                f"ScheduleDepartureTime le {request.DepartureTime}"
            )  # 出發時間（條件為小於等於）

        if request.ArrivalTime:
            filter_list.append(
                f"ScheduleArrivalTime ge {request.ArrivalTime}"
            )  # 抵達時間（條件為大於等於）

        if request.DepartureAirportID:
            filter_list.append(
                f"DepartureAirportID eq '{request.DepartureAirportID}'"
            )  # 起點機場ID

        if request.ArrivalAirportID:
            filter_list.append(
                f"ArrivalAirportID eq '{request.ArrivalAirportID}'"
            )  # 目的地機場ID

        # TDX OData uses Edm.Date for schedule dates; date literals should NOT be quoted.
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

        if request.ScheduleStartDate:
            start_date = request.ScheduleStartDate
            start_literal = start_date if date_pattern.match(start_date) else f"'{start_date}'"
            filter_list.append(
                f"ScheduleStartDate le {start_literal}"
            )  # 航班出發日期(起)

        if request.ScheduleEndDate:
            end_date = request.ScheduleEndDate
            end_literal = end_date if date_pattern.match(end_date) else f"'{end_date}'"
            filter_list.append(
                f"ScheduleEndDate ge {end_literal}"
            )  # 航班出發日期(終)

        if request.Friday:
            filter_list.append(f"Friday eq {str(request.Friday).lower()}")  # 星期五班表

        if request.Monday:
            filter_list.append(f"Monday eq {str(request.Monday).lower()}")  # 星期一班表

        if request.Tuesday:
            filter_list.append(f"Tuesday eq {str(request.Tuesday).lower()}")  # 星期二班表

        if request.Wednesday:
            filter_list.append(f"Wednesday eq {str(request.Wednesday).lower()}")  # 星期三班表

        if request.Thursday:
            filter_list.append(f"Thursday eq {str(request.Thursday).lower()}")  # 星期四班表

        if request.Saturday:
            filter_list.append(f"Saturday eq {str(request.Saturday).lower()}")  # 星期六班表

        if request.Sunday:
            filter_list.append(f"Sunday eq {str(request.Sunday).lower()}")  # 星期日班表

        # 最後組合成 filter 字串
        filter_str = " and ".join(filter_list)
        print("組好的filter：", filter_str)
        
        filter_query = " and ".join(filter_list)
        print(filter_query)
            
        headers = {'Authorization': f'Bearer {token}'}
        params = {
            '$filter': f'{filter_query}',
            '$format': 'JSON',
            '$top': 10  # 你可以調整回傳筆數
        }
        
        response = requests.get(self.api_url, headers=headers, params=params, timeout=30)
        try:
            response.raise_for_status()
        except requests.HTTPError:
            # Include TDX error body to help debug filter syntax/fields.
            print("TDX API error status:", response.status_code)
            print("TDX API error body:", response.text[:2000])
            raise
        
        data = json.loads(response.content)  # 先轉換 content 成 Python list
        print("TDX response count:", len(data) if isinstance(data, list) else type(data))
        # 依照抵達時間排序（TDX 可能使用不同欄位名稱）
        def _arrival_time_key(item: dict) -> str:
            return (
                item.get("ArrivalTime")
                or item.get("ScheduleArrivalTime")
                or ""
            )

        sorted_data = sorted(data, key=_arrival_time_key)

        def _weekday_summary(item: dict) -> str:
            weekdays = [
                ("Mon", item.get("Monday")),
                ("Tue", item.get("Tuesday")),
                ("Wed", item.get("Wednesday")),
                ("Thu", item.get("Thursday")),
                ("Fri", item.get("Friday")),
                ("Sat", item.get("Saturday")),
                ("Sun", item.get("Sunday")),
            ]
            enabled = [label for label, enabled_flag in weekdays if enabled_flag is True]
            return ",".join(enabled)

        # 整理成可閱讀的文字（班表時間通常是「每日時間」，不是特定日期）
        output = ""
        for flight in sorted_data:
            departure_time = flight.get("ScheduleDepartureTime") or flight.get("DepartureTime") or ""
            arrival_time = flight.get("ScheduleArrivalTime") or flight.get("ArrivalTime") or ""
            weekday_text = _weekday_summary(flight)
            weekday_part = f", 營運日: {weekday_text}" if weekday_text else ""
            output += (
                f"航空公司: {flight.get('AirlineID','')}, "
                f"航班: {flight.get('FlightNumber','')}, "
                f"起飛(班表時間): {flight.get('DepartureAirportID','')} {departure_time}, "
                f"抵達(班表時間): {flight.get('ArrivalAirportID','')} {arrival_time}, "
                f"有效期間: {flight.get('ScheduleStartDate','')} ~ {flight.get('ScheduleEndDate','')}"
                f"{weekday_part}\n"
            )
        # No matching flights is not an error.
        if not output.strip():
            return ""

        return output

if __name__ == '__main__':
    tdx_service = TDXInternationalFlight()
    international_flights = tdx_service.get_international_schedule()
    print(international_flights)
