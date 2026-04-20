/**
 * 财务模型知识图谱 D3.js 可视化
 */

// 全局状态
let graphData = { nodes: [], edges: [] };
let simulation = null;
let svg = null;
let nodeElements = null;
let edgeElements = null;
let selectedNode = null;
let currentSheet = null;
let _graphInitialized = false;

// Sheet颜色映射
const sheetColors = {
    '参数输入表': '#4CAF50',
    '表3-成本费用表': '#2196F3',
    '表4-收入税金表': '#FF9800',
    '表5-利润表-资本金': '#9C27B0',
    'default': '#607D8B'
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initGraph();
    setupControls();
    setupStreamlitCommunication();
});

/**
 * 初始化图谱
 */
function initGraph() {
    if (_graphInitialized) return;
    _graphInitialized = true;

    const container = document.getElementById('graph-container');
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;

    svg = d3.select('#graph-svg')
        .attr('width', width)
        .attr('height', height);

    // 主容器 - 必须在zoom之前定义
    const g = svg.append('g').attr('id', 'main-group');

    // 添加缩放功能
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });

    svg.call(zoom);

    // 保存g到全局变量供其他函数使用
    window.graphMainGroup = g;

    // 等待数据加载
    window.streamlitReceiveData = (data) => {
        console.log('streamlitReceiveData被调用');
        console.log('接收数据:', data.nodes ? data.nodes.length : 0, '个节点');

        graphData = {
            nodes: data.nodes || [],
            edges: data.edges || []
        };

        console.log('开始渲染图谱...');
        renderGraph(width, height);
        updateStats();
        populateFilters();

        console.log('图谱渲染完成');
        console.log('nodeElements状态:', nodeElements ? '已定义' : '未定义');
    };
}

/**
 * 渲染力导向图
 */
function renderGraph(width, height) {
    const g = svg.select('#main-group');
    g.selectAll('*').remove();

    // 限制显示节点数（性能优化）
    let displayNodes = graphData.nodes;
    let displayEdges = graphData.edges;

    if (graphData.nodes.length > 2000) {
        // 取输入节点和部分公式节点
        const inputNodes = graphData.nodes.filter(n => n.depth === 0);
        const formulaNodes = graphData.nodes.filter(n => n.depth > 0).slice(0, 500);
        displayNodes = [...inputNodes, ...formulaNodes];
        displayEdges = graphData.edges.filter(e =>
            displayNodes.some(n => n.id === e.source) &&
            displayNodes.some(n => n.id === e.target)
        );
    }

    // 创建节点索引
    const nodeMap = {};
    displayNodes.forEach(n => nodeMap[n.id] = n);

    // 创建力模拟
    simulation = d3.forceSimulation(displayNodes)
        .force('link', d3.forceLink(displayEdges)
            .id(d => d.id)
            .distance(50)
            .strength(0.5))
        .force('charge', d3.forceManyBody()
            .strength(-100))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(20));

    // 绘制边
    edgeElements = g.append('g')
        .attr('class', 'edges')
        .selectAll('line')
        .data(displayEdges)
        .enter()
        .append('line')
        .attr('class', d => d.is_cross_sheet ? 'edge cross-sheet' : 'edge')
        .attr('stroke', d => d.is_cross_sheet ? '#E91E63' : '#BDBDBD')
        .attr('stroke-width', 0.5)
        .attr('opacity', 0.6);

    // 绘制节点
    nodeElements = g.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(displayNodes)
        .enter()
        .append('g')
        .attr('class', 'node-group')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded));

    // 节点圆圈
    nodeElements.append('circle')
        .attr('class', 'node')
        .attr('r', d => Math.max(5, Math.min(15, 3 + d.out_degree * 0.5)))
        .attr('fill', d => getSheetColor(d.sheet))
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
        .on('click', (event, d) => selectNode(d))
        .on('mouseover', (event, d) => highlightNode(d))
        .on('mouseout', (event, d) => unhighlightNode(d));

    // 节点标签（可选）
    nodeElements.append('text')
        .attr('class', 'node-label')
        .attr('dx', 12)
        .attr('dy', 4)
        .text(d => d.id.split('_').slice(-2).join('_'))
        .attr('font-size', 8)
        .attr('fill', '#333');

    // 运行模拟
    simulation.on('tick', () => {
        edgeElements
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        nodeElements
            .attr('transform', d => `translate(${d.x},${d.y})`);
    });
}

