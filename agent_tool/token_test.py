import requests

def get_token(client_id, client_secret):
    url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_id": "s1811332013-6b7f1284-10aa-4d26",
        "client_secret": "555fc500-3561-42b2-9946-ed5aac068782",
        "grant_type": "client_credentials"
    }
    resp = requests.post(url, headers=headers, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

# 使用你的金鑰
token = get_token("YOUR_CLIENT_ID", "YOUR_CLIENT_SECRET")
print("成功取得 Token！", token)