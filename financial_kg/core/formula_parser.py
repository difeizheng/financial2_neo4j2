"""公式解析器 - Excel公式 tokenizer → AST"""
import re
from dataclasses import dataclass
from typing import Optional, List, Any


# === Token 类型 ===
TOKEN_TYPES = [
    # 跨sheet范围引用：'表3'!A1:F10 或 参数输入表!A1:B10
    ("SHEET_RANGE_REF", r"('[^']+')!([$]?[A-Z]{1,3}[$]?\d+):([$]?[A-Z]{1,3}[$]?\d+)|([\w\u4e00-\u9fff]+)!([$]?[A-Z]{1,3}[$]?\d+):([$]?[A-Z]{1,3}[$]?\d+)"),
    # 跨sheet引用：参数输入表!$I$380 或 '表 3'!A1
    ("SHEET_REF", r"('[^']+')!([$]?[A-Z]{1,3}[$]?\d+)|([\w\u4e00-\u9fff]+)!([$]?[A-Z]{1,3}[$]?\d+)"),
    # 范围引用：A1:B10 或 $A$1:$B$10
    ("RANGE_REF", r"([$]?[A-Z]{1,3}[$]?\d+):([$]?[A-Z]{1,3}[$]?\d+)"),
    # 单元格引用：$A$1, A1, $A1, A$1
    ("CELL_REF", r"[$]?[A-Z]{1,3}[$]?\d+"),
    # 函数名：SUM, IF, ROUND, DATEDIF
    ("FUNC", r"[A-Z_][A-Z0-9_]+(?=\s*\()"),
    # 百分比：50%（必须在NUMBER前面，否则NUMBER会先匹配）
    ("PERCENT", r"\d+%"),
    # 数字：123, 1.5, .5（不匹配负数，负号作为运算符处理）
    ("NUMBER", r"\d+\.?\d*|\.\d+"),
    # 字符串："hello"
    ("STRING", r'"[^"]*"'),
    # 布尔
    ("BOOL", r"(TRUE|FALSE)"),
    # 运算符：+, -, *, /, ^, =, <>, <, >, <=, >=
    ("OP", r"[+\-*/^]|<>|<=|>=|[=<>]"),
    # 括号
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    # 逗号（参数分隔）
    ("COMMA", r","),
    # 空格（忽略但需识别）
    ("SPACE", r"\s+"),
]


@dataclass
class Token:
    type: str
    value: str
    sheet: Optional[str] = None      # 跨sheet引用时的sheet名
    col: Optional[str] = None        # 列字母
    row: Optional[int] = None        # 行号
    abs_col: bool = False            # 列是否绝对引用 $
    abs_row: bool = False            # 行是否绝对引用 $
    start_ref: Optional['Token'] = None  # 范围引用的起点
    end_ref: Optional['Token'] = None    # 范围引用的终点


