from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument


def generate_launch_description():
    """Generate launch description for perception node."""
    
    # 声明启动参数
    model_path_arg = DeclareLaunchArgument(
        'model_path',
        default_value='/home/go2/inspection_system/models/best_nano_seg.pt',
        description='Path to YOLO model file (.pt or .engine)'
    )
    
    confidence_arg = DeclareLaunchArgument(
        'confidence_threshold',
        default_value='0.5',
        description='Detection confidence threshold'
    )
    
    input_topic_arg = DeclareLaunchArgument(
        'input_topic',
        default_value='/camera/color/image_raw',
        description='Input image topic'
    )
    
    # YOLO检测节点
    yolo_detector_node = Node(
        package='inspection_perception',
        executable='yolo_detector',
        name='yolo_detector',
        output='screen',
        parameters=[{
            'model_path': LaunchConfiguration('model_path'),
            'confidence_threshold': LaunchConfiguration('confidence_threshold'),
            'input_topic': LaunchConfiguration('input_topic'),
            'device': 'cuda',
            'publish_visualization': True,
        }],
        remappings=[
            ('/detections', '/inspection/detections'),
            ('/detections/visualization', '/inspection/detections/visualization'),
        ]
    )
    
    return LaunchDescription([
        model_path_arg,
        confidence_arg,
        input_topic_arg,
        yolo_detector_node,
    ])
