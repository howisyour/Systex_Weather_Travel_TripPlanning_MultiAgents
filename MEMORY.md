# MEMORY.md — 長期記憶

> 這份文件是 AI 助手的長期記憶庫。每次新對話請先閱讀，以還原重要的上下文與知識。

---

## 專案概覽

**倉庫**：`howisyour/Systex_Weather_Travel_TripPlanning_MultiAgents`
**目的**：多 Agent 天氣旅遊行程規劃系統
**主要技術**：LangGraph、FastAPI、Gradio、ChromaDB、Ollama

---

## 架構摘要

- `WorkFlowAgent_Rebuild/` — 主系統
  - Supervisor Agent → 路由到子圖 Agent（Tool Calling / RAG / 一般 LLM）
  - 工具：`weather_info`, `flight_info`, `attraction_info`, `discount`
  - FastAPI 服務埠：`8088`
- `agent_tool/` — 工具服務（向量搜尋、模型 API）

---

## 關鍵設定

| 項目 | 值 |
|------|----|
| FastAPI 埠 | `8088` |
| Ollama 模型 | `llama3.2:3b`, `llama3.1:8b` |
| Embedding | `nomic-embed-text` |
| Agent 設定檔 | `WorkFlowAgent_Rebuild/lang_graph/main/config.json` |

---

## 已知問題 / 注意事項

- 天氣查詢若缺少地點參數會失敗（預期行為，需補全參數）
- 航班查詢若缺少出發地同樣會失敗

---

## 長期目標

- [ ] 完善 Self-RAG 子系統的文件
- [ ] 整合更多旅遊工具 Plugin
- [ ] 提升參數補全的準確率

---

## 里程碑

| 日期 | 事件 |
|------|------|
| 2026-05-03 | 初始化 AI 工作空間（AGENTS.md、MEMORY.md、SOUL.md） |

---

*最後更新：2026-05-03*
