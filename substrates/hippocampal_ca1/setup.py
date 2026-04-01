from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="Hippocampal-CA1-LAM",
    version="2.0.0",
    author="Yaroslav Vasylenko",
    author_email="neuron7xlab@gmail.com",
    description="Production-grade CA1 hippocampus model for AI memory and neuroscience",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/neuron7xLab/Hippocampal-CA1-LAM",
    packages=find_packages(exclude=["tests", "examples", "docs"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "scikit-learn>=1.2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "flake8>=6.0.0",
            "black>=23.0.0",
            "mypy>=1.5.0",
        ],
        "viz": [
            "matplotlib>=3.7.0",
        ],
    },
    entry_points={},
)
