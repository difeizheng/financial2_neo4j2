"""SiliconFlow LLM后端 - 兼容OpenAI格式"""
import os
import json
import requests
import asyncio
from typing import Dict, Any, Optional
from .base import LLMBackend, LLMResponse


class SiliconFlowBackend(LLMBackend):
    """SiliconFlow API后端

    SiliconFlow提供OpenAI兼容的API接口
    支持多种开源大模型: Qwen, DeepSeek, Yi等
    """

    name: str = "siliconflow"

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.api_key = api_key or os.environ.get("SILICONFLOW_API_KEY", "")
        self.base_url = base_url or os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
        self.model = model or os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        self.temperature = temperature
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError("SiliconFlow API key未配置，请设置SILICONFLOW_API_KEY环境变量")

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """调用SiliconFlow API完成对话"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        import time
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=self.model,
                usage=data.get("usage", {"input_tokens": 0, "output_tokens": 0}),
                latency_ms=latency_ms,
                success=True,
            )

        except requests.exceptions.RequestException as e:
            return LLMResponse(
                content="",
                model=self.model,
                usage={"input_tokens": 0, "output_tokens": 0},
                latency_ms=0,
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
        """异步调用API"""
        import aiohttp
        import time

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    latency_ms = (time.time() - start_time) * 1000

                    return LLMResponse(
                        content=data["choices"][0]["message"]["content"],
                        model=self.model,
                        usage=data.get("usage", {"input_tokens": 0, "output_tokens": 0}),
                        latency_ms=latency_ms,
                        success=True,
                    )

        except Exception as e:
            return LLMResponse(
                content="",
                model=self.model,
                usage={"input_tokens": 0, "output_tokens": 0},
                latency_ms=0,
                success=False,
                error=str(e),
            )