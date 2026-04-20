"""JSON导入器 - 加载已导出的图谱数据"""
import json
from pathlib import Path
from typing import Optional

from ..models.cell import CellNode
from ..models.edge import DependencyEdge
from ..models.graph import KnowledgeGraph, GraphStats


class JSONImporter:
    """从JSON文件加载知识图谱"""

    def import_graph(
        self,
        nodes_file: str,
        edges_file: str,
        name: str = "imported_graph",
        source_file: str = "",
    ) -> KnowledgeGraph:
        """
        从JSON文件导入图谱

        Args:
            nodes_file: nodes.json文件路径
            edges_file: edges.json文件路径
            name: 图谱名称
            source_file: 源Excel文件路径

        Returns:
            KnowledgeGraph实例
        """
        # 加载节点
        with open(nodes_file, "r", encoding="utf-8") as f:
            nodes_data = json.load(f)

        # 加载边
        with open(edges_file, "r", encoding="utf-8") as f:
            edges_data = json.load(f)

        # 创建图谱
        graph = KnowledgeGraph(
            name=name,
            source_file=source_file,
            sheets=list(set(n["sheet"] for n in nodes_data)),
        )

        # 添加节点
        for n in nodes_data:
            node = CellNode(
                id=n["id"],
                sheet=n["sheet"],
                row=n["row"],
                col=n["col"],
                col_index=n["col_index"],
                address=n["address"],
                value=n["value"],
                value_type=n.get("value_type", "unknown"),
                formula_raw=n.get("formula_raw"),
                formula_ast=n.get("formula_ast"),
                computed_value=n.get("computed_value"),
                is_header=n.get("is_header", False),
                is_merged=n.get("is_merged", False),
                merge_range=n.get("merge_range"),
                table_id=n.get("table_id"),
                row_category=n.get("row_category"),
                col_category=n.get("col_category"),
                row_label=n.get("row_label"),
                col_label=n.get("col_label"),
                semantic_name=n.get("semantic_name"),
                semantic_unit=n.get("semantic_unit"),
                semantic_tags=n.get("semantic_tags", []),
                depth=n.get("depth", 0),
                in_degree=n.get("in_degree", 0),
                out_degree=n.get("out_degree", 0),
                is_input=n.get("is_input", False),
                is_output=n.get("is_output", False),
                parse_status=n.get("parse_status", "raw"),
            )
            graph.add_node(node)

        # 添加边
        for e in edges_data:
            edge = DependencyEdge(
                id=e["id"],
                source_id=e["source"],
                target_id=e["target"],
                edge_type=e.get("type", "formula_ref"),
                ref_type=e.get("ref_type", "relative"),
                ref_raw=e.get("ref_raw", ""),
                is_cross_sheet=e.get("is_cross_sheet", False),
                weight=e.get("weight", 1.0),
            )
            graph.add_edge(edge)

        # 更新统计
        graph.update_stats()

        return graph


def load_graph_from_json(output_dir: str, prefix: str = "") -> KnowledgeGraph:
    """
    从输出目录加载图谱

    Args:
        output_dir: 输出目录路径
        prefix: 文件前缀

    Returns:
        KnowledgeGraph实例
    """
    importer = JSONImporter()

    nodes_file = Path(output_dir) / f"{prefix}nodes.json"
    edges_file = Path(output_dir) / f"{prefix}edges.json"

    if not nodes_file.exists() or not edges_file.exists():
        raise FileNotFoundError(f"图谱文件不存在: {nodes_file} 或 {edges_file}")

    return importer.import_graph(
        nodes_file=str(nodes_file),
        edges_file=str(edges_file),
    )