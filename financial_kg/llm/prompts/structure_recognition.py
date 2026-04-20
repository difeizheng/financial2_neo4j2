"""结构识别Prompt - 识别Excel中的子表边界和表头结构"""
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class TableRegion:
    """识别出的表格区域"""
    table_id: str           # 表格标识
    sheet: str              # 所在sheet
    start_row: int          # 起始行
    end_row: int            # 结束行
    start_col: str          # 起始列
    end_col: str            # 结束列
    header_rows: List[int]  # 表头行号列表
    category_col: str       # 分类列（如参数名称列）
    value_cols: List[str]   # 数值列（如年份列）
    description: str        # 表格用途描述


class StructureRecognitionPrompt:
    """结构识别Prompt生成器"""

    SYSTEM_PROMPT = """你是一位专业的财务模型结构分析专家。
你的任务是分析Excel财务模型的sheet结构，识别其中的子表边界、表头位置、分类列和数值列。

你需要：
1. 找出每个sheet中的独立表格区域（子表）
2. 识别表头行（可能有多行合并表头）
3. 区分分类列（参数名称、项目名称）和数值列（年份、金额）
4. 推断表格用途（参数输入、成本表、利润表等）

输出格式为JSON，包含识别出的所有表格区域信息。"""

    def build_prompt(
        self,
        sheet_name: str,
        sheet_data: List[Dict[str, Any]],
        sample_cells: List[Dict[str, Any]],
    ) -> str:
        """构建结构识别prompt

        Args:
            sheet_name: sheet名称
            sheet_data: sheet基本信息（行数、列数、合并单元格等）
            sample_cells: 样本单元格数据（前50行非空cell）

        Returns:
            完整prompt文本
        """
        user_prompt = f"""请分析以下Excel sheet的结构：

## Sheet基本信息
- Sheet名称: {sheet_name}
- 数据范围: {sheet_data.get('max_row', 0)}行 × {sheet_data.get('max_col', 0)}列
- 合并单元格数量: {len(sheet_data.get('merged_ranges', []))}

## 合并单元格列表
{self._format_merged_ranges(sheet_data.get('merged_ranges', []))}

## 样本单元格（前50行非空cell）
{self._format_sample_cells(sample_cells[:100])}

请识别这个sheet中的所有独立表格区域，输出JSON格式：

```json
{{
  "tables": [
    {{
      "table_id": "表格唯一标识",
      "start_row": 起始行号,
      "end_row": 结束行号,
      "start_col": "起始列字母",
      "end_col": "结束列字母",
      "header_rows": [表头行号列表],
      "category_col": "分类列字母",
      "value_cols": ["数值列字母列表"],
      "description": "表格用途描述"
    }}
  ]
}}
```"""

        return user_prompt

    def _format_merged_ranges(self, ranges: List[str]) -> str:
        """格式化合并单元格列表"""
        if not ranges:
            return "无合并单元格"
        return "\n".join(f"- {r}" for r in ranges[:20])

    def _format_sample_cells(self, cells: List[Dict[str, Any]]) -> str:
        """格式化样本单元格"""
        lines = []
        for cell in cells:
            addr = cell.get("address", "")
            value = cell.get("value", "")
            formula = cell.get("formula_raw", "")
            if formula:
                lines.append(f"- {addr}: {value} [公式: {formula}]")
            else:
                lines.append(f"- {addr}: {value}")
        return "\n".join(lines)

    def parse_response(self, response: str) -> List[TableRegion]:
        """解析LLM响应，返回表格区域列表"""
        import json
        import re

        # 提取JSON块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析
            json_str = response

        try:
            data = json.loads(json_str)
            tables = []
            for t in data.get("tables", []):
                tables.append(TableRegion(
                    table_id=t.get("table_id", ""),
                    sheet=t.get("sheet", ""),
                    start_row=t.get("start_row", 0),
                    end_row=t.get("end_row", 0),
                    start_col=t.get("start_col", "A"),
                    end_col=t.get("end_col", "A"),
                    header_rows=t.get("header_rows", []),
                    category_col=t.get("category_col", "A"),
                    value_cols=t.get("value_cols", []),
                    description=t.get("description", ""),
                ))
            return tables
        except json.JSONDecodeError:
            return []