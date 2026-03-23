#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv26n TensorRT转换脚本
用于将PyTorch模型(.pt)转换为TensorRT引擎(.engine)以加速推理

Author: 封科全
Date: 2026-03-23
"""

import os
import sys
import argparse
from pathlib import Path

def check_environment():
    """检查环境是否满足转换要求"""
    print("🔍 检查转换环境...")
    
    # 检查ultralytics
    try:
        from ultralytics import YOLO
        print("✅ ultralytics已安装")
    except ImportError:
        print("❌ 错误: 未安装ultralytics")
        print("💡 请运行: pip3 install ultralytics")
        return False
    
    # 检查CUDA
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✅ CUDA可用: {torch.cuda.get_device_name(0)}")
        else:
            print("⚠️ 警告: CUDA不可用，转换会很慢")
    except ImportError:
        print("⚠️ 警告: 未安装PyTorch")
    
    return True

def convert_to_tensorrt(model_path, output_path=None, imgsz=640, half=True, workspace=2):
    """
    将YOLO模型转换为TensorRT引擎
    
    参数:
        model_path: 输入的.pt模型路径
        output_path: 输出的.engine路径（可选）
        imgsz: 输入图像尺寸，默认640
        half: 是否使用FP16半精度，默认True（推荐用于Jetson）
        workspace: 工作空间大小(GB)，默认2
    """
    from ultralytics import YOLO
    
    # 检查输入文件
    if not os.path.exists(model_path):
        print(f"❌ 错误: 找不到模型文件: {model_path}")
        return False
    
    print(f"📦 加载模型: {model_path}")
    model = YOLO(model_path)
    
    # 获取模型信息
    print(f"📝 模型信息:")
    print(f"   - 任务类型: {model.task}")
    print(f"   - 检测类别: {model.names}")
    
    # 设置输出路径
    if output_path is None:
        output_path = model_path.replace('.pt', '.engine')
    
    print(f"\n🔧 开始转换TensorRT引擎...")
    print(f"   - 输入尺寸: {imgsz}x{imgsz}")
    print(f"   - FP16半精度: {'开启' if half else '关闭'}")
    print(f"   - 工作空间: {workspace}GB")
    print(f"   - 输出文件: {output_path}")
    print()
    
    try:
        # 执行转换
        model.export(
            format='engine',
            imgsz=imgsz,
            half=half,
            workspace=workspace,
            verbose=True
        )
        
        # 检查输出文件
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"\n✅ 转换成功!")
            print(f"📁 输出文件: {output_path}")
            print(f"📊 文件大小: {size_mb:.1f} MB")
            return True
        else:
            print(f"\n❌ 转换失败: 未找到输出文件")
            return False
            
    except Exception as e:
        print(f"\n❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def benchmark_models(pt_path, engine_path, test_image=None):
    """
    对比测试PyTorch和TensorRT模型的性能
    
    参数:
        pt_path: PyTorch模型路径
        engine_path: TensorRT引擎路径
        test_image: 测试图像路径（可选）
    """
    import time
    import numpy as np
    from ultralytics import YOLO
    
    print("\n" + "="*60)
    print("📊 性能对比测试")
    print("="*60)
    
    # 如果没有测试图像，创建随机图像
    if test_image is None or not os.path.exists(test_image):
        print("⚠️ 未提供测试图像，使用随机数据测试")
        test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    results = {}
    
    # 测试PyTorch模型
    if os.path.exists(pt_path):
        print(f"\n🔄 测试PyTorch模型: {pt_path}")
        model_pt = YOLO(pt_path)
        
        # 预热
        for _ in range(5):
            model_pt.predict(test_image, verbose=False)
        
        # 正式测试
        times_pt = []
        for i in range(20):
            start = time.time()
            model_pt.predict(test_image, verbose=False)
            times_pt.append(time.time() - start)
        
        avg_pt = np.mean(times_pt[5:]) * 1000  # 转换为ms，跳过前5次
        fps_pt = 1000 / avg_pt
        results['PyTorch'] = {'latency': avg_pt, 'fps': fps_pt}
        
        print(f"   平均延迟: {avg_pt:.1f} ms")
        print(f"   FPS: {fps_pt:.1f}")
    
    # 测试TensorRT模型
    if os.path.exists(engine_path):
        print(f"\n🔄 测试TensorRT模型: {engine_path}")
        model_trt = YOLO(engine_path)
        
        # 预热
        for _ in range(5):
            model_trt.predict(test_image, verbose=False)
        
        # 正式测试
        times_trt = []
        for i in range(20):
            start = time.time()
            model_trt.predict(test_image, verbose=False)
            times_trt.append(time.time() - start)
        
        avg_trt = np.mean(times_trt[5:]) * 1000
        fps_trt = 1000 / avg_trt
        results['TensorRT'] = {'latency': avg_trt, 'fps': fps_trt}
        
        print(f"   平均延迟: {avg_trt:.1f} ms")
        print(f"   FPS: {fps_trt:.1f}")
    
    # 对比结果
    if 'PyTorch' in results and 'TensorRT' in results:
        speedup = results['PyTorch']['latency'] / results['TensorRT']['latency']
        print(f"\n📈 性能提升:")
        print(f"   TensorRT比PyTorch快: {speedup:.1f}x")
        print(f"   FPS提升: {results['TensorRT']['fps'] - results['PyTorch']['fps']:.1f}")
    
    print("="*60)

def main():
    parser = argparse.ArgumentParser(
        description='YOLOv26n TensorRT转换工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本转换（FP16，推荐用于Jetson）
  python3 convert_to_tensorrt.py --model ~/inspection_system/models/yolo26n-seg.pt
  
  # 指定输出路径
  python3 convert_to_tensorrt.py --model best.pt --output my_model.engine
  
  # 使用FP32精度（更高精度但更慢）
  python3 convert_to_tensorrt.py --model yolo26n-seg.pt --no-half
  
  # 转换并性能测试
  python3 convert_to_tensorrt.py --model yolo26n-seg.pt --benchmark
        """
    )
    
    parser.add_argument('--model', '-m', required=True,
                        help='输入的PyTorch模型文件路径 (.pt)')
    parser.add_argument('--output', '-o', default=None,
                        help='输出的TensorRT引擎路径 (.engine)，默认与输入同名')
    parser.add_argument('--imgsz', '-s', type=int, default=640,
                        help='输入图像尺寸，默认640')
    parser.add_argument('--no-half', action='store_true',
                        help='禁用FP16半精度（默认开启，Jetson推荐开启）')
    parser.add_argument('--workspace', '-w', type=int, default=2,
                        help='TensorRT工作空间大小(GB)，默认2')
    parser.add_argument('--benchmark', '-b', action='store_true',
                        help='转换后进行性能对比测试')
    parser.add_argument('--test-image', '-t', default=None,
                        help='用于测试的图像路径')
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 YOLOv26n TensorRT转换工具")
    print("="*60)
    print()
    
    # 检查环境
    if not check_environment():
        sys.exit(1)
    
    print()
    
    # 执行转换
    success = convert_to_tensorrt(
        model_path=args.model,
        output_path=args.output,
        imgsz=args.imgsz,
        half=not args.no_half,
        workspace=args.workspace
    )
    
    if not success:
        sys.exit(1)
    
    # 性能测试
    if args.benchmark:
        output_path = args.output if args.output else args.model.replace('.pt', '.engine')
        benchmark_models(args.model, output_path, args.test_image)
    
    print("\n✨ 转换完成!")
    print("💡 提示: 使用.engine文件启动检测节点可获得更好性能")
    print(f"   ros2 launch inspection_perception perception.launch.py model_path:={output_path}")

if __name__ == '__main__':
    main()
