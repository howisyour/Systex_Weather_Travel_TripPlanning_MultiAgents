import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import VectorParams, Distance


# 設定 Ollama Server 位址
# ollama_base_url = "http://10.20.1.97:11433"



# 測試要問的問題
# question = "中華航空2025年9月1日前往日本大阪的航班推出限時優惠，經濟艙來回票價優惠價6,800元起，豪華經濟艙亦有折扣，票價含稅，享有23公斤托運行李、機上餐食與哩程累積，部分優惠票種還可免費改期一次，適合自由行及商務旅客。"
question="""
桃園飛大阪限時優惠】

 中華航空
來回票價：TWD 11,934
出發期間：2025/06/23 - 2025/07/04
備註：經濟艙快閃價，含稅含餐
立即預訂：https://www.china-airlines.com

 長榮航空
來回票價：TWD 12,414
出發期間：2025/09/12 - 2025/09/18
備註：含免費餐飲與機上娛樂
立即預訂：https://flights.evaair.com

 星宇航空
來回票價：TWD 13,302
出發期間：近期出發
備註：高質感服務、哩程累積
立即預訂：https://www.starlux-airlines.com

 國泰航空
來回票價：TWD 11,616
出發期間：2025/06/10 - 2025/06/17
備註：經濟艙含稅、含服務費
立即預訂：https://flights.cathaypacific.com

 Skyscanner 比價平台
來回票價：TWD 5,241 起（單程 TWD 2,388 起）
備註：不定期超值促銷，建議彈性日期搜尋
立即比價：https://www.skyscanner.com.tw
"""
embed_model = "imac/zpoint_large_embedding_zh:latest"

# 產生 embedding（指定 base_url）
embedding_response = ollama.embeddings(
    model=embed_model,
    prompt=question,
    options={"device": "cpu"}
)

embedding_vector = embedding_response['embedding']
print(f"✅ 取得 embedding 長度: {len(embedding_vector)}")  # 確認維度是否為 1024

# Qdrant client 連線
client = QdrantClient(url="http://localhost", port=6398, api_key="MySecret12345")

client.recreate_collection(
    collection_name="flight_discount_zpoint_large_embedding_zh",
    vectors_config=VectorParams(
        size=len(embedding_vector),  # 向量維度，例如 1024
        distance=Distance.COSINE     # 可選 COSINE、EUCLID、DOT
    )
)

# 上傳到你的 collection
client.upsert(
    collection_name="flight_discount_zpoint_large_embedding_zh",
    points=[
        PointStruct(
            id=1,  # 可以改成你自己的 ID
            vector=embedding_vector,
            payload={"document": question, "page_number": "1", "filename": "SystexFlight"}
        )
    ]
)

search_query = "請問學生有什麼行李優惠？"

# 產生搜尋問題的 embedding
search_embedding = ollama.embeddings(
    model=embed_model,
    prompt=search_query,
    options={"device": "cpu"}
)['embedding']

# 向量搜尋
search_result = client.search(
    collection_name="flight_discount_zpoint_large_embedding_zh",
    query_vector=search_embedding,
    limit=3  # 回傳最相近的前 3 筆
)

# 顯示結果
print("🔍 搜尋結果：")
for i, hit in enumerate(search_result):
    print(f"第 {i+1} 筆：score={hit.score}")
    print(f"內容：{hit.payload['document']}")
    print("-" * 40)


print("✅ 成功上傳到 Qdrant！")


