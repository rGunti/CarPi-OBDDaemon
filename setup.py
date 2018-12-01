"""
CARPI REDIS DATA BUS
(C) 2018, Raphael "rGunti" Guntersweiler
Licensed under MIT
"""

from setuptools import setup

with open('README.md', 'r') as f:
    long_description = f.read()

setup(name='carpi-obddaemon',
      version='0.3.0',
      description='OBD II Daemon (developed for CarPi)',
      long_description=long_description,
      url='https://github.com/rGunti/CarPi-OBDDaemon',
      keywords='carpi redis data bus',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.6'
      ],
      author='Raphael "rGunti" Guntersweiler',
      author_email='raphael@rgunti.ch',
      license='MIT',
      packages=['obddaemon'],
      install_requires=[
          'obd',
          'wheel'
      ],
      zip_safe=False,
      include_package_data=True)
