"""单元测试 - 公式解析器"""
import pytest
from financial_kg.core.formula_parser import FormulaParser


class TestFormulaParser:
    """公式解析器测试"""

    def setup_method(self):
        self.parser = FormulaParser()

    # === 基础测试 ===

    def test_parse_simple_number(self):
        """测试纯数字"""
        ast = self.parser.parse("123", "Sheet1")
        assert ast.node_type == "literal"
        assert ast.value == 123

    def test_parse_simple_cell_ref(self):
        """测试单元格引用"""
        ast = self.parser.parse("A1", "Sheet1")
        assert ast.node_type == "cell_ref"
        assert ast.col == "A"
        assert ast.row == 1
        assert ast.sheet is None  # 同sheet引用，sheet为None

    def test_parse_cross_sheet_ref(self):
        """测试跨sheet引用"""
        ast = self.parser.parse("参数输入表!A1", "Sheet1")
        assert ast.node_type == "cell_ref"
        assert ast.sheet == "参数输入表"
        assert ast.col == "A"
        assert ast.row == 1

    def test_parse_cross_sheet_ref_with_chinese(self):
        """测试中文sheet名引用"""
        ast = self.parser.parse("'参数输入表'!$I$380", "Sheet1")
        assert ast.node_type == "cell_ref"
        assert ast.sheet == "参数输入表"
        assert ast.col == "I"
        assert ast.row == 380
        assert ast.abs_col == True
        assert ast.abs_row == True

    def test_parse_range_ref(self):
        """测试范围引用"""
        ast = self.parser.parse("A1:B10", "Sheet1")
        assert ast.node_type == "range_ref"
        assert len(ast.children) == 2
        assert ast.children[0].col == "A"
        assert ast.children[0].row == 1
        assert ast.children[1].col == "B"
        assert ast.children[1].row == 10

    def test_parse_cross_sheet_range(self):
        """测试跨sheet范围引用"""
        ast = self.parser.parse("'表3'!A1:F10", "Sheet1")
        assert ast.node_type == "range_ref"
        assert ast.sheet == "表3"

    # === 运算符测试 ===

    def test_parse_binary_add(self):
        """测试加法"""
        ast = self.parser.parse("1+2", "Sheet1")
        assert ast.node_type == "binary_op"
        assert ast.operator == "+"
        assert ast.children[0].value == 1
        assert ast.children[1].value == 2

    def test_parse_binary_subtract(self):
        """测试减法"""
        ast = self.parser.parse("A1-5", "Sheet1")
        assert ast.node_type == "binary_op"
        assert ast.operator == "-"

    def test_parse_binary_multiply(self):
        """测试乘法"""
        ast = self.parser.parse("A1*B1", "Sheet1")
        assert ast.node_type == "binary_op"
        assert ast.operator == "*"

    def test_parse_binary_divide(self):
        """测试除法"""
        ast = self.parser.parse("10/2", "Sheet1")
        assert ast.node_type == "binary_op"
        assert ast.operator == "/"

    def test_parse_binary_power(self):
        """测试幂运算"""
        ast = self.parser.parse("2^3", "Sheet1")
        assert ast.node_type == "binary_op"
        assert ast.operator == "^"

    def test_parse_comparison_operators(self):
        """测试比较运算符"""
        tests = [
            ("A1=B1", "="),
            ("A1<>B1", "<>"),
            ("A1<B1", "<"),
            ("A1>B1", ">"),
            ("A1<=B1", "<="),
            ("A1>=B1", ">="),
        ]
        for formula, op in tests:
            ast = self.parser.parse(formula, "Sheet1")
            assert ast.node_type == "binary_op"
            assert ast.operator == op

    def test_parse_operator_precedence(self):
        """测试运算符优先级"""
        # 乘法优先于加法: 1+2*3 -> 1+(2*3)
        ast = self.parser.parse("1+2*3", "Sheet1")
        assert ast.node_type == "binary_op"
        assert ast.operator == "+"
        assert ast.children[1].node_type == "binary_op"
        assert ast.children[1].operator == "*"

    def test_parse_parentheses(self):
        """测试括号改变优先级"""
        # (1+2)*3
        ast = self.parser.parse("(1+2)*3", "Sheet1")
        assert ast.node_type == "binary_op"
        assert ast.operator == "*"
        assert ast.children[0].node_type == "binary_op"
        assert ast.children[0].operator == "+"

    # === 函数测试 ===

    def test_parse_simple_function(self):
        """测试简单函数"""
        ast = self.parser.parse("SUM(A1:A10)", "Sheet1")
        assert ast.node_type == "function_call"
        assert ast.func_name == "SUM"
        assert len(ast.children) == 1
        assert ast.children[0].node_type == "range_ref"

    def test_parse_function_with_multiple_args(self):
        """测试多参数函数"""
        ast = self.parser.parse("SUM(A1, B1, C1)", "Sheet1")
        assert ast.node_type == "function_call"
        assert ast.func_name == "SUM"
        assert len(ast.children) == 3

    def test_parse_nested_function(self):
        """测试嵌套函数"""
        ast = self.parser.parse("IF(A1>0, SUM(B1:B10), 0)", "Sheet1")
        assert ast.node_type == "function_call"
        assert ast.func_name == "IF"
        assert len(ast.children) == 3
        assert ast.children[0].node_type == "binary_op"  # A1>0
        assert ast.children[1].node_type == "function_call"  # SUM
        assert ast.children[2].node_type == "literal"  # 0

    def test_parse_if_function(self):
        """测试IF函数"""
        ast = self.parser.parse("IF(A1=1, \"是\", \"否\")", "Sheet1")
        assert ast.node_type == "function_call"
        assert ast.func_name == "IF"
        assert len(ast.children) == 3

    def test_parse_round_function(self):
        """测试ROUND函数"""
        ast = self.parser.parse("ROUND(A1, 2)", "Sheet1")
        assert ast.node_type == "function_call"
        assert ast.func_name == "ROUND"
        assert len(ast.children) == 2

    # === 复杂公式测试 ===

    def test_parse_complex_formula(self):
        """测试复杂公式"""
        formula = "IF(参数输入表!$I$380=1, SUM('表3'!F5:F10)*100, 0)"
        ast = self.parser.parse(formula, "Sheet1")
        assert ast.node_type == "function_call"
        assert ast.func_name == "IF"

    def test_parse_formula_with_string(self):
        """测试包含字符串的公式"""
        ast = self.parser.parse("\"Test\"", "Sheet1")
        assert ast.node_type == "literal"
        assert ast.value == "Test"

    def test_parse_percentage(self):
        """测试百分比"""
        ast = self.parser.parse("50%", "Sheet1")
        assert ast.node_type == "literal"
        assert ast.value == 0.5

    # === get_references测试 ===

    def test_get_references_cell(self):
        """测试获取单元格引用"""
        ast = self.parser.parse("A1+B1", "Sheet1")
        refs = ast.get_references()
        assert len(refs) == 2
        assert refs[0]["type"] == "cell"
        assert refs[0]["col"] == "A"
        assert refs[0]["row"] == 1

    def test_get_references_range(self):
        """测试获取范围引用"""
        ast = self.parser.parse("SUM(A1:B10)", "Sheet1")
        refs = ast.get_references()
        assert len(refs) == 1
        assert refs[0]["type"] == "range"

    def test_get_references_cross_sheet(self):
        """测试获取跨sheet引用"""
        ast = self.parser.parse("'参数输入表'!A1", "Sheet1")
        refs = ast.get_references()
        assert len(refs) == 1
        assert refs[0]["sheet"] == "参数输入表"

    # === AST序列化测试 ===

    def test_ast_to_dict(self):
        """测试AST转字典"""
        ast = self.parser.parse("A1+B1", "Sheet1")
        d = ast.to_dict()
        assert d["node_type"] == "binary_op"
        assert d["operator"] == "+"
        assert "children" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])