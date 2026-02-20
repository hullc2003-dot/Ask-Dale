from langchain_core.messages import HumanMessage, SystemMessage

Model = "llama-3.3-70b-versatile",  # or "mixtral-8x7b-32768", "gemma2-9b-it"
    temperature=0.7,
    api_key="your_groq_api_key"  # or set GROQ_API_KEY env variable
ChatGroq = "Model"

)

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Tell me a fun fact about space.")
]

response = llm.invoke(messages)
print(response.content)
