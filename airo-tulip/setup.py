import setuptools
from setuptools import find_packages

setuptools.setup(
    name="airo-tulip",
    version="0.0.1",
    author="Mathieu De Coster",
    author_email="mathieu.decoster@ugent.be",
    description="Python driver for the KELO Robile platform",
    install_requires=[
        "numpy==1.24.4",
        "pyzmq==26.0.3",
        "loguru>=0.7.2",
        "pysoem>=1.1.6"
    ],
    packages=find_packages(),
)
