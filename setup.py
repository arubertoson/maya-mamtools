from setuptools import setup, find_packages
import os
import sys
import mamtools


with open('README.rst') as f:
    readme = f.read()


setup(
    name='mamtools',
    version=mamtools.__version__,
    description=mamtools.__description__,
    long_description=readme,
    author=mamtools.__author__,
    author_email=mamtools.__email__,
    license=mamtools.__license__,
    package_data={
        '': ['LICENSE', 'README.rst'],
        'mamtools': ['']
    },
    packages=find_packages(),
    include_package_data=True,
    classifiers=(
        'Development Status :: 1 - Alpha',
        'Intended Audience :: Artists',
        'License :: OSI Approved :: MIT License',
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        'Programming Language :: Python :: 2',
        "Topic :: Software Development :: Libraries :: Python Modules",
    )
)
