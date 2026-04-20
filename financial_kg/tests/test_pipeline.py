"""测试脚本 - 验证Excel解析和公式计算"""
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from financial_kg.core.excel_parser import ExcelParser
from financial_kg.core.calc_engine import CalcEngine
from financial_kg.core.formula_parser import FormulaParser
from financial_kg.storage.json_exporter import JSONExporter


def test_parse_excel():
    """测试解析Excel文件"""
    # Excel文件路径
    excel_file = os.path.join(
        project_root,
        "数字化系统财务模型边界【抽水蓄能】v15(亏损弥补+分红预提税+净资产税+折旧摊销优化）.xlsx"
    )

    # 目标sheet（全量14个）
    target_sheets = [
        "参数输入表",
        "时间序列",
        "投产&达产比例",
        "投资概算明细",
        "表1-资金筹措及还本付息表",
        "表2-折旧摊销表",
        "表3-成本费用表",
        "表4-收入税金表",
        "表5-利润表-资本金",
        "表6-现金流量表-资本金",
        "表7-利润表-全投资",
        "表8-现金流量表-全投资",
        "表9-现金流量表-财务计划",
        "表10-资产负债表",
    ]

    print(f"正在解析Excel: {excel_file}")
    print(f"目标sheet: {target_sheets}")

    # 1. 解析Excel
    parser = ExcelParser(excel_file, target_sheets)
    graph = parser.parse(graph_name="抽水蓄能财务模型_v15")

    print(f"\n解析完成:")
    print(f"  - 节点数: {len(graph.nodes)}")
    print(f"  - 有公式的节点: {sum(1 for n in graph.nodes.values() if n.formula_raw)}")

    # 2. 构建依赖DAG
    print("\n构建依赖DAG...")
    engine = CalcEngine(graph)
    adjacency = engine.build_dag()

    print(f"  - 边数: {len(graph.edges)}")
    print(f"  - 跨sheet边: {sum(1 for e in graph.edges if e.is_cross_sheet)}")

    # 3. 拓扑排序
    print("\n拓扑排序...")
    topo_order = engine.topological_sort()
    print(f"  - 排序节点数: {len(topo_order)}")

    # 4. 计算深度
    print("\n计算节点深度...")
    engine.compute_depths()

    depths = {}
    for node in graph.nodes.values():
        d = node.depth
        depths[d] = depths.get(d, 0) + 1

    print(f"  - 深度分布: {dict(sorted(depths.items()))}")

    # 5. 求值验证
    print("\n求值并验证...")
    report = engine.validate()

    print(f"  - 总公式数: {report['total']}")
    print(f"  - 匹配数: {report['matches']}")
    print(f"  - 不匹配: {report['mismatches']}")
    print(f"  - 错误数: {report['errors']}")
    print(f"  - 准确率: {report['accuracy']:.2%}")

    # 6. 导出JSON
    print("\n导出JSON...")
    output_dir = os.path.join(project_root, "financial_kg", "data", "output")
    exporter = JSONExporter(output_dir=output_dir)
    files = exporter.export(graph, prefix="test_")
    exporter.export_validation_report(report, prefix="test_")

    print(f"  - nodes.json: {files['nodes']}")
    print(f"  - edges.json: {files['edges']}")
    print(f"  - graph_meta.json: {files['meta']}")

    # 7. 示例：查看几个节点的详情
    print("\n示例节点:")
    sample_ids = ["参数输入表_4_I", "参数输入表_380_I"]
    for nid in sample_ids:
        node = graph.get_node(nid)
        if node:
            print(f"  {nid}:")
            print(f"    value={node.value}")
            print(f"    formula={node.formula_raw}")
            print(f"    depth={node.depth}")
            print(f"    out_degree={node.out_degree}")

    return graph, report


def test_formula_parser():
    """测试公式解析器"""
    parser = FormulaParser()

    test_cases = [
        "=参数输入表!$I$380*参数输入表!$I$382/(1+参数输入表!$I$383)*F5",
        "=SUM(F6:BA6)",
        "=IF(A1>0, A1*B1, 0)",
        "=ROUND(DATEDIF(I5,I7,\"D\")/365*12,0)",
        "='表4-收入税金表'!F6",
    ]

    print("\n公式解析测试:")
    for formula in test_cases:
        try:
            ast = parser.parse(formula, current_sheet="表3-成本费用表")
            refs = ast.get_references()
            print(f"  {formula[:50]}...")
            print(f"    AST: {ast.node_type}")
            print(f"    引用数: {len(refs)}")
        except Exception as e:
            print(f"  {formula[:50]}... ERROR: {e}")


if __name__ == "__main__":
    test_formula_parser()
    graph, report = test_parse_excel()