from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints import *
from utils.model_loader import loader
from utils.function_calling import *
from contextlib import asynccontextmanager
import uvicorn

"""
@asynccontextmanager：這是 Python 的一個裝飾器，用於創建異步上下文管理器。
它允許你在上下文管理器的 __aenter__ 和 __aexit__ 方法中執行異步操作。
lifespan 函數：這個函數定義了應用程式的生命周期。
在 yield 之前的代碼會在應用程式啟動時執行，而 yield 之後的代碼會在應用程式關閉時執行。
"""
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時載入模型
    loader.load_model("DiTy/gemma-2-9b-it-function-calling-GGUF")
    print("Model and tokenizer loaded successfully.")
    yield
    # 關閉時清理資源
    # global model, tokenizer
    # model = None
    # tokenizer = None
    # print("Cleaned up resources.")

app = FastAPI(
    title="LangChain Server",
    version="1.0",
    description="A simple api server using Langchain's Runnable interfaces",
    # lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origins=["*"]
)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8088)
