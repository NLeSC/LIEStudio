#! /usr/bin/env python
# -*- coding: utf-8 -*-

# package: lie_cli
# file: setup.py
#
# A command line interface component to MDStudio
#
# Copyright © 2018 Marc van Dijk, VU University Amsterdam, the Netherlands
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup, find_packages

distribution_name = 'lie_cli'

setup(
    name=distribution_name,
    version=0.1,
    description='A command line interface component to MDStudio',
    author='Marc van Dijk, VU University, Amsterdam, The Netherlands',
    author_email='m4.van.dijk@vu.nl',
    url='https://github.com/MD-Studio/MDStudio',
    license='Apache Software License 2.0',
    keywords='MDStudio CLI',
    platforms=['Any'],
    packages=find_packages(),
    py_modules=[distribution_name],
    entry_points = {
        'console_scripts': ['mdstudio_cli=lie_cli.cli_services:main']
    },
    include_package_data=True,
    zip_safe=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
        'Operating System :: OS Independent',
        'Intended Audience :: Science/Research',
    ],
)
