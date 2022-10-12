from setuptools import setup, find_packages

setup(
    name='demeter',
    version='0.1.0',
    packages=find_packages(exclude=["tests", "tests.*", "samples", "samples.*"]),
    url='https://zelos-demeter.readthedocs.io',
    license='MIT',
    author='zelos team',
    author_email='liang.hou@antalpha.com',
    description='better back testing tool for uniswap v3',
    python_requires='>=3.10',
    install_requires=["pandas>=1.4.4",
                      "tqdm>=4.64.1",
                      "google-cloud-bigquery>=3.3.5",
                      "db-dtypes>=1.0.4"],
)

# rm -rf ./demeter.egg-info/ && python setup.py sdist upload -r private
