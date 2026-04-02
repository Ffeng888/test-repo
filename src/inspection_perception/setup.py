from setuptools import setup
import os
from glob import glob

package_name = 'inspection_perception'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'models'), glob('models/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='封科全',
    maintainer_email='fengkequan@cau.edu.cn',
    description='YOLO-based perception for network facility inspection - 支持YOLOv26n模型',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'yolo_detector = inspection_perception.yolo_detector:main',
        ],
    },
)
