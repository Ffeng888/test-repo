# 网络设施智能巡检系统 - 部署指南

## 📋 概述

本指南详细说明如何在宇树Go2四足机器人（配备Jetson Orin算力模组）上部署基于YOLOv8视觉感知与ROS2的智能化网络设施巡检系统。

**目标平台**：
- 机器人：宇树Go2 EDU
- 计算平台：NVIDIA Jetson Orin（机载）
- 深度相机：Intel RealSense D435i
- 操作系统：Ubuntu 20.04
- ROS版本：ROS2 Foxy

---

## 🚀 快速部署步骤

### 第一步：环境准备

在Go2的Jetson板卡上执行以下操作：

```bash
# 1. 创建工作目录
mkdir -p ~/inspection_system/src
cd ~/inspection_system/src

# 2. 克隆代码仓库
git clone https://github.com/Ffeng888/test-repo.git

# 3. 复制到ROS2工作空间
cp -r test-repo/inspection_system/src/* .
```

### 第二步：安装依赖

```bash
# 1. 安装ROS2依赖
cd ~/inspection_system
rosdep install --from-paths src --ignore-src -r -y

# 2. 安装Python依赖
pip3 install ultralytics flask flask-cors

# 3. 安装TensorRT（Jetson通常已预装）
# 检查TensorRT版本
dpkg -l | grep TensorRT
```

### 第三步：编译工作空间

```bash
cd ~/inspection_system
colcon build --symlink-install
source install/setup.bash
```

### 第四步：复制训练好的模型

从你的Windows电脑复制模型到Jetson：

```bash
# 在Windows上（PowerShell）
scp E:\port_segment\runs\segment\switch_port_seg_nano\weights\best.pt go2@<jetson_ip>:~/inspection_system/models/

# 或者使用WinSCP等工具手动复制
```

**目标路径**：`/home/go2/inspection_system/models/best.pt`

### 第五步：转换TensorRT引擎（可选但推荐）

```bash
# 1. 导出ONNX模型
cd ~/inspection_system/models
python3 -c "
from ultralytics import YOLO
model = YOLO('best.pt')
model.export(format='onnx', imgsz=640, simplify=True)
"

# 2. 转换为TensorRT引擎
/usr/src/tensorrt/bin/trtexec \
    --onnx=best.onnx \
    --saveEngine=best_nano_seg.engine \
    --fp16 \
    --workspace=2048
```

---

## 🎯 启动系统

### 方式一：快速启动（推荐用于中期检查）

```bash
# 1. SSH连接到Go2
ssh go2@<jetson_ip>

# 2. 激活ROS2环境
source /opt/ros/foxy/setup.bash
source ~/inspection_system/install/setup.bash

# 3. 启动相机节点（如果未运行）
ros2 launch realsense2_camera rs_launch.py \
    depth_module.profile:=640x480x30 \
    rgb_camera.profile:=640x480x30 \
    align_depth.enable:=true

# 4. 在新的终端窗口启动YOLO检测节点
ros2 launch inspection_perception perception.launch.py \
    model_path:=~/inspection_system/models/best.pt

# 5. 在新的终端窗口启动Web服务器
ros2 launch inspection_viz web_server.launch.py
```

### 方式二：一键启动脚本

创建启动脚本 `~/start_inspection.sh`：

```bash
#!/bin/bash

# 激活环境
source /opt/ros/foxy/setup.bash
source ~/inspection_system/install/setup.bash

# 启动相机
echo "启动RealSense相机..."
ros2 launch realsense2_camera rs_launch.py &
sleep 5

# 启动检测节点
echo "启动YOLO检测节点..."
ros2 launch inspection_perception perception.launch.py &
sleep 3

# 启动Web服务器
echo "启动Web服务器..."
ros2 launch inspection_viz web_server.launch.py &
sleep 2

echo "系统启动完成！"
echo "访问 http://$(hostname -I | awk '{print $1}'):5000 查看可视化界面"
```

赋予执行权限并运行：
```bash
chmod +x ~/start_inspection.sh
~/start_inspection.sh
```

---

## 📊 访问可视化界面

系统启动后，在浏览器中访问：

```
http://<jetson_ip>:5000
```

**示例**：`http://192.168.1.100:5000`

界面功能：
- 实时显示检测画面
- 显示检测统计信息
- 导出巡检报告（CSV格式）

---

## 🎥 录制演示视频

### 方法1：使用rqt_image_view录制

```bash
# 安装rqt工具
sudo apt install ros-foxy-rqt-image-view

# 运行图像查看器
ros2 run rqt_image_view rqt_image_view
# 选择话题: /detections/visualization

# 使用录屏软件录制（如OBS Studio）
```

### 方法2：使用rosbag记录

```bash
# 录制话题数据
ros2 bag record /detections/visualization /camera/color/image_raw -o inspection_demo

# 之后可以回放
ros2 bag play inspection_demo
```

### 方法3：保存视频文件

