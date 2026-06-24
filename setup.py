#!/usr/bin/env python

import os
import re
from setuptools import setup


def load_readme():
    with open('README.rst', 'r') as fd:
        return fd.read()


def load_requirements():
    """Parse requirements.txt"""
    reqs_path = os.path.join('.', 'requirements.txt')
    with open(reqs_path, 'r') as fd:
        requirements = [line.rstrip() for line in fd]
    return requirements


package_name = 'log2seq'

with open(os.path.join(os.path.dirname(__file__), package_name, '__init__.py')) as f:
    version = re.search("__version__ = '([^']+)'", f.read()).group(1)


setup(name=package_name,
      version=version,
      description='A tool to parse syslog-like messages into word sequences',
      long_description=load_readme(),
      long_description_content_type='text/x-rst',
      author='Satoru Kobayashi',
      author_email='sat@3at.work',
      url='https://github.com/cpflat/log2seq/',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Information Technology',
          'Intended Audience :: Science/Research',
          "Intended Audience :: Developers",
          'License :: OSI Approved :: BSD License',
          "Operating System :: OS Independent",
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Programming Language :: Python :: 3.12',
          'Topic :: Scientific/Engineering :: Information Analysis',
          'Topic :: Software Development :: Libraries :: Python Modules'],
      license='BSD 3-Clause "New" or "Revised" License',

      packages=['log2seq'],
      python_requires='>=3.8',
      install_requires=load_requirements(),
      entry_points={
          "console_scripts": [
              "log2seq=log2seq.__main__:main",
          ],
      },
      test_suite="tests",
      )
