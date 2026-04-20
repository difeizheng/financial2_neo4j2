/**
 * 值传播动画模块 - 实现波浪式传播可视化
 */

// 传播动画状态
let propagationState = {
    active: false,
    changes: [],
    currentIndex: 0,
    animationInterval: null
};

// 传播颜色配置
const propagationColors = {
    source: '#FF5722',      // 源节点 - 橙红色
    affected: '#E91E63',    // 受影响节点 - 粉红色
    wave: '#4CAF50',        // 传播波 - 绿色
    original: null          // 原始颜色（恢复用）
};

/**
 * 执行传播动画
 * @param {Array} changes - 变化列表 [{nodeId, oldValue, newValue, depth}]
 * @param {string} sourceNodeId - 源节点ID
 */
function executePropagationAnimation(changes, sourceNodeId) {
    try {
        console.log('=== executePropagationAnimation开始 ===');
        console.log('changes数量:', changes ? changes.length : 0);
        console.log('sourceNodeId:', sourceNodeId);

        // 检查全局变量
        console.log('检查graphData:', typeof graphData);
        if (graphData && graphData.nodes) {
            console.log('graphData.nodes数量:', graphData.nodes.length);
        } else {
            console.error('graphData或nodes未定义');
            return;
        }

        console.log('检查nodeElements:', typeof nodeElements);
        if (!nodeElements) {
            console.error('nodeElements未定义');
            return;
        }

        if (propagationState.active) {
            console.log('停止之前的动画');
            stopPropagationAnimation();
        }

        propagationState.active = true;
        propagationState.currentIndex = 0;
        propagationState.lastChanges = changes;
        propagationState.lastSourceNodeId = sourceNodeId;

        // 按深度排序变化
        console.log('开始排序变化...');
        const sortedChanges = sortChangesByDepth(changes);
        propagationState.changes = sortedChanges;
        console.log('排序完成，数量:', sortedChanges.length);

        // 高亮源节点
        console.log('高亮源节点:', sourceNodeId);
        highlightSourceNode(sourceNodeId);

        // 开始波浪式传播
        console.log('开始波浪动画');
        startWaveAnimation();

        console.log('=== executePropagationAnimation完成 ===');
    } catch (error) {
        console.error('executePropagationAnimation错误:', error);
        console.error('错误堆栈:', error.stack);
    }
}

/**
 * 按深度排序变化（使用Python BFS计算的相对深度，不覆盖为绝对深度）
 */
function sortChangesByDepth(changes) {
    try {
        console.log('sortChangesByDepth开始, 输入数量:', changes.length);
        const result = [...changes].sort((a, b) => (a.depth || 0) - (b.depth || 0));
        console.log('sortChangesByDepth完成, 输出数量:', result.length);
        return result;
    } catch (error) {
        console.error('sortChangesByDepth错误:', error);
        return changes;
    }
}

/**
 * 高亮源节点
 */
function highlightSourceNode(nodeId) {
    console.log('highlightSourceNode调用, nodeId:', nodeId);

    const nodeGroup = nodeElements.filter(d => d.id === nodeId);
    console.log('找到节点数量:', nodeGroup.size());

    if (nodeGroup.empty()) {
        console.warn('源节点不在当前显示的节点中:', nodeId);
        // 尝试查找节点数据
        const nodeData = graphData.nodes.find(n => n.id === nodeId);
        console.log('节点数据存在:', nodeData ? '是' : '否');
        return;
    }

    nodeGroup.select('circle')
        .transition()
        .duration(300)
        .attr('r', 20)
        .attr('fill', propagationColors.source)
        .attr('stroke', '#FFF')
        .attr('stroke-width', 4);

    // 添加源节点标签
    nodeGroup.append('text')
        .attr('class', 'source-label')
        .attr('dy', -25)
        .attr('text-anchor', 'middle')
        .attr('fill', propagationColors.source)
        .attr('font-size', 12)
        .attr('font-weight', 'bold')
        .text('起点');

    console.log('源节点高亮完成');

    // 存储原始颜色
    const node = graphData.nodes.find(n => n.id === nodeId);
    if (node) {
        propagationColors.original = getSheetColor(node.sheet);
    }
}

