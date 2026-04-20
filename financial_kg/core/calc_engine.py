"""计算引擎 - 依赖DAG构建、拓扑排序、值传播"""
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
from .formula_parser import FormulaParser, ASTNode
from .formula_evaluator import FormulaEvaluator
from ..models.cell import CellNode
from ..models.edge import DependencyEdge
from ..models.graph import KnowledgeGraph


class CalcEngine:
    """依赖图计算引擎"""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self.parser = FormulaParser()
        self.evaluator = FormulaEvaluator(graph)
        self.visited_for_depth: Set[str] = set()

    def build_dag(self) -> Dict[str, List[str]]:
        """从所有公式节点的AST引用构建邻接表"""
        for node_id, node in self.graph.nodes.items():
            if node.formula_raw is None:
                continue

            # 解析公式为AST
            try:
                ast = self.parser.parse(node.formula_raw, node.sheet)
                node.formula_ast = ast.to_dict()
                node.parse_status = "parsed"

                # 提取引用，创建边
                refs = ast.get_references()
                for ref in refs:
                    self._create_edge_from_ref(ref, node)

            except Exception as e:
                node.parse_status = "error"
                node.error_msg = str(e)

        # 更新邻接表统计
        self._update_degrees()

        return self.graph.adjacency

    def _create_edge_from_ref(self, ref: dict, target_node: CellNode) -> None:
        """从引用信息创建依赖边"""
        if ref.get("type") == "range":
            # 范围引用：展开为所有单元格
            sheet = ref.get("sheet") or target_node.sheet
            start_col = ref.get("start_col")
            start_row = ref.get("start_row")
            end_col = ref.get("end_col")
            end_row = ref.get("end_row")

            # 展开范围
            start_col_idx = self._col_to_index(start_col)
            end_col_idx = self._col_to_index(end_col)

            for row in range(start_row, end_row + 1):
                for col_idx in range(start_col_idx, end_col_idx + 1):
                    col_letter = self._index_to_col(col_idx)
                    source_id = f"{sheet}_{row}_{col_letter}"
                    self._add_edge(source_id, target_node.id, "range_ref", is_cross_sheet=(sheet != target_node.sheet))

        else:
            # 单单元格引用
            sheet = ref.get("sheet") or target_node.sheet
            col = ref.get("col")
            row = ref.get("row")

            source_id = f"{sheet}_{row}_{col}"
            ref_type = "absolute" if ref.get("abs_col") and ref.get("abs_row") else "relative"
            is_cross = sheet != target_node.sheet

            self._add_edge(source_id, target_node.id, "formula_ref" if not is_cross else "cross_sheet_ref", ref_type=ref_type, is_cross_sheet=is_cross)

    def _add_edge(self, source_id: str, target_id: str, edge_type: str, ref_type: str = "relative", is_cross_sheet: bool = False) -> None:
        """添加边到图谱"""
        # 检查源节点是否存在（可能未解析）
        if source_id not in self.graph.nodes:
            # 创建虚拟节点（标记为缺失）
            # 这里暂时跳过，等完整解析后再处理
            return

        edge = DependencyEdge(
            id=DependencyEdge.make_id(source_id, target_id),
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            ref_type=ref_type,
            is_cross_sheet=is_cross_sheet,
        )
        self.graph.add_edge(edge)

    def _update_degrees(self) -> None:
        """更新节点的入度出度"""
        for node_id, node in self.graph.nodes.items():
            # out_degree: 依赖的上游节点数
            node.out_degree = len(self.graph.adjacency.get(node_id, []))
            # in_degree: 被下游依赖的节点数
            node.in_degree = len(self.graph.reverse_adjacency.get(node_id, []))

            # 标记输入/输出节点
            node.is_input = node.formula_raw is None and node.out_degree == 0
            node.is_output = node.in_degree == 0 and node.formula_raw is not None

    def topological_sort(self) -> List[str]:
        """Kahn算法拓扑排序，返回有序node_id列表

        改进：区分"跨表双向引用"和真正的循环依赖
        - 跨表双向引用：参数输入表 ↔ 其他表（Excel财务模型常见设计）
        - 真正的循环依赖：同sheet内的公式循环引用
        """
        # 计算入度（依赖数）
        in_degree = defaultdict(int)
        for node_id in self.graph.nodes:
            in_degree[node_id] = len(self.graph.adjacency.get(node_id, []))

        # 找入度为0的节点作为起点
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])

        result = []
        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            # 减少下游节点的入度
            for downstream_id in self.graph.reverse_adjacency.get(node_id, []):
                in_degree[downstream_id] -= 1
                if in_degree[downstream_id] == 0:
                    queue.append(downstream_id)

        # 处理剩余节点（入度不为0的节点）
        if len(result) != len(self.graph.nodes):
            remaining = [nid for nid in self.graph.nodes if nid not in result]

            # 分析循环类型
            for nid in remaining:
                node = self.graph.nodes[nid]

                # 检查是否是跨表双向引用
                is_cross_bidirectional = self._is_cross_sheet_bidirectional(nid)

                if is_cross_bidirectional:
                    # 跨表双向引用：标记为特殊状态，不是错误
                    node.parse_status = "cross_bidirectional"
                    node.error_msg = "跨表双向引用（参数表汇总）"
                else:
                    # 真正的循环依赖：标记为错误
                    node.parse_status = "error"
                    node.error_msg = "循环依赖"

        self.graph.topo_order = result
        return result

    def _is_cross_sheet_bidirectional(self, node_id: str) -> bool:
        """判断节点是否属于跨表双向引用（高效版本）

        跨表双向引用在Excel财务模型中很常见：
        - 参数输入表汇总其他表数据，其他表又引用参数输入表参数
        - 判断标准：
          1. 节点有跨sheet依赖（上游或下游在不同sheet）
          2. 节点依赖跨sheet引用节点（间接跨表）
        """
        node = self.graph.nodes.get(node_id)
        if node is None:
            return False

        # 检查上游依赖是否有跨sheet节点
        upstream_ids = self.graph.adjacency.get(node_id, [])
        for up_id in upstream_ids:
            up_node = self.graph.nodes.get(up_id)
            if up_node and up_node.sheet != node.sheet:
                return True
            # 检查上游节点是否是跨sheet引用节点（parse_status为cross_bidirectional）
            if up_node and up_node.parse_status == "cross_bidirectional":
                return True

        # 检查下游被依赖是否有跨sheet节点
        downstream_ids = self.graph.reverse_adjacency.get(node_id, [])
        for down_id in downstream_ids:
            down_node = self.graph.nodes.get(down_id)
            if down_node and down_node.sheet != node.sheet:
                return True

        return False

    def compute_depths(self) -> None:
        """计算每个节点的DAG深度"""
        # 深度 = 最长依赖链长度
        # 沿拓扑序正向计算
        for node_id in self.graph.topo_order:
            node = self.graph.nodes[node_id]
            if node.formula_raw is None:
                node.depth = 0
            else:
                # depth = max(上游depth) + 1
                upstream_ids = self.graph.adjacency.get(node_id, [])
                if not upstream_ids:
                    node.depth = 1
                else:
                    max_upstream_depth = max(
                        (self.graph.nodes.get(uid, CellNode(id=uid, sheet="", row=0, col="", col_index=0, address="", value=None)).depth for uid in upstream_ids),
                        default=0
                    )
                    node.depth = max_upstream_depth + 1

    def evaluate_all(self) -> Dict[str, Tuple[Any, Any]]:
        """按拓扑序求值所有公式节点，返回验证报告 {node_id: (excel_value, computed_value)}"""
        report = {}

        for node_id in self.graph.topo_order:
            node = self.graph.nodes.get(node_id)
            if node is None:
                continue

            if node.formula_raw is None:
                node.computed_value = node.value
                continue

            # 求值
            try:
                computed = self.evaluator.evaluate(node_id, node.sheet)
                node.computed_value = computed
                node.parse_status = "evaluated"

                # 验证
                report[node_id] = (node.value, computed)

            except Exception as e:
                node.parse_status = "error"
                node.error_msg = str(e)
                report[node_id] = (node.value, None)

        return report

    def propagate(self, node_id: str, new_value: Any) -> Dict[str, Tuple[Any, Any]]:
        """修改某节点值后，沿DAG传播重算所有下游，返回变更集 {node_id: (old_value, new_value)}"""
        changes = {}

        node = self.graph.get_node(node_id)
        if node is None:
            return changes

        # 记录旧值（优先使用value，fallback到computed_value）
        old_value = node.value if node.value is not None else node.computed_value
        node.value = new_value
        node.computed_value = new_value
        changes[node_id] = (old_value, new_value)

        # 获取所有下游节点（按深度排序）
        downstream = self.graph.get_downstream(node_id)
        downstream_sorted = sorted(
            downstream,
            key=lambda nid: self.graph.nodes.get(nid, CellNode(id=nid, sheet="", row=0, col="", col_index=0, address="", value=None)).depth
        )

        # 按深度顺序重算
        for ds_id in downstream_sorted:
            ds_node = self.graph.get_node(ds_id)
            if ds_node is None or ds_node.formula_raw is None:
                continue

            # 记录旧值（优先使用computed_value，因为公式节点可能value为None）
            old_ds_value = ds_node.computed_value if ds_node.computed_value is not None else ds_node.value
            try:
                new_ds_value = self.evaluator.evaluate(ds_id, ds_node.sheet)
                ds_node.computed_value = new_ds_value
                changes[ds_id] = (old_ds_value, new_ds_value)
            except Exception as e:
                ds_node.error_msg = str(e)
                changes[ds_id] = (old_ds_value, None)

        return changes

    def detect_cycles(self) -> List[List[str]]:
        """检测循环依赖，返回所有环"""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node_id: str, path: List[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for downstream in self.graph.reverse_adjacency.get(node_id, []):
                if downstream not in visited:
                    dfs(downstream, path)
                elif downstream in rec_stack:
                    # 找到环
                    cycle_start = path.index(downstream)
                    cycle = path[cycle_start:] + [downstream]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node_id)

        for node_id in self.graph.nodes:
            if node_id not in visited:
                dfs(node_id, [])

        return cycles

    def validate(self) -> Dict[str, Any]:
        """验证计算结果与Excel原值的一致性"""
        report = self.evaluate_all()

        matches = 0
        mismatches = 0
        errors = 0

        for node_id, (excel_val, computed_val) in report.items():
            if computed_val is None:
                errors += 1
            elif self._values_match(excel_val, computed_val):
                matches += 1
            else:
                mismatches += 1

        return {
            "total": len(report),
            "matches": matches,
            "mismatches": mismatches,
            "errors": errors,
            "accuracy": matches / len(report) if report else 0,
        }

    def _values_match(self, a: Any, b: Any, tolerance: float = 0.0001) -> bool:
        """比较两个值是否匹配（浮点数考虑容差）"""
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False

        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return abs(a - b) < tolerance

        return a == b

    def _col_to_index(self, col: str) -> int:
        """列字母转索引"""
        result = 0
        for char in col:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1

    def _index_to_col(self, index: int) -> str:
        """索引转列字母"""
        result = ""
        index += 1
        while index > 0:
            index -= 1
            result = chr(ord('A') + index % 26) + result
            index //= 26
        return result