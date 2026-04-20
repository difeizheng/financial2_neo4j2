"""D3.js图谱组件 - Streamlit桥接"""
import streamlit.components.v1 as components
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, List


# 组件目录
COMPONENT_DIR = Path(__file__).parent / "frontend"


def render_d3_graph(
    nodes: List[Dict],
    edges: List[Dict],
    height: int = 600,
    key: Optional[str] = None,
) -> Optional[Dict]:
    """
    渲染D3.js知识图谱

    Args:
        nodes: 节点数据列表
        edges: 边数据列表
        height: 图谱高度
        key: Streamlit组件key

    Returns:
        用户交互返回的数据（如传播请求）
    """
    # 准备数据
    graph_data = {
        "nodes": nodes,
        "edges": edges,
    }

    # 构建完整的HTML（内嵌数据和脚本）
    html_content = _build_html_content(graph_data)

    # 渲染组件
    result = components.html(
        html_content,
        height=height,
        scrolling=False,
    )

    return result


def _build_html_content(graph_data: Dict) -> str:
    """构建完整HTML内容，内嵌数据"""

    # 读取模板文件
    with open(COMPONENT_DIR / "index.html", "r", encoding="utf-8") as f:
        html_template = f.read()

    with open(COMPONENT_DIR / "graph.js", "r", encoding="utf-8") as f:
        js_content = f.read()

    with open(COMPONENT_DIR / "propagation.js", "r", encoding="utf-8") as f:
        propagation_js = f.read()

    with open(COMPONENT_DIR / "style.css", "r", encoding="utf-8") as f:
        css_content = f.read()

    # 使用稳定的 CDN + fallback
    d3_script = '<script src="https://unpkg.com/d3@7/dist/d3.min.js"></script>'
    d3_fallback = '''
<script>
if(typeof d3==='undefined'){
    document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"><\\/script>');
}
</script>'''

    # 内嵌数据初始化脚本
    data_script = f"""
    <script>
        // 初始化数据
        const initialData = {json.dumps(graph_data, ensure_ascii=False)};

        // 在页面加载后自动渲染
        window.addEventListener('DOMContentLoaded', function() {{
            // 等待streamlit通信设置完成
            setTimeout(function() {{
                if (window.streamlitReceiveData) {{
                    window.streamlitReceiveData(initialData);
                }} else {{
                    // 直接渲染
                    graphData = initialData;
                    initGraph();
                }}
            }}, 100);
        }});
    </script>
    """

    # 组合完整HTML - 替换CDN
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


class D3GraphComponent:
    """D3图谱组件类"""

    def __init__(self):
        self.nodes = []
        self.edges = []

    def load_from_json(self, nodes_file: str, edges_file: str) -> None:
        """从JSON文件加载图谱数据"""
        with open(nodes_file, "r", encoding="utf-8") as f:
            self.nodes = json.load(f)

        with open(edges_file, "r", encoding="utf-8") as f:
            self.edges = json.load(f)

    def render(self, height: int = 600, key: Optional[str] = None) -> Optional[Dict]:
        """渲染图谱"""
        return render_d3_graph(
            nodes=self.nodes,
            edges=self.edges,
            height=height,
            key=key,
        )

    def handle_propagation(
        self,
        node_id: str,
        new_value: float,
        calc_engine,
    ) -> Dict[str, Any]:
        """
        处理值传播请求

        Args:
            node_id: 要修改的节点ID
            new_value: 新值
            calc_engine: CalcEngine实例

        Returns:
            传播结果（包含变化列表和动画数据）
        """
        changes = calc_engine.propagate(node_id, new_value)

        # 构建动画数据
        animation_changes = []
        for nid, (old_val, new_val) in changes.items():
            node = self.get_node(nid)
            animation_changes.append({
                "nodeId": nid,
                "oldValue": old_val,
                "newValue": new_val,
                "depth": node.get("depth", 0) if node else 0,
            })

        # 更新节点数据
        for nid, (old_val, new_val) in changes.items():
            for node in self.nodes:
                if node["id"] == nid:
                    node["value"] = new_val
                    node["computed_value"] = new_val
                    break

        return {
            "action": "propagation_result",
            "sourceNodeId": node_id,
            "changes": animation_changes,
            "totalAffected": len(changes),
        }

    def get_node(self, node_id: str) -> Optional[Dict]:
        """获取节点数据"""
        for node in self.nodes:
            if node["id"] == node_id:
                return node
        return None

    def get_propagation_animation_data(
        self,
        changes: Dict[str, tuple],
    ) -> List[Dict]:
        """
        构建传播动画数据

        Args:
            changes: 传播变化字典 {node_id: (old_value, new_value)}

        Returns:
            动画数据列表
        """
        animation_data = []
        for node_id, (old_val, new_val) in changes.items():
            node = self.get_node(node_id)
            animation_data.append({
                "nodeId": node_id,
                "oldValue": old_val,
                "newValue": new_val,
                "depth": node.get("depth", 0) if node else 0,
                "sheet": node.get("sheet", "") if node else "",
            })
        return animation_data


def render_propagation_result(
    component: D3GraphComponent,
    changes: Dict[str, tuple],
    source_node_id: str,
) -> str:
    """
    渲染传播结果动画HTML

    Args:
        component: D3图谱组件实例
        changes: 传播变化
        source_node_id: 源节点ID

    Returns:
        包含动画触发脚本的HTML
    """
    animation_data = component.get_propagation_animation_data(changes)

    # 构建触发动画的HTML
    trigger_script = f"""
    <script>
        // 触发传播动画
        if (window.receivePropagationResult) {{
            window.receivePropagationResult({
                changes: {json.dumps(animation_data, ensure_ascii=False)},
                sourceNodeId: '{source_node_id}'
            });
        }}
    </script>
    """

    return trigger_script