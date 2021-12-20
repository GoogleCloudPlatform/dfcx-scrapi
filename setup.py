"""Setuptools for SCRAPI package."""

# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pathlib
from setuptools import setup, find_packages

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='dfcx-scrapi',
    version='1.1.0',
    description='A high level scripting API for bot builders, developers, and\
      maintainers.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/GoogleCloudPlatform/dfcx-scrapi',
    author='Patrick Marlow',
    author_email='pmarlow@google.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Communications :: Chat',
        'Topic :: Software Development',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords='dialogflow, cx, google, bot, chatbot, intent, dfcx, entity',
    package_dir={'':'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.6, <4',
    install_requires=['google-cloud-dialogflow-cx']
)
