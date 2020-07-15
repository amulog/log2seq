#!/usr/bin/env python

import os
from setuptools import setup


def load_readme():
    with open('README.md', 'r') as f:
        return f.read()


def load_requirements():
    """Parse requirements.txt"""
    reqs_path = os.path.join('.', 'requirements.txt')
    with open(reqs_path, 'r') as f:
        requirements = [line.rstrip() for line in f]
    return requirements


package_name = 'log2seq'

setup(name=package_name,
      version='0.1.0',
      description='A tool to parse syslog-like messages into word sequences',
      long_description=load_readme(),
      long_description_content_type='text/markdown',
      author='Satoru Kobayashi',
      author_email='sat@nii.ac.jp',
      url='https://github.com/cpflat/log2seq/',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Information Technology',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 3.7',
          'Topic :: Scientific/Engineering :: Information Analysis',
          'Topic :: Software Development :: Libraries :: Python Modules'],
      license='BSD 3-Clause "New" or "Revised" License',

      packages=['log2seq'],
      install_requires=load_requirements(),
      test_suite="tests",
      )
