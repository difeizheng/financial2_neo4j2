"""异常检测Prompt - 检测财务模型中的异常值和断链"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class AnomalyType(Enum):
    """异常类型"""
    UNREASONABLE_VALUE = "unreasonable_value"       # 不合理值
    MISSING_DEPENDENCY = "missing_dependency"       # 断链（依赖缺失）
    FORMULA_ERROR = "formula_error"                 # 公式错误
    UNIT_MISMATCH = "unit_mismatch"                 # 单位不一致
    LOGICAL_ERROR = "logical_error"                 # 逻辑错误
    CIRCULAR_DEPENDENCY = "circular_dependency"     # 循环依赖


@dataclass
class Anomaly:
    """异常检测结果"""
    cell_id: str                # 异常单元格ID
    anomaly_type: AnomalyType   # 异常类型
    severity: str               # 严重程度: "low", "medium", "high", "critical"
    description: str            # 异常描述
    suggestion: str             # 修复建议
    related_cells: List[str]    # 相关单元格


class AnomalyDetectionPrompt:
    """异常检测Prompt生成器"""

    SYSTEM_PROMPT = """你是一位专业的财务模型质量审计专家。
你的任务是检测Excel财务模型中的异常值、逻辑错误和结构问题。

你需要检测以下异常：
1. 不合理值：数值超出合理范围（如负数成本、超大的比率）
2. 断链问题：公式依赖的单元格不存在或值为空
3. 公式错误：公式计算失败或产生错误结果
4. 单位不一致：同一列数值单位混乱
5. 逻辑错误：计算逻辑与财务常识不符
6. 循环依赖：公式形成循环引用

输出格式为JSON，包含检测到的所有异常。"""

    def build_prompt(
        self,
        cells: List[Dict[str, Any]],
        validation_report: Optional[Dict[str, Any]] = None,
        focus_type: Optional[str] = None,
    ) -> str:
        """构建异常检测prompt

        Args:
            cells: 待检测单元格列表
            validation_report: 计算验证报告（匹配率等）
            focus_type: 重点检测类型（可选）

        Returns:
            完整prompt文本
        """
        report_str = ""
        if validation_report:
            report_str = f"""
## 计算验证报告
- 总公式数: {validation_report.get('total', 0)}
- 匹配数: {validation_report.get('matches', 0)}
- 不匹配数: {validation_report.get('mismatches', 0)}
- 错误数: {validation_report.get('errors', 0)}
- 匹配率: {validation_report.get('accuracy', 0):.1%}
"""

        focus_str = ""
        if focus_type:
            focus_str = f"\n重点检测: {focus_type}"

        user_prompt = f"""请检测以下财务模型单元格的异常：

{report_str}{focus_str}
## 待检测单元格（样本）
{self._format_cells(cells[:50])}

## 不匹配单元格详情
{self._format_mismatches((validation_report or {}).get('mismatch_details', [])[:20])}

请输出JSON格式的异常检测结果：

```json
{{
  "anomalies": [
    {{
      "cell_id": "异常单元格ID",
      "anomaly_type": "异常类型",
      "severity": "严重程度",
      "description": "异常描述",
      "suggestion": "修复建议",
      "related_cells": ["相关单元格ID列表"]
    }}
  ],
  "summary": {{
    "total_anomalies": 异常总数,
    "by_severity": {{ "critical": 数量, "high": 数量 }},
    "by_type": {{ "unreasonable_value": 数量 }}
  }}
}}
```"""

        return user_prompt

    def _format_cells(self, cells: List[Dict[str, Any]]) -> str:
        """格式化单元格列表"""
        lines = []
        for cell in cells:
            cell_id = cell.get("id", "")
            value = cell.get("value", "")
            computed = cell.get("computed_value", "")
            formula = cell.get("formula_raw", "")
            semantic = cell.get("semantic_name", "")
            unit = cell.get("semantic_unit", "")

            if formula:
                lines.append(f"- {cell_id}: 原始值={value}, 计算值={computed}, 公式={formula[:50]}")
            else:
                lines.append(f"- {cell_id}: {value} ({semantic}) [{unit}]")
        return "\n".join(lines)

    def _format_mismatches(self, mismatches: List[Dict[str, Any]]) -> str:
        """格式化不匹配详情"""
        if not mismatches:
            return "无不匹配"
        lines = []
        for m in mismatches:
            cell_id = m.get("cell_id", "")
            excel_val = m.get("excel_value", "")
            computed_val = m.get("computed_value", "")
            lines.append(f"- {cell_id}: Excel={excel_val}, 计算={computed_val}")
        return "\n".join(lines)

    def parse_response(self, response: str) -> List[Anomaly]:
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
            anomalies = []
            for a in data.get("anomalies", []):
                type_str = a.get("anomaly_type", "unreasonable_value")
                try:
                    anomaly_type = AnomalyType(type_str)
                except ValueError:
                    anomaly_type = AnomalyType.UNREASONABLE_VALUE

                anomalies.append(Anomaly(
                    cell_id=a.get("cell_id", ""),
                    anomaly_type=anomaly_type,
                    severity=a.get("severity", "medium"),
                    description=a.get("description", ""),
                    suggestion=a.get("suggestion", ""),
                    related_cells=a.get("related_cells", []),
                ))
            return anomalies
        except json.JSONDecodeError:
            return []