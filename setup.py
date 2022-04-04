from setuptools import setup

setup(
    name="ParserCombinators",
    version="0.1.7",
    description="Parser Combinators",
    packages=["parsers"],
    install_requires=[
        "FileData @ git+https://github.com/Ascedete/FileData.git@master",
        "Result @ git+https://github.com/Ascedete/Result.git@master",
    ],
    url="https://github.com/Ascedete/Parsers",
)
