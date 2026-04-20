"""单元测试 - 新增函数（ISBLANK、XIRR等）"""
import pytest
from datetime import date
from financial_kg.core.formula_functions import (
    ISBLANK, XIRR, ISNUMBER, ISTEXT, ISERROR,
    SUM, IF, ROUND, IRR, NPV
)
from financial_kg.core.formula_evaluator import FormulaEvaluator
from financial_kg.core.formula_parser import FormulaParser
from financial_kg.models.graph import KnowledgeGraph
from financial_kg.models.cell import CellNode


class TestNewFunctions:
    """新增函数测试"""

    # === ISBLANK 测试 ===

    def test_isblank_none(self):
        """ISBLANK(None) = True"""
        assert ISBLANK(None) == True

    def test_isblank_empty_string(self):
        """ISBLANK("") = True"""
        assert ISBLANK("") == True

    def test_isblank_zero(self):
        """ISBLANK(0) = False（0不是空）"""
        assert ISBLANK(0) == False

    def test_isblank_string(self):
        """ISBLANK("test") = False"""
        assert ISBLANK("test") == False

    def test_isblank_number(self):
        """ISBLANK(123) = False"""
        assert ISBLANK(123) == False

    # === ISNUMBER 测试 ===

    def test_isnumber_int(self):
        """ISNUMBER(123) = True"""
        assert ISNUMBER(123) == True

    def test_isnumber_float(self):
        """ISNUMBER(1.5) = True"""
        assert ISNUMBER(1.5) == True

    def test_isnumber_string(self):
        """ISNUMBER("abc") = False"""
        assert ISNUMBER("abc") == False

    def test_isnumber_none(self):
        """ISNUMBER(None) = False"""
        assert ISNUMBER(None) == False

    # === ISTEXT 测试 ===

    def test_istext_string(self):
        """ISTEXT("abc") = True"""
        assert ISTEXT("abc") == True

    def test_istext_number(self):
        """ISTEXT(123) = False"""
        assert ISTEXT(123) == False

    def test_istext_none(self):
        """ISTEXT(None) = False"""
        assert ISTEXT(None) == False

    # === ISERROR 测试 ===

    def test_iserror_na(self):
        """ISERROR("#N/A") = True"""
        assert ISERROR("#N/A") == True

    def test_iserror_value(self):
        """ISERROR("#VALUE!") = True"""
        assert ISERROR("#VALUE!") == True

    def test_iserror_num(self):
        """ISERROR("#NUM!") = True"""
        assert ISERROR("#NUM!") == True

    def test_iserror_normal(self):
        """ISERROR(123) = False"""
        assert ISERROR(123) == False

    def test_iserror_none(self):
        """ISERROR(None) = False"""
        assert ISERROR(None) == False

    # === XIRR 测试 ===

    def test_xirr_simple(self):
        """XIRR基本测试：简单现金流"""
        # 投资-100，每年收回50，持续3年
        values = [-100, 50, 50, 50]
        dates = [1, 366, 731, 1096]  # Excel日期序列号（1年间隔）
        result = XIRR(values, dates)
        assert result is not None
        assert 15 < result < 25  # 约18-20%

    def test_xirr_negative_first(self):
        """XIRR：首笔为负（投资）"""
        values = [-1000, 200, 200, 200, 200, 200]
        dates = [1, 366, 731, 1096, 1461, 1826]
        result = XIRR(values, dates)
        assert result is not None

    def test_xirr_no_positive(self):
        """XIRR：无正数现金流，返回None"""
        values = [-100, -50, -30]
        dates = [1, 366, 731]
        result = XIRR(values, dates)
        assert result is None

    def test_xirr_no_negative(self):
        """XIRR：无负数现金流，返回None"""
        values = [100, 50, 30]
        dates = [1, 366, 731]
        result = XIRR(values, dates)
        assert result is None

    def test_xirr_empty(self):
        """XIRR：空数组，返回None"""
        assert XIRR([], []) is None
        assert XIRR([100], [1]) is None

    def test_xirr_with_python_dates(self):
        """XIRR：使用Python date对象"""
        values = [-100, 50, 50]
        dates = [date(2024, 1, 1), date(2025, 1, 1), date(2026, 1, 1)]
        result = XIRR(values, dates)
        assert result is not None

    # === 公式求值器集成测试 ===

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

    def test_eval_isblank_formula(self):
        """测试ISBLANK公式求值"""
        # A1为空，B1判断A1是否为空
        self._add_node("Sheet1", 1, "A", None)
        self._add_node("Sheet1", 1, "B", None, "ISBLANK(A1)")
        result = self.evaluator.evaluate("Sheet1_1_B", "Sheet1")
        assert result == True

        # A2有值，B2判断A2是否为空
        self._add_node("Sheet1", 2, "A", 100)
        self._add_node("Sheet1", 2, "B", None, "ISBLANK(A2)")
        result = self.evaluator.evaluate("Sheet1_2_B", "Sheet1")
        assert result == False

    def test_eval_if_isblank(self):
        """测试IF+ISBLANK组合"""
        # =IF(ISBLANK(A1), 0, A1)
        self._add_node("Sheet1", 1, "A", None)
        self._add_node("Sheet1", 1, "B", None, "IF(ISBLANK(A1), 0, A1)")
        result = self.evaluator.evaluate("Sheet1_1_B", "Sheet1")
        assert result == 0

        # A2有值
        self._add_node("Sheet1", 2, "A", 100)
        self._add_node("Sheet1", 2, "B", None, "IF(ISBLANK(A2), 0, A2)")
        result = self.evaluator.evaluate("Sheet1_2_B", "Sheet1")
        assert result == 100

    def test_eval_xirr_formula(self):
        """测试XIRR公式求值"""
        # 添加现金流数据
        self._add_node("Sheet1", 1, "A", -100)  # 初始投资
        self._add_node("Sheet1", 1, "B", 50)    # 第1年收回
        self._add_node("Sheet1", 1, "C", 50)    # 第2年收回
        self._add_node("Sheet1", 1, "D", 50)    # 第3年收回

        # 日期（Excel序列号）
        self._add_node("Sheet1", 2, "A", 1)
        self._add_node("Sheet1", 2, "B", 366)
        self._add_node("Sheet1", 2, "C", 731)
        self._add_node("Sheet1", 2, "D", 1096)

        # XIRR公式
        self._add_node("Sheet1", 3, "E", None, "XIRR(A1:D1, A2:D2)")
        result = self.evaluator.evaluate("Sheet1_3_E", "Sheet1")
        assert result is not None
        assert 15 < result < 25

    def test_eval_isnumber_formula(self):
        """测试ISNUMBER公式求值"""
        self._add_node("Sheet1", 1, "A", 123)
        self._add_node("Sheet1", 1, "B", None, "ISNUMBER(A1)")
        result = self.evaluator.evaluate("Sheet1_1_B", "Sheet1")
        assert result == True

        self._add_node("Sheet1", 2, "A", "text")
        self._add_node("Sheet1", 2, "B", None, "ISNUMBER(A2)")
        result = self.evaluator.evaluate("Sheet1_2_B", "Sheet1")
        assert result == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])