from setuptools import setup, find_packages

setup(
    name="moneyradar",
    version="0.1.0",
    description="Internal Monetization Engine - Revenue Intelligence & Optimization",
    author="M-Soho",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.9",
    install_requires=[
        "flask>=3.0.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.13.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.0",
        "stripe>=7.0.0",
        "pandas>=2.1.0",
        "apscheduler>=3.10.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=7.0.0",
            "mypy>=1.7.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "moneyradar=monetization_engine.cli:main",
        ],
    },
)
