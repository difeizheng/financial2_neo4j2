"""知识图谱容器模型"""
from dataclasses import dataclass, field
from typing import Any, Optional
from .cell import CellNode
from .edge import DependencyEdge


@dataclass
class GraphStats:
    """图谱统计信息"""
    total_nodes: int = 0
    total_edges: int = 0
    input_nodes: int = 0      # 纯输入节点数
    formula_nodes: int = 0    # 有公式的节点数
    max_depth: int = 0        # 最大DAG深度
    cross_sheet_edges: int = 0  # 跨sheet边数


@dataclass
class KnowledgeGraph:
    """财务模型知识图谱容器"""

    name: str                          # 项目/模型名称
    source_file: str                   # Excel源文件名
    sheets: list = field(default_factory=list)  # 包含的sheet列表
    nodes: dict = field(default_factory=dict)   # id → CellNode
    edges: list = field(default_factory=list)   # DependencyEdge列表

    # === 邻接表（构建后填充） ===
    adjacency: dict = field(default_factory=dict)      # node_id → [依赖的上游node_ids]
    reverse_adjacency: dict = field(default_factory=dict)  # node_id → [被依赖的下游node_ids]

    # === 拓扑排序结果 ===
    topo_order: list = field(default_factory=list)  # 拓扑排序后的node_id列表

    # === 统计 ===
    stats: GraphStats = field(default_factory=GraphStats)

    def add_node(self, node: CellNode) -> None:
        """添加节点"""
        self.nodes[node.id] = node

    def add_edge(self, edge: DependencyEdge) -> None:
        """添加边，同时更新邻接表"""
        self.edges.append(edge)

        # 正向邻接表：target依赖source
        if edge.target_id not in self.adjacency:
            self.adjacency[edge.target_id] = []
        if edge.source_id not in self.adjacency[edge.target_id]:
            self.adjacency[edge.target_id].append(edge.source_id)

        # 反向邻接表：source被target依赖
        if edge.source_id not in self.reverse_adjacency:
            self.reverse_adjacency[edge.source_id] = []
        if edge.target_id not in self.reverse_adjacency[edge.source_id]:
            self.reverse_adjacency[edge.source_id].append(edge.target_id)

    def get_node(self, node_id: str) -> Optional[CellNode]:
        """获取节点"""
        return self.nodes.get(node_id)

    def get_upstream(self, node_id: str, depth: Optional[int] = None) -> list:
        """获取上游依赖节点（递归）
        depth=None表示全部，depth=1表示直接上游
        """
        if depth == 1:
            return self.adjacency.get(node_id, [])

        result = []
        visited = set()
        stack = [(node_id, 0)]
        while stack:
            curr, d = stack.pop()
            if curr in visited:
                continue
            visited.add(curr)
            for upstream in self.adjacency.get(curr, []):
                result.append(upstream)
                stack.append((upstream, d + 1))
        return list(set(result))

    def get_downstream(self, node_id: str, depth: Optional[int] = None) -> list:
        """获取下游被依赖节点（递归）"""
        if depth == 1:
            return self.reverse_adjacency.get(node_id, [])

        result = []
        visited = set()
        stack = [(node_id, 0)]
        while stack:
            curr, d = stack.pop()
            if curr in visited:
                continue
            visited.add(curr)
            for downstream in self.reverse_adjacency.get(curr, []):
                result.append(downstream)
                stack.append((downstream, d + 1))
        return list(set(result))

    def update_stats(self) -> None:
        """更新统计信息"""
        self.stats.total_nodes = len(self.nodes)
        self.stats.total_edges = len(self.edges)
        self.stats.input_nodes = sum(1 for n in self.nodes.values() if n.is_input)
        self.stats.formula_nodes = sum(1 for n in self.nodes.values() if n.formula_raw)
        self.stats.max_depth = max((n.depth for n in self.nodes.values()), default=0)
        self.stats.cross_sheet_edges = sum(1 for e in self.edges if e.is_cross_sheet)

    def to_dict(self) -> dict:
        """导出为JSON兼容字典"""
        self.update_stats()
        return {
            "name": self.name,
            "source_file": self.source_file,
            "sheets": self.sheets,
            "stats": {
                "total_nodes": self.stats.total_nodes,
                "total_edges": self.stats.total_edges,
                "input_nodes": self.stats.input_nodes,
                "formula_nodes": self.stats.formula_nodes,
                "max_depth": self.stats.max_depth,
                "cross_sheet_edges": self.stats.cross_sheet_edges,
            },
        }