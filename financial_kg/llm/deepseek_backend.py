"""DeepSeek API 后端"""
import os
import time
import json
from typing import Optional
from .base import LLMBackend, LLMResponse


class DeepSeekBackend(LLMBackend):
    """DeepSeek API 后端（兼容 OpenAI 格式）"""

    name = "deepseek"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "deepseek-chat",
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.model = model
        self.base_url = base_url or "https://api.deepseek.com"
        self._client = None

    def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        return self._client

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
            client = self._get_client()

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            latency = (time.time() - start_time) * 1000

            usage = response.usage or {}
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "input_tokens": usage.prompt_tokens or 0,
                    "output_tokens": usage.completion_tokens or 0,
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