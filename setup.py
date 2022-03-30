from setuptools import setup

setup(
    name="ParserCombinators",
    version="0.1.6",
    description="Parser Combinators",
    packages=["parsers"],
    install_requires=["FileData @ git+https://github.com/Ascedete/FileData.git@master"],
    url="https://github.com/Ascedete/Parsers",
)
