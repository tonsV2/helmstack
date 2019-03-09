from setuptools import setup

setup(
    name='helmstack',
    version='1.3.0',
    description='See https://github.com/tonsV2/helmstack',
    python_requires='>=3',
    py_modules=['helmstack'],
    install_requires=[
        'click',
        'ruamel.yaml'
    ],
    entry_points='''
        [console_scripts]
        helmstack=helmstack:cli
    '''
)
