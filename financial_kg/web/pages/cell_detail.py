"""单元格详情页面"""
import streamlit as st
import json
import sys
from pathlib import Path
from typing import Dict, Any

# ===== 设置路径（必须在其他导入之前）=====
project_root = Path(__file__).parent.parent.parent.parent  # 往上4层
if str(project_root.resolve()) not in sys.path:
    sys.path.insert(0, str(project_root.resolve()))

from financial_kg.config import get_config
from financial_kg.storage.task_db import TaskDB
from financial_kg.storage.json_importer import JSONImporter
from financial_kg.core.calc_engine import CalcEngine
from financial_kg.llm.integration import LLMIntegrationService


def render_cell_detail_page():
    """渲染单元格详情页面"""
    st.title("单元格详情")
    st.markdown("查看单元格的完整信息，包括值、公式、语义、依赖关系等。")

    config = get_config()
    task_db = TaskDB()

    # 选择任务
    completed_tasks = task_db.get_tasks(status="completed", limit=10)

    if not completed_tasks:
        st.info("暂无已完成的解析任务。请先解析Excel文件。")
        return

    # 任务选择
    task_options = {t.name: t.id for t in completed_tasks}
    selected_name = st.selectbox("选择任务", list(task_options.keys()))

    if selected_name is None:
        return

    task_id = task_options[selected_name]
    task = task_db.get_task(task_id)

    if task is None:
        st.error("任务不存在")
        return

    # 加载图谱数据
    nodes_file = task.stats.get("nodes_file")
    edges_file = task.stats.get("edges_file")

    if not nodes_file or not Path(nodes_file).exists():
        st.error("图谱数据文件不存在")
        return

    with open(nodes_file, "r", encoding="utf-8") as f:
        nodes = json.load(f)

    with open(edges_file, "r", encoding="utf-8") as f:
        edges = json.load(f)

    # 构建节点字典
    node_dict = {n["id"]: n for n in nodes}

    # 构建依赖关系
    upstream_map = {}  # 被谁依赖
    downstream_map = {}  # 依赖谁

    for e in edges:
        source = e.get("source")
        target = e.get("target")
        if source and target:
            if target not in upstream_map:
                upstream_map[target] = []
            upstream_map[target].append(source)

            if source not in downstream_map:
                downstream_map[source] = []
            downstream_map[source].append(target)

    # === 单元格搜索 ===
    st.markdown("---")
    st.markdown("### 单元格搜索")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        search_type = st.selectbox("搜索方式", ["ID搜索", "地址搜索", "值搜索"])

    with col2:
        search_term = st.text_input("搜索内容", "")

    with col3:
        sheets = list(set(n.get("sheet", "unknown") for n in nodes))
        sheet_filter = st.selectbox("Sheet", ["全部"] + sheets)

    # 执行搜索
    if search_term:
        filtered_nodes = []

        for n in nodes:
            # Sheet过滤
            if sheet_filter != "全部" and n.get("sheet") != sheet_filter:
                continue

            # 搜索类型
            if search_type == "ID搜索":
                if search_term.lower() in n.get("id", "").lower():
                    filtered_nodes.append(n)
            elif search_type == "地址搜索":
                addr = n.get("address", "")
                if search_term.lower() in addr.lower():
                    filtered_nodes.append(n)
            elif search_type == "值搜索":
                val = str(n.get("value", ""))
                if search_term.lower() in val.lower():
                    filtered_nodes.append(n)

        if filtered_nodes:
            st.info(f"找到 {len(filtered_nodes)} 个匹配节点")

            # 显示搜索结果列表
            for i, n in enumerate(filtered_nodes[:20]):
                with st.expander(f"**{n.get('address', n.get('id'))}** - {n.get('value', '')}", expanded=(i == 0)):
                    display_cell_detail(n, node_dict, upstream_map, downstream_map, nodes_file, edges_file, task.name)

        else:
            st.warning("未找到匹配的单元格")

    # === 直接ID输入 ===
    st.markdown("---")
    st.markdown("### 直接输入单元格ID")

    direct_id = st.text_input("输入完整节点ID（如：参数输入表_380_I）", "")

    if direct_id:
        node = node_dict.get(direct_id)
        if node:
            display_cell_detail(node, node_dict, upstream_map, downstream_map, nodes_file, edges_file, task.name)
        else:
            st.error(f"节点不存在: {direct_id}")

    # === 公式错误列表 ===
    st.markdown("---")
    st.markdown("### 公式错误节点")

    error_nodes = [n for n in nodes if n.get("parse_status") == "error"]
    if error_nodes:
        st.warning(f"共有 {len(error_nodes)} 个公式解析错误")

        # 错误类型分类
        error_types = {}
        for n in error_nodes:
            err_msg = n.get("error_msg", "未知错误")
            if err_msg not in error_types:
                error_types[err_msg] = []
            error_types[err_msg].append(n)

        st.markdown("**错误类型分布:**")
        for err_msg, nodes_list in sorted(error_types.items(), key=lambda x: -len(x[1])):
            with st.expander(f"**{err_msg}** ({len(nodes_list)}个)", expanded=(err_msg == list(error_types.keys())[0])):
                # 显示该错误类型的典型公式
                for n in nodes_list[:20]:
                    formula = n.get("formula_raw", "")
                    addr = n.get("address", n.get("id", ""))
                    # 显示公式内容（截断过长的公式）
                    if len(formula) > 80:
                        formula_display = formula[:80] + "..."
                    else:
                        formula_display = formula
                    st.markdown(f"- **{addr}**: `{formula_display}`")

                if len(nodes_list) > 20:
                    st.markdown(f"... 还有 {len(nodes_list) - 20} 个同类错误")

    else:
        st.success("所有公式解析成功")