class Tokenizer:
    """Excel公式词法分析器"""

    def __init__(self, formula: str):
        self.formula = formula
        self.pos = 0
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        """将公式字符串转换为token列表"""
        # 去掉开头的等号
        if self.formula.startswith("="):
            text = self.formula[1:]
        else:
            text = self.formula

        while text:
            matched = False
            for token_type, pattern in TOKEN_TYPES:
                regex = re.compile(pattern, re.IGNORECASE)
                match = regex.match(text)
                if match:
                    matched = True
                    value = match.group(0)

                    # 根据类型创建Token
                    token = self._create_token(token_type, value, match)
                    if token.type != "SPACE":  # 忽略空格
                        self.tokens.append(token)

                    text = text[len(value):]
                    break

            if not matched:
                # 未知字符，跳过或报错
                raise ValueError(f"无法解析的字符: '{text[0]}' 在位置 {self.pos}")

        return self.tokens

    def _create_token(self, token_type: str, value: str, match) -> Token:
        """根据匹配结果创建Token"""
        if token_type == "SHEET_RANGE_REF":
            # 跨sheet范围引用：'表3'!A1:F10
            if match.group(1):  # quoted sheet name
                sheet_name = match.group(1).strip("'")
                start_ref = match.group(2)
                end_ref = match.group(3)
            else:  # unquoted sheet name
                sheet_name = match.group(4)
                start_ref = match.group(5)
                end_ref = match.group(6)
            start = self._parse_cell_ref_token(start_ref)
            end = self._parse_cell_ref_token(end_ref)
            return Token(
                type="RANGE_REF",
                value=value,
                sheet=sheet_name,
                start_ref=start,
                end_ref=end,
            )

        elif token_type == "SHEET_REF":
            # 跨sheet引用：'参数输入表'!$I$380 或 参数输入表!$I$380
            if match.group(1):  # quoted sheet name like '表名'
                sheet_name = match.group(1).strip("'")
                cell_ref = match.group(2)
            else:  # unquoted sheet name
                sheet_name = match.group(3)
                cell_ref = match.group(4)
            col, row, abs_col, abs_row = self._parse_cell_ref(cell_ref)
            return Token(
                type="CELL_REF",
                value=value,
                sheet=sheet_name,
                col=col,
                row=row,
                abs_col=abs_col,
                abs_row=abs_row,
            )

        elif token_type == "RANGE_REF":
            # 范围引用：F5:F10
            start_str = match.group(1)
            end_str = match.group(2)
            start = self._parse_cell_ref_token(start_str)
            end = self._parse_cell_ref_token(end_str)
            return Token(
                type="RANGE_REF",
                value=value,
                start_ref=start,
                end_ref=end,
            )

        elif token_type == "CELL_REF":
            # 单单元格引用
            col, row, abs_col, abs_row = self._parse_cell_ref(value)
            return Token(
                type="CELL_REF",
                value=value,
                col=col,
                row=row,
                abs_col=abs_col,
                abs_row=abs_row,
            )

        elif token_type == "FUNC":
            return Token(type="FUNC", value=value.upper())

        elif token_type == "NUMBER":
            num = float(value) if '.' in value else int(value)
            return Token(type="NUMBER", value=num)

        elif token_type == "PERCENT":
            # 百分比：50% -> 0.5
            num = float(value[:-1]) / 100
            return Token(type="NUMBER", value=num)

        elif token_type == "STRING":
            # 去掉引号
            return Token(type="STRING", value=value[1:-1])

        elif token_type == "BOOL":
            return Token(type="BOOL", value=value.upper() == "TRUE")

        else:
            return Token(type=token_type, value=value)

    def _parse_cell_ref(self, ref: str) -> tuple:
        """解析单元格引用 A1, $A$1, $A1, A$1"""
        abs_col = ref.startswith("$")
        if abs_col:
            ref = ref[1:]

        # 分离列字母和行号
        col_match = re.match(r"([A-Z]+)", ref)
        row_match = re.match(r"([A-Z]+)(\$?)(\d+)", ref)

        if not row_match:
            raise ValueError(f"无效的单元格引用: {ref}")

        col = row_match.group(1)
        abs_row = row_match.group(2) == "$"
        row = int(row_match.group(3))

        return col, row, abs_col, abs_row

    def _parse_cell_ref_token(self, ref: str) -> Token:
        """解析单元格引用为Token"""
        col, row, abs_col, abs_row = self._parse_cell_ref(ref)
        return Token(
            type="CELL_REF",
            value=ref,
            col=col,
            row=row,
            abs_col=abs_col,
            abs_row=abs_row,
        )


