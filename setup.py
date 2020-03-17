
from setuptools import setup

setup(
    name='arma-manager',
    version='0.1.0',
    description='Arma Service Manager',
    author='Sigmund "Sig" Klåpbakken',
    author_email='sigmundklaa@outlook.com',
    packages=['manager'],
    install_requires=['pboutil', 'requests']
)