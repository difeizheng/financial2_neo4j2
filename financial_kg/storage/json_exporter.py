"""JSON导出器 - 导出nodes.json / edges.json"""
import json
from typing import Any, Dict, List
from pathlib import Path
from ..models.graph import KnowledgeGraph


class JSONExporter:
    """知识图谱JSON导出器"""

    def __init__(self, output_dir: str = "data/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, graph: KnowledgeGraph, prefix: str = "") -> Dict[str, str]:
        """导出图谱为JSON文件，返回文件路径"""
        # 导出节点
        nodes_file = self.output_dir / f"{prefix}nodes.json"
        nodes_data = [node.to_dict() for node in graph.nodes.values()]
        with open(nodes_file, "w", encoding="utf-8") as f:
            json.dump(nodes_data, f, ensure_ascii=False, indent=2)

        # 导出边
        edges_file = self.output_dir / f"{prefix}edges.json"
        edges_data = [edge.to_dict() for edge in graph.edges]
        with open(edges_file, "w", encoding="utf-8") as f:
            json.dump(edges_data, f, ensure_ascii=False, indent=2)

        # 导出图谱元数据
        meta_file = self.output_dir / f"{prefix}graph_meta.json"
        meta_data = graph.to_dict()
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)

        return {
            "nodes": str(nodes_file),
            "edges": str(edges_file),
            "meta": str(meta_file),
        }

    def export_validation_report(self, report: Dict[str, Any], prefix: str = "") -> str:
        """导出验证报告"""
        report_file = self.output_dir / f"{prefix}validation_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return str(report_file)