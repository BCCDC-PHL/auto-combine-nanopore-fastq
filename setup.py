from setuptools import setup, find_namespace_packages


setup(
    name='auto-combine-nanopore-fastq',
    version='0.1.0-alpha',
    packages=find_namespace_packages(),
    entry_points={
        "console_scripts": [
            "auto-combine-nanopore-fastq = auto_combine_nanopore_fastq.__main__:main",
        ]
    },
    scripts=[],
    package_data={
    },
    install_requires=[
    ],
    description=' Automated combining of nanopore sequence data',
    url='https://github.com/BCCDC-PHL/auto-combine-nanopore-fastq',
    author='Dan Fornika',
    author_email='dan.fornika@bccdc.ca',
    include_package_data=True,
    keywords=[],
    zip_safe=False
)
