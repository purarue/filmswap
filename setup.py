from pathlib import Path
from setuptools import setup, find_packages  # type: ignore[import]

long_description = Path("README.md").read_text()

pkg = "filmswap"
setup(
    name=pkg,
    version="0.1.0",
    url="https://github.com/purarue/filmswap",
    author="purarue",
    description=("""bot to swap films to watch anonymously"""),
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    packages=find_packages(include=[pkg]),
    package_data={pkg: ["py.typed"]},
    zip_safe=False,
    keywords="",
    python_requires=">=3.7",
    entry_points={"console_scripts": ["filmswap = filmswap.__main__:main"]},
    extras_require={
        "testing": [
            "mypy",
            "flake8",
        ]
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
