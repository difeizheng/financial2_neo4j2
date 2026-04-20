"""单元格节点模型"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CellNode:
    """Excel单元格节点 - 知识图谱的基本单元"""

    # === 定位 ===
    id: str                          # "参数输入表_380_I" 或 "表3-成本费用表_5_F"
    sheet: str                       # sheet名称
    row: int                         # 行号（1-based）
    col: str                         # 列号字母（A, B, ..., Z, AA, AB...）
    col_index: int                   # 列号数字（0-based，用于计算）
    address: str                     # Excel原生地址 "参数输入表!I380"

    # === 值与公式 ===
    value: Any                       # 原始值（从Excel读取，可能为None）
    value_type: str = "unknown"      # "number" | "string" | "date" | "bool" | "empty" | "unknown"
    formula_raw: Optional[str] = None  # 原始公式字符串 "=参数输入表!$I$380*F5"
    formula_ast: Optional[dict] = None  # 解析后的AST（JSON序列化）
    computed_value: Optional[Any] = None  # 引擎计算值（用于验证）

    # === 结构语义（规则解析） ===
    is_header: bool = False          # 是否表头行/列
    is_merged: bool = False          # 是否合并单元格（只记录左上角）
    merge_range: Optional[str] = None  # 合并范围 "B4:B32"
    table_id: Optional[str] = None   # 所属子表标识 "参数输入表.工程计划"
    row_category: Optional[str] = None  # 行类别（来自合并单元格）
    col_category: Optional[str] = None  # 列类别（来自表头）
    row_label: Optional[str] = None  # 行标签（同行参数名）
    col_label: Optional[str] = None  # 列标签（年份列头如"2025"）

    # === LLM语义增强（Phase 2） ===
    semantic_name: Optional[str] = None  # 语义名称 "建设期_年数"
    semantic_desc: Optional[str] = None  # 描述
    semantic_unit: Optional[str] = None  # 单位 "年"|"万元"|"%"
    semantic_tags: list = field(default_factory=list)  # 标签 ["参数", "工程计划"]

    # === 图属性（计算引擎填充） ===
    in_degree: int = 0               # 被多少节点依赖（下游数）
    out_degree: int = 0              # 依赖多少节点（上游数）
    depth: int = 0                   # DAG深度（0=纯输入节点）
    is_input: bool = False           # 纯输入节点（无公式）
    is_output: bool = False          # 纯输出节点（无下游）

    # === 状态 ===
    parse_status: str = "raw"        # "raw"|"parsed"|"evaluated"|"error"|"unsupported"
    error_msg: Optional[str] = None

    def to_dict(self) -> dict:
        """导出为JSON兼容字典"""
        return {
            "id": self.id,
            "sheet": self.sheet,
            "row": self.row,
            "col": self.col,
            "col_index": self.col_index,
            "address": self.address,
            "value": self._serialize_value(self.value),
            "value_type": self.value_type,
            "formula_raw": self.formula_raw,
            "formula_ast": self.formula_ast,
            "computed_value": self._serialize_value(self.computed_value),
            "is_header": self.is_header,
            "is_merged": self.is_merged,
            "merge_range": self.merge_range,
            "table_id": self.table_id,
            "row_category": self.row_category,
            "col_category": self.col_category,
            "row_label": self.row_label,
            "col_label": self.col_label,
            "semantic_name": self.semantic_name,
            "semantic_desc": self.semantic_desc,
            "semantic_unit": self.semantic_unit,
            "semantic_tags": self.semantic_tags,
            "depth": self.depth,
            "in_degree": self.in_degree,
            "out_degree": self.out_degree,
            "is_input": self.is_input,
            "is_output": self.is_output,
            "parse_status": self.parse_status,
            "error_msg": self.error_msg,
        }

    def _serialize_value(self, v: Any) -> Any:
        """序列化值（处理datetime等特殊类型）"""
        if v is None:
            return None
        import datetime
        if isinstance(v, datetime.datetime):
            return v.strftime("%Y-%m-%d")
        if isinstance(v, datetime.date):
            return v.strftime("%Y-%m-%d")
        return v

    @classmethod
    def make_id(cls, sheet: str, row: int, col: str) -> str:
        """生成节点ID"""
        return f"{sheet}_{row}_{col}"