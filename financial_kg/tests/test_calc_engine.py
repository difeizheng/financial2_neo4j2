"""单元测试 - 计算引擎"""
import pytest
from financial_kg.core.calc_engine import CalcEngine
from financial_kg.core.formula_parser import FormulaParser
from financial_kg.models.graph import KnowledgeGraph
from financial_kg.models.cell import CellNode


class TestCalcEngine:
    """计算引擎测试"""

    def setup_method(self):
        self.graph = KnowledgeGraph(name="test", source_file="test.xlsx")
        self.parser = FormulaParser()

    def _add_node(self, sheet: str, row: int, col: str, value, formula=None):
        """添加测试节点"""
        col_idx = self._col_to_index(col)
        node = CellNode(
            id=f"{sheet}_{row}_{col}",
            sheet=sheet,
            row=row,
            col=col,
            col_index=col_idx,
            address=f"{sheet}!{col}{row}",
            value=value,
            formula_raw=formula,
        )
        self.graph.add_node(node)
        return node

    def _col_to_index(self, col: str) -> int:
        """列字母转索引"""
        result = 0
        for char in col:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1

    # === DAG构建测试 ===

    def test_build_dag_single_formula(self):
        """测试单个公式DAG"""
        self._add_node("Sheet1", 1, "A", 100)
        self._add_node("Sheet1", 2, "B", None, "=A1")

        engine = CalcEngine(self.graph)
        engine.build_dag()

        # A1被B2依赖，所以A1的in_degree为1
        assert self.graph.nodes["Sheet1_1_A"].in_degree == 1
        # B2依赖A1，所以B2的out_degree为1
        assert self.graph.nodes["Sheet1_2_B"].out_degree == 1

    def test_build_dag_range_reference(self):
        """测试范围引用DAG"""
        self._add_node("Sheet1", 1, "A", 1)
        self._add_node("Sheet1", 1, "B", 2)
        self._add_node("Sheet1", 1, "C", 3)
        self._add_node("Sheet1", 2, "D", None, "=SUM(A1:C1)")

        engine = CalcEngine(self.graph)
        engine.build_dag()

        # D2依赖A1, B1, C1，所以D2的out_degree为3
        assert self.graph.nodes["Sheet1_2_D"].out_degree == 3

    def test_build_dag_cross_sheet(self):
        """测试跨sheet引用DAG"""
        self._add_node("Sheet2", 1, "A", 50)
        self._add_node("Sheet1", 1, "B", None, "=Sheet2!A1")

        engine = CalcEngine(self.graph)
        engine.build_dag()

        # 检查边是否标记为跨sheet（edges是列表）
        for edge in self.graph.edges:
            if edge.source_id == "Sheet2_1_A" and edge.target_id == "Sheet1_1_B":
                assert edge.is_cross_sheet == True
                break

    # === 拓扑排序测试 ===

    def test_topological_sort_simple(self):
        """测试简单拓扑排序"""
        self._add_node("Sheet1", 1, "A", 100)  # 输入
        self._add_node("Sheet1", 2, "B", None, "=A1")  # 依赖A1
        self._add_node("Sheet1", 3, "C", None, "=B2")  # 依赖B2

        engine = CalcEngine(self.graph)
        engine.build_dag()
        order = engine.topological_sort()

        # A1应该排在B2前面，B2排在C3前面
        assert order.index("Sheet1_1_A") < order.index("Sheet1_2_B")
        assert order.index("Sheet1_2_B") < order.index("Sheet1_3_C")

    def test_topological_sort_multiple_inputs(self):
        """测试多个输入节点的拓扑排序"""
        self._add_node("Sheet1", 1, "A", 10)
        self._add_node("Sheet1", 1, "B", 20)
        self._add_node("Sheet1", 2, "C", None, "=A1+B1")

        engine = CalcEngine(self.graph)
        engine.build_dag()
        order = engine.topological_sort()

        # A1和B1都应该排在C2前面
        assert order.index("Sheet1_1_A") < order.index("Sheet1_2_C")
        assert order.index("Sheet1_1_B") < order.index("Sheet1_2_C")

    def test_topological_sort_detect_cycle(self):
        """测试循环依赖检测"""
        # 创建循环：A1=B1, B1=A1
        self._add_node("Sheet1", 1, "A", None, "=B1")
        self._add_node("Sheet1", 1, "B", None, "=A1")

        engine = CalcEngine(self.graph)
        engine.build_dag()
        order = engine.topological_sort()

        # 应该检测到循环依赖（结果长度小于节点总数）
        assert len(order) < len(self.graph.nodes)

    # === 深度计算测试 ===

    def test_compute_depths(self):
        """测试深度计算"""
        self._add_node("Sheet1", 1, "A", 100)  # depth=0
        self._add_node("Sheet1", 2, "B", None, "=A1")  # depth=1
        self._add_node("Sheet1", 3, "C", None, "=B2")  # depth=2
        self._add_node("Sheet1", 4, "D", None, "=A1+C3")  # depth=3

        engine = CalcEngine(self.graph)
        engine.build_dag()
        engine.topological_sort()
        engine.compute_depths()

        assert self.graph.nodes["Sheet1_1_A"].depth == 0
        assert self.graph.nodes["Sheet1_2_B"].depth == 1
        assert self.graph.nodes["Sheet1_3_C"].depth == 2
        assert self.graph.nodes["Sheet1_4_D"].depth == 3

    # === 求值测试 ===

    def test_evaluate_all(self):
        """测试批量求值"""
        self._add_node("Sheet1", 1, "A", 100)
        self._add_node("Sheet1", 2, "B", None, "=A1")
        self._add_node("Sheet1", 3, "C", None, "=B2*2")

        engine = CalcEngine(self.graph)
        engine.build_dag()
        engine.topological_sort()
        engine.compute_depths()
        report = engine.evaluate_all()

        # 检查计算结果
        assert self.graph.nodes["Sheet1_2_B"].computed_value == 100
        assert self.graph.nodes["Sheet1_3_C"].computed_value == 200

    def test_validate(self):
        """测试验证"""
        self._add_node("Sheet1", 1, "A", 100)
        self._add_node("Sheet1", 2, "B", None, "=A1")  # 正确
        self._add_node("Sheet1", 3, "C", None, "=A1*2")  # 应该是200

        # 设置正确值
        self.graph.nodes["Sheet1_2_B"].value = 100
        self.graph.nodes["Sheet1_3_C"].value = 200

        engine = CalcEngine(self.graph)
        engine.build_dag()
        engine.topological_sort()
        engine.compute_depths()
        report = engine.validate()

        assert report["accuracy"] == 1.0  # 100%匹配

    # === 值传播测试 ===

    def test_propagate_simple(self):
        """测试简单传播"""
        self._add_node("Sheet1", 1, "A", 100)
        self._add_node("Sheet1", 2, "B", None, "=A1")
        self._add_node("Sheet1", 3, "C", None, "=B2")

        engine = CalcEngine(self.graph)
        engine.build_dag()
        engine.topological_sort()
        engine.compute_depths()
        engine.evaluate_all()  # 初始化computed_value

        # 修改A1
        changes = engine.propagate("Sheet1_1_A", 200)

        assert "Sheet1_1_A" in changes
        assert "Sheet1_2_B" in changes
        assert "Sheet1_3_C" in changes

        assert self.graph.nodes["Sheet1_1_A"].computed_value == 200
        assert self.graph.nodes["Sheet1_2_B"].computed_value == 200
        assert self.graph.nodes["Sheet1_3_C"].computed_value == 200

    def test_propagate_with_formula(self):
        """测试带公式的传播"""
        self._add_node("Sheet1", 1, "A", 10)
        self._add_node("Sheet1", 2, "B", None, "=A1*2")
        self._add_node("Sheet1", 3, "C", None, "=B2+5")

        engine = CalcEngine(self.graph)
        engine.build_dag()
        engine.topological_sort()
        engine.compute_depths()
        engine.evaluate_all()

        # 修改A1从10到20
        changes = engine.propagate("Sheet1_1_A", 20)

        # B2应该变成40
        assert self.graph.nodes["Sheet1_2_B"].computed_value == 40
        # C3应该变成45
        assert self.graph.nodes["Sheet1_3_C"].computed_value == 45

    def test_propagate_partial(self):
        """测试部分传播"""
        self._add_node("Sheet1", 1, "A", 100)
        self._add_node("Sheet1", 1, "B", 200)  # 不依赖A1
        self._add_node("Sheet1", 2, "C", None, "=A1")
        self._add_node("Sheet1", 2, "D", None, "=B1")  # 不受A1影响

        engine = CalcEngine(self.graph)
        engine.build_dag()
        engine.topological_sort()
        engine.compute_depths()
        engine.evaluate_all()

        changes = engine.propagate("Sheet1_1_A", 300)

        # 只有A1和C2受影响
        assert "Sheet1_1_A" in changes
        assert "Sheet1_2_C" in changes
        assert "Sheet1_1_B" not in changes
        assert "Sheet1_2_D" not in changes

    # === 循环依赖检测测试 ===

    def test_detect_cycles(self):
        """测试循环检测"""
        self._add_node("Sheet1", 1, "A", None, "=B1")
        self._add_node("Sheet1", 1, "B", None, "=A1")

        engine = CalcEngine(self.graph)
        engine.build_dag()
        cycles = engine.detect_cycles()

        assert len(cycles) > 0

    def test_detect_cycles_complex(self):
        """测试复杂循环"""
        self._add_node("Sheet1", 1, "A", None, "=B1")
        self._add_node("Sheet1", 1, "B", None, "=C1")
        self._add_node("Sheet1", 1, "C", None, "=A1")

        engine = CalcEngine(self.graph)
        engine.build_dag()
        cycles = engine.detect_cycles()

        assert len(cycles) > 0

    def test_detect_cycles_none(self):
        """测试无循环"""
        self._add_node("Sheet1", 1, "A", 100)
        self._add_node("Sheet1", 2, "B", None, "=A1")
        self._add_node("Sheet1", 3, "C", None, "=B2")

        engine = CalcEngine(self.graph)
        engine.build_dag()
        cycles = engine.detect_cycles()

        assert len(cycles) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])