/**
 * 获取Sheet颜色
 */
function getSheetColor(sheet) {
    return sheetColors[sheet] || sheetColors['default'];
}

/**
 * 选中节点
 */
function selectNode(node) {
    selectedNode = node;

    // 高亮选中节点
    nodeElements.selectAll('circle')
        .attr('stroke-width', d => d.id === node.id ? 3 : 1.5)
        .attr('stroke', d => d.id === node.id ? '#FF5722' : '#fff');

    // 显示详情面板
    showDetailPanel(node);
    updateStats();
}

/**
 * 高亮节点及其依赖链
 */
function highlightNode(node) {
    // 找到上下游节点
    const upstream = getUpstream(node.id);
    const downstream = getDownstream(node.id);

    // 高亮相关边
    edgeElements
        .attr('stroke-width', d => {
            if (d.target.id === node.id || d.source.id === node.id) return 2;
            return 0.5;
        })
        .attr('opacity', d => {
            if (d.target.id === node.id || d.source.id === node.id) return 1;
            return 0.3;
        });

    // 高亮相关节点
    nodeElements.selectAll('circle')
        .attr('opacity', d => {
            if (d.id === node.id) return 1;
            if (upstream.includes(d.id) || downstream.includes(d.id)) return 0.9;
            return 0.5;
        });
}

/**
 * 取消高亮
 */
function unhighlightNode(node) {
    if (selectedNode && selectedNode.id === node.id) return;

    edgeElements
        .attr('stroke-width', 0.5)
        .attr('opacity', 0.6);

    nodeElements.selectAll('circle')
        .attr('opacity', 1);
}

/**
 * 获取上游节点
 */
function getUpstream(nodeId) {
    const upstream = [];
    graphData.edges.forEach(e => {
        if (e.target === nodeId) upstream.push(e.source);
    });
    return upstream;
}

/**
 * 获取下游节点
 */
function getDownstream(nodeId) {
    const downstream = [];
    graphData.edges.forEach(e => {
        if (e.source === nodeId) downstream.push(e.target);
    });
    return downstream;
}

/**
 * 显示详情面板
 */
function showDetailPanel(node) {
    const panel = document.getElementById('detail-panel');
    panel.classList.remove('hidden');

    // 填充节点信息
    const infoHtml = `
        <div class="info-row"><strong>ID:</strong> ${node.id}</div>
        <div class="info-row"><strong>Sheet:</strong> ${node.sheet}</div>
        <div class="info-row"><strong>位置:</strong> ${node.col}${node.row}</div>
        <div class="info-row"><strong>值:</strong> ${formatValue(node.value)}</div>
        <div class="info-row"><strong>公式:</strong> ${node.formula_raw || '无'}</div>
        <div class="info-row"><strong>深度:</strong> ${node.depth}</div>
        <div class="info-row"><strong>入度:</strong> ${node.in_degree}</div>
        <div class="info-row"><strong>出度:</strong> ${node.out_degree}</div>
    `;
    document.getElementById('node-info').innerHTML = infoHtml;

    // 填充依赖关系
    const upstream = getUpstream(node.id);
    const downstream = getDownstream(node.id);

    document.getElementById('upstream-list').innerHTML = upstream.length > 0
        ? `<strong>上游 (${upstream.length}):</strong> ${upstream.slice(0, 10).join(', ')}${upstream.length > 10 ? '...' : ''}`
        : '无上游依赖';

    document.getElementById('downstream-list').innerHTML = downstream.length > 0
        ? `<strong>下游 (${downstream.length}):</strong> ${downstream.slice(0, 10).join(', ')}${downstream.length > 10 ? '...' : ''}`
        : '无下游依赖';

    // 值修改区域（仅输入节点可修改）
    const valueModifyDiv = document.getElementById('value-modify');
    if (node.depth === 0 && node.is_input) {
        valueModifyDiv.classList.remove('hidden');
        document.getElementById('new-value-input').value = node.value || '';
    } else {
        valueModifyDiv.classList.add('hidden');
    }
}

