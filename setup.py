import pathlib
import sys
import os
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup
HERE = pathlib.Path(__file__).parent
README = (HERE / "Readme.md").read_text()

extra_link_args = []
libraries = []
library_dirs = []
include_dirs = []
exec(open('imax/version.py').read())
setup(
    name='imax',
    version=__version__,
    description='Interactive tool for visualize and classify multiple images at a time',
    long_description=README,
    long_description_content_type='text/markdown',
    author='Matias Carrasco Kind',
    author_email='mcarras2@illinois.edu',
    scripts=["imax-run"],
    packages=['imax'],
    package_data = {
        'imax/static': ['*'],
        'imax/templates': ['*'],
        'imax' : ['config_template.yaml']
    },
    license='LICENSE.txt',
    url='https://github.com/mgckind/imax.git',
    install_requires=[
        "aiohttp",
        "aiohttp_cors",
        "Pillow",
        "click",
        "pyyaml",
        "coloredlogs",
        "asyncio",
        "numpy",
        "tornado",
        "matplotlib",
        "requests"
    ],
)
