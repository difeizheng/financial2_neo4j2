"""LLM集成服务 - 将LLM能力接入解析流水线"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from .router import LLMRouter
from .prompts import (
    StructureRecognitionPrompt,
    SemanticAnnotationPrompt,
    FormulaExplanationPrompt,
    AnomalyDetectionPrompt,
)
from .prompts.structure_recognition import TableRegion
from .prompts.semantic_annotation import SemanticInfo
from .prompts.formula_explanation import FormulaExplanation
from .prompts.anomaly_detection import Anomaly


def _get_router() -> LLMRouter:
    """获取LLM路由器"""
    try:
        from financial_kg.config import get_config
        config = get_config()
        return config.get_llm_router()
    except Exception as e:
        raise RuntimeError(f"无法获取LLM路由器: {e}")


class LLMIntegrationService:
    """LLM集成服务，协调各prompt与LLM后端"""

    def __init__(self, router: Optional[LLMRouter] = None):
        if router is None:
            self.router = _get_router()
        else:
            self.router = router
        self.structure_prompt = StructureRecognitionPrompt()
        self.semantic_prompt = SemanticAnnotationPrompt()
        self.formula_prompt = FormulaExplanationPrompt()
        self.anomaly_prompt = AnomalyDetectionPrompt()

    def recognize_structure(
        self,
        sheet_name: str,
        sheet_data: Dict[str, Any],
        sample_cells: List[Dict[str, Any]],
    ) -> List[TableRegion]:
        """识别sheet中的表格结构

        Args:
            sheet_name: sheet名称
            sheet_data: sheet基本信息
            sample_cells: 样本单元格

        Returns:
            识别出的表格区域列表
        """
        # 使用结构识别任务类型的后端
        backend = self.router.get_backend("structure_recognition")

        # 构建prompt
        prompt = self.structure_prompt.build_prompt(sheet_name, sheet_data, sample_cells)

        # 调用LLM
        response = backend.complete(
            prompt=prompt,
            system_prompt=self.structure_prompt.SYSTEM_PROMPT,
        )

        # 解析响应（response是LLMResponse对象）
        response_text = response.content if response.success else ""
        return self.structure_prompt.parse_response(response_text)

    def annotate_semantics(
        self,
        cells: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        batch_size: int = 30,
    ) -> List[SemanticInfo]:
        """批量标注单元格语义

        Args:
            cells: 待标注单元格列表
            context: 上下文信息
            batch_size: 批量大小（避免prompt过长）

        Returns:
            语义标注列表
        """
        backend = self.router.get_backend("semantic_annotation")
        annotations = []

        # 分批处理
        for i in range(0, len(cells), batch_size):
            batch = cells[i:i + batch_size]
            prompt = self.semantic_prompt.build_prompt(batch, context)

            response = backend.complete(
                prompt=prompt,
                system_prompt=self.semantic_prompt.SYSTEM_PROMPT,
            )

            response_text = response.content if response.success else ""
            batch_annotations = self.semantic_prompt.parse_response(response_text)
            annotations.extend(batch_annotations)

        return annotations

    def explain_formula(
        self,
        cell: Dict[str, Any],
        dependencies: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[FormulaExplanation]:
        """解释公式含义

        Args:
            cell: 公式单元格信息
            dependencies: 依赖单元格信息
            context: 上下文信息

        Returns:
            公式解释
        """
        backend = self.router.get_backend("formula_explanation")

        prompt = self.formula_prompt.build_prompt(cell, dependencies, context)

        response = backend.complete(
            prompt=prompt,
            system_prompt=self.formula_prompt.SYSTEM_PROMPT,
        )

        response_text = response.content if response.success else ""
        return self.formula_prompt.parse_response(response_text)

    def detect_anomalies(
        self,
        cells: List[Dict[str, Any]],
        validation_report: Optional[Dict[str, Any]] = None,
        focus_type: Optional[str] = None,
    ) -> List[Anomaly]:
        """检测财务模型异常

        Args:
            cells: 待检测单元格列表
            validation_report: 计算验证报告
            focus_type: 重点检测类型

        Returns:
            异常列表
        """
        backend = self.router.get_backend("anomaly_detection")

        prompt = self.anomaly_prompt.build_prompt(cells, validation_report, focus_type)

        response = backend.complete(
            prompt=prompt,
            system_prompt=self.anomaly_prompt.SYSTEM_PROMPT,
        )

        response_text = response.content if response.success else ""
        return self.anomaly_prompt.parse_response(response_text)

    def run_full_pipeline(
        self,
        graph_data: Dict[str, Any],
        sheets_info: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """运行完整LLM流水线

        Args:
            graph_data: 图谱数据（nodes, edges）
            sheets_info: 各sheet信息

        Returns:
            增强后的图谱数据
        """
        results = {
            "tables": {},
            "semantics": {},
            "anomalies": [],
        }

        # 1. 结构识别
        for sheet_name, sheet_data in sheets_info.items():
            # 提取样本单元格
            sample_cells = [
                n for n in graph_data.get("nodes", [])
                if n.get("sheet") == sheet_name
            ][:100]

            tables = self.recognize_structure(sheet_name, sheet_data, sample_cells)
            results["tables"][sheet_name] = [
                {
                    "table_id": t.table_id,
                    "start_row": t.start_row,
                    "end_row": t.end_row,
                    "start_col": t.start_col,
                    "end_col": t.end_col,
                    "header_rows": t.header_rows,
                    "category_col": t.category_col,
                    "value_cols": t.value_cols,
                    "description": t.description,
                }
                for t in tables
            ]

        # 2. 语义标注（仅标注输入节点）
        input_nodes = [
            n for n in graph_data.get("nodes", [])
            if n.get("formula_raw") is None and n.get("value") is not None
        ]

        if input_nodes:
            semantics = self.annotate_semantics(input_nodes[:50])  # 限制数量
            for s in semantics:
                results["semantics"][s.cell_id] = {
                    "semantic_name": s.semantic_name,
                    "semantic_desc": s.semantic_desc,
                    "semantic_unit": s.semantic_unit,
                    "semantic_tags": s.semantic_tags,
                    "semantic_category": s.semantic_category,
                    "confidence": s.confidence,
                }

        # 3. 异常检测
        validation_report = graph_data.get("validation_report")
        anomalies = self.detect_anomalies(
            graph_data.get("nodes", [])[:50],
            validation_report,
        )
        results["anomalies"] = [
            {
                "cell_id": a.cell_id,
                "anomaly_type": a.anomaly_type.value,
                "severity": a.severity,
                "description": a.description,
                "suggestion": a.suggestion,
                "related_cells": a.related_cells,
            }
            for a in anomalies
        ]

        return results

    def save_results(self, results: Dict[str, Any], output_path: Path) -> None:
        """保存LLM处理结果"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)