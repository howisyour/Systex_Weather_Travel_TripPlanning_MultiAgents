### Generate

from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from llm import ollama_instance as llm
# Prompt
prompt = hub.pull("rlm/rag-prompt")

# Post-processing
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Chain
rag_chain = prompt | llm | StrOutputParser()

# Run
# generation = rag_chain.invoke({"context": docs, "question": question})
# print(generation)