/**
 * 开始波浪式传播动画
 */
function startWaveAnimation() {
    console.log('startWaveAnimation开始');

    const depthGroups = groupByDepth(propagationState.changes);
    const depths = Object.keys(depthGroups).sort((a, b) => a - b);

    console.log('深度分组:', depths);
    console.log('各深度节点数:', depths.map(d => d + ':' + depthGroups[d].length));

    if (depths.length === 0) {
        console.warn('无深度分组数据，动画结束');
        return;
    }

    let depthIndex = 0;

    propagationState.animationInterval = setInterval(() => {
        try {
            console.log('动画帧:', depthIndex, '/', depths.length);

            if (depthIndex >= depths.length) {
                console.log('动画完成');
                finishPropagationAnimation();
                return;
            }

            const currentDepth = depths[depthIndex];
            const nodesAtDepth = depthGroups[currentDepth];

            console.log('处理深度', currentDepth, '节点数:', nodesAtDepth.length);

            // 同时高亮同一深度的所有节点
            animateNodesAtDepth(nodesAtDepth, parseInt(currentDepth));

            // 高亮相关边
            highlightPropagationEdges(nodesAtDepth);

            // 显示进度
            updatePropagationProgress(depthIndex + 1, depths.length);

            depthIndex++;
        } catch (error) {
            console.error('动画帧错误:', error);
            finishPropagationAnimation();
        }
    }, 500); // 每层500ms

    console.log('动画interval已启动');
}

/**
 * 按深度分组
 */
function groupByDepth(changes) {
    const groups = {};
    changes.forEach(change => {
        const depth = change.depth;
        if (!groups[depth]) {
            groups[depth] = [];
        }
        groups[depth].push(change);
    });
    return groups;
}

/**
 * 动画显示特定深度的节点
 */
function animateNodesAtDepth(changes, depth) {
    changes.forEach(change => {
        const nodeGroup = nodeElements.filter(d => d.id === change.nodeId);

        if (nodeGroup.empty()) return;

        // 节点放大并变色
        nodeGroup.select('circle')
            .transition()
            .duration(300)
            .attr('r', d => Math.max(8, Math.min(18, 5 + d.out_degree * 0.5)))
            .attr('fill', propagationColors.affected)
            .attr('stroke', propagationColors.wave)
            .attr('stroke-width', 3);

        // 添加值变化标签
        const valueChange = change.newValue - change.oldValue;
        const changeText = valueChange >= 0 ? `+${formatChange(valueChange)}` : formatChange(valueChange);

        // 移除旧标签
        nodeGroup.selectAll('.change-label').remove();

        // 添加新标签
        nodeGroup.append('text')
            .attr('class', 'change-label')
            .attr('dy', -20)
            .attr('text-anchor', 'middle')
            .attr('fill', valueChange >= 0 ? '#4CAF50' : '#F44336')
            .attr('font-size', 10)
            .attr('font-weight', 'bold')
            .text(changeText);

        // 更新节点数据
        const node = graphData.nodes.find(n => n.id === change.nodeId);
        if (node) {
            node.value = change.newValue;
            node.computed_value = change.newValue;
        }
    });

    // 显示深度层提示
    showToast(`传播到深度 ${depth} 层 (${changes.length} 个节点)`);
}

/**
 * 高亮传播路径的边
 */
function highlightPropagationEdges(changes) {
    if (!edgeElements) {
        console.warn('edgeElements未定义，跳过边高亮');
        return;
    }

    try {
        const affectedIds = changes.map(c => c.nodeId);

        edgeElements
            .transition()
            .duration(200)
            .attr('stroke', d => {
                const targetId = typeof d.target === 'object' ? d.target.id : d.target;
                const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
                if (affectedIds.includes(targetId) || affectedIds.includes(sourceId)) {
                    return propagationColors.wave;
                }
                return d.is_cross_sheet ? '#E91E63' : '#BDBDBD';
            })
            .attr('stroke-width', d => {
                const targetId = typeof d.target === 'object' ? d.target.id : d.target;
                const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
                if (affectedIds.includes(targetId) || affectedIds.includes(sourceId)) {
                    return 2;
                }
                return 0.5;
            })
            .attr('opacity', d => {
                const targetId = typeof d.target === 'object' ? d.target.id : d.target;
                const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
                if (affectedIds.includes(targetId) || affectedIds.includes(sourceId)) {
                    return 1;
                }
                return 0.3;
            });
    } catch (error) {
        console.error('highlightPropagationEdges错误:', error);
    }
}

