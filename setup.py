from setuptools import setup

setup(
    name='helmstack',
    version='1.0.0',
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