# === AST节点 ===
@dataclass
class ASTNode:
    """抽象语法树节点"""
    node_type: str
    value: Any = None
    children: List['ASTNode'] = None

    # 引用类型节点的额外字段
    sheet: Optional[str] = None
    col: Optional[str] = None
    row: Optional[int] = None
    abs_col: bool = False
    abs_row: bool = False
    func_name: Optional[str] = None
    operator: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典（用于JSON序列化）"""
        result = {"node_type": self.node_type}
        if self.value is not None:
            result["value"] = self.value
        if self.sheet is not None:
            result["sheet"] = self.sheet
        if self.col is not None:
            result["col"] = self.col
        if self.row is not None:
            result["row"] = self.row
        if self.abs_col:
            result["abs_col"] = self.abs_col
        if self.abs_row:
            result["abs_row"] = self.abs_row
        if self.func_name:
            result["func_name"] = self.func_name
        if self.operator:
            result["operator"] = self.operator
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        return result

    def get_references(self) -> List[dict]:
        """递归提取所有单元格引用（用于构建依赖边）"""
        refs = []
        if self.node_type == "cell_ref":
            refs.append({
                "type": "cell",
                "sheet": self.sheet,
                "col": self.col,
                "row": self.row,
                "abs_col": self.abs_col,
                "abs_row": self.abs_row,
            })
        elif self.node_type == "range_ref":
            # 范围引用返回一个range类型的引用
            refs.append({
                "type": "range",
                "sheet": self.sheet,
                "start_col": self.children[0].col if self.children else None,
                "start_row": self.children[0].row if self.children else None,
                "end_col": self.children[1].col if len(self.children) > 1 else None,
                "end_row": self.children[1].row if len(self.children) > 1 else None,
            })
        if self.children:
            for child in self.children:
                # 跳过range_ref内部的cell_ref（已包含在range中）
                if child.node_type != "cell_ref" or self.node_type != "range_ref":
                    refs.extend(child.get_references())
        return refs


class FormulaParser:
    """Excel公式解析器 - Token流 → AST"""

    def __init__(self):
        self.tokens: List[Token] = []
        self.pos = 0
        self.current_sheet: Optional[str] = None  # 当前sheet上下文

    def parse(self, formula: str, current_sheet: str = None) -> ASTNode:
        """解析公式字符串为AST"""
        self.current_sheet = current_sheet
        tokenizer = Tokenizer(formula)
        self.tokens = tokenizer.tokenize()
        self.pos = 0

        if not self.tokens:
            return ASTNode(node_type="empty")

        ast = self._parse_expression()
        return ast

    def _parse_expression(self) -> ASTNode:
        """解析表达式（最低优先级：比较运算）"""
        left = self._parse_additive()

        while self.pos < len(self.tokens) and self.tokens[self.pos].type == "OP":
            op = self.tokens[self.pos].value
            if op in ("=", "<>", "<", ">", "<=", ">="):
                self.pos += 1
                right = self._parse_additive()
                left = ASTNode(
                    node_type="binary_op",
                    operator=op,
                    children=[left, right],
                )
            else:
                break

        return left

    def _parse_additive(self) -> ASTNode:
        """解析加减运算"""
        left = self._parse_multiplicative()

        while self.pos < len(self.tokens) and self.tokens[self.pos].type == "OP":
            op = self.tokens[self.pos].value
            if op in ("+", "-"):
                self.pos += 1
                right = self._parse_multiplicative()
                left = ASTNode(
                    node_type="binary_op",
                    operator=op,
                    children=[left, right],
                )
            else:
                break

        return left

    def _parse_multiplicative(self) -> ASTNode:
        """解析乘除运算"""
        left = self._parse_power()

        while self.pos < len(self.tokens) and self.tokens[self.pos].type == "OP":
            op = self.tokens[self.pos].value
            if op in ("*", "/"):
                self.pos += 1
                right = self._parse_power()
                left = ASTNode(
                    node_type="binary_op",
                    operator=op,
                    children=[left, right],
                )
            else:
                break

        return left

    def _parse_power(self) -> ASTNode:
        """解析幂运算"""
        left = self._parse_unary()

        while self.pos < len(self.tokens) and self.tokens[self.pos].type == "OP":
            op = self.tokens[self.pos].value
            if op == "^":
                self.pos += 1
                right = self._parse_unary()
                left = ASTNode(
                    node_type="binary_op",
                    operator=op,
                    children=[left, right],
                )
            else:
                break

        return left

    def _parse_unary(self) -> ASTNode:
        """解析一元运算符"""
        if self.pos < len(self.tokens) and self.tokens[self.pos].type == "OP":
            op = self.tokens[self.pos].value
            if op in ("+", "-"):
                self.pos += 1
                operand = self._parse_unary()
                return ASTNode(
                    node_type="unary_op",
                    operator=op,
                    children=[operand],
                )

        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        """解析基本元素：数字、字符串、单元格引用、函数调用、括号表达式"""
        if self.pos >= len(self.tokens):
            raise ValueError("意外的表达式结尾")

        token = self.tokens[self.pos]

        # 数字
        if token.type == "NUMBER":
            self.pos += 1
            return ASTNode(node_type="literal", value=token.value)

        # 字符串
        if token.type == "STRING":
            self.pos += 1
            return ASTNode(node_type="literal", value=token.value)

        # 布尔
        if token.type == "BOOL":
            self.pos += 1
            return ASTNode(node_type="literal", value=token.value)

        # 单元格引用
        if token.type == "CELL_REF":
            self.pos += 1
            sheet = token.sheet or self.current_sheet
            return ASTNode(
                node_type="cell_ref",
                sheet=sheet,
                col=token.col,
                row=token.row,
                abs_col=token.abs_col,
                abs_row=token.abs_row,
            )

        # 范围引用
        if token.type == "RANGE_REF":
            self.pos += 1
            # 使用token.sheet（跨sheet范围）或current_sheet
            range_sheet = token.sheet if hasattr(token, 'sheet') and token.sheet else self.current_sheet
            start = ASTNode(
                node_type="cell_ref",
                sheet=range_sheet,
                col=token.start_ref.col,
                row=token.start_ref.row,
            )
            end = ASTNode(
                node_type="cell_ref",
                sheet=range_sheet,
                col=token.end_ref.col,
                row=token.end_ref.row,
            )
            return ASTNode(
                node_type="range_ref",
                sheet=range_sheet,
                children=[start, end],
            )

        # 函数调用
        if token.type == "FUNC":
            return self._parse_function_call(token)

        # 括号表达式
        if token.type == "LPAREN":
            self.pos += 1
            expr = self._parse_expression()
            if self.pos < len(self.tokens) and self.tokens[self.pos].type == "RPAREN":
                self.pos += 1
            else:
                raise ValueError("缺少右括号")
            return expr

        raise ValueError(f"意外的token: {token.type} '{token.value}'")

    def _parse_function_call(self, func_token: Token) -> ASTNode:
        """解析函数调用"""
        self.pos += 1  # 跳过函数名

        if self.pos >= len(self.tokens) or self.tokens[self.pos].type != "LPAREN":
            raise ValueError(f"函数 {func_token.value} 缺少左括号")

        self.pos += 1  # 跳过左括号

        args = []
        while self.pos < len(self.tokens) and self.tokens[self.pos].type != "RPAREN":
            arg = self._parse_expression()
            args.append(arg)

            if self.pos < len(self.tokens):
                if self.tokens[self.pos].type == "COMMA":
                    self.pos += 1
                elif self.tokens[self.pos].type != "RPAREN":
                    raise ValueError("函数参数之间需要逗号分隔")

        if self.pos >= len(self.tokens) or self.tokens[self.pos].type != "RPAREN":
            raise ValueError(f"函数 {func_token.value} 缺少右括号")

        self.pos += 1  # 跳过右括号

        return ASTNode(
            node_type="function_call",
            func_name=func_token.value,
            children=args,
        )