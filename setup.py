from setuptools import setup, find_packages

setup(
    name="ParserCombinators",
    version="0.1",
    description="Parser Combinators",
    packages=find_packages("parsers", exclude="test"),
    install_requires=["FileData"],
)