/**
 * 格式化变化值
 */
function formatChange(value) {
    if (Math.abs(value) < 0.01) return value.toFixed(4);
    if (Math.abs(value) < 1) return value.toFixed(2);
    return Math.round(value);
}

/**
 * 更新传播进度
 */
function updatePropagationProgress(current, total) {
    const progressBar = document.getElementById('propagation-progress-bar');
    const progressText = document.getElementById('propagation-progress-text');

    if (progressBar) {
        progressBar.style.width = `${(current / total) * 100}%`;
    }
    if (progressText) {
        progressText.textContent = `传播进度: ${current}/${total} 层`;
    }
}

/**
 * 完成传播动画
 */
function finishPropagationAnimation() {
    clearInterval(propagationState.animationInterval);
    propagationState.active = false;

    // 显示完成提示
    showToast(`传播完成！共更新 ${propagationState.changes.length} 个节点`);

    // 更新统计
    updateStats();

    // 延迟恢复节点颜色
    setTimeout(() => {
        restoreNodeColors();
    }, 2000);
}

/**
 * 停止传播动画
 */
function stopPropagationAnimation() {
    if (propagationState.animationInterval) {
        clearInterval(propagationState.animationInterval);
    }
    propagationState.active = false;
    restoreNodeColors();
}

/**
 * 恢复节点原始颜色
 */
function restoreNodeColors() {
    if (!nodeElements || !edgeElements) return;

    // 移除所有动画标签
    nodeElements.selectAll('.change-label').remove();
    nodeElements.selectAll('.source-label').remove();

    // 恢复节点样式
    nodeElements.select('circle')
        .transition()
        .duration(500)
        .attr('r', d => Math.max(5, Math.min(15, 3 + d.out_degree * 0.5)))
        .attr('fill', d => getSheetColor(d.sheet))
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5);

    // 恢复边样式
    edgeElements
        .transition()
        .duration(500)
        .attr('stroke', d => {
            const isCross = typeof d.is_cross_sheet !== 'undefined' ? d.is_cross_sheet : false;
            return isCross ? '#E91E63' : '#BDBDBD';
        })
        .attr('stroke-width', 0.5)
        .attr('opacity', 0.6);

    // 重置进度条
    const progressBar = document.getElementById('propagation-progress-bar');
    if (progressBar) {
        progressBar.style.width = '0%';
    }
}

/**
 * 获取传播历史
 */
function getPropagationHistory() {
    return propagationState.changes.map(change => ({
        nodeId: change.nodeId,
        oldValue: change.oldValue,
        newValue: change.newValue,
        depth: change.depth
    }));
}

/**
 * 重播传播动画（使用上次的数据）
 */
function replayPropagationAnimation() {
    if (!propagationState.lastChanges || !propagationState.lastSourceNodeId) {
        showToast('暂无可重播的动画数据');
        return;
    }
    // 先恢复节点颜色，再重新播放
    restoreNodeColors();
    setTimeout(() => {
        executePropagationAnimation(propagationState.lastChanges, propagationState.lastSourceNodeId);
    }, 600);
}

// 导出函数
window.executePropagationAnimation = executePropagationAnimation;
window.stopPropagationAnimation = stopPropagationAnimation;
window.getPropagationHistory = getPropagationHistory;
window.replayPropagationAnimation = replayPropagationAnimation;

// 确认模块加载
console.log('propagation.js已加载，executePropagationAnimation已导出:', typeof window.executePropagationAnimation);