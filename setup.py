from setuptools import setup

setup(
    name='helmstack',
    version='1.1.1',
    description='See https://github.com/tonsV2/helmstack',
    py_modules=['helmstack'],
    install_requires=[
        'click',
        'ruamel.yaml',
        'python-dotenv'
    ],
    entry_points='''
        [console_scripts]
        helmstack=helmstack:cli
    '''
)
