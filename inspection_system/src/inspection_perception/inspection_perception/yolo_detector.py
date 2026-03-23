#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv8 Instance Segmentation ROS2 Node
用于网络设施巡检的视觉感知节点

Author: 封科全
Date: 2025-12
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
from geometry_msgs.msg import Pose2D
from cv_bridge import CvBridge
import cv2
import numpy as np
from ultralytics import YOLO
import torch
import time
from typing import List, Tuple, Optional


class YOLODetectorNode(Node):
    """YOLOv8分割检测节点"""
    
    def __init__(self):
        super().__init__('yolo_detector')
        
        # 声明参数
        self.declare_parameter('model_path', '/home/go2/inspection_system/models/best_nano_seg.pt')
        self.declare_parameter('confidence_threshold', 0.5)
        self.declare_parameter('iou_threshold', 0.45)
        self.declare_parameter('input_topic', '/camera/color/image_raw')
        self.declare_parameter('camera_info_topic', '/camera/color/camera_info')
        self.declare_parameter('publish_visualization', True)
        self.declare_parameter('device', 'cuda')  # 在Jetson上使用CUDA
        self.declare_parameter('inference_size', 640)
        
        # 获取参数
        model_path = self.get_parameter('model_path').value
        self.conf_thresh = self.get_parameter('confidence_threshold').value
        self.iou_thresh = self.get_parameter('iou_threshold').value
        input_topic = self.get_parameter('input_topic').value
        camera_info_topic = self.get_parameter('camera_info_topic').value
        self.publish_viz = self.get_parameter('publish_visualization').value
        device = self.get_parameter('device').value
        self.inference_size = self.get_parameter('inference_size').value
        
        # 初始化CV桥接
        self.bridge = CvBridge()
        
        # 加载模型
        self.get_logger().info(f'正在加载模型: {model_path}')
        try:
            self.model = YOLO(model_path)
            self.model.to(device)
            self.get_logger().info(f'模型加载成功! 使用设备: {device}')
        except Exception as e:
            self.get_logger().error(f'模型加载失败: {e}')
            raise
        
        # 类别名称映射
        self.class_names = {0: 'switch', 1: 'unplugged_port'}
        self.class_colors = {
            0: (0, 255, 0),      # 交换机 - 绿色
            1: (0, 0, 255)       # 未插网口 - 红色
        }
        
        # 相机内参
        self.camera_matrix = None
        self.distortion_coeffs = None
        
        # 订阅者
        self.image_sub = self.create_subscription(
            Image,
            input_topic,
            self.image_callback,
            10
        )
        
        self.camera_info_sub = self.create_subscription(
            CameraInfo,
            camera_info_topic,
            self.camera_info_callback,
            10
        )
        
        # 发布者
        self.detection_pub = self.create_publisher(
            Detection2DArray,
            '/detections',
            10
        )
        
        if self.publish_viz:
            self.viz_pub = self.create_publisher(
                Image,
                '/detections/visualization',
                10
            )
        
        # 性能统计
        self.frame_count = 0
        self.total_inference_time = 0.0
        self.fps_timer = self.create_timer(1.0, self.print_fps)
        
        self.get_logger().info('YOLO检测节点初始化完成!')
    
    def camera_info_callback(self, msg: CameraInfo):
        """接收相机内参"""
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.k).reshape(3, 3)
            self.distortion_coeffs = np.array(msg.d)
            self.get_logger().info('相机内参已接收')
    
    def image_callback(self, msg: Image):
        """处理图像并进行检测"""
        try:
            # 转换ROS图像到OpenCV
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
            # 记录开始时间
            start_time = time.time()
            
            # 运行YOLO检测
            results = self.model(
                cv_image,
                conf=self.conf_thresh,
                iou=self.iou_thresh,
                imgsz=self.inference_size,
                verbose=False
            )
            
            # 计算推理时间
            inference_time = time.time() - start_time
            self.total_inference_time += inference_time
            self.frame_count += 1
            
            # 处理检测结果
            detections_msg = self.process_detections(results[0], msg.header)
            
            # 发布检测结果
            self.detection_pub.publish(detections_msg)
            
            # 发布可视化图像
            if self.publish_viz:
                viz_image = self.visualize_detections(cv_image, results[0])
                viz_msg = self.bridge.cv2_to_imgmsg(viz_image, encoding='bgr8')
                viz_msg.header = msg.header
                self.viz_pub.publish(viz_msg)
            
        except Exception as e:
            self.get_logger().error(f'图像处理错误: {e}')
    
    def process_detections(self, result, header) -> Detection2DArray:
        """处理YOLO检测结果并转换为ROS消息"""
        detections_msg = Detection2DArray()
        detections_msg.header = header
        
        if result.boxes is None or len(result.boxes) == 0:
            return detections_msg
        
        boxes = result.boxes
        masks = result.masks
        
        for i, box in enumerate(boxes):
            detection = Detection2D()
            detection.header = header
            
            # 获取边界框坐标
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            
            # 计算中心点和宽高
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            width = x2 - x1
            height = y2 - y1
            
            # 设置边界框
            detection.bbox.center = Pose2D(x=center_x, y=center_y, theta=0.0)
            detection.bbox.size_x = width
            detection.bbox.size_y = height
            
            # 获取类别和置信度
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            
            # 创建假设
            hypothesis = ObjectHypothesisWithPose()
            hypothesis.hypothesis.class_id = self.class_names.get(cls_id, f'class_{cls_id}')
            hypothesis.hypothesis.score = confidence
            detection.results.append(hypothesis)
            
            # 如果有分割掩码，计算掩码质心
            if masks is not None:
                mask = masks.data[i].cpu().numpy()
                # 计算掩码的质心
                y_indices, x_indices = np.where(mask > 0.5)
                if len(x_indices) > 0:
                    mask_center_x = np.mean(x_indices)
                    mask_center_y = np.mean(y_indices)
                    
                    # 添加掩码质心作为额外信息
                    detection.source_img.width = int(mask_center_x)
                    detection.source_img.height = int(mask_center_y)
            
            detections_msg.detections.append(detection)
        
        return detections_msg
    
    def visualize_detections(self, image: np.ndarray, result) -> np.ndarray:
        """在图像上绘制检测结果"""
        viz_image = image.copy()
        
        if result.boxes is None:
            return viz_image
        
        boxes = result.boxes
        masks = result.masks
        
        # 绘制分割掩码
        if masks is not None:
            for i, mask in enumerate(masks.data):
                cls_id = int(boxes.cls[i])
                color = self.class_colors.get(cls_id, (255, 255, 255))
                
                # 转换掩码为二值图
                mask_np = mask.cpu().numpy()
                mask_binary = (mask_np > 0.5).astype(np.uint8)
                
                # 创建彩色掩码
                colored_mask = np.zeros_like(viz_image)
                colored_mask[mask_binary > 0] = color
                
                # 叠加掩码到图像
                viz_image = cv2.addWeighted(viz_image, 1.0, colored_mask, 0.4, 0)
        
        # 绘制边界框和标签
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            
            color = self.class_colors.get(cls_id, (255, 255, 255))
            class_name = self.class_names.get(cls_id, f'Class {cls_id}')
            
            # 绘制边界框
            cv2.rectangle(viz_image, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签背景
            label = f'{class_name}: {confidence:.2f}'
            (text_width, text_height), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(
                viz_image,
                (x1, y1 - text_height - 10),
                (x1 + text_width, y1),
                color,
                -1
            )
            
            # 绘制标签文字
            cv2.putText(
                viz_image,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
        
        # 绘制FPS信息
        avg_inference_time = self.total_inference_time / max(self.frame_count, 1)
        fps = 1.0 / avg_inference_time if avg_inference_time > 0 else 0
        
        fps_text = f'FPS: {fps:.1f} | Inference: {avg_inference_time*1000:.1f}ms'
        cv2.putText(
            viz_image,
            fps_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        
        return viz_image
    
    def print_fps(self):
        """定时打印FPS统计"""
        if self.frame_count > 0:
            avg_time = self.total_inference_time / self.frame_count
            fps = 1.0 / avg_time
            self.get_logger().info(
                f'平均FPS: {fps:.1f} | 平均推理时间: {avg_time*1000:.1f}ms | '
                f'处理帧数: {self.frame_count}'
            )


def main(args=None):
    """主函数"""
    rclpy.init(args=args)
    
    try:
        node = YOLODetectorNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'节点运行错误: {e}')
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
