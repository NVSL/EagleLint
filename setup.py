from setuptools import setup
from codecs import open
import os

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'DESCRIPTION.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(os.path.join(here, 'VERSION.txt'), encoding='utf-8') as f:
    version = f.read()

setup(name='EagleLint',
      version=version,
      description="EagleLint is a style and correctness checker for Eagle PCB design files.",
      long_description=long_description,
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Topic :: Scientific/Engineering",
          "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
          "Topic :: System",
          "Topic :: System :: Hardware",
      ],
      author="NVSL, University of California San Diego",
      author_email="swanson@cs.ucsd.edu",
      install_requires=["Swoop>=0.6.3"],
      packages = ["EagleLint"],
      package_dir={
          'EagleLint' : '.',
      },
      entry_points={
        'console_scripts': [
            'eaglelint = EagleLint.eaglelint:main',
            ]
        },
      
      )


