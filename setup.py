from pathlib import Path

from setuptools import setup, find_packages

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="zelos-demeter",
    version="0.7.5",
    packages=find_packages(exclude=["tests", "tests.*", "samples", "samples.*"]),
    url="https://zelos-demeter.readthedocs.io",
    license="MIT",
    author="zelos research",
    author_email="zelos@antalpha.com",
    description="better DEFI backtesting tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.11",
    install_requires=[
        "numpy>=1.26.4",
        "pandas>=2.2.0",
        "python-dateutil>=2.9.0.post0",
        "pytz>=2024.1",
        "six>=1.16.0",
        "db-dtypes>=1.2.0",
        "tqdm>=4.66.2",
        "orjson>=3.9.15",
    ],
)

# rm -rf ./demeter.egg-info/ && python setup.py sdist upload -r private
# python setup.py sdist
# twine upload -r pypi dist/*
