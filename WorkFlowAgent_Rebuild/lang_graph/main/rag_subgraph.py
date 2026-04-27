import requests
import json
import re

# lacnggraph and langchain
from langchain.text_splitter import RecursiveCharacterTextSplitter # 用於將文本分割成塊的工具
from langchain_community.document_loaders import WebBaseLoader # 用於從網頁加載文檔的工具
from langchain_community.vectorstores import Chroma # 用於建立和管理向量資料庫的工具
# from langchain_community import embeddings # Langchain 提供的嵌入模型
# from langchain_community.embeddings import OllamaEmbeddings # 從 Ollama 加載嵌入模型的工具
from langchain_ollama import OllamaEmbeddings # 從 Ollama 加載嵌入模型的工具
from langchain_core.messages import AIMessage
# test
# from grader import grader # 假設是先前建立的評分器類別或函式 (目前程式碼並未使用)


# 定義RAG 所需
"""
設定要加載的網頁 URL 列表 -
從網頁加載文檔 -
設定文本分割器，使用 tiktoken 編碼器進行分割，設定塊大小為 250，無重疊
"""
# 設定要加載的網頁 URL 列表
# urls = [
#     "https://lilianweng.github.io/posts/2023-06-23-agent/",
#     "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",
#     "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",
# ]

# # 從網頁加載文檔
# docs = [WebBaseLoader(url).load() for url in urls]
# # 將多個文檔列表合併為一個列表
# docs_list = [item for sublist in docs for item in sublist]

# # 設定文本分割器，使用 tiktoken 編碼器進行分割，設定塊大小為 250，無重疊
# text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
#     chunk_size=250, chunk_overlap=0
# )

# # 將加載的文檔分割成更小的文本塊
# doc_splits = text_splitter.split_documents(docs_list)
# # 設定本地 Ollama 嵌入模型
# local_embeddings = OllamaEmbeddings(model="nomic-embed-text")

# # 建立向量資料庫 Chroma，將分割後的文檔和嵌入模型存入
# vectorstore = Chroma.from_documents(
#     documents= doc_splits,
#     collection_name="rag-chroma",
#     embedding=local_embeddings
# )


def api_retriver():
    return "api searching~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"


# 定義檢索器函式
# def get_retriver():
    """返回一個可以從向量資料庫檢索相關文檔的檢索器物件"""
    # return vectorstore.as_retriever()

# Retrieval Grader(評分者)
from langchain_core.prompts import ChatPromptTemplate # 用於建立聊天機器人提示詞的工具
from pydantic import BaseModel, Field # 用於資料模型驗證和定義的工具
# from llm import ollama_instance as llm # 導入 Ollama LLM 模型

from langchain_ollama import ChatOllama

llm = ChatOllama(
        model="llama3.1:8b",
        temperature=0,
        format="json"
    )

# Data model
class GradeDocuments(BaseModel):
    """二元評分模型，用於檢索到的文檔的相關性檢查."""

    binary_score: str = Field(
        description="文檔是否與問題相關，'yes' 或 'no'"
    )


# 定義評分器函式
def get_grader():
    """
    返回一個用於評估檢索到的文檔是否與用戶問題相關的評分器物件。
    該評分器使用 LLM 和一個結構化的輸出格式。
    """
    # 使用 LLM 來產生結構化輸出 (這裡的結構化輸出格式是 GradeDocuments)
    structured_llm_grader = llm.with_structured_output(GradeDocuments)
    
    # 定義評分器的提示詞模板，包含系統訊息和使用者訊息
    system = """你是一個評分員，負責評估檢索到的文檔與使用者問題的相關性。\n 
        如果文檔包含與問題相關的關鍵字或語義意義，則將其評為相關。\n
        給出二元分數 'yes' 或 'no'，以表示文檔是否與問題相關。"""
    grade_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "檢索到的文檔：\n\n {documents} \n\n 使用者問題：{question}"),
        ]
    )
    return grade_prompt | structured_llm_grader
    
def rag_generator():
    system = """
        以下的參考資料為一個問題敘述，請你幫我判斷使用者問題敘述相似是否與參考資料中的問題相似。
        回答規則如下：
        1. 只回答 "沒有相關資料" 或
        2. 回答相似的完整文檔內容，不得生成額外解釋或評論。
        輸出必須為繁體中文，且不得添加任何延伸內容。
    """
    rag_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            (   "human",
                "檢索到的文檔：\n{documents}\n 使用者問題：\n{question}\n"
            )
        ]
    )
    question_rewriter = rag_prompt | llm | StrOutputParser()
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print(rag_prompt)
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    
    return question_rewriter
    
# lacnggraph and langchain
from langchain.text_splitter import RecursiveCharacterTextSplitter # 從這裡開始又重複定義了一次, 不建議這樣寫
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
# from langchain_community import embeddings
# from langchain_community.embeddings import OllamaEmbeddings
from langchain_ollama import OllamaEmbeddings

