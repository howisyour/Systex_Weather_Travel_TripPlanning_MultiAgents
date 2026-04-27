import uvicorn
from api import app

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=1235, #原port號為8088
        reload=True
    )
    
    # nohup python service.py --listen --api --trust-remote-code --reload > server.log 2>&1 &
