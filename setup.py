#!/usr/bin/env python

from __future__ import print_function

import os
from setuptools import setup

package_name = 'log2seq'
data_dir = "/".join((package_name, "data"))
data_files = ["/".join((data_dir, fn)) for fn in os.listdir(data_dir)]

setup(name=package_name,
      version='0.0.1',
      description='',
      author='Satoru Kobayashi',
      author_email='sat@nii.ac.jp',
      url='https://github.com/cpflat/log2seq/',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Information Technology',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 3.4.3',
          'Topic :: Scientific/Engineering :: Information Analysis',
          'Topic :: Software Development :: Libraries :: Python Modules'],
      license='BSD 3-Clause "New" or "Revised" License',
      
      packages=['log2seq'],
      package_data={'log2seq' : data_files},
      )
