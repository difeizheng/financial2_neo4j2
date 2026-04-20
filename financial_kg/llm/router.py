"""LLM后端路由器"""
from typing import Optional, Dict, Any
from .base import LLMBackend, LLMResponse


class LLMRouter:
    """LLM后端路由器 - 按任务类型选择不同后端"""

    # 默认任务路由配置
    DEFAULT_ROUTING = {
        "structure_recognition": "siliconflow",
        "semantic_annotation": "siliconflow",
        "formula_explanation": "siliconflow",
        "anomaly_detection": "siliconflow",
        "default": "siliconflow",
    }

    def __init__(
        self,
        backends: Dict[str, LLMBackend],
        routing: Optional[Dict[str, str]] = None,
    ):
        self.backends = backends
        self.routing = routing or self.DEFAULT_ROUTING.copy()

    def get_backend(self, task_type: str = "default") -> LLMBackend:
        """根据任务类型获取后端"""
        backend_name = self.routing.get(task_type, self.routing.get("default", "default"))

        if backend_name not in self.backends:
            # fallback to first available backend
            if self.backends:
                return list(self.backends.values())[0]
            raise ValueError(f"没有可用的LLM后端，请检查API密钥配置")

        return self.backends[backend_name]

    def complete(
        self,
        prompt: str,
        task_type: str = "default",
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """完成请求"""
        backend = self.get_backend(task_type)
        return backend.complete(prompt, system_prompt, **kwargs)

    def complete_json(
        self,
        prompt: str,
        task_type: str = "default",
        system_prompt: Optional[str] = None,
    ) -> dict:
        """完成请求并解析JSON"""
        backend = self.get_backend(task_type)
        return backend.complete_json(prompt, system_prompt)

    def health_check_all(self) -> Dict[str, bool]:
        """检查所有后端健康状态"""
        results = {}
        for name, backend in self.backends.items():
            results[name] = backend.health_check()
        return results

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "LLMRouter":
        """从配置创建路由器"""
        backends = {}

        backend_configs = config.get("backends", {})

        # 按优先级顺序尝试初始化后端
        priority_order = ["siliconflow", "deepseek", "claude", "ollama"]

        for name in priority_order:
            bc = backend_configs.get(name, {})

            try:
                if name == "siliconflow":
                    from .siliconflow_backend import SiliconFlowBackend
                    api_key = bc.get("api_key", "")
                    if api_key:  # 只有API key存在才初始化
                        backends[name] = SiliconFlowBackend(
                            api_key=api_key,
                            base_url=bc.get("base_url", "https://api.siliconflow.cn/v1"),
                            model=bc.get("model", "Qwen/Qwen2.5-7B-Instruct"),
                        )

                elif name == "deepseek":
                    from .deepseek_backend import DeepSeekBackend
                    api_key = bc.get("api_key", "")
                    if api_key:
                        backends[name] = DeepSeekBackend(
                            api_key=api_key,
                            model=bc.get("model", "deepseek-chat"),
                            base_url=bc.get("base_url", "https://api.deepseek.com"),
                        )

                elif name == "claude":
                    from .claude_backend import ClaudeBackend
                    api_key = bc.get("api_key", "")
                    if api_key:
                        backends[name] = ClaudeBackend(
                            api_key=api_key,
                            model=bc.get("model", "claude-sonnet-4-6"),
                        )

                elif name == "ollama":
                    from .ollama_backend import OllamaBackend
                    # Ollama不需要API key，只要有base_url就尝试
                    base_url = bc.get("base_url", "http://localhost:11434")
                    backends[name] = OllamaBackend(
                        base_url=base_url,
                        model=bc.get("model", "qwen2.5:7b"),
                    )

            except Exception as e:
                # 初始化失败，跳过该后端
                print(f"警告: {name}后端初始化失败: {e}")
                continue

        # 获取路由配置
        routing = config.get("task_routing", cls.DEFAULT_ROUTING.copy())

        # 确保路由指向存在的后端
        if backends:
            available_backend = list(backends.keys())[0]
            for task, backend_name in routing.items():
                if backend_name not in backends:
                    routing[task] = available_backend

        if not backends:
            raise ValueError(
                "没有可用的LLM后端！请配置至少一个API密钥:\n"
                "- SILICONFLOW_API_KEY (推荐)\n"
                "- DEEPSEEK_API_KEY\n"
                "- ANTHROPIC_API_KEY\n"
                "或启动Ollama本地服务"
            )

        return cls(backends=backends, routing=routing)