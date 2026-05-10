from setuptools import setup, find_packages

setup(
    name="steerplane",
    version="0.4.0",
    description="Agent Control Plane for Autonomous Systems — Runtime guards, loop detection, cost limits, and telemetry for AI agents.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="SteerPlane",
    author_email="hello@steerplane.ai",
    url="https://github.com/vijaym2k6/SteerPlane",
    project_urls={
        "Homepage": "https://steerplane.ai",
        "Documentation": "https://docs.steerplane.ai",
        "Repository": "https://github.com/vijaym2k6/SteerPlane",
        "Issues": "https://github.com/vijaym2k6/SteerPlane/issues",
    },
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "cli": [
            "click>=8.1.0",
        ],
        "yaml": [
            "pyyaml>=6.0",
        ],
        "langchain": [
            "langchain-core>=0.1.0",
        ],
        "crewai": [
            "crewai>=0.30.0",
        ],
        "autogen": [
            "pyautogen>=0.2.0",
        ],
        "all": [
            "click>=8.1.0",
            "pyyaml>=6.0",
            "langchain-core>=0.1.0",
        ],
        "dev": [
            "pytest>=7.0",
            "pytest-cov",
            "ruff",
        ],
    },
    entry_points={
        "console_scripts": [
            "steerplane=steerplane.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="ai agents guard safety monitoring telemetry llm steerplane",
)
