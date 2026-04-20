"""LLM后端抽象基类"""
from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLM响应封装"""
    content: str
    model: str
    usage: dict  # {"input_tokens": int, "output_tokens": int}
    latency_ms: float
    success: bool = True
    error: Optional[str] = None


class LLMBackend(ABC):
    """LLM后端抽象基类"""

    name: str = "base"

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """同步完成请求"""
        pass

    @abstractmethod
    async def complete_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """异步完成请求"""
        pass

    def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """完成请求并解析JSON响应"""
        response = self.complete(prompt, system_prompt, temperature=0.3)
        if not response.success:
            return {"error": response.error}

        # 尝试提取JSON
        content = response.content
        try:
            import json
            import re

            # 尝试直接解析
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass

            # 尝试从markdown代码块提取
            json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", content)
            if json_match:
                return json.loads(json_match.group(1))

            return {"error": "无法解析JSON响应", "raw": content}
        except Exception as e:
            return {"error": str(e), "raw": content}

    def health_check(self) -> bool:
        """检查后端是否可用"""
        try:
            response = self.complete("Hello", max_tokens=10)
            return response.success
        except Exception:
            return False