from setuptools import setup, find_packages

setup(
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.10',
    ],
    name='demeter',
    version='0.1.0',
    packages=find_packages(exclude=["tests", "tests.*", "samples", "samples.*"]),
    # packages=["demeter", ],  # "broker" "core", "download", "indicator", "strategy", "utils"
    # package_dir={'demeter': 'demeter'
    #              # 'broker': './demeter/broker',
    #              # 'core': './demeter/core',
    #              # 'download': './demeter/download',
    #              # 'indicator': './demeter/indicator',
    #              # 'strategy': './demeter/strategy',
    #              # 'utils': './demeter/utils',
    #              },
    url='https://zelos-demeter.readthedocs.io',
    license='MIT',
    author='zelos team',
    author_email='liang.hou@antalpha.com',
    description='better back testing tool for uniswap v3',
    python_requires='>=3.10',
    install_requires=["pandas>=1.4.4", "tqdm>=4.64.1"],

)

# rm -rf ./demeter.egg-info/ & python setup.py sdist upload -r private
