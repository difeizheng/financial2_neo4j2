"""解析状态页面"""
import streamlit as st
import time
import json
import sys
from pathlib import Path

# ===== 设置路径（必须在其他导入之前）=====
project_root = Path(__file__).parent.parent.parent.parent  # 往上4层
if str(project_root.resolve()) not in sys.path:
    sys.path.insert(0, str(project_root.resolve()))

from financial_kg.config import get_config
from financial_kg.storage.task_db import TaskDB
from financial_kg.core.excel_parser import ExcelParser
from financial_kg.core.calc_engine import CalcEngine
from financial_kg.storage.json_exporter import JSONExporter
from financial_kg.llm.integration import LLMIntegrationService


def render_parse_status_page():
    """渲染解析状态页面"""
    st.title("解析状态")
    st.markdown("查看和管理解析任务。")

    config = get_config()
    task_db = TaskDB()

    # 任务列表
    tasks = task_db.get_tasks(limit=20)

    if not tasks:
        st.info("暂无解析任务。请先上传Excel文件。")
        return

    # 任务表格
    st.markdown("### 任务列表")

    for task in tasks:
        with st.expander(f"**{task.name}** (ID: {task.id}) - {task.status}", expanded=(task.status == "pending")):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**源文件**: {Path(task.source_file).name}")
                st.markdown(f"**目标Sheet**: {', '.join(task.target_sheets)}")
                st.markdown(f"**创建时间**: {task.created_at}")

                if task.error_msg:
                    st.error(f"错误: {task.error_msg}")

                if task.stats:
                    st.json(task.stats)

            with col2:
                # 状态指示
                status_color = {
                    "pending": "⚪",
                    "parsing": "🔵",
                    "parsed": "🟡",
                    "evaluating": "🟠",
                    "completed": "🟢",
                    "error": "🔴",
                }
                st.markdown(f"状态: {status_color.get(task.status, '⚪')} {task.status}")

                # 操作按钮
                if task.status == "pending":
                    # LLM选项
                    use_llm = st.checkbox("启用LLM语义标注", value=False, key=f"llm_{task.id}")

                    if st.button("开始解析", key=f"start_{task.id}"):
                        # 执行解析
                        run_parse_task(task.id, task_db, config, use_llm=use_llm)
                        st.rerun()

                elif task.status == "completed":
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("查看图谱", key=f"view_{task.id}"):
                            st.session_state["view_task_id"] = task.id
                            st.info("请前往 **图谱浏览** 页面")
                    with col_btn2:
                        # LLM增强按钮
                        if st.button("LLM增强", key=f"llm_enhance_{task.id}"):
                            run_llm_enhance(task.id, task_db)
                            st.rerun()

                # 删除按钮
                if st.button("删除任务", key=f"del_{task.id}"):
                    task_db.delete_task(task.id)
                    st.rerun()


