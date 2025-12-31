import json
import time
import requests
from typing import Optional, Dict

class AIService:
    """Service for interacting with Ollama AI"""
    
    def __init__(self, url: str, model: str, timeout: int = 1):
        self.url = url
        self.model = model
        self.timeout = timeout
    
    def query(self, prompt: str) -> str:
        """Send a prompt to Ollama and get the response"""
        stream_timeout_s = min(self.timeout, 180)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": "30m",
            "options": {
                "num_predict": 128,  # Limit response length
                "temperature": 0.7,
            },
        }

        prompt_size = len(prompt or "")
        print(f"[ollama] prompt_size_chars={prompt_size}")

        max_attempts = 2
        backoff_s = 2

        for attempt in range(1, max_attempts + 1):
            start = time.perf_counter()
            try:
                response = requests.post(
                    self.url,
                    json=payload,
                    timeout=(5, stream_timeout_s),
                    stream=True,
                )
                elapsed = time.perf_counter() - start
                print(f"[ollama] attempt={attempt} status={response.status_code} duration_s={elapsed:.2f}")

                if response.status_code == 200:
                    chunks = []
                    stream_start = time.perf_counter()
                    for line in response.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        token = data.get("response")
                        if token:
                            chunks.append(token)
                        if data.get("done") is True:
                            break
                        if time.perf_counter() - stream_start > stream_timeout_s:
                            print("[ollama] stream timeout reached, returning partial response")
                            break
                    if chunks:
                        print(f"[ollama] stream_complete chars={sum(len(c) for c in chunks)}")
                        return "".join(chunks)
                    return "Error: Ollama returned an empty streamed response"
                return f"Error: Ollama returned status code {response.status_code}"

            except requests.exceptions.ConnectionError:
                return _get_connection_error_message()
            except Exception as e:
                elapsed = time.perf_counter() - start
                print(f"[ollama] attempt={attempt} error={type(e).__name__} duration_s={elapsed:.2f}")
                if attempt < max_attempts:
                    time.sleep(backoff_s)
                    backoff_s *= 2
                    continue
                return f"Error querying Ollama: {str(e)}"
    
    def generate_health_insights(self, health_summary: Dict, question: str) -> str:
        """Generate AI insights based on health data and user question"""
        prompt = self._build_health_prompt(health_summary, question)
        return self.query(prompt)

    def warm_up(self) -> None:
        """Prime Ollama with a minimal request so the model loads."""
        try:
            _ = self.query("Warm-up request. Reply with OK.")
        except Exception:
            pass
    
    @staticmethod
    def _build_health_prompt(health_summary: Dict, question: str) -> str:
        """Build prompt for health data analysis"""
        aggregations = health_summary.get('aggregations', {})
        trimmed = _trim_aggregations_for_question(aggregations, question, max_rows=60)

        prompt = (
            "You are analyzing Apple Health data.\n"
            "Use ONLY the aggregated tables provided below to answer the user's question.\n"
            "If data is missing, say so briefly.\n\n"
            f"User question: {question}\n\n"
            "Aggregated tables (JSON):\n"
        )

        prompt += json.dumps(trimmed or {}, ensure_ascii=True, indent=2)

        prompt += (
            "\n\nProvide a clear, helpful answer with specific insights and actionable recommendations. "
            "Be encouraging and practical. Keep your response concise but informative."
        )

        return prompt


def _trim_aggregations_for_question(
    aggregations: Dict,
    question: str,
    *,
    max_rows: int = 14,
) -> Dict:
    """
    Keep only relevant tables and limit row counts to shrink the prompt.
    """
    if not isinstance(aggregations, dict):
        return {}

    q = (question or "").lower()
    table_map = {
        "steps_calories_circadian": ["step", "walk", "calorie", "energy"],
        "heart_rate_stats": ["heart", "bpm", "pulse", "hr"],
        "glucose_oxygen_thresholds": ["glucose", "sugar", "oxygen", "spo2", "saturation"],
        "sleep_session_shift": ["sleep", "bed", "wake"],
    }

    selected = []
    for table, keywords in table_map.items():
        if any(k in q for k in keywords):
            selected.append(table)

    if not selected:
        selected = list(table_map.keys())

    trimmed: Dict[str, object] = {}
    for table in selected:
        rows = aggregations.get(table, [])
        if isinstance(rows, list):
            trimmed[table] = rows[-max_rows:]
        else:
            trimmed[table] = rows

    return trimmed


def _get_connection_error_message() -> str:
    """Return error message when Ollama connection fails"""
    return """⚠️ Cannot connect to Ollama. Please make sure:
1. Ollama is installed (https://ollama.ai)
2. Run 'ollama serve' in a terminal
3. Run 'ollama pull llama3.2'"""