def display_cell_detail(
    node: Dict[str, Any],
    node_dict: Dict[str, Any],
    upstream_map: Dict[str, list],
    downstream_map: Dict[str, list],
    nodes_file: str,
    edges_file: str,
    graph_name: str,
):
    """显示单个单元格的详细信息"""

    node_id = node.get("id")

    # === 基本信息 ===
    st.markdown("#### 基本信息")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"**ID**: {node_id}")
        st.markdown(f"**地址**: {node.get('address', '')}")
        st.markdown(f"**Sheet**: {node.get('sheet', '')}")
        st.markdown(f"**位置**: 行 {node.get('row', 0)}, 列 {node.get('col', '')}")

    with col2:
        st.metric("深度", node.get("depth", 0))
        st.metric("入度", node.get("in_degree", 0))
        st.metric("出度", node.get("out_degree", 0))

    # === 值与公式 ===
    st.markdown("---")
    st.markdown("#### 值与公式")

    value_col1, value_col2 = st.columns([1, 1])

    with value_col1:
        st.markdown(f"**原始值**: {node.get('value', '无')}")

        computed = node.get("computed_value")
        if computed is not None:
            st.markdown(f"**计算值**: {computed}")

            # 验证匹配
            excel_val = node.get("value")
            if excel_val is not None and isinstance(excel_val, (int, float)) and isinstance(computed, (int, float)):
                diff = abs(excel_val - computed)
                if diff < 0.0001:
                    st.success("✅ 计算值与Excel一致")
                else:
                    st.warning(f"⚠️ 差异: {diff:.6f}")

    with value_col2:
        formula = node.get("formula_raw")
        if formula:
            st.markdown(f"**公式**: `{formula}`")
            st.markdown(f"**解析状态**: {node.get('parse_status', '未解析')}")

            if node.get("formula_ast"):
                with st.expander("查看AST"):
                    st.json(node.get("formula_ast"))
        else:
            st.info("输入节点（无公式）")

    # === 依赖关系 ===
    st.markdown("---")
    st.markdown("#### 依赖关系")

    upstream = upstream_map.get(node_id, [])
    downstream = downstream_map.get(node_id, [])

    dep_col1, dep_col2 = st.columns([1, 1])

    with dep_col1:
        st.markdown(f"**上游依赖** ({len(upstream)}个)")
        if upstream:
            for uid in upstream[:10]:
                u_node = node_dict.get(uid)
                if u_node:
                    addr = u_node.get("address", uid)
                    val = u_node.get("value", "")
                    st.markdown(f"- {addr}: {val}")
            if len(upstream) > 10:
                st.markdown(f"... 还有 {len(upstream) - 10} 个")
        else:
            st.info("无上游依赖")

    with dep_col2:
        st.markdown(f"**下游影响** ({len(downstream)}个)")
        if downstream:
            for did in downstream[:10]:
                d_node = node_dict.get(did)
                if d_node:
                    addr = d_node.get("address", did)
                    formula = d_node.get("formula_raw", "")
                    st.markdown(f"- {addr}: `{formula[:30]}...`" if len(formula) > 30 else f"- {addr}: `{formula}`")
            if len(downstream) > 10:
                st.markdown(f"... 还有 {len(downstream) - 10} 个")
        else:
            st.info("无下游影响")

    # === 语义信息 ===
    st.markdown("---")
    st.markdown("#### 语义信息")

    semantic_name = node.get("semantic_name")
    if semantic_name:
        st.markdown(f"**语义名称**: {semantic_name}")
        st.markdown(f"**语义描述**: {node.get('semantic_desc', '')}")
        st.markdown(f"**单位**: {node.get('semantic_unit', '')}")
        st.markdown(f"**标签**: {', '.join(node.get('semantic_tags', []))}")
    else:
        st.info("未标注语义")

        # LLM标注按钮
        if st.button("使用LLM标注语义", key=f"annotate_{node_id}"):
            try:
                llm_service = LLMIntegrationService()

                # 获取上下文
                context = {
                    "table_id": node.get("sheet", ""),
                    "row_category": node.get("row_label", ""),
                    "col_label": node.get("col_label", ""),
                }

                annotations = llm_service.annotate_semantics([node], context)

                if annotations:
                    ann = annotations[0]
                    st.success("标注完成")
                    st.markdown(f"**语义名称**: {ann.semantic_name}")
                    st.markdown(f"**语义描述**: {ann.semantic_desc}")
                    st.markdown(f"**单位**: {ann.semantic_unit}")
                    st.markdown(f"**置信度**: {ann.confidence:.2f}")

            except Exception as e:
                st.error(f"标注失败: {e}")

    # === 公式解释 ===
    if node.get("formula_raw"):
        st.markdown("---")
        st.markdown("#### 公式解释")

        if st.button("解释此公式", key=f"explain_{node_id}"):
            try:
                llm_service = LLMIntegrationService()

                # 获取依赖节点信息
                dependencies = {}
                for uid in upstream[:20]:
                    u_node = node_dict.get(uid)
                    if u_node:
                        dependencies[uid] = u_node

                explanation = llm_service.explain_formula(node, dependencies)

                if explanation:
                    st.markdown(f"**整体含义**: {explanation.explanation}")
                    st.markdown("**计算步骤**:")
                    for i, step in enumerate(explanation.logic_steps, 1):
                        st.markdown(f"{i}. {step}")
                    st.markdown(f"**业务含义**: {explanation.business_meaning}")
                    if explanation.tips:
                        st.markdown(f"**提示**: {explanation.tips}")

            except Exception as e:
                st.error(f"解释失败: {e}")

    # === 值传播模拟 ===
    if node.get("depth") == 0 and node.get("formula_raw") is None:
        st.markdown("---")
        st.markdown("#### 值传播模拟（输入节点）")

        new_value = st.number_input("新值", value=float(node.get("value", 0) or 0), key=f"new_val_{node_id}")

        if st.button("执行传播", key=f"propagate_{node_id}"):
            try:
                importer = JSONImporter()
                graph = importer.import_graph(
                    nodes_file=nodes_file,
                    edges_file=edges_file,
                    name=graph_name,
                    source_file="",
                )

                engine = CalcEngine(graph)
                engine.build_dag()
                engine.topological_sort()
                engine.compute_depths()
                engine.evaluate_all()

                changes = engine.propagate(node_id, new_value)

                st.success(f"传播完成，{len(changes)} 个节点更新")

                # 显示变更
                change_list = list(changes.items())[:50]
                for cid, (old, new) in change_list:
                    c_node = node_dict.get(cid)
                    addr = c_node.get("address", cid) if c_node else cid
                    st.markdown(f"- {addr}: {old} → {new}")

            except Exception as e:
                st.error(f"传播失败: {e}")