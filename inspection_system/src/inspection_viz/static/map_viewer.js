/**
 * 网络设施巡检系统 - Web可视化控制器
 * 实时显示检测结果和统计信息
 */

// WebSocket连接
let ws = null;
let reconnectInterval = null;

// 统计数据
let stats = {
    switches: 0,
    ports: 0,
    total: 0,
    confidenceSum: 0,
    fps: 0,
    inferenceTime: 0,
    frameCount: 0
};

// 检测历史
let detectionHistory = [];
const MAX_HISTORY = 50;

/**
 * 初始化WebSocket连接
 */
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function() {
        console.log('WebSocket连接已建立');
        showNotification('系统连接成功', 'success');
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket错误:', error);
    };
    
    ws.onclose = function() {
        console.log('WebSocket连接已关闭，尝试重连...');
        showNotification('连接断开，正在重连...', 'warning');
        
        // 尝试重连
        if (!reconnectInterval) {
            reconnectInterval = setInterval(() => {
                initWebSocket();
            }, 3000);
        }
    };
}

/**
 * 处理收到的消息
 */
function handleMessage(data) {
    switch (data.type) {
        case 'detection':
            updateDetections(data.detections);
            updateStats(data.stats);
            break;
        case 'image':
            updateVideoFeed(data.image);
            break;
        case 'status':
            updateStatus(data.status);
            break;
    }
}

/**
 * 更新检测结果显示
 */
function updateDetections(detections) {
    const listElement = document.getElementById('detection-list');
    
    // 更新统计数据
    let switches = 0;
    let ports = 0;
    let confidenceSum = 0;
    
    detections.forEach(det => {
        if (det.class === 'switch') switches++;
        if (det.class === 'unplugged_port') ports++;
        confidenceSum += det.confidence;
    });
    
    stats.switches += switches;
    stats.ports += ports;
    stats.total += detections.length;
    stats.confidenceSum += confidenceSum;
    
    // 添加到历史记录
    detectionHistory.unshift({
        timestamp: new Date(),
        detections: detections
    });
    
    // 限制历史记录数量
    if (detectionHistory.length > MAX_HISTORY) {
        detectionHistory.pop();
    }
    
    // 更新UI
    updateStatsDisplay();
    
    // 生成检测项HTML
    if (detections.length === 0) {
        listElement.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #999;">
                <p>当前帧未检测到目标</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    detections.forEach((det, index) => {
        const isSwitch = det.class === 'switch';
        const icon = isSwitch ? '📦' : '🔌';
        const className = isSwitch ? 'switch' : 'port';
        const displayName = isSwitch ? '交换机' : '未插网口';
        const confidence = Math.round(det.confidence * 100);
        const confidenceClass = confidence > 80 ? 'confidence-high' : 'confidence-medium';
        
        html += `
            <div class="detection-item">
                <div class="detection-icon ${className}">${icon}</div>
                <div class="detection-info">
                    <h4>
                        ${displayName}
                        <span class="confidence-badge ${confidenceClass}">${confidence}%</span>
                    </h4>
                    <p>位置: (${Math.round(det.x)}, ${Math.round(det.y)}) | 大小: ${Math.round(det.width)}x${Math.round(det.height)}</p>
                </div>
            </div>
        `;
    });
    
    listElement.innerHTML = html;
}

/**
 * 更新统计显示
 */
function updateStatsDisplay() {
    document.getElementById('switch-count').textContent = stats.switches;
    document.getElementById('port-count').textContent = stats.ports;
    document.getElementById('total-count').textContent = stats.total;
    
    const avgConfidence = stats.total > 0 
        ? Math.round((stats.confidenceSum / stats.total) * 100) 
        : 0;
    document.getElementById('avg-confidence').textContent = avgConfidence + '%';
}

/**
 * 更新状态信息
 */
function updateStatus(status) {
    if (status.fps) {
        document.getElementById('fps').textContent = status.fps.toFixed(1);
    }
    if (status.inference_time) {
        document.getElementById('inference-time').textContent = status.inference_time.toFixed(1) + ' ms';
    }
    if (status.frame_count) {
        document.getElementById('frame-count').textContent = status.frame_count;
    }
}

/**
 * 更新视频画面
 */
function updateVideoFeed(imageData) {
    const img = document.getElementById('video-feed');
    img.src = 'data:image/jpeg;base64,' + imageData;
}

/**
 * 导出巡检报告
 */
function exportReport() {
    const report = {
        timestamp: new Date().toISOString(),
        summary: {
            total_detections: stats.total,
            switches_found: stats.switches,
            ports_found: stats.ports,
            avg_confidence: stats.total > 0 ? (stats.confidenceSum / stats.total).toFixed(2) : 0
        },
        detections: detectionHistory
    };
    
    // 转换为CSV格式
    let csv = '时间戳,类型,置信度,X坐标,Y坐标,宽度,高度\n';
    detectionHistory.forEach(entry => {
        entry.detections.forEach(det => {
            csv += `${entry.timestamp.toISOString()},${det.class},${det.confidence},${det.x},${det.y},${det.width},${det.height}\n`;
        });
    });
    
    // 下载文件
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    link.href = URL.createObjectURL(blob);
    link.download = `巡检报告_${timestamp}.csv`;
    link.click();
    
    showNotification('巡检报告已导出', 'success');
}

/**
 * 清空检测记录
 */
function clearDetections() {
    stats = {
        switches: 0,
        ports: 0,
        total: 0,
        confidenceSum: 0,
        fps: 0,
        inferenceTime: 0,
        frameCount: 0
    };
    detectionHistory = [];
    
    updateStatsDisplay();
    document.getElementById('detection-list').innerHTML = `
        <div style="text-align: center; padding: 40px; color: #999;">
            <p>等待检测结果...</p>
        </div>
    `;
    
    showNotification('检测记录已清空', 'info');
}

/**
 * 显示通知
 */
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 8px;
        color: white;
        font-weight: bold;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    // 根据类型设置颜色
    const colors = {
        success: '#28a745',
        warning: '#ffc107',
        error: '#dc3545',
        info: '#17a2b8'
    };
    notification.style.backgroundColor = colors[type] || colors.info;
    notification.textContent = message;
    
    // 添加动画样式
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(notification);
    
    // 3秒后自动移除
    setTimeout(() => {
        notification.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * 模拟数据（用于测试）
 */
function simulateData() {
    // 模拟检测结果
    const mockDetections = [
        {
            class: 'switch',
            confidence: 0.92,
            x: 320,
            y: 240,
            width: 120,
            height: 80
        },
        {
            class: 'unplugged_port',
            confidence: 0.87,
            x: 450,
            y: 300,
            width: 30,
            height: 20
        }
    ];
    
    handleMessage({
        type: 'detection',
        detections: mockDetections,
        stats: {}
    });
    
    handleMessage({
        type: 'status',
        status: {
            fps: 28.5,
            inference_time: 35.2,
            frame_count: 1523
        }
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 尝试连接WebSocket
    // initWebSocket();
    
    // 如果没有WebSocket，则使用模拟数据（测试用）
    console.log('使用模拟数据进行测试');
    setInterval(simulateData, 2000);
});

// 页面关闭时清理
window.addEventListener('beforeunload', function() {
    if (ws) {
        ws.close();
    }
    if (reconnectInterval) {
        clearInterval(reconnectInterval);
    }
});