"""依赖边模型"""
from dataclasses import dataclass


@dataclass
class DependencyEdge:
    """公式依赖关系边 - 表示一个单元格引用另一个单元格"""

    id: str                          # "参数输入表_380_I->表3_5_F"
    source_id: str                   # 被依赖的节点ID（上游）
    target_id: str                   # 公式所在节点ID（下游）
    edge_type: str = "formula_ref"   # "formula_ref"|"cross_sheet_ref"|"range_ref"
    ref_type: str = "absolute"       # "absolute"|"relative"|"mixed"
    ref_raw: str = ""                # 公式中的原始引用文本 "参数输入表!$I$380"
    is_cross_sheet: bool = False     # 是否跨sheet引用
    weight: float = 1.0              # 可用于可视化边粗细

    def to_dict(self) -> dict:
        """导出为JSON兼容字典"""
        return {
            "id": self.id,
            "source": self.source_id,
            "target": self.target_id,
            "type": self.edge_type,
            "ref_type": self.ref_type,
            "ref_raw": self.ref_raw,
            "is_cross_sheet": self.is_cross_sheet,
            "weight": self.weight,
        }

    @classmethod
    def make_id(cls, source_id: str, target_id: str) -> str:
        """生成边ID"""
        return f"{source_id}->{target_id}"