from langchain_core.prompts import ChatPromptTemplate # 與前面重複定義
from langchain_core.output_parsers import StrOutputParser # 用於將 LLM 輸出轉換為字符串的工具

# 定義改寫器的提示詞模板
system = """你是一個問題改寫器，將輸入的問題轉換為更適合網路搜尋的版本。\n 
     觀察輸入並嘗試推理其底層的語義意圖/含義。"""
re_write_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        (
            "human",
            "這是初始問題：\n\n {question} \n 形成一個改進的問題。",
        ),
    ]
)

# 定義改寫器函式
def get_rewriter():
    """
    返回一個用於改寫用戶問題，使其更適合網路搜尋的改寫器物件。
    該改寫器使用 LLM 和一個字串輸出解析器。
    """
    # 將提示詞、LLM 模型和字串輸出解析器串連起來，建立一個改寫管道
    question_rewriter = re_write_prompt | llm | StrOutputParser()
    return question_rewriter

import getpass
import os

from langchain_community.tools.tavily_search import TavilySearchResults
from lang_graph.main.state import State
from typing import List
from typing_extensions import TypedDict
from langchain.schema import Document
from langgraph.graph import END, StateGraph, START
from pprint import pprint

# retriever = get_retriver()
retriever = api_retriver()
retrieval_grader = get_grader()
question_rewriter = get_rewriter()
rag = rag_generator()

import os

# 設置環境變數
os.environ["TAVILY_API_KEY"] = "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"


web_search_tool = TavilySearchResults(k=3)

from langchain import hub
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
# Prompt
prompt = hub.pull("rlm/rag-prompt")

# Post-processing
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Chain

rag_chain = prompt | llm | StrOutputParser()

