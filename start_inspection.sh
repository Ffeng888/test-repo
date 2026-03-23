#!/bin/bash
# 网络设施智能巡检系统 - 一键启动脚本
# 作者：封科全
# 使用：./start_inspection.sh

set -e  # 遇到错误立即退出

echo "=================================="
echo "  网络设施智能巡检系统启动脚本"
echo "=================================="
echo ""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查ROS2环境
if [ -z "$ROS_DISTRO" ]; then
    echo -e "${YELLOW}[INFO] 正在激活ROS2环境...${NC}"
    source /opt/ros/foxy/setup.bash
fi

# 检查工作空间
if [ ! -d "$HOME/inspection_system" ]; then
    echo -e "${RED}[ERROR] 未找到工作目录 ~/inspection_system${NC}"
    echo "请先克隆代码仓库并编译"
    exit 1
fi

cd ~/inspection_system
source install/setup.bash

echo -e "${GREEN}[OK] ROS2环境已激活${NC}"

# 检查模型文件
MODEL_PATH="$HOME/inspection_system/models/best.pt"
if [ ! -f "$MODEL_PATH" ]; then
    echo -e "${YELLOW}[WARN] 未找到模型文件: $MODEL_PATH${NC}"
    echo "请先将训练好的模型复制到该路径"
    echo "继续启动？(y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi

# 启动函数
start_camera() {
    echo -e "${YELLOW}[1/3] 正在启动RealSense相机...${NC}"
    ros2 launch realsense2_camera rs_launch.py \
        depth_module.profile:=640x480x30 \
        rgb_camera.profile:=640x480x30 \
        align_depth.enable:=true &
    CAMERA_PID=$!
    sleep 5
    
    # 检查相机是否启动成功
    if ros2 topic list | grep -q "/camera/color/image_raw"; then
        echo -e "${GREEN}[OK] 相机启动成功${NC}"
    else
        echo -e "${RED}[ERROR] 相机启动失败，请检查连接${NC}"
        exit 1
    fi
}

start_detection() {
    echo -e "${YELLOW}[2/3] 正在启动YOLO检测节点...${NC}"
    ros2 launch inspection_perception perception.launch.py &
    DETECTION_PID=$!
    sleep 3
    
    if ros2 node list | grep -q "yolo_detector"; then
        echo -e "${GREEN}[OK] 检测节点启动成功${NC}"
    else
        echo -e "${RED}[ERROR] 检测节点启动失败${NC}"
        exit 1
    fi
}

start_web() {
    echo -e "${YELLOW}[3/3] 正在启动Web服务器...${NC}"
    ros2 launch inspection_viz web_server.launch.py &
    WEB_PID=$!
    sleep 2
    
    # 获取IP地址
    IP=$(hostname -I | awk '{print $1}')
    echo -e "${GREEN}[OK] Web服务器启动成功${NC}"
    echo ""
    echo -e "${GREEN}==================================${NC}"
    echo -e "${GREEN}  系统启动完成！${NC}"
    echo -e "${GREEN}==================================${NC}"
    echo ""
    echo "访问可视化界面:"
    echo -e "  ${YELLOW}http://${IP}:5000${NC}"
    echo ""
    echo "查看ROS话题:"
    echo "  ros2 topic list"
    echo ""
    echo "查看检测节点日志:"
    echo "  ros2 node info /yolo_detector"
    echo ""
    echo "按 Ctrl+C 停止所有服务"
    echo ""
}

# 启动所有服务
start_camera
start_detection
start_web

# 等待用户中断
trap 'echo -e "\n${YELLOW}正在停止所有服务...${NC}"; kill $CAMERA_PID $DETECTION_PID $WEB_PID 2>/dev/null; exit 0' INT

wait