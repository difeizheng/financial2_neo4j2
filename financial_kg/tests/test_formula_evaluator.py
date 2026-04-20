"""单元测试 - 公式求值器"""
import pytest
from financial_kg.core.formula_evaluator import FormulaEvaluator
from financial_kg.core.formula_parser import FormulaParser
from financial_kg.models.graph import KnowledgeGraph
from financial_kg.models.cell import CellNode


class TestFormulaEvaluator:
    """公式求值器测试"""

    def setup_method(self):
        self.graph = KnowledgeGraph(name="test", source_file="test.xlsx")
        self.parser = FormulaParser()
        self.evaluator = FormulaEvaluator(self.graph)

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
        if formula:
            ast = self.parser.parse(formula, sheet)
            node.formula_ast = ast.to_dict()
        self.graph.add_node(node)
        return node

    def _col_to_index(self, col: str) -> int:
        """列字母转索引"""
        result = 0
        for char in col:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1

    # === 基础求值测试 ===

    def test_eval_literal(self):
        """测试纯数字求值"""
        self._add_node("Sheet1", 1, "A", None, "123")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 123

    def test_eval_cell_ref(self):
        """测试单元格引用求值"""
        self._add_node("Sheet1", 1, "A", 100)  # A1 = 100
        self._add_node("Sheet1", 2, "B", None, "A1")  # B2 = A1
        result = self.evaluator.evaluate("Sheet1_2_B", "Sheet1")
        assert result == 100

    def test_eval_cell_ref_with_computed_value(self):
        """测试使用computed_value"""
        self._add_node("Sheet1", 1, "A", 100)
        self.graph.nodes["Sheet1_1_A"].computed_value = 200
        self._add_node("Sheet1", 2, "B", None, "A1")
        result = self.evaluator.evaluate("Sheet1_2_B", "Sheet1")
        assert result == 200  # 使用computed_value而非value

    def test_eval_cross_sheet_ref(self):
        """测试跨sheet引用"""
        self._add_node("Sheet2", 1, "A", 50)
        self._add_node("Sheet1", 1, "B", None, "Sheet2!A1")
        result = self.evaluator.evaluate("Sheet1_1_B", "Sheet1")
        assert result == 50

    def test_eval_range_ref(self):
        """测试范围引用"""
        self._add_node("Sheet1", 1, "A", 1)
        self._add_node("Sheet1", 1, "B", 2)
        self._add_node("Sheet1", 1, "C", 3)
        self._add_node("Sheet1", 2, "D", None, "A1:C1")
        result = self.evaluator.evaluate("Sheet1_2_D", "Sheet1")
        assert result == [1, 2, 3]

    # === 运算符求值测试 ===

    def test_eval_add(self):
        """测试加法"""
        self._add_node("Sheet1", 1, "A", None, "1+2")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 3

    def test_eval_subtract(self):
        """测试减法"""
        self._add_node("Sheet1", 1, "A", 10)
        self._add_node("Sheet1", 1, "B", None, "A1-3")
        result = self.evaluator.evaluate("Sheet1_1_B", "Sheet1")
        assert result == 7

    def test_eval_multiply(self):
        """测试乘法"""
        self._add_node("Sheet1", 1, "A", None, "2*3")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 6

    def test_eval_divide(self):
        """测试除法"""
        self._add_node("Sheet1", 1, "A", None, "10/2")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 5

    def test_eval_divide_by_zero(self):
        """测试除零"""
        self._add_node("Sheet1", 1, "A", None, "10/0")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result is None

    def test_eval_power(self):
        """测试幂运算"""
        self._add_node("Sheet1", 1, "A", None, "2^3")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 8

    def test_eval_comparison(self):
        """测试比较运算"""
        self._add_node("Sheet1", 1, "A", 10)
        self._add_node("Sheet1", 1, "B", None, "A1>5")
        result = self.evaluator.evaluate("Sheet1_1_B", "Sheet1")
        assert result == True

        self._add_node("Sheet1", 1, "C", None, "A1<5")
        result = self.evaluator.evaluate("Sheet1_1_C", "Sheet1")
        assert result == False

    def test_eval_operator_precedence(self):
        """测试运算符优先级"""
        self._add_node("Sheet1", 1, "A", None, "1+2*3")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 7  # 1 + (2*3)

    def test_eval_parentheses(self):
        """测试括号"""
        self._add_node("Sheet1", 1, "A", None, "(1+2)*3")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 9

    # === 函数求值测试 ===

    def test_eval_sum(self):
        """测试SUM函数"""
        self._add_node("Sheet1", 1, "A", 1)
        self._add_node("Sheet1", 1, "B", 2)
        self._add_node("Sheet1", 1, "C", 3)
        self._add_node("Sheet1", 2, "D", None, "SUM(A1:C1)")
        result = self.evaluator.evaluate("Sheet1_2_D", "Sheet1")
        assert result == 6

    def test_eval_sum_with_numbers(self):
        """测试SUM直接参数"""
        self._add_node("Sheet1", 1, "A", None, "SUM(1, 2, 3)")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 6

    def test_eval_if_true(self):
        """测试IF为真"""
        self._add_node("Sheet1", 1, "A", None, "IF(1>0, 100, 0)")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 100

    def test_eval_if_false(self):
        """测试IF为假"""
        self._add_node("Sheet1", 1, "A", None, "IF(1<0, 100, 0)")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 0

    def test_eval_round(self):
        """测试ROUND"""
        self._add_node("Sheet1", 1, "A", None, "ROUND(1.567, 2)")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 1.57

    def test_eval_max(self):
        """测试MAX"""
        self._add_node("Sheet1", 1, "A", 1)
        self._add_node("Sheet1", 1, "B", 5)
        self._add_node("Sheet1", 1, "C", 3)
        self._add_node("Sheet1", 2, "D", None, "MAX(A1:C1)")
        result = self.evaluator.evaluate("Sheet1_2_D", "Sheet1")
        assert result == 5

    def test_eval_min(self):
        """测试MIN"""
        self._add_node("Sheet1", 1, "A", 1)
        self._add_node("Sheet1", 1, "B", 5)
        self._add_node("Sheet1", 1, "C", 3)
        self._add_node("Sheet1", 2, "D", None, "MIN(A1:C1)")
        result = self.evaluator.evaluate("Sheet1_2_D", "Sheet1")
        assert result == 1

    def test_eval_average(self):
        """测试AVERAGE"""
        self._add_node("Sheet1", 1, "A", 1)
        self._add_node("Sheet1", 1, "B", 2)
        self._add_node("Sheet1", 1, "C", 3)
        self._add_node("Sheet1", 2, "D", None, "AVERAGE(A1:C1)")
        result = self.evaluator.evaluate("Sheet1_2_D", "Sheet1")
        assert result == 2

    def test_eval_abs(self):
        """测试ABS"""
        self._add_node("Sheet1", 1, "A", None, "ABS(-5)")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == 5

    def test_eval_and(self):
        """测试AND"""
        self._add_node("Sheet1", 1, "A", None, "AND(1, 1)")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == True

        self._add_node("Sheet1", 1, "B", None, "AND(1, 0)")
        result = self.evaluator.evaluate("Sheet1_1_B", "Sheet1")
        assert result == False

    def test_eval_or(self):
        """测试OR"""
        self._add_node("Sheet1", 1, "A", None, "OR(0, 1)")
        result = self.evaluator.evaluate("Sheet1_1_A", "Sheet1")
        assert result == True

    def test_eval_nested_function(self):
        """测试嵌套函数"""
        self._add_node("Sheet1", 1, "A", 1)
        self._add_node("Sheet1", 1, "B", 2)
        self._add_node("Sheet1", 1, "C", 3)
        self._add_node("Sheet1", 2, "D", None, "ROUND(SUM(A1:C1), 0)")
        result = self.evaluator.evaluate("Sheet1_2_D", "Sheet1")
        assert result == 6

    # === 复杂公式测试 ===

    def test_eval_complex_formula(self):
        """测试复杂公式"""
        self._add_node("Sheet1", 1, "A", 100)
        self._add_node("Sheet1", 1, "B", 1)
        self._add_node("Sheet1", 1, "C", 2)
        self._add_node("Sheet1", 1, "D", 3)
        self._add_node("Sheet1", 2, "E", None, "IF(A1>50, SUM(B1:D1), 0)")
        result = self.evaluator.evaluate("Sheet1_2_E", "Sheet1")
        assert result == 6

    # === None值处理测试 ===

    def test_eval_comparison_with_none(self):
        """测试None值比较（不应抛出TypeError）"""
        # None与数值比较应返回False
        self._add_node("Sheet1", 1, "A", None)  # A1 = None
        self._add_node("Sheet1", 1, "B", None, "A1<0")  # None < 0
        result = self.evaluator.evaluate("Sheet1_1_B", "Sheet1")
        assert result == False

        self._add_node("Sheet1", 1, "C", None, "A1>0")  # None > 0
        result = self.evaluator.evaluate("Sheet1_1_C", "Sheet1")
        assert result == False

        self._add_node("Sheet1", 1, "D", None, "A1=0")  # None = 0
        result = self.evaluator.evaluate("Sheet1_1_D", "Sheet1")
        assert result == False

    def test_eval_arithmetic_with_none(self):
        """测试None值算术运算"""
        self._add_node("Sheet1", 1, "A", None)
        self._add_node("Sheet1", 1, "B", 10)
        self._add_node("Sheet1", 1, "C", None, "A1+B1")  # None + 10
        result = self.evaluator.evaluate("Sheet1_1_C", "Sheet1")
        assert result is None

    def test_eval_if_short_circuit(self):
        """测试IF短路求值（避免求值else分支）"""
        # 当条件为True时，不应求值else分支
        # 即使else分支有None比较错误，也应正常返回
        self._add_node("Sheet1", 1, "A", None)  # A1 = None (会引发比较错误)
        self._add_node("Sheet1", 1, "B", 100)   # B1 = 100
        # IF(B1>50, 1, A1<0) - 条件为True，不应求值A1<0
        self._add_node("Sheet1", 1, "C", None, "IF(B1>50, 1, A1<0)")
        result = self.evaluator.evaluate("Sheet1_1_C", "Sheet1")
        assert result == 1  # 返回true分支，不报错

        # 条件为False时，应求值else分支
        self._add_node("Sheet1", 1, "D", None, "IF(B1<50, 1, 0)")
        result = self.evaluator.evaluate("Sheet1_1_D", "Sheet1")
        assert result == 0

    def test_eval_nested_if_with_none(self):
        """测试嵌套IF处理None值"""
        # IF(ISBLANK(A1), 0, A1-10) 模式
        self._add_node("Sheet1", 1, "A", None)  # A1 = None
        self._add_node("Sheet1", 1, "B", None, "IF(ISBLANK(A1), 0, A1-10)")
        result = self.evaluator.evaluate("Sheet1_1_B", "Sheet1")
        assert result == 0  # ISBLANK返回True，返回0

        # A1有值时
        self._add_node("Sheet1", 2, "A", 20)
        self._add_node("Sheet1", 2, "B", None, "IF(ISBLANK(A2), 0, A2-10)")
        result = self.evaluator.evaluate("Sheet1_2_B", "Sheet1")
        assert result == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])