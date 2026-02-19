#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from setuptools import find_packages

from setuptools import setup


with open('README.md', 'rt') as readme_file:
    readme = readme_file.read()


def prerelease_local_scheme(version):
    """
    Return local scheme version unless building on master in CircleCI.

    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).
    """
    from setuptools_scm.version import get_local_node_and_date

    if os.getenv('CIRCLE_BRANCH') in {'master'}:
        return ''
    else:
        return get_local_node_and_date(version)


setup(
    name='general',
    use_scm_version={'local_scheme': prerelease_local_scheme},
    description='Plugins for FTU Spot Aggregation and other spatial omics tasks',
    long_description=readme,
    long_description_content_type='text/markdown',
    author='Anish Tatke',
    author_email='anish.tatke@ufl.edu',
    url='https://github.com/SarderLab/Spatial-Omics-Plugins',
    packages=find_packages(exclude=['tests', '*_test']),
    package_dir={
        'SpatialAggregation': 'SpatialAggregation',
    },
    include_package_data=True,
    install_requires=[
        'fusion-tools[interactive]>=3.6.84',
        'numpy>=2.3.4',
        'tqdm>=4.66.1',
    ],
    extras_require={
        'dsa': [
            'girder-client',
            'girder-slicer-cli-web',
            'ctk-cli',
        ],
        'all': [
            'Pillow>=12.0.0',
            'scikit-image>=0.25.0',
            'scikit-learn>=1.4.0',
            'girder-slicer-cli-web',
            'girder-client',
            'ctk-cli',
            'dash==3.2.0',
            'dash-extensions>=2.0.4',
            'wsi-annotations-kit>=1.4.9',
            'rasterio>=1.3.6',
        ],
    },
    license='Apache Software License 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    zip_safe=False,
)