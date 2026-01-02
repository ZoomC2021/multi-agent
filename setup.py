from setuptools import setup, find_packages

setup(
    name="multi-agent-consensus",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "litellm>=1.0.0",
        "pyyaml>=6.0",
        "typing-extensions>=4.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "consensus-cli=consensus_system.cli:main",
        ],
    },
)
