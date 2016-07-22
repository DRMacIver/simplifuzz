from setuptools import find_packages, setup
import os


def local_file(name):
    return os.path.relpath(os.path.join(os.path.dirname(__file__), name))

SOURCE = local_file("src")
README = local_file("README.md")


setup(
    name='simplifuzz',
    version="0.0.1",
    author='David R. MacIver',
    author_email='david@drmaciver.com',
    packages=find_packages(SOURCE),
    package_dir={"": SOURCE},
    url='https://github.com/DRMacIver/simplifuzz',
    license='AGPL v3',
    description='A new type of fuzzer',
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    install_requires=['click', 'sortedcontainers', 'sysv_ipc'],
    long_description=open(README).read(),
    entry_points={
        'console_scripts': [
            'simplifuzz=simplifuzz.__main__:simplifuzz'
        ]
    }
)
