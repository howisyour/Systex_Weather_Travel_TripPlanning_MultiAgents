from datetime import date
from datetime import date, timedelta

today = date.today()
today_formatted = today.strftime("%Y-%m-%d")

yesterday = today - timedelta(days=1)
yesterday_formatted = yesterday.strftime("%Y-%m-%d")

WEATHER_MAPPING = {
    # 台灣 Taiwan
    "臺北": "taipei",
    "台北": "taipei",
    "中華台北": "taipei",
    "新北": "new taipei",
    "桃園": "taoyuan",
    "台中": "taichung",
    "臺中": "taichung",
    "台南": "tainan",
    "臺南": "tainan",
    "高雄": "kaohsiung",
    "基隆": "keelung",
    "新竹": "hsinchu",
    "嘉義": "chiayi",
    "宜蘭": "yilan",
    "花蓮": "hualien",
    "台東": "taitung",
    "臺東": "taitung",
    "澎湖": "penghu",
    "金門": "kinmen",
    "馬祖": "matsu",
    
    # 日本 Japan
    "東京": "tokyo",
    "大阪": "osaka",
    "京都": "kyoto",
    "名古屋": "nagoya",
    "橫濱": "yokohama",
    "札幌": "sapporo",
    "福岡": "fukuoka",
    "神戶": "kobe",
    "仙台": "sendai",
    "廣島": "hiroshima",
    "長崎": "nagasaki",
    "那霸": "naha",
    "鹿兒島": "kagoshima",
    "青森": "aomori",
    "大分": "oita",
    "熊本": "kumamoto",
    "函館": "hakodate",
    "小樽": "otaru",
    "旭川": "asahikawa",
    "日本松平": "osaka",
    "新本東京": "osaka"
}

DATE_MAPPING = {
    "今日": today_formatted,
    "今天": today_formatted,
    "現在": today_formatted,
    "昨天": yesterday_formatted,
    "昨日": yesterday_formatted,
    "前一天": yesterday_formatted,
    "昨天": yesterday_formatted,
    "昨日": yesterday_formatted,
    "前一天": yesterday_formatted,
}

DAYS_MAPPING={
    "今日": "1",
    "今天": "1",
    "現在": "1",
}

