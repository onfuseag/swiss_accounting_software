# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in swiss_accounting_software/__init__.py
from swiss_accounting_software import __version__ as version

setup(
	name='swiss_accounting_software',
	version=version,
	description='Extend ERPNext for Switzerland with QR bills, payment automation and much more',
	author='ONFUSE',
	author_email='contact@onfuse.ch',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
