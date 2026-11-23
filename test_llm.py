import os
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

load_dotenv()

if not os.getenv("DEEPSEEK_API_KEY"): raise SystemExit("DEEPSEEK_API_KEY not found. Check your .env file.")

llm = ChatDeepSeek(model="deepseek-chat", temperature=0)

response = llm.invoke("Reply with exactly: connection works")
print(response.content)