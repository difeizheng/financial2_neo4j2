"""Claude API 后端"""
import os
import time
from typing import Optional
from .base import LLMBackend, LLMResponse


class ClaudeBackend(LLMBackend):
    """Anthropic Claude API 后端"""

    name = "claude"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-6",
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.base_url = base_url or "https://api.anthropic.com"
        self._client = None

    def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise ImportError("请安装 anthropic: pip install anthropic")
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

            messages = [{"role": "user", "content": prompt}]

            params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system_prompt:
                params["system"] = system_prompt

            response = client.messages.create(**params)

            latency = (time.time() - start_time) * 1000

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
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
        # Claude SDK 的异步版本
        import asyncio

        # 简单包装同步调用
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.complete(prompt, system_prompt, temperature, max_tokens),
        )