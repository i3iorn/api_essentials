from setuptools import setup, find_packages


setup(
    name="ApiEssentials",
    version="0.1.0",
    author="Björn",
    author_email="bjorn@schrammel.dev",
    description="A Python package for API essentials.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    install_requires=[
        "httpx",
        "tenacity",
        "python-dotenv",
        "requests",
        "pydantic",
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "pytest-asyncio",
        "black",
        "flake8",
        "mypy"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7"
)
