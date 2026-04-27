from langchain_ollama import ChatOllama

ollama_instance = ChatOllama(
        model="llama3.1:8b",
        temperature=0,
        format="json"
    )