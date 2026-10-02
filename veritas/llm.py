import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to your .env file or Streamlit secrets."
        )

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    return LLM(
        model=f"groq/{model}",
        api_key=api_key,
        temperature=0.2,
    )
