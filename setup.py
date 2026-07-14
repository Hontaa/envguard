import os
from setuptools import setup, find_packages

setup(
    name="envguard",
    version="0.1.0",
    description="Python-native validator for .env / config files with secret-leak detection and drift diffing.",
    py_modules=[],
    packages=find_packages(exclude=("tests",)),
    entry_points={"console_scripts": ["envguard=envguard.cli:main"]},
    python_requires=">=3.9",
    install_requires=[],
)