def run_parse_task(task_id: int, task_db: TaskDB, config, use_llm: bool = False):
    """执行解析任务"""
    task = task_db.get_task(task_id)
    if task is None:
        return

    # 更新状态
    task_db.update_task(task_id, status="parsing")

    try:
        # 1. 解析Excel
        parser = ExcelParser(task.source_file, task.target_sheets)
        graph = parser.parse(graph_name=task.name)

        # 更新状态
        task_db.update_task(task_id, status="parsed")

        # 2. 构建DAG
        engine = CalcEngine(graph)
        engine.build_dag()
        engine.topological_sort()
        engine.compute_depths()

        # 更新状态
        task_db.update_task(task_id, status="evaluating")

        # 3. 求值验证
        report = engine.validate()

        # 4. LLM处理（可选）
        llm_results = None
        if use_llm:
            try:
                llm_service = LLMIntegrationService()

                # 构建图谱数据
                graph_data = {
                    "nodes": [n.__dict__ for n in graph.nodes.values()],
                    "edges": [e.__dict__ for e in graph.edges.values()],
                    "validation_report": report,
                }

                sheets_info = {sheet: {"max_row": 100, "max_col": 20} for sheet in task.target_sheets}

                llm_results = llm_service.run_full_pipeline(graph_data, sheets_info)

                # 保存LLM结果
                llm_output_file = config.output_dir / f"task_{task_id}_llm_results.json"
                llm_service.save_results(llm_results, llm_output_file)

                # 更新节点语义信息
                if llm_results.get("semantics"):
                    for node_id, semantic_info in llm_results["semantics"].items():
                        node = graph.nodes.get(node_id)
                        if node:
                            node.semantic_name = semantic_info.get("semantic_name")
                            node.semantic_desc = semantic_info.get("semantic_desc")
                            node.semantic_unit = semantic_info.get("semantic_unit")
                            node.semantic_tags = semantic_info.get("semantic_tags", [])

            except Exception as e:
                st.warning(f"LLM处理失败: {e}")

        # 5. 导出JSON
        exporter = JSONExporter(output_dir=str(config.output_dir))
        files = exporter.export(graph, prefix=f"task_{task_id}_")
        exporter.export_validation_report(report, prefix=f"task_{task_id}_")

        # 更新完成状态
        stats = {
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "formula_nodes": sum(1 for n in graph.nodes.values() if n.formula_raw),
            "accuracy": report["accuracy"],
            "nodes_file": files["nodes"],
            "edges_file": files["edges"],
            "llm_enabled": use_llm,
            "llm_results_file": str(llm_output_file) if llm_results else None,
        }

        task_db.update_task(
            task_id,
            status="completed",
            result_path=files["nodes"],
            stats=stats,
        )

    except Exception as e:
        task_db.update_task(task_id, status="error", error_msg=str(e))


def run_llm_enhance(task_id: int, task_db: TaskDB):
    """对已完成任务进行LLM增强"""
    task = task_db.get_task(task_id)
    if task is None or task.status != "completed":
        return

    nodes_file = task.stats.get("nodes_file")
    edges_file = task.stats.get("edges_file")

    if not nodes_file or not Path(nodes_file).exists():
        st.error("图谱数据文件不存在")
        return

    try:
        with st.spinner("LLM处理中..."):
            # 加载图谱数据
            with open(nodes_file, "r", encoding="utf-8") as f:
                nodes = json.load(f)
            with open(edges_file, "r", encoding="utf-8") as f:
                edges = json.load(f)

            # LLM处理
            llm_service = LLMIntegrationService()

            graph_data = {
                "nodes": nodes,
                "edges": edges,
                "validation_report": {"accuracy": task.stats.get("accuracy", 0)},
            }

            sheets_info = {task.target_sheets[0]: {"max_row": 100, "max_col": 20}}

            llm_results = llm_service.run_full_pipeline(graph_data, sheets_info)

            # 保存LLM结果
            config = get_config()
            llm_output_file = config.output_dir / f"task_{task_id}_llm_results.json"
            llm_service.save_results(llm_results, llm_output_file)

            # 更新节点文件（添加语义信息）
            if llm_results.get("semantics"):
                for node in nodes:
                    semantic_info = llm_results["semantics"].get(node["id"])
                    if semantic_info:
                        node["semantic_name"] = semantic_info.get("semantic_name")
                        node["semantic_desc"] = semantic_info.get("semantic_desc")
                        node["semantic_unit"] = semantic_info.get("semantic_unit")
                        node["semantic_tags"] = semantic_info.get("semantic_tags", [])

                # 保存更新后的节点文件
                with open(nodes_file, "w", encoding="utf-8") as f:
                    json.dump(nodes, f, ensure_ascii=False, indent=2)

            # 更新任务状态
            task.stats["llm_enabled"] = True
            task.stats["llm_results_file"] = str(llm_output_file)
            task.stats["semantic_nodes"] = len(llm_results.get("semantics", {}))
            task.stats["anomalies"] = len(llm_results.get("anomalies", []))

            task_db.update_task(task_id, stats=task.stats)

            st.success(f"LLM增强完成！标注了 {len(llm_results.get('semantics', {}))} 个节点")

    except Exception as e:
        st.error(f"LLM增强失败: {e}")