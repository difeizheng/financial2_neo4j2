"""全局配置"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

# 加载.env文件
try:
    from dotenv import load_dotenv
    # 项目根目录的.env文件
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv未安装时跳过


@dataclass
class Config:
    """全局配置"""

    # 项目路径
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data")
    uploads_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "uploads")
    output_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "output")

    # LLM 配置 - 从环境变量读取
    llm_config: Dict[str, Any] = field(default_factory=lambda: {
        "default_backend": os.environ.get("DEFAULT_LLM_BACKEND", "siliconflow"),
        "backends": {
            "siliconflow": {
                "api_key": os.environ.get("SILICONFLOW_API_KEY", ""),
                "base_url": os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
                "model": os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
            },
            "claude": {
                "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
                "model": "claude-sonnet-4-6",
            },
            "deepseek": {
                "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
                "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            },
            "ollama": {
                "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                "model": os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"),
            },
        },
        "task_routing": {
            "structure_recognition": os.environ.get("LLM_TASK_ROUTING_STRUCTURE_RECOGNITION", "siliconflow"),
            "semantic_annotation": os.environ.get("LLM_TASK_ROUTING_SEMANTIC_ANNOTATION", "siliconflow"),
            "formula_explanation": os.environ.get("LLM_TASK_ROUTING_FORMULA_EXPLANATION", "siliconflow"),
            "anomaly_detection": os.environ.get("LLM_TASK_ROUTING_ANOMALY_DETECTION", "siliconflow"),
            "default": os.environ.get("DEFAULT_LLM_BACKEND", "siliconflow"),
        },
    })

    # 解析配置
    parse_config: Dict[str, Any] = field(default_factory=lambda: {
        "batch_size": int(os.environ.get("PARSE_BATCH_SIZE", "50")),
        "timeout_seconds": int(os.environ.get("PARSE_TIMEOUT_SECONDS", "300")),
    })

    def __post_init__(self):
        """确保目录存在"""
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_llm_router(self):
        """获取LLM路由器"""
        from .llm.router import LLMRouter
        return LLMRouter.from_config(self.llm_config)

    def validate_llm_config(self) -> Dict[str, bool]:
        """验证LLM配置是否有效"""
        results = {}
        backends = self.llm_config.get("backends", {})

        for name, config in backends.items():
            if name == "ollama":
                # Ollama不需要API key
                results[name] = bool(config.get("base_url"))
            else:
                # 其他后端需要API key
                results[name] = bool(config.get("api_key"))

        return results

    def get_available_backends(self) -> list:
        """获取可用的LLM后端列表"""
        validation = self.validate_llm_config()
        return [name for name, valid in validation.items() if valid]


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """设置全局配置"""
    global _config
    _config = config


def reload_config() -> Config:
    """重新加载配置（从.env重新读取）"""
    global _config
    _config = Config()
    return _config