创建脚本 `~/record_video.py`：

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class VideoRecorder(Node):
    def __init__(self):
        super().__init__('video_recorder')
        self.bridge = CvBridge()
        self.sub = self.create_subscription(
            Image, '/detections/visualization', self.callback, 10)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(
            'inspection_demo.mp4', fourcc, 30.0, (640, 480))
        
    def callback(self, msg):
        img = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        self.writer.write(img)
        
    def destroy_node(self):
        self.writer.release()
        super().destroy_node()

rclpy.init()
node = VideoRecorder()
try:
    rclpy.spin(node)
except KeyboardInterrupt:
    pass
finally:
    node.destroy_node()
    rclpy.shutdown()
```

运行：
```bash
python3 ~/record_video.py
# 录制完成后按Ctrl+C停止
```

---

## 🔧 常见问题解决

### 问题1：相机无法启动

**症状**：`ros2 launch realsense2_camera rs_launch.py` 报错

**解决**：
```bash
# 检查相机连接
lsusb | grep Intel

# 重置相机
ros2 run realsense2_camera list_cameras

# 检查权限
sudo usermod -aG video $USER
# 重新登录后生效
```

### 问题2：YOLO模型加载失败

**症状**：`ModuleNotFoundError: No module named 'ultralytics'`

**解决**：
```bash
pip3 install ultralytics --upgrade

# 如果CUDA版本不匹配，安装CPU版本
pip3 install ultralytics --extra-index-url https://download.pytorch.org/whl/cpu
```

### 问题3：TensorRT转换失败

**症状**：`trtexec: command not found`

**解决**：
```bash
# 检查TensorRT安装路径
ls /usr/src/tensorrt/bin/

# 添加到环境变量
echo 'export PATH=$PATH:/usr/src/tensorrt/bin' >> ~/.bashrc
source ~/.bashrc
```

### 问题4：Web界面无法访问

**症状**：浏览器显示"无法访问此网站"

**解决**：
```bash
# 检查防火墙
sudo ufw allow 5000

# 检查服务是否运行
ros2 node list | grep web_server

# 手动指定IP启动
ros2 launch inspection_viz web_server.launch.py host:=0.0.0.0
```

### 问题5：SSH连接断开

**症状**：连接不稳定，经常断开

**解决**：
```bash
# 修改SSH配置
sudo nano /etc/ssh/sshd_config

# 添加以下行
ClientAliveInterval 60
ClientAliveCountMax 3

# 重启SSH服务
sudo systemctl restart sshd
```

---

## 📈 性能优化建议

### 1. TensorRT加速

已完成的模型可以使用TensorRT加速推理：
```bash
# 在launch文件中指定引擎文件
ros2 launch inspection_perception perception.launch.py \
    model_path:=~/inspection_system/models/best_nano_seg.engine
```

### 2. 降低分辨率

如果FPS太低，可以降低输入分辨率：
```bash
ros2 launch inspection_perception perception.launch.py \
    inference_size:=320
```

### 3. 使用量化模型

```bash
# INT8量化（需要校准数据集）
/usr/src/tensorrt/bin/trtexec \
    --onnx=best.onnx \
    --saveEngine=best_int8.engine \
    --int8 \
    --workspace=2048
```

---

## 📝 中期检查准备清单

### 必做事项

- [ ] 代码已部署到Go2并可以运行
- [ ] 实时检测画面可以正常显示
- [ ] 已录制2-3分钟演示视频
- [ ] Web界面可以访问
- [ ] PPT已完成（15-20页）

### PPT建议内容

1. **封面** - 课题名称、姓名、学号、导师
2. **研究背景** - 物理安全的重要性
3. **技术方案** - 系统架构图
4. **已完成工作** - 数据集、模型训练结果
5. **演示视频** - 实际检测效果
6. **遇到的问题** - 建图问题及解决思路
7. **后续计划** - 甘特图展示

### 展示建议

1. **现场演示**（2分钟）
   - 打开Web界面
   - 展示实时检测效果
   - 说明检测到的设备类型

2. **视频展示**（1-2分钟）
   - 播放预先录制的演示视频
   - 展示Go2行走+检测的全过程

3. **PPT汇报**（10分钟）
   - 重点讲已完成的技术工作
   - 展示训练过程和结果

---

## 📞 技术支持

如遇问题，请检查：

1. **日志文件**：`~/.ros/log/`
2. **ROS话题列表**：`ros2 topic list`
3. **节点状态**：`ros2 node list`

---

## 📚 相关资源

- [YOLOv8官方文档](https://docs.ultralytics.com/)
- [ROS2 Foxy文档](https://docs.ros.org/en/foxy/)
- [TensorRT文档](https://docs.nvidia.com/deeplearning/tensorrt/)
- [RealSense ROS2 Wrapper](https://github.com/IntelRealSense/realsense-ros)

---

**最后更新**：2026年3月23日
**作者**：封科全
**指导老师**：杨丽丽 副教授
