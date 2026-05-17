import os
from groq import Groq
from dotenv import load_dotenv
# from .env import 
load_dotenv()

# Set your key directly here (for testing)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

def call_llm(prompt: str):
    chat = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return chat.choices[0].message.content


if __name__ == "__main__":
    print(call_llm("What is the capital of India?"))
