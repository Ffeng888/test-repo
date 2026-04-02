from setuptools import setup
import os
from glob import glob
setup(
    name='inspection_viz',
    version='1.0.0',
    packages=['inspection_viz'],
    data_files=[
        ('share/inspection_viz', ['package.xml']),
        ('share/inspection_viz/resource', ['resource/inspection_viz']),
        (os.path.join('share', 'inspection_viz', 'static'), 
         glob('static/*')),
    ],
    install_requires=['flask', 'flask-cors'],
    entry_points={
        'console_scripts': [
            'web_server = inspection_viz.web_server:main',
        ],
    },
)
