import os
import requests
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = "sk-7d82e98ed52444609cb46118a5ba3ad3"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"


DEFAULT_SYSTEM_PROMPT = """
You are BRIGHTLY AI, a legal public intelligence and defensive cybersecurity assistant.

Rules:
- Analyze only public-source information, user-consented verified profile records, and metadata.
- Do not reveal private addresses, passwords, SIM registration databases, tax databases, banking data, government records, hidden accounts, or private databases.
- If sensitive data is requested, mark it as REDACTED, BLOCKED, or NOT ACCESSED.
- Explain findings clearly and professionally.
- For names/usernames, say that matches are possible public references, not confirmed identity.
- For phones, explain that metadata and consent-based records are allowed, but owner lookup from private systems is not.
""".strip()


def ask_deepseek(message: str, context: str = "", system_prompt: str = None) -> str:
    """
    DeepSeek AI assistant for BRIGHTLY.
    Accepts:
    - message
    - context
    - system_prompt
    """

    if not DEEPSEEK_API_KEY:
        return (
            "DeepSeek API key is missing. Add DEEPSEEK_API_KEY to backend/.env. "
            "For now, BRIGHTLY AI is running in fallback mode."
        )

    final_system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    user_content = message

    if context:
        user_content = f"""
User message:
{message}

Current BRIGHTLY context:
{context}
""".strip()

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": final_system_prompt
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        "temperature": 0.4,
        "max_tokens": 900
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=40
        )

        if response.status_code != 200:
            return (
                f"DeepSeek API error {response.status_code}: "
                f"{response.text[:500]}"
            )

        data = response.json()

        return data["choices"][0]["message"]["content"]

    except requests.exceptions.Timeout:
        return "DeepSeek request timed out. Try again."

    except Exception as e:
        return f"DeepSeek request failed: {str(e)}"