/**
 * 格式化值显示
 */
function formatValue(value) {
    if (value === null || value === undefined) return '空';
    if (typeof value === 'number') {
        if (Number.isInteger(value)) return value;
        return value.toFixed(4);
    }
    return String(value).substring(0, 50);
}

/**
 * 关闭详情面板
 */
document.getElementById('close-panel')?.addEventListener('click', () => {
    document.getElementById('detail-panel').classList.add('hidden');
    selectedNode = null;
    updateStats();
});

/**
 * 应用新值并传播
 */
document.getElementById('apply-value-btn')?.addEventListener('click', () => {
    if (!selectedNode) return;

    const newValue = parseFloat(document.getElementById('new-value-input').value);
    if (isNaN(newValue)) {
        alert('请输入有效数值');
        return;
    }

    // 发送传播请求到Streamlit
    sendPropagationRequest(selectedNode.id, newValue);
});

/**
 * 拖拽函数
 */
function dragStarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragEnded(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

/**
 * 控制面板设置
 */
function setupControls() {
    // 搜索
    document.getElementById('search-btn')?.addEventListener('click', () => {
        const term = document.getElementById('search-input').value.toLowerCase();
        searchNode(term);
    });

    document.getElementById('search-input')?.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
            const term = e.target.value.toLowerCase();
            searchNode(term);
        }
    });

    // Sheet过滤
    document.getElementById('sheet-filter')?.addEventListener('change', (e) => {
        filterBySheet(e.target.value);
    });

    // 重置
    document.getElementById('reset-btn')?.addEventListener('click', () => {
        resetView();
    });
}

/**
 * 搜索节点
 */
function searchNode(term) {
    const found = graphData.nodes.find(n =>
        n.id.toLowerCase().includes(term) ||
        String(n.value).toLowerCase().includes(term)
    );

    if (found) {
        selectNode(found);

        // 移动视图到该节点
        const transform = d3.zoomIdentity
            .translate(400 - found.x, 300 - found.y)
            .scale(1.5);

        svg.transition()
            .duration(500)
            .call(d3.zoom().transform, transform);
    } else {
        showToast('未找到匹配节点');
    }
}

/**
 * Sheet过滤
 */
function filterBySheet(sheet) {
    nodeElements.selectAll('circle')
        .attr('opacity', d => {
            if (sheet === 'all') return 1;
            return d.sheet === sheet ? 1 : 0.1;
        });

    edgeElements
        .attr('opacity', d => {
            if (sheet === 'all') return 0.6;
            const sourceNode = graphData.nodes.find(n => n.id === d.source);
            const targetNode = graphData.nodes.find(n => n.id === d.target);
            return (sourceNode?.sheet === sheet || targetNode?.sheet === sheet) ? 0.6 : 0.1;
        });
}

/**
 * 重置视图
 */
function resetView() {
    svg.transition()
        .duration(500)
        .call(d3.zoom().transform, d3.zoomIdentity);

    nodeElements.selectAll('circle')
        .attr('opacity', 1)
        .attr('stroke-width', 1.5)
        .attr('stroke', '#fff');

    edgeElements
        .attr('opacity', 0.6)
        .attr('stroke-width', 0.5);

    document.getElementById('detail-panel').classList.add('hidden');
    selectedNode = null;
    updateStats();
}

/**
 * 填充过滤选项
 */
function populateFilters() {
    const sheets = [...new Set(graphData.nodes.map(n => n.sheet))];
    const select = document.getElementById('sheet-filter');

    sheets.forEach(sheet => {
        const option = document.createElement('option');
        option.value = sheet;
        option.textContent = sheet;
        select.appendChild(option);
    });
}

/**
 * 更新统计信息
 */
function updateStats() {
    document.getElementById('node-count').textContent = `节点: ${graphData.nodes.length}`;
    document.getElementById('edge-count').textContent = `边: ${graphData.edges.length}`;
    document.getElementById('selected-node').textContent = selectedNode
        ? `选中: ${selectedNode.id}`
        : '选中: 无';
}

/**
 * 显示提示
 */
function showToast(message) {
    const toast = document.getElementById('propagation-toast');
    document.getElementById('propagation-message').textContent = message;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

/**
 * Streamlit通信
 */
function setupStreamlitCommunication() {
    // 发送数据请求
    window.parent.postMessage({
        type: 'streamlit:componentReady',
        data: { ready: true }
    }, '*');
}

function sendPropagationRequest(nodeId, newValue) {
    window.parent.postMessage({
        type: 'streamlit:setComponentValue',
        data: {
            action: 'propagate',
            nodeId: nodeId,
            newValue: newValue
        }
    }, '*');

    showToast(`正在传播 ${nodeId} 的新值: ${newValue}`);
}

/**
 * 接收传播结果并执行动画
 */
window.receivePropagationResult = (data) => {
    console.log('receivePropagationResult被调用, data:', data);

    const { changes, sourceNodeId } = data;

    if (!changes || changes.length === 0) {
        console.error('没有变化数据');
        return;
    }

    console.log('变化节点数:', changes.length, '源节点:', sourceNodeId);

    // 显示传播面板
    const panel = document.getElementById('propagation-panel');
    if (panel) {
        panel.classList.remove('hidden');
    }

    const sourceNameEl = document.getElementById('source-node-name');
    if (sourceNameEl) {
        sourceNameEl.textContent = sourceNodeId;
    }

    const affectedCountEl = document.getElementById('affected-count');
    if (affectedCountEl) {
        affectedCountEl.textContent = changes.length;
    }

    // 执行传播动画
    console.log('检查executePropagationAnimation:', typeof window.executePropagationAnimation);

    if (window.executePropagationAnimation) {
        console.log('调用executePropagationAnimation...');
        window.executePropagationAnimation(changes, sourceNodeId);
    } else {
        console.error('executePropagationAnimation函数未定义');
    }

    const message = `开始传播动画，共 ${changes.length} 个节点`;
    console.log(message);

    if (typeof showToast === 'function') {
        showToast(message);
    }
};

/**
 * 停止传播按钮
 */
document.getElementById('stop-propagation-btn')?.addEventListener('click', () => {
    if (window.stopPropagationAnimation) {
        window.stopPropagationAnimation();
    }
    document.getElementById('propagation-panel').classList.add('hidden');
});

/**
 * 重播传播动画按钮
 */
document.getElementById('replay-propagation-btn')?.addEventListener('click', () => {
    if (window.replayPropagationAnimation) {
        window.replayPropagationAnimation();
    }
});

/**
 * 全屏按钮
 */
document.getElementById('fullscreen-btn')?.addEventListener('click', () => {
    const container = document.getElementById('container');
    const btn = document.getElementById('fullscreen-btn');
    if (container.classList.contains('fullscreen')) {
        container.classList.remove('fullscreen');
        btn.title = '全屏';
        btn.textContent = '⛶';
    } else {
        container.classList.add('fullscreen');
        btn.title = '退出全屏';
        btn.textContent = '✕';
        // 重新适配SVG尺寸
        if (svg && simulation) {
            const w = container.clientWidth;
            const h = container.clientHeight - 80; // 减去控制栏和状态栏
            svg.attr('width', w).attr('height', h);
            simulation.force('center', d3.forceCenter(w / 2, h / 2)).alpha(0.3).restart();
        }
    }
});

/**
 * 导出变化详情按钮
 */
document.getElementById('export-changes-btn')?.addEventListener('click', () => {
    if (window.getPropagationHistory) {
        const history = window.getPropagationHistory();
        const csvContent = generateCSV(history);
        downloadCSV(csvContent, 'propagation_changes.csv');
    }
});

/**
 * 生成CSV内容
 */
function generateCSV(data) {
    const headers = ['NodeID', 'OldValue', 'NewValue', 'Change', 'Depth'];
    const rows = data.map(item => [
        item.nodeId,
        item.oldValue,
        item.newValue,
        item.newValue - item.oldValue,
        item.depth
    ]);

    return [headers, ...rows].map(row => row.join(',')).join('\n');
}

/**
 * 下载CSV文件
 */
function downloadCSV(content, filename) {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

// 确认模块加载
console.log('graph.js已加载');
console.log('graphData:', typeof graphData);
console.log('nodeElements:', typeof nodeElements);
console.log('receivePropagationResult已导出:', typeof window.receivePropagationResult);