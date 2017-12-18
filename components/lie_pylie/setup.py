# -*- coding: utf-8 -*-

# package: pylie
# file: setup.py
#
# Part of ‘pylie’, providing LIE data modelling routines
# LIEStudio package.
#
# Copyright © 2016 Marc van Dijk, VU University Amsterdam, the Netherlands
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

distribution_name = 'pylie'
test_requirements = ['unittest2']

setup(
    name=distribution_name,
    version=0.1,
    description='LIE modelling library of the MDStudio application',
    author='Marc van Dijk, VU University, Amsterdam, The Netherlands',
    author_email='m4.van.dijk@vu.nl',
    url='https://github.com/NLeSC/LIEStudio',
    license='Apache Software License 2.0',
    keywords='MDStudio LIE statistics modelling',
    platforms=['Any'],
    packages=find_packages(),
    package_data={'': ['*.json']},
    py_modules=[distribution_name],
    test_suite="tests",
    test_requirements=test_requirements,
    install_requires=['numpy', 'pandas', 'statsmodels', 'jsonschema'] + test_requirements,
    include_package_data=True,
    zip_safe=True,
    entry_points={
        'autobahn.twisted.wamplet': [
            'wamp_services = pylie.wamp_services:make'
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
        'Operating System :: OS Independent',
        'Intended Audience :: Science/Research',
    ],
)
