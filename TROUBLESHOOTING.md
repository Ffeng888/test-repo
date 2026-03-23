# 故障排除指南

> 部署过程中遇到问题？这里是常见问题和解决方案的汇总。

---

## 🚨 安装阶段问题

### 问题1: pip安装超时或失败

**症状**:
```
ERROR: Could not find a version that satisfies the requirement ultralytics
```

**解决方案**:
```bash
# 使用国内镜像
pip3 install ultralytics -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或者使用清华大学的完整镜像源
pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install ultralytics
```

---

### 问题2: ROS2依赖安装失败

**症状**:
```
rosdep: command not found
```

**解决方案**:
```bash
# 安装rosdep
sudo apt install python3-rosdep

# 初始化
sudo rosdep init
rosdep update

# 然后重新安装依赖
cd ~/inspection_system
rosdep install --from-paths src --ignore-src -r -y
```

---

## 🚨 编译阶段问题

### 问题3: colcon build失败

**症状**:
```
ImportError: No module named 'cv_bridge'
```

**解决方案**:
```bash
# 安装缺失的ROS2包
sudo apt install ros-foxy-cv-bridge ros-foxy-vision-msgs

# 重新编译
cd ~/inspection_system
colcon build --symlink-install
```

---

### 问题4: 编译时找不到Python包

**症状**:
```
ModuleNotFoundError: No module named 'ultralytics'
```

**解决方案**:
```bash
# 确保在系统Python中安装
sudo pip3 install ultralytics

# 或者指定Python路径
python3 -m pip install ultralytics
```

---

## 🚨 运行阶段问题

### 问题5: 相机节点启动失败

**症状**:
```
[ERROR] [camera]: No RealSense devices were found!
```

**解决步骤**:

1. **检查USB连接**:
   ```bash
   lsusb | grep Intel
   ```
   应该看到类似 `Intel Corp.` 的设备。

2. **检查权限**:
   ```bash
   # 将用户添加到video组
   sudo usermod -aG video $USER
   # 重新登录后生效
   ```

3. **重置相机**:
   ```bash
   # 重新插拔USB
   # 或者使用命令
   rs-enumerate-devices
   ```

4. **安装相机驱动**:
   ```bash
   sudo apt install ros-foxy-realsense2-camera
   ```

---

### 问题6: YOLO模型加载失败

**症状**:
```
[ERROR] [yolo_detector]: 模型加载失败: [Errno 2] No such file...
```

**解决步骤**:

1. **检查模型文件是否存在**:
   ```bash
   ls -lh ~/inspection_system/models/
   ```
   应该看到 `yolo26n-seg.pt` 文件，大小应该在几MB到几十MB。

2. **检查文件完整性**:
   ```bash
   # 如果文件太小（如只有几百字节），说明传输不完整
   # 重新复制模型
   ```

3. **手动测试模型加载**:
   ```bash
   python3 << 'EOF'
   from ultralytics import YOLO
   try:
       model = YOLO('/home/go2/inspection_system/models/yolo26n-seg.pt')
       print("✅ 模型加载成功!")
       print(f"模型任务: {model.task}")
       print(f"检测类别: {model.names}")
   except Exception as e:
       print(f"❌ 错误: {e}")
   EOF
   ```

4. **检查ultralytics版本**:
   ```bash
   pip3 show ultralytics
   # 版本应该 >= 8.3.0 才能支持YOLOv26
   ```

---

### 问题7: CUDA/GPU不可用

**症状**:
```
[WARN] [yolo_detector]: CUDA不可用，切换到CPU模式
```

**解决方案**:
```bash
# 检查CUDA是否安装
nvidia-smi

# 检查PyTorch是否支持CUDA
python3 -c "import torch; print(f'CUDA可用: {torch.cuda.is_available()}')"

# 如果CUDA可用但PyTorch检测不到，可能需要重新安装PyTorch
# 注意：Jetson上需要从NVIDIA安装PyTorch，不能从pip安装
```

**Jetson上的特殊处理**:
```bash
# Jetson上PyTorch通常已预装，但需要验证
python3 -c "import torch; import torchvision; print('PyTorch版本:', torch.__version__)"

# 确保ultralytics使用正确的PyTorch
pip3 uninstall ultralytics -y
pip3 install --no-cache-dir ultralytics
```

---

### 问题8: Web界面无法访问

**症状**:
浏览器显示"无法访问此网站"或连接超时。

**解决步骤**:

1. **检查Web服务器是否运行**:
   ```bash
   ros2 node list | grep web_server
   ```
   应该看到 `/web_server` 节点。

2. **检查防火墙**:
   ```bash
   sudo ufw status
   sudo ufw allow 5000
   ```

