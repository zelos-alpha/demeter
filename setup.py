from setuptools import setup, find_packages

setup(
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.10',
    ],
    name='demeter',
    version='0.1.0',
    # packages=find_packages(include=["demeter"], exclude=["test", "sample"]),
    packages=["demeter"],
    url='',
    license='',
    author='zelos team',
    author_email='liang.hou@antalpha.com',
    description='better back testing tool for uniswap v3',
    python_requires='>=3.10',
    install_requires=["pandas>=1.4.4", "tqdm>=4.64.1"],
    # data_files=[
    #     ('', ['conf/*.conf']),
    #     ('/usr/lib/systemd/system/', ['bin/*.service']),
    # ],

    # package_data={
    #     '': ['*.txt'],
    #     'bandwidth_reporter': ['*.txt']
    # },
    exclude_package_data={
        'data': ['*.*'],
        'auth': ['*.json'],
        'tests': ['*.*'],
        'samples': ['*.*'],
        'demeter.egg-info': ['*.*'],
    }
)

# python setup.py sdist upload -r private