class RagSubGraph:
    def __init__(self):
        print("---INIT RAG SUBGRAPH---")

    # get_user_input -> retrieve
    def rag_node(self, state: State):
        """
        Retrieve documents

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, documents, that contains retrieved documents
        """
        print("---RETRIEVE---")
        # question = state["question"]
        # 拿問題去檢索
        question = state["feedback"]
        print("!!---QUESTION---!!\n", question)
        # 觸發 打API
        # ~~~~<先註解>搜尋結果~~~
        url = "http://10.20.1.97:54088/rag/retrieval"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        data = {
            "embed_model": "imac/zpoint_large_embedding_zh",
            "category": "flight_discount",
            "question": question,
            "topk": 1,
            "score_threshold": 0
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        print("============================retrival response=========================")
        print(response)
        print("="*50)
        if response.status_code == 200 and response != "":
            print(f"Response content {type(response)}")
            response_json = response.json()
            print("----------------------------rag response----------------------------")
            similarity_search_result = response_json.get("similarity_search_result", None) 
            print(response_json)
            return {"documents": similarity_search_result , "feedback": question}
        
    # return flight_info
        
        # documents = retriever
        # documents = retriever.invoke(question)
        print("---RETRIEVED DOCUMENTS---\n", similarity_search_result)
        return {"documents": similarity_search_result , "feedback": question}

    def keyword_search(self, state: State):
        """
        Web search based on the re-phrased question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates documents key with appended web results
        """
        print("~~~~~~~~~~~print rag retrieve state~~~~~~~~~~~~")
        print(state)
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        url = "http://10.20.1.97:8000/rag/Rag_agnet"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        data = {
            "embed_model": "imac/zpoint_large_embedding_zh",
            "category": "flight_discount",
            "question": question,
            "topk": 5,
            "score_threshold": 0
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200 and response != "":
            print(f"Response content {type(response)}")
            response_json = response.json()
            similarity_search_result = response_json.get("similarity_search_result", None) 
            return {"documents": similarity_search_result , "feedback": question}

    
    def grade_documents(self, state: State):
        """
        Determines whether the retrieved documents are relevant to the question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates documents key with only filtered relevant documents
        """

        print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
        question = state["feedback"]
        documents = state["documents"]
        print("---grade_documents QUESTION---\n", question)
        print("---grade_documents DOCUMENTS---\n", documents)
        # Score each doc
        filtered_docs = []
        web_search = "yes"
        # for d in documents:
        score = retrieval_grader.invoke(
            {"documents": documents ,"question": question}
        )
        grade = score.binary_score
        
        print("---GRADE: DOCUMENT RELEVANT---")
        print(f"grade : {grade}")
        print("----------------------------")
        
        if grade.lower() == "no":
            print("---GRADE: DOCUMENT NOT RELEVANT---")
            web_search = "yes"
            filtered_docs.append(documents)
        else:
            print("---GRADE: DOCUMENT RELEVANT---")
            web_search = "no"
            # continue
        return {"documents": documents, "question": question, "web_search": web_search}

    def transform_query(self, state):
        """
        Transform the query to produce a better question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates question key with a re-phrased question
        """

        print("---TRANSFORM QUERY---")
        print(state)
        print("-"*50)
        question = state["question"]
        documents = state["documents"]

        # Re-write question
        better_question = question_rewriter.invoke({"question": question})

        return {"documents": documents, "question": better_question}

    def web_search(self, state: State):
        """
        Web search based on the re-phrased question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates documents key with appended web results
        """

        print("---WEB SEARCH---")
        question = state["question"]
        documents = state["documents"]

        # Web search
        docs = web_search_tool.invoke({"query": question})
        print("---WEB DOCS---\n", docs)
        web_results = "\n".join([d["content"] for d in docs])
        print("---WEB RESULTS---\n", web_results)
        web_results = Document(page_content=web_results)
        documents.append(web_results)
        
        url = "http://10.20.1.97:54088/rag/keyword_search"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        data = {
            "embed_model": "imac/zpoint_large_embedding_zh",
            "category": "flight_discount",
            "user_question": question,
            "topk": 5,
            "score_threshold": 0
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        print("============================web_search response=========================")
        print(response)
        print("="*50)
        
        if response.status_code == 200 and response != "":
            print(f"Response content {type(response)}")
            response_json = response.json()
            search_result = response_json.get("search_result", None) 
        return {"documents": search_result, "question": question}

    def generate(self, state: State):
        """
        Generate answer

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
        """
        print("------------------- state ----------------------")
        print(state)
        print("---GENERATE---")
        question = state["feedback"]
        print("---GENERATE QUESTION---\n", question)
        documents = state["documents"]
        print("---GENERATE DOCUMENTS---\n", documents)
        # generation = rag_chain.invoke({"context": documents, "question": question})
        system = """
            以下的參考資料為一個問題敘述，幫我判斷使用者問題敘述相似是否與參考資料中的問題相似。
            規則如下：
            1. 如果內容包含任何JSON格式或類似 {{"xxx": "yyy"}} 這類內容，請直接回答「沒有相關資料」。
            2. 如果有符合的相似文本，請直接「逐字完整貼上相似文檔」。
            3. 禁止任何額外評論、補充、或改寫。
        """

        rag_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human",
                    """檢索到的文檔（相似度高）：\n
                        {documents}\n
                        使用者問題：\n
                        {question}
                    """
                )
            ]
        )
        question_rewriter = rag_prompt | llm | StrOutputParser()
        print("-------------generator documets----------------")
        print(documents)
        print("!++++++++++++++++++++==========================")
        generation = question_rewriter.invoke({"documents": documents, "question": question})
        print("====LLM generation====")
        print(generation)
        # if generation.startswith('{') and generation.endswith('}'):
        #     # 擷取 key 內容
        #     match = re.match(r'^\{["\']?(.*?)["\']?\s*:\s*["\']?\s*["\']?\}$', generation)
        #     if match:
        #         generation = match.group(1).strip()
        
        output = AIMessage(content=generation)
        
        
        # match = re.search(r'"(.*?)"\s*:\s*""', output)  # 匹配 `"內容" : ""`
        # extracted_text = match.group(1) if match else generation  # 取出匹配的內容
        print("---GENERATION---\n", output)
        return {
            "messages": [output],
            "documents": documents,
            "question": question,
            "condition": "output"  
        }


    # Edges
    def decide_to_generate(self, state: State):
        """
        Determines whether to generate an answer, or re-generate a question.

        Args:
            state (dict): The current graph state

        Returns:
            str: Binary decision for next node to call
        """

        print("---ASSESS GRADED DOCUMENTS---")
        state["question"]
        web_search = state["web_search"]
        # state["documents"]

        if web_search == "Yes":
            # All documents have been filtered check_relevance
            # We will re-generate a new query
            print(
                "---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY---"
            )
            return "keyword_search_node"
        else:
            # We have relevant documents, so generate answer
            print("---DECISION: GENERATE---")
            return "generate"

    def decide_to_keyword_search(self, state: State):
        """
        Determines whether to keyword search, or end process.

        Args:
            state (dict): The current graph state

        Returns:
            str: Binary decision for next node to call
        """
        # state["question"]
        print("~~~~~~~~~~~~~~~~~~~~~~~~~decide_to_keyword_search STATE~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print(state)
        print("~"*20)
        keyword_search ="No" if "沒有相關資料" in state["documents"] else "Yes"
        if keyword_search == "Yes":
            # All documents have been filtered check_relevance
            # We will re-generate a new query
            print(
                "---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY---"
            )
            return "keyword_search_node"
        else:
            # We have relevant documents, so generate answer
            print("---DECISION: GENERATE---")
            return "human_feedback"


# 程式的入口點
if __name__ == "__main__":
    # 取得檢索器
    retriever = get_retriver()
    # 設定要檢索的問題
    question = "agent memory"
    # 呼叫 grader 函式 (請注意, 此處沒有正確執行 grader, 請參考我上次的回答)
    # 正確的呼叫方式應該是先利用 retriever 檢索文檔，然後再用 grader 評分
    # grader(retriever,question)