3. **检查端口占用**:
   ```bash
   netstat -tulpn | grep 5000
   # 或者
   lsof -i :5000
   ```

4. **检查IP地址**:
   ```bash
   hostname -I
   # 确保使用正确的IP访问
   ```

5. **从机器狗本地测试**:
   ```bash
   curl http://localhost:5000
   # 如果能返回HTML，说明服务正常，是网络问题
   ```

---

### 问题9: SSH连接断开

**症状**:
SSH连接不稳定，经常断开。

**解决方案**:
```bash
# 在机器狗上修改SSH配置
sudo nano /etc/ssh/sshd_config

# 添加或修改以下行
ClientAliveInterval 60
ClientAliveCountMax 3

# 重启SSH服务
sudo systemctl restart sshd
```

**在Windows客户端**:
```powershell
# 使用SSH配置文件
notepad $env:USERPROFILE\.ssh\config
```

添加:
```
Host go2
    HostName 192.168.1.100
    User go2
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

---

### 问题10: FPS太低（<10）

**症状**:
Web界面显示的FPS很低，画面卡顿。

**解决方案**:

1. **降低输入分辨率**:
   ```bash
   ros2 launch inspection_perception perception.launch.py inference_size:=320
   ```

2. **使用TensorRT加速**:
   ```bash
   # 转换模型为TensorRT格式
   cd ~/inspection_system/models
   python3 << 'EOF'
   from ultralytics import YOLO
   model = YOLO('yolo26n-seg.pt')
   model.export(format='engine', imgsz=640, half=True)
   EOF
   
   # 使用TensorRT模型
   ros2 launch inspection_perception perception.launch.py model_path:=~/inspection_system/models/yolo26n-seg.engine
   ```

3. **检查CPU/GPU使用率**:
   ```bash
   # 安装jtop查看系统状态
   sudo pip3 install jetson-stats
   jtop
   ```

---

## 🚨 其他问题

### 问题11: 检测结果不准确

**可能原因**:
- 置信度阈值太高或太低
- 输入图像分辨率不合适
- 光照条件变化

**解决方案**:
```bash
# 调整置信度阈值
ros2 launch inspection_perception perception.launch.py confidence_threshold:=0.3

# 降低阈值会看到更多检测结果（可能包含误检）
# 提高阈值只看到高置信度结果（可能漏检）
```

---

### 问题12: 分割mask显示异常

**症状**:
分割mask位置偏移或形状不对。

**解决方案**:
```bash
# 检查模型是否是分割模型
python3 << 'EOF'
from ultralytics import YOLO
model = YOLO('/home/go2/inspection_system/models/yolo26n-seg.pt')
print(f"模型任务: {model.task}")
# 应该是 'segment'
EOF
```

---

## 📝 日志查看

如果以上方法都无法解决问题，请查看日志：

```bash
# 查看ROS日志
ls ~/.ros/log/

# 查看最新的日志
cd ~/.ros/log/latest
ls -la

# 查看特定节点的日志
cat yolo_detector-*.log
```

---

## 🔍 调试技巧

### 1. 测试单个组件

**测试相机**:
```bash
ros2 topic echo /camera/color/image_raw --once
# 如果能看到数据，说明相机正常
```

**测试检测节点**:
```bash
ros2 topic echo /detections --once
# 如果能看到检测结果，说明检测节点正常
```

**测试可视化**:
```bash
ros2 topic echo /detections/visualization --once
# 如果能看到图像数据，说明可视化正常
```

### 2. 使用rqt工具

```bash
# 安装rqt工具
sudo apt install ros-foxy-rqt-graph ros-foxy-rqt-image-view

# 查看节点关系图
ros2 run rqt_graph rqt_graph

# 查看图像
ros2 run rqt_image_view rqt_image_view
```

### 3. 录制数据包

```bash
# 录制所有相关话题
ros2 bag record /camera/color/image_raw /detections /detections/visualization -o debug_session

# 之后可以回放
ros2 bag play debug_session
```

---

## 🆘 仍然无法解决？

如果以上方法都无法解决问题，请提供以下信息寻求帮助：

1. **完整的错误日志**:
   ```bash
   # 复制日志到文件
   cd ~/.ros/log/latest
   tar -czvf ~/ros_logs.tar.gz .
   ```

2. **系统信息**:
   ```bash
   uname -a
   lsb_release -a
   nvidia-smi
   ```

3. **ROS环境**:
   ```bash
   echo $ROS_DISTRO
   ros2 --version
   pip3 show ultralytics | grep Version
   ```

4. **复现步骤**:
   - 你执行了什么命令？
   - 出现了什么错误？
   - 你已经尝试过哪些解决方案？

---

**祝部署顺利！** 🚀
