# WorkFlowAgent_Rebuild

一個基於 LangGraph 構建的多 Agent 工作流系統，整合了 FastAPI API 服務與 Gradio 前端介面，支援航班查詢、天氣資訊、旅遊景點推薦及優惠折扣查詢等功能。

## 📋 目錄

- [功能特色](#-功能特色)
- [專案架構](#-專案架構)
- [技術棧](#-技術棧)
- [安裝指南](#-安裝指南)
- [使用說明](#-使用說明)
- [核心模組說明](#-核心模組說明)
- [API 端點](#-api-端點)
- [配置說明](#-配置說明)

## ✨ 功能特色

- **多 Agent 架構**：透過 Supervisor Agent 智慧路由到對應的子圖 Agent
- **Tool Calling**：支援 LLM 工具呼叫，自動解析缺失參數
- **RAG (檢索增強生成)**：整合 Self-RAG 實現知識檢索與回答生成
- **即時串流回應**：支援 Streaming 方式回傳 AI 回覆
- **動態工具上傳**：支援動態上傳新的工具 Plugin
- **雙前端支援**：同時提供 FastAPI RESTful API 與 Gradio Web UI

## 📂 專案架構

WorkFlowAgent_Rebuild/
├── fastapi_app.py # FastAPI 主應用程式進入點
├── gradio_service.py # Gradio 前端服務
├── requirements.txt # Python 依賴套件
│
├── api/ # API 路由層
│ ├── init.py
│ └── endpoints.py # FastAPI 路由端點定義
│
├── configs/ # 配置文件
│ ├── configs.py # 全域配置（API URL、路徑等）
│ └── weather_mapping.py # 天氣地名映射表
│
├── lang_graph/ # LangGraph 核心邏輯
│ ├── main/ # 主要 Agent 系統
│ │ ├── app.py # 應用程式入口
│ │ ├── graph.py # 圖形建構與管理
│ │ ├── supervisor.py # Supervisor Agent（路由邏輯）
│ │ ├── subgraph.py # 子圖 Agent 邏輯
│ │ ├── rag_subgraph.py # RAG 子圖（檢索增強生成）
│ │ ├── state.py # 全域狀態定義
│ │ ├── tools.py # 工具函數（天氣、航班等）
│ │ ├── config.py # 執行緒與初始狀態配置
│ │ ├── config.json # Agent 配置檔
│ │ ├── about_file.py # 動態函數 Schema 生成
│ │ ├── question_control.py # 問題控制邏輯
│ │ └── db.py # 資料庫連接
│ │
│ └── self-RAG/ # Self-RAG 實作
│ ├── app.py # RAG 圖形入口
│ ├── rag.py # 檢索器設定
│ ├── grader.py # 文檔相關性評分器
│ ├── generate.py # 回答生成
│ ├── rewriter.py # 查詢重寫器
│ └── llm.py # LLM 模型配置
│
├── tools/ # 工具 Plugin 存放區
│ └── init.py
│
├── utils/ # 工具函數
│ ├── model_loader.py # HuggingFace 模型載入器
│ ├── function_calling.py # Function Calling 處理
│ ├── langgraph_function_calling.py # LangGraph FC 整合
│ ├── langgraph_gen_graph.py # 圖形生成工具
│ ├── convert_to_tool.py # 函數轉 Tool 轉換器
│ └── each_agent.py # Agent 輔助函數
│
└── graph_img/ # 生成的圖形可視化存放區

## 🛠 技術棧

| 類別 | 技術 |
|------|------|
| **框架** | FastAPI, Gradio |
| **LLM 框架** | LangChain, LangGraph |
| **模型服務** | Ollama (llama3.2:3b, llama3.1:8b) |
| **向量資料庫** | ChromaDB |
| **Embedding** | Ollama Embeddings (nomic-embed-text) |
| **模型載入** | HuggingFace Transformers |

## 📦 安裝指南

### 前置需求

- Python 3.12+
- Ollama (需安裝並運行 llama3.2:3b 和 llama3.1:8b 模型)
- PostgreSQL (選用，用於資料庫功能)

### 安裝步驟

1. **克隆專案**
   ```bash
   git clone <repository-url>
   cd WorkFlowAgent_Rebuild
```

## 📚 使用說明

- **FastAPI 端點**：`/api/` 路由層提供航班、天氣、景點、優惠等查詢
- **Gradio 前端**：`/gradio/` 提供圖形化介面，可視化 Agent 工作流
- **工具上傳**：可上傳新的工具 Plugin，支援動態擴充功能
- **配置管理**：可透過 `configs.py` 修改 API URL、路徑等設定

## 🧩 核心模組說明

- **Supervisor Agent**：智慧路由到對應的子圖 Agent
- **Tool Calling**：支援 LLM 工具呼叫，自動解析缺失參數
- **RAG (檢索增強生成)**：整合 Self-RAG 實現知識檢索與回答生成
- **即時串流回應**：支援 Streaming 方式回傳 AI 回覆
- **動態工具上傳**：支援動態上傳新的工具 Plugin
- **雙前端支援**：同時提供 FastAPI RESTful API 與 Gradio Web UI

## 🌐 API 端點

- **航班查詢**：`/api/flight`
- **天氣資訊**：`/api/weather`
- **旅遊景點**：`/api/attractions`
- **優惠折扣**：`/api/discounts`

## 📝 配置說明

- `configs.py`：全域配置（API URL、路徑等）
- `weather_mapping.py`：天氣地名映射表
- `config.json`：Agent 配置檔

## 🚀 問題與建議

請聯絡開發者或提交 GitHub Issues。

安裝依賴
pip install -r requirements.txt
# 或使用 lang_graph/main/requirements.txt 獲取完整依賴
pip install -r lang_graph/main/requirements.txt

安裝 Ollama 模型
ollama pull llama3.2:3b
ollama pull llama3.1:8b
ollama pull nomic-embed-text

配置環境

修改 configs/configs.py 中的 API 端點配置
修改 lang_graph/main/config.json 中的 Agent 配置
🚀 使用說明
啟動 FastAPI 服務
python fastapi_app.py
服務將在 http://localhost:8088 啟動

啟動 Gradio 介面
python gradio_service.py


📚 核心模組說明
1. Graph (圖形系統)
graph.py - 負責建構和管理 LangGraph 工作流圖形
建構子圖：根據 config.json 配置建構多個 Agent 子圖
Agent 類型：
type=0：一般 LLM 對話
type=1：Tool Calling Agent
type=2：RAG Agent
2. Supervisor (監督者)
supervisor.py - 負責將使用者請求路由到適當的子圖 Agent

分析使用者輸入意圖
根據可用 Agent 描述選擇最佳匹配
支援特殊指令 (<<skip>>, <<previous>>, <<stop>>)
3. SubGraph (子圖)
subgraph.py - 各個功能 Agent 的實作

human_feedback：處理使用者回饋
assistant：LLM 助手節點
tools：工具執行節點
arg_assistant：參數補全助手
4. Tools (工具函數)
tools.py - 可用的工具函數

工具	功能	參數
weather_info	查詢天氣資訊	location, date, days
flight_info	查詢航班資訊	DepartureAirportID, ArrivalAirportID, ScheduleStartDate, ScheduleEndDate
attraction_info	查詢旅遊景點	-
discount	查詢航班優惠	departure, arrival, ScheduleEndDate
5. RAG 子系統
rag_subgraph.py 與 self-RAG

檢索：從向量資料庫檢索相關文檔
評分：評估文檔相關性
生成：基於檢索結果生成回答
網頁搜尋：當檢索結果不足時進行網頁搜尋
🔌 API 端點
FastAPI Endpoints
方法	路徑	說明
POST	/ask	發送問題（串流回應）
POST	/ask_not_streaming	發送問題（非串流）
POST	/upload_tools	上傳新工具 Plugin
GET	/get_files_in_folder	取得已上傳的工具清單
DELETE	/remove_tools	刪除指定工具
POST	/generate_function_not_file	動態生成函數

請求範例
# 查詢天氣
curl -X POST http://localhost:8088/ask \
  -H "Content-Type: application/json" \
  -d '{"content": "今天台中天氣如何?", "model_type": "langgraph"}'

# 查詢航班
curl -X POST http://localhost:8088/ask \
  -H "Content-Type: application/json" \
  -d '{"content": "幫我查詢2026年10月28號台北到大阪的航班", "model_type": "langgraph"}'

⚙️ 配置說明
config.json
{
    "tool_function_list": ["flight_info", "discount", "weather_info", "attraction_info"],
    "type": [1, 2, 1, 0]
}
tool_function_list：啟用的工具函數清單
type：對應工具的 Agent 類型 (0=一般, 1=Tool Calling, 2=RAG)

configs.py
FAST_BASE_PORT = "8088"           # FastAPI 服務埠號
TOOL:/S_BASE_URL = "http/10.20.1.97:8088"  # 外部工具服務 URL
GRAPH_SAVED_DIR = "/path/to/graph_img"     # 圖形輸出目錄

 測試案例
測試	問題	預期結果
Case 1	今天台中天氣如何?	✅ 正常回覆天氣
Case 2	今天東京天氣如何?	✅ 正常回覆天氣
Case 3	今天天氣如何?	❌ 缺少地點參數
Case 4	幫我查詢2024年10月28號台北到大阪的航班	✅ 正常回覆航班
Case 5	幫我查詢2024年10月28號到大阪的航班	❌ 缺少出發地
📄 License
MIT License

👥 Contributors
開發團隊

這個 README 涵蓋了：
- 專案功能介紹
- 完整的目錄結構說明
- 技術棧清單
- 安裝與使用指南
- 核心模組詳細說明
- API 端點文檔
- 配置說明
- 測試案例這個 README 涵蓋了：
- 專案功能介紹
- 完整的目錄結構說明
- 技術棧清單
- 安裝與使用指南
- 核心模組詳細說明
- API 端點文檔
- 配置說明
- 測試案例