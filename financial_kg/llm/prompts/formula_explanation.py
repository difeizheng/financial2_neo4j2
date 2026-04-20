"""公式解释Prompt - 为公式生成人类可读的解释"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class FormulaExplanation:
    """公式解释结果"""
    cell_id: str                # 单元格ID
    formula_raw: str            # 原始公式
    explanation: str            # 公式解释
    logic_steps: List[str]      # 计算逻辑步骤
    dependencies_desc: str      # 依赖说明
    business_meaning: str       # 业务含义
    tips: str                   # 使用提示


class FormulaExplanationPrompt:
    """公式解释Prompt生成器"""

    SYSTEM_PROMPT = """你是一位专业的财务公式分析专家。
你的任务是将Excel财务公式转换为人类可读的解释，帮助用户理解计算逻辑。

你需要：
1. 解释公式的整体含义
2. 分解计算步骤（从内层函数到外层）
3. 说明依赖的单元格/范围含义
4. 阐述公式的业务意义
5. 提供使用提示或注意事项

输出格式为JSON，包含完整的公式解释信息。"""

    def build_prompt(
        self,
        cell: Dict[str, Any],
        dependencies: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建公式解释prompt

        Args:
            cell: 公式单元格信息
            dependencies: 依赖单元格信息
            context: 上下文信息（表格用途等）

        Returns:
            完整prompt文本
        """
        deps_str = ""
        if dependencies:
            deps_str = f"""
## 依赖单元格信息
{self._format_dependencies(dependencies)}"""

        context_str = ""
        if context:
            context_str = f"""
## 上下文信息
- 所在表格: {context.get('table_id', '未知')}
- 表格用途: {context.get('table_description', '未知')}
- 单元格语义: {context.get('semantic_name', '未知')}
"""

        user_prompt = f"""请解释以下Excel公式：

## 公式单元格
- ID: {cell.get('id', '')}
- 地址: {cell.get('address', '')}
- 原始公式: {cell.get('formula_raw', '')}
- 计算值: {cell.get('computed_value', '')}
{context_str}{deps_str}
请输出JSON格式的公式解释：

```json
{{
  "cell_id": "单元格ID",
  "formula_raw": "原始公式",
  "explanation": "公式整体含义解释",
  "logic_steps": ["计算步骤1", "计算步骤2"],
  "dependencies_desc": "依赖说明",
  "business_meaning": "业务含义",
  "tips": "使用提示"
}}
```"""

        return user_prompt

    def _format_dependencies(self, dependencies: Dict[str, Any]) -> str:
        """格式化依赖信息"""
        lines = []
        for dep_id, dep_info in dependencies.items():
            addr = dep_info.get("address", "")
            value = dep_info.get("value", "")
            semantic = dep_info.get("semantic_name", "")
            lines.append(f"- {dep_id} ({addr}): {semantic or value}")
        return "\n".join(lines[:20])  # 限制显示数量

    def parse_response(self, response: str) -> Optional[FormulaExplanation]:
        """解析LLM响应"""
        import json
        import re

        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response

        try:
            data = json.loads(json_str)
            return FormulaExplanation(
                cell_id=data.get("cell_id", ""),
                formula_raw=data.get("formula_raw", ""),
                explanation=data.get("explanation", ""),
                logic_steps=data.get("logic_steps", []),
                dependencies_desc=data.get("dependencies_desc", ""),
                business_meaning=data.get("business_meaning", ""),
                tips=data.get("tips", ""),
            )
        except json.JSONDecodeError:
            return None