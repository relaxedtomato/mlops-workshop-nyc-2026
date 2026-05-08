from openai import OpenAI
import httpx


class LLMClient:
    def __init__(self, endpoint, api_key, model, max_tokens=512):
        self.client = OpenAI(base_url=endpoint, api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def summarize(self, content):
        query = f"Summarize in 1-2 sentences:\n{content}"
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": query}],
                max_tokens=self.max_tokens,
            )
            out = completion.choices[0].message.content or ""
            return out.split("</think>")[-1].strip()
        except (httpx.ConnectTimeout, httpx.ConnectError, Exception) as e:
            return f"LLM unavailable: {e}"
