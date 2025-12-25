import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"  # change if your ollama model name differs

def ask(prompt: str) -> str:
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    r = requests.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()
    return r.json().get("response", "").strip()

def main() -> None:
    print("AI Daily Assistant (Phase 0)")
    print("Type a request. Type 'quit' to exit.\n")

    while True:
        user = input("You> ").strip()
        if user.lower() in {"quit", "exit"}:
            break
        if not user:
            continue
        reply = ask(user)
        print(f"\nAssistant> {reply}\n")

if __name__ == "__main__":
    main()
