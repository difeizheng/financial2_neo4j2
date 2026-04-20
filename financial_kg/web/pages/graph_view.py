"""图谱浏览页面"""
import streamlit as st
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any
import pandas as pd

# ===== 设置路径（必须在其他导入之前）=====
project_root = Path(__file__).parent.parent.parent.parent  # 往上4层
if str(project_root.resolve()) not in sys.path:
    sys.path.insert(0, str(project_root.resolve()))

from financial_kg.config import get_config
from financial_kg.storage.task_db import TaskDB
from financial_kg.core.calc_engine import CalcEngine
from financial_kg.storage.json_importer import JSONImporter
from financial_kg.web.components.d3_graph.component import D3GraphComponent


def _build_animation_html(component, propagation_data):
    """构建带传播动画的HTML"""
    import json

    # 读取D3组件文件
    component_dir = Path(__file__).parent.parent / "components" / "d3_graph" / "frontend"

    with open(component_dir / "index.html", "r", encoding="utf-8") as f:
        html_template = f.read()

    with open(component_dir / "graph.js", "r", encoding="utf-8") as f:
        js_content = f.read()

    with open(component_dir / "propagation.js", "r", encoding="utf-8") as f:
        propagation_js = f.read()

    with open(component_dir / "style.css", "r", encoding="utf-8") as f:
        css_content = f.read()

    # 内联D3.js以避免CDN超时问题（使用unpkg备用CDN）
    d3_script = '<script src="https://unpkg.com/d3@7/dist/d3.min.js"></script>'
    # 如果unpkg也失败，使用cdnjs备用
    d3_fallback = '''
<script>
if(typeof d3==='undefined'){
    document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"><\\/script>');
}
</script>'''

    # 图谱数据
    graph_data = {
        "nodes": component.nodes,
        "edges": component.edges,
    }

    # 初始化和动画触发脚本 - 避免重复初始化，确保动画稳定执行
    data_script = f"""
    <script>
        // 全局数据
        const initialData = {json.dumps(graph_data, ensure_ascii=False)};
        const propagationData = {json.dumps(propagation_data, ensure_ascii=False)};

        console.log('数据准备完成:', initialData.nodes.length, '个节点');

        // 标记是否已初始化，防止重复调用
        let _animationInitialized = false;

        function initAndAnimate() {{
            if (_animationInitialized) return;
            _animationInitialized = true;

            console.log('开始初始化图谱...');

            // 等待streamlitReceiveData就绪（由graph.js的DOMContentLoaded设置）
            function waitForReady() {{
                if (typeof window.streamlitReceiveData === 'function') {{
                    console.log('传递图谱数据...');
                    window.streamlitReceiveData(initialData);

                    // 等待力导向模拟稳定后触发动画
                    setTimeout(function() {{
                        triggerAnimation();
                    }}, 2000);
                }} else {{
                    // streamlitReceiveData还没准备好，等待
                    setTimeout(waitForReady, 50);
                }}
            }}

            waitForReady();
        }}

        function triggerAnimation() {{
            try {{
                console.log('触发传播动画...');
                console.log('检查receivePropagationResult:', typeof window.receivePropagationResult);
                console.log('检查executePropagationAnimation:', typeof window.executePropagationAnimation);
                console.log('检查nodeElements:', typeof nodeElements, nodeElements ? 'size=' + (nodeElements.size ? nodeElements.size() : 'N/A') : 'null');

                if (typeof window.receivePropagationResult === 'function') {{
                    window.receivePropagationResult(propagationData);
                }} else {{
                    console.error('receivePropagationResult函数未定义');
                }}
            }} catch (error) {{
                console.error('triggerAnimation错误:', error);
                console.error('错误堆栈:', error.stack);
            }}
        }}

        // 等待DOMContentLoaded（graph.js会在此事件中调用initGraph）
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', function() {{
                // graph.js的DOMContentLoaded已注册，会先执行initGraph
                // 延迟一帧确保graph.js初始化完成
                setTimeout(initAndAnimate, 50);
            }});
        }} else {{
            // DOM已就绪，graph.js的initGraph可能已执行
            setTimeout(initAndAnimate, 50);
        }}
    </script>
    """

    # 组合HTML - 替换CDN为更稳定的unpkg + fallback
    full_html = html_template.replace(
        '<link rel="stylesheet" href="style.css">',
        f'<style>{css_content}</style>'
    ).replace(
        '<script src="https://d3js.org/d3.v7.min.js"></script>',
        d3_script + d3_fallback
    ).replace(
        '<script src="graph.js"></script>',
        f'<script>{js_content}</script>'
    ).replace(
        '<script src="propagation.js"></script>',
        f'<script>{propagation_js}</script>{data_script}'
    )

    return full_html


