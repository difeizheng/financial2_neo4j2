"""语义标注Prompt - 为单元格添加语义信息"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SemanticInfo:
    """单元格语义信息"""
    cell_id: str                # 单元格ID
    semantic_name: str          # 语义名称（如"建设期_年数"）
    semantic_desc: str          # 语义描述
    semantic_unit: str          # 单位（如"年"、"万元"、"%"）
    semantic_tags: List[str]    # 标签（如"输入参数"、"计算结果"）
    semantic_category: str      # 类别（如"时间参数"、"成本项"）
    confidence: float           # 标注置信度


class SemanticAnnotationPrompt:
    """语义标注Prompt生成器"""

    SYSTEM_PROMPT = """你是一位专业的财务模型语义分析专家。
你的任务是为Excel财务模型的单元格添加语义标注，使其更容易被理解和使用。

你需要：
1. 推断每个单元格的语义名称（简洁、符合财务惯例）
2. 描述单元格的含义和用途
3. 判断数值单位（年、月、万元、元、%等）
4. 添加分类标签（输入参数、中间计算、输出结果、时间参数、成本项等）
5. 判断置信度（对推断不确定的标注较低置信度）

输出格式为JSON，包含每个单元格的语义信息。"""

    def build_prompt(
        self,
        cells: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建语义标注prompt

        Args:
            cells: 待标注单元格列表（建议批量不超过50个）
            context: 上下文信息（表格结构、相邻单元格等）

        Returns:
            完整prompt文本
        """
        context_str = ""
        if context:
            context_str = f"""
## 上下文信息
- 所在表格: {context.get('table_id', '未知')}
- 表格用途: {context.get('table_description', '未知')}
- 同行分类: {context.get('row_category', '未知')}
- 同列标签: {context.get('col_label', '未知')}
"""

        user_prompt = f"""请为以下单元格添加语义标注：

{context_str}
## 待标注单元格
{self._format_cells(cells)}

请输出JSON格式的语义标注：

```json
{{
  "annotations": [
    {{
      "cell_id": "单元格ID",
      "semantic_name": "语义名称",
      "semantic_desc": "语义描述",
      "semantic_unit": "单位",
      "semantic_tags": ["标签列表"],
      "semantic_category": "类别",
      "confidence": 置信度(0-1)
    }}
  ]
}}
```"""

        return user_prompt

    def _format_cells(self, cells: List[Dict[str, Any]]) -> str:
        """格式化单元格列表"""
        lines = []
        for cell in cells:
            cell_id = cell.get("id", "")
            address = cell.get("address", "")
            value = cell.get("value", "")
            formula = cell.get("formula_raw", "")
            row_label = cell.get("row_label", "")
            col_label = cell.get("col_label", "")

            info = f"- ID: {cell_id}, 地址: {address}"
            if row_label:
                info += f", 行标签: {row_label}"
            if col_label:
                info += f", 列标签: {col_label}"
            if formula:
                info += f", 公式: {formula}"
            else:
                info += f", 值: {value}"
            lines.append(info)
        return "\n".join(lines)

    def parse_response(self, response: str) -> List[SemanticInfo]:
        """解析LLM响应，返回语义信息列表"""
        import json
        import re

        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response

        try:
            data = json.loads(json_str)
            annotations = []
            for a in data.get("annotations", []):
                annotations.append(SemanticInfo(
                    cell_id=a.get("cell_id", ""),
                    semantic_name=a.get("semantic_name", ""),
                    semantic_desc=a.get("semantic_desc", ""),
                    semantic_unit=a.get("semantic_unit", ""),
                    semantic_tags=a.get("semantic_tags", []),
                    semantic_category=a.get("semantic_category", ""),
                    confidence=a.get("confidence", 0.5),
                ))
            return annotations
        except json.JSONDecodeError:
            return []