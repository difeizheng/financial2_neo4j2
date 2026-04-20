"""Ollama 本地后端"""
import time
import json
from typing import Optional
from .base import LLMBackend, LLMResponse


class OllamaBackend(LLMBackend):
    """Ollama 本地后端"""

    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
    ):
        self.base_url = base_url
        self.model = model

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """同步完成请求"""
        start_time = time.time()

        try:
            import requests

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            if system_prompt:
                payload["system"] = system_prompt

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()

            data = response.json()
            latency = (time.time() - start_time) * 1000

            return LLMResponse(
                content=data.get("response", ""),
                model=data.get("model", self.model),
                usage={
                    "input_tokens": data.get("prompt_eval_count", 0),
                    "output_tokens": data.get("eval_count", 0),
                },
                latency_ms=latency,
                success=True,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return LLMResponse(
                content="",
                model=self.model,
                usage={},
                latency_ms=latency,
                success=False,
                error=str(e),
            )

    async def complete_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """异步完成请求"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.complete(prompt, system_prompt, temperature, max_tokens),
        )

    def health_check(self) -> bool:
        """检查 Ollama 是否运行"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list:
        """列出可用模型"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []