"""公式求值器 - AST递归求值"""
from typing import Any, Optional, List
from datetime import datetime, date
from .formula_parser import ASTNode
from .formula_functions import EXCEL_FUNCTIONS
from ..models.graph import KnowledgeGraph

# Excel日期序列号基准（1899-12-30，因为Excel有1900年bug）
EXCEL_DATE_BASE = date(1899, 12, 30)


def _to_excel_number(value: Any) -> Any:
    """将值转换为Excel兼容的数值类型（用于算术运算）

    Excel中日期存储为序列号（从1899-12-30开始的天数）
    """
    if value is None:
        return None

    # 已经是数值
    if isinstance(value, (int, float)):
        return value

    # 日期类型转换为序列号
    if isinstance(value, datetime):
        delta = value.date() - EXCEL_DATE_BASE
        return delta.days
    if isinstance(value, date):
        delta = value - EXCEL_DATE_BASE
        return delta.days

    # 日期字符串尝试转换（格式：YYYY-MM-DD）
    if isinstance(value, str):
        # 尝试解析常见日期格式
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
            try:
                dt = datetime.strptime(value, fmt)
                delta = dt.date() - EXCEL_DATE_BASE
                return delta.days
            except ValueError:
                continue

        # 尝试直接转换为数字
        try:
            return float(value)
        except ValueError:
            pass

    return value


class FormulaEvaluator:
    """基于AST的公式求值器"""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self.current_sheet: Optional[str] = None

    def evaluate(self, node_id: str, current_sheet: str) -> Any:
        """对单个节点求值（假设依赖已求值）"""
        node = self.graph.get_node(node_id)
        if node is None:
            return None

        if node.formula_ast is None:
            return node.value

        self.current_sheet = current_sheet
        ast = self._dict_to_ast(node.formula_ast)
        return self._eval_ast(ast)

    def _dict_to_ast(self, ast_dict: dict) -> ASTNode:
        """字典转AST节点"""
        children = None
        if "children" in ast_dict:
            children = [self._dict_to_ast(c) for c in ast_dict["children"]]

        return ASTNode(
            node_type=ast_dict["node_type"],
            value=ast_dict.get("value"),
            sheet=ast_dict.get("sheet"),
            col=ast_dict.get("col"),
            row=ast_dict.get("row"),
            abs_col=ast_dict.get("abs_col", False),
            abs_row=ast_dict.get("abs_row", False),
            func_name=ast_dict.get("func_name"),
            operator=ast_dict.get("operator"),
            children=children,
        )

    def _eval_ast(self, ast: ASTNode) -> Any:
        """递归求值AST"""
        if ast.node_type == "literal":
            return ast.value

        if ast.node_type == "cell_ref":
            return self._resolve_cell_ref(ast.sheet, ast.col, ast.row)

        if ast.node_type == "range_ref":
            return self._resolve_range_ref(ast.sheet, ast.children)

        if ast.node_type == "binary_op":
            left = self._eval_ast(ast.children[0])
            right = self._eval_ast(ast.children[1])
            return self._apply_binary_op(ast.operator, left, right)

        if ast.node_type == "unary_op":
            operand = self._eval_ast(ast.children[0])
            return self._apply_unary_op(ast.operator, operand)

        if ast.node_type == "function_call":
            args = [self._eval_ast(arg) for arg in ast.children]
            return self._call_function(ast.func_name, args)

        return None

    def _resolve_cell_ref(self, sheet: Optional[str], col: str, row: int) -> Any:
        """解析单元格引用，返回值"""
        sheet = sheet or self.current_sheet
        node_id = f"{sheet}_{row}_{col}"
        node = self.graph.get_node(node_id)

        if node is None:
            # 节点不在图谱中（可能未解析该sheet）
            return None

        # 返回计算值（优先）或原始值
        if node.computed_value is not None:
            return node.computed_value
        return node.value

    def _resolve_range_ref(self, sheet: Optional[str], children: List[ASTNode]) -> List[Any]:
        """解析范围引用，返回值列表"""
        sheet = sheet or self.current_sheet

        start_col = children[0].col
        start_row = children[0].row
        end_col = children[1].col
        end_row = children[1].row

        # 转换列字母为数字索引
        start_col_idx = self._col_to_index(start_col)
        end_col_idx = self._col_to_index(end_col)

        values = []
        for row in range(start_row, end_row + 1):
            for col_idx in range(start_col_idx, end_col_idx + 1):
                col_letter = self._index_to_col(col_idx)
                node_id = f"{sheet}_{row}_{col_letter}"
                node = self.graph.get_node(node_id)
                if node:
                    values.append(node.computed_value or node.value)
                else:
                    values.append(None)

        return values

    def _col_to_index(self, col: str) -> int:
        """列字母转索引 A=0, B=1, ..., Z=25, AA=26"""
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

    def _apply_binary_op(self, op: str, left: Any, right: Any) -> Any:
        """应用二元运算符"""
        if left is None or right is None:
            if op in ("+", "-", "*", "/", "^"):
                return None
            # 比较运算
            if op == "=":
                return left == right
            if op == "<>":
                return left != right

        # 算术运算前转换为Excel兼容数值（处理日期等）
        if op in ("+", "-", "*", "/", "^"):
            left_num = _to_excel_number(left)
            right_num = _to_excel_number(right)
            if left_num is None or right_num is None:
                return None

        # 算术运算
        if op == "+":
            return left_num + right_num
        if op == "-":
            return left_num - right_num
        if op == "*":
            return left_num * right_num
        if op == "/":
            if right_num == 0:
                return None  # Excel返回#DIV/0!
            return left_num / right_num
        if op == "^":
            return left_num ** right_num

        # 比较运算
        if op == "=":
            return left == right
        if op == "<>":
            return left != right
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right

        return None

    def _apply_unary_op(self, op: str, operand: Any) -> Any:
        """应用一元运算符"""
        if operand is None:
            return None
        if op == "+":
            return operand
        if op == "-":
            return -operand
        return None

    def _call_function(self, func_name: str, args: List[Any]) -> Any:
        """调用Excel函数"""
        func = EXCEL_FUNCTIONS.get(func_name.upper())
        if func is None:
            # 未实现的函数
            return None

        try:
            return func(*args)
        except Exception as e:
            # 函数执行错误
            return None