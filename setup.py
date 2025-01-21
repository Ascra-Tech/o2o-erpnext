from setuptools import find_packages, setup

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in o2o_erpnext/__init__.py
from o2o_erpnext import __version__ as version

setup(
    name="o2o_erpnext",
    version=version,
    description="Custom o2o ERPNext Integration",
    author="1byZero",
    author_email="amit@ascratech.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)