def render_graph_view_page():
    """渲染图谱浏览页面"""
    st.title("图谱浏览")
    st.markdown("交互式浏览财务模型知识图谱。")

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

    # 显示统计信息
    st.markdown("### 图谱统计")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("节点数", task.stats.get("total_nodes", 0))
    with col2:
        st.metric("边数", task.stats.get("total_edges", 0))
    with col3:
        st.metric("公式节点", task.stats.get("formula_nodes", 0))
    with col4:
        st.metric("准确率", f"{task.stats.get('accuracy', 0):.1%}")
    with col5:
        st.metric("语义标注", task.stats.get("semantic_nodes", 0))

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

    # === D3图谱可视化 ===
    st.markdown("---")
    st.markdown("### 交互式图谱可视化")

    # 限制显示节点数（D3性能）
    view_limit = st.slider("显示节点数", 100, 2000, 500, key="d3_view_limit")

    # 过滤节点
    display_nodes = nodes[:view_limit]
    node_ids = set(n["id"] for n in display_nodes)
    display_edges = [e for e in edges if e.get("source") in node_ids and e.get("target") in node_ids]

    # 转换边数据格式（D3需要source/target字段）
    for e in display_edges:
        if "source_id" in e and "source" not in e:
            e["source"] = e["source_id"]
        if "target_id" in e and "target" not in e:
            e["target"] = e["target_id"]

    # 渲染D3图谱
    d3_component = D3GraphComponent()
    d3_component.nodes = display_nodes
    d3_component.edges = display_edges

    st.markdown(f"显示 {len(display_nodes)} 个节点，{len(display_edges)} 条边")

    # 始终渲染正常图谱
    d3_component.render(height=500, key=f"d3_graph_{task_id}")

    # === 节点搜索和过滤 ===
    st.markdown("---")
    st.markdown("### 节点搜索")

    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_term = st.text_input("搜索节点ID或值", "")
    with search_col2:
        sheets = list(set(n.get("sheet", "unknown") for n in nodes))
        sheet_filter = st.multiselect("Sheet过滤", sheets, default=sheets)

    # 过滤节点
    if search_term:
        filtered_nodes = [
            n for n in nodes
            if search_term.lower() in str(n.get("id", "")).lower()
            or search_term.lower() in str(n.get("value", "")).lower()
        ]
    else:
        filtered_nodes = [n for n in nodes if n.get("sheet") in sheet_filter]

    # 限制显示数量（处理边界情况，避免Streamlit dataframe性能问题）
    total_filtered = len(filtered_nodes)
    if total_filtered <= 100:
        display_limit = total_filtered
        st.info(f"找到 {total_filtered} 个节点（全部显示）")
    else:
        # 限制最大显示500行，避免Streamlit内部错误
        max_slider = min(500, total_filtered)
        default_slider = min(200, total_filtered)
        display_limit = st.slider("显示节点数", 100, max_slider, default_slider)
        if total_filtered > 500:
            st.caption(f"⚠️ Streamlit dataframe 限制最多500行，实际找到 {total_filtered} 个节点")
    display_nodes_table = filtered_nodes[:display_limit]

    st.info(f"显示 {len(display_nodes_table)} 个节点")

    # 显示节点表格 - 预处理避免Arrow警告
    st.markdown("---")
    st.markdown("### 节点数据")

    if display_nodes_table:
        # 构建DataFrame并处理混合类型列
        df_data = []
        for n in display_nodes_table:
            df_data.append({
                "id": str(n.get("id", "")),
                "sheet": str(n.get("sheet", "")),
                "row": n.get("row", 0),
                "col": str(n.get("col", "")),
                "value": str(n.get("value", "")) if n.get("value") is not None else "",
                "formula_raw": str(n.get("formula_raw", "")) if n.get("formula_raw") else "",
                "depth": n.get("depth", 0),
                "in_degree": n.get("in_degree", 0),
                "out_degree": n.get("out_degree", 0),
                "semantic_name": str(n.get("semantic_name", "")) if n.get("semantic_name") else "",
            })
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, height=400)

    # 节点详情查看
    st.markdown("---")
    st.markdown("### 节点详情")

    node_id_input = st.text_input("输入节点ID查看详情", "")

    if node_id_input:
        node = next((n for n in nodes if n.get("id") == node_id_input), None)
        if node:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.json({
                    "id": node.get("id"),
                    "sheet": node.get("sheet"),
                    "position": f"{node.get('col')}{node.get('row')}",
                    "value": node.get("value"),
                    "formula": node.get("formula_raw"),
                    "depth": node.get("depth"),
                    "in_degree": node.get("in_degree"),
                    "out_degree": node.get("out_degree"),
                    "semantic_name": node.get("semantic_name"),
                })

            with col2:
                upstream = [e.get("source") for e in edges if e.get("target") == node_id_input]
                downstream = [e.get("target") for e in edges if e.get("source") == node_id_input]

                st.metric("上游依赖", len(upstream))
                st.metric("下游影响", len(downstream))

                if upstream[:10]:
                    st.text("上游: " + ", ".join(str(s) for s in upstream[:10]))
                if downstream[:10]:
                    st.text("下游: " + ", ".join(str(s) for s in downstream[:10]))

        else:
            st.warning(f"未找到节点: {node_id_input}")

    # === 值传播模拟 ===
    st.markdown("---")
    st.markdown("### 值传播模拟")
    st.markdown("修改节点值后，系统将自动计算所有下游节点的变化并在图谱中动画展示。")

    # 搜索模式选择
    search_mode = st.radio(
        "搜索范围",
        ["仅输入节点（推荐）", "全部节点"],
        horizontal=True,
        key="propagate_search_mode",
        help="输入节点：depth=0且无公式，可直接修改值。全部节点：包含公式节点，修改后会触发重算。"
    )

    if search_mode == "仅输入节点（推荐）":
        # 获取输入节点列表 - 使用 is_input 字段或 depth=0 且无公式
        searchable_nodes = [
            n for n in nodes
            if n.get("is_input") == True
            or (n.get("depth") == 0 and n.get("formula_raw") is None and n.get("value_type") == "number")
        ]
    else:
        # 全部节点（数值类型优先）
        searchable_nodes = [n for n in nodes if n.get("value_type") == "number"]
        # 如果数值节点太少，添加全部节点
        if len(searchable_nodes) < 100:
            searchable_nodes = nodes

    # === 可搜索的节点选择 ===
    st.markdown("**选择节点**")

    if len(searchable_nodes) == 0:
        st.warning(f"无可搜索节点。总节点数: {len(nodes)}")
        propagate_node = st.text_input("手动输入节点ID", key="manual_node_input")
    else:
        st.caption(f"可搜索节点数: {len(searchable_nodes)}")

        # 搜索输入框
        search_input = st.text_input(
            "🔍 搜索节点",
            value=st.session_state.get("propagate_search", ""),
            placeholder="输入节点ID、地址、Sheet名或值...",
            key="propagate_search_input",
            help="支持搜索节点ID、地址(sheet!colrow)、Sheet名称、值"
        )

        # 根据搜索过滤节点
        if search_input:
            search_lower = search_input.lower()
            filtered_nodes = [
                n for n in searchable_nodes
                if search_lower in n.get("id", "").lower()
                or search_lower in n.get("address", "").lower()
                or search_lower in n.get("sheet", "").lower()
                or search_lower in str(n.get("value", "")).lower()
                or (n.get("semantic_name") and search_lower in n.get("semantic_name").lower())
            ]
        else:
            # 默认显示前20个节点
            filtered_nodes = searchable_nodes[:20]

        # 显示搜索结果数量
        st.caption(f"找到 {len(filtered_nodes)} 个匹配节点")

    # 选择节点
    if filtered_nodes:
        # 构建选项列表（显示ID、值、公式信息）
        select_options = []
        for n in filtered_nodes:
            formula_info = "输入" if not n.get("formula_raw") else f"公式:{n.get('formula_raw', '')[:30]}"
            select_options.append(
                f"{n.get('id', '')} | 值: {n.get('value', '空')} | {formula_info} | {n.get('address', '')}"
            )

        selected_option = st.selectbox(
            "选择节点",
            select_options,
            key="propagate_node_select",
            help="从搜索结果中选择，或继续在上方搜索框中输入以筛选"
        )

        # 提取节点ID
        if selected_option:
            propagate_node = selected_option.split(" | ")[0]
            # 显示选中节点的详细信息
            selected_node = next((n for n in filtered_nodes if n.get("id") == propagate_node), None)
            if selected_node:
                node_type = "输入节点" if not selected_node.get("formula_raw") else "公式节点"
                st.markdown(f"**已选**: `{propagate_node}` | 类型: `{node_type}` | Sheet: `{selected_node.get('sheet', '')}` | 深度: `{selected_node.get('depth', 0)}`")
                if selected_node.get("formula_raw"):
                    st.caption(f"公式: `{selected_node.get('formula_raw')}`")
        else:
            propagate_node = ""
    else:
        st.warning("未找到匹配节点，请修改搜索条件或手动输入节点ID")
        propagate_node = st.text_input("手动输入节点ID", key="manual_node_input_fallback")

    # 新值输入
    new_value = st.number_input("输入新值", value=0.0, key="propagate_new_value")

    # 动画选项
    col_anim1, col_anim2 = st.columns([1, 1])
    with col_anim1:
        show_animation = st.checkbox("显示D3动画", value=True, help="在图谱中动画展示传播路径")
    with col_anim2:
        show_table = st.checkbox("显示变更表格", value=True, help="表格形式显示所有变更")

    # 执行按钮
    if st.button("🚀 执行传播模拟", type="primary", key="execute_propagate"):
        if propagate_node:
            try:
                with st.spinner("正在执行传播计算..."):
                    # 加载完整图谱进行传播
                    importer = JSONImporter()
                    full_graph = importer.import_graph(
                        nodes_file=nodes_file,
                        edges_file=edges_file,
                        name=task.name,
                        source_file=task.source_file,
                    )

                    engine = CalcEngine(full_graph)
                    engine.build_dag()
                    engine.topological_sort()
                    engine.compute_depths()

                    # 关键：先执行一次求值初始化所有节点的 computed_value
                    engine.evaluate_all()

                    # 执行传播
                    changes = engine.propagate(propagate_node, new_value)

                    st.success(f"传播完成，{len(changes)} 个节点更新")

                # 显示变更统计
                st.markdown("#### 传播结果")

                change_count = len(changes)
                increase_count = sum(1 for old, new in changes.values() if isinstance(old, (int, float)) and isinstance(new, (int, float)) and new > old)
                decrease_count = sum(1 for old, new in changes.values() if isinstance(old, (int, float)) and isinstance(new, (int, float)) and new < old)

                stat_col1, stat_col2, stat_col3 = st.columns(3)
                with stat_col1:
                    st.metric("总变化", change_count)
                with stat_col2:
                    st.metric("增加", increase_count)
                with stat_col3:
                    st.metric("减少", decrease_count)

                # 显示变更表格 - 确保类型一致避免Arrow序列化错误
                if show_table:
                    display_count = min(100, len(changes))
                    change_list = list(changes.items())[:display_count]

                    # 构建数据，确保数值类型统一
                    change_data = []
                    for nid, (old, new) in change_list:
                        # 转换为float，None用NaN替代
                        old_val = float(old) if isinstance(old, (int, float)) else 0.0
                        new_val = float(new) if isinstance(new, (int, float)) else 0.0
                        diff_val = new_val - old_val if isinstance(old, (int, float)) and isinstance(new, (int, float)) else 0.0

                        change_data.append({
                            "节点ID": nid,
                            "旧值": old_val,
                            "新值": new_val,
                            "变化": diff_val,
                        })

                    change_df = pd.DataFrame(change_data)
                    st.dataframe(change_df, height=300)

                    # 导出按钮
                    if len(changes) > display_count:
                        if st.button("导出全部变更到CSV"):
                            full_change_df = pd.DataFrame([
                                {"节点ID": nid, "旧值": old, "新值": new}
                                for nid, (old, new) in changes.items()
                            ])
                            csv = full_change_df.to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                "下载CSV",
                                csv,
                                f"propagate_changes_{propagate_node}.csv",
                                "text/csv"
                            )

                # === D3传播动画 ===
                if show_animation and len(changes) > 0:
                    st.markdown("---")
                    st.markdown("#### 传播动画可视化")

                    # 计算每个变化节点在传播路径中的相对深度（BFS跳数）
                    from collections import deque as _deque
                    changed_ids = set(changes.keys())
                    relative_depth = {propagate_node: 0}
                    bfs_queue = _deque([propagate_node])
                    while bfs_queue:
                        curr = bfs_queue.popleft()
                        curr_depth = relative_depth[curr]
                        for downstream in full_graph.reverse_adjacency.get(curr, []):
                            if downstream in changed_ids and downstream not in relative_depth:
                                relative_depth[downstream] = curr_depth + 1
                                bfs_queue.append(downstream)

                    animation_changes = []
                    for nid, (old_val, new_val) in changes.items():
                        animation_changes.append({
                            "nodeId": nid,
                            "oldValue": float(old_val) if isinstance(old_val, (int, float)) else 0.0,
                            "newValue": float(new_val) if isinstance(new_val, (int, float)) else 0.0,
                            "depth": relative_depth.get(nid, 0),
                        })

                    propagation_data_local = {
                        "sourceNodeId": propagate_node,
                        "changes": animation_changes[:200],
                    }

                    st.info(f"🎬 源节点: `{propagate_node}` | 动画节点数: {len(propagation_data_local['changes'])}")

                    # 确保源节点在动画显示节点中
                    anim_nodes = list(display_nodes)
                    anim_node_ids = set(n["id"] for n in anim_nodes)
                    if propagate_node not in anim_node_ids:
                        source_node_data = next((n for n in nodes if n.get("id") == propagate_node), None)
                        if source_node_data:
                            anim_nodes = [source_node_data] + anim_nodes
                            anim_node_ids.add(propagate_node)
                    anim_edges = [e for e in display_edges if e.get("source") in anim_node_ids and e.get("target") in anim_node_ids]

                    anim_component = D3GraphComponent()
                    anim_component.nodes = anim_nodes
                    anim_component.edges = anim_edges
                    html_content = _build_animation_html(anim_component, propagation_data_local)
                    st.components.v1.html(html_content, height=600, scrolling=False)

            except Exception as e:
                st.error(f"传播失败: {e}")
        else:
            st.warning("请选择或输入节点ID")