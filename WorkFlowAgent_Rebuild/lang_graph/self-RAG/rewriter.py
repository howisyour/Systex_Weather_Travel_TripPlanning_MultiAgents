from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm import ollama_instance as llm

# Prompt
system = """You a question re-writer that converts an input question to a better version that is optimized \n 
     for web search. Look at the input and try to reason about the underlying semantic intent / meaning."""
re_write_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        (
            "human",
            "Here is the initial question: \n\n {question} \n Formulate an improved question.",
        ),
    ]
)


def get_rewriter():
    question_rewriter = re_write_prompt | llm | StrOutputParser()
    # result = question_rewriter.invoke({"question": "Autonomous Agents"})
    # print("result:",result)
    return question_rewriter
# result = question_rewriter.invoke({"question": "agent memory"})
# print(result)
