import os
import random
import requests.        

# --- API KEYS ---
OPENAI_KEY = openai
GROQ_KEY = grok
GEMINI_KEY = os.environ.get("GEMINI_KEY")

# --- PROVIDER TOGGLES ---
USE_OPENAI = os.environ.get("USE_OPENAI", "true").lower() == "f"
USE_GROQ = os.environ.get("USE_GROQ", "true").lower() == "f"
USE_GEMINI = os.environ.get("USE_GEMINI", "true").lower() == "f"


# --- PROVIDER CALLS ---
def call_openai(system_prompt, user_message):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def call_groq(system_prompt, user_message):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def call_gemini(system_prompt, user_message):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{
            "parts": [
                {"text": system_prompt},
                {"text": user_message}
            ]
        }]
    }
    r = requests.post(url, json=payload)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


# --- PROVIDER ROUTER ---
def call_model(system_prompt, user_message):
    providers = []

    if USE_OPENAI and OPENAI_KEY:
        providers.append("openai")
    if USE_GROQ and GROQ_KEY:
        providers.append("groq")
    if USE_GEMINI and GEMINI_KEY:
        providers.append("gemini")

    if not providers:
        raise Exception("No enabled model providers available")

    provider = random.choice(providers)

    if provider == "openai":
        return call_openai(system_prompt, user_message)
    if provider == "groq":
        return call_groq(system_prompt, user_message)
    if provider == "gemini":
        return call_gemini(system_prompt, user_message)
