from setuptools import setup, find_packages

setup(
    name="ai_engine",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "grpcio>=1.59.0",
        "grpcio-tools>=1.59.0",
        "protobuf>=4.24.0",
        "rocketmq-client-python>=2.1.0",
        "pyyaml>=6.0.1",
        "torch>=2.0.0",
        "torchserve>=0.8.1",
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.1",
            "black>=23.7.0",
            "isort>=5.12.0",
        ]
    },
    python_requires=">=3.8",
) 