from __future__ import annotations
from filedata.result import Result, Error, Success
from filedata.filedata import FileData

from typing import Any, Callable, Tuple, TypeVar

_T = TypeVar("_T")

ExtractionResult = Tuple[FileData, Result[_T]]

_T2 = TypeVar("_T2")

ParserFunction = Callable[[FileData], ExtractionResult[_T]]


def character(c: str) -> ParserFunction[str]:
    def parser(data: FileData) -> ExtractionResult[str]:
        new_data = data.copy()
        if (char := data.read()) and char == c:
            new_data.consume()
            return (new_data, Success(f"{c}"))
        else:
            return (data, Error(f"{c} not found"))

    parser.__name__ = "Parse" + c
    return parser


def andthen(
    p1: ParserFunction[_T], p2: ParserFunction[_T2], label: str
) -> ParserFunction[tuple[_T, _T2]]:
    """define that 2 parsers are applied in succession"""

    def parser(data: FileData) -> ExtractionResult[tuple[_T, _T2]]:
        d1, res1 = p1(data)
        if isinstance(res1, Error):
            errmsg = (
                f"{parser.__name__} failed parsing from {data.cursor}\n"
                + f"-> {res1}\n"
            )
            return (data, Error(errmsg))

        (d2, res2) = p2(d1)
        if isinstance(res2, Error):
            errmsg = (
                f"{parser.__name__} failed parsing from {data.cursor}\n"
                + f"-> {res1}\n"
            )
            return (data, Error(errmsg))
        else:
            return (d2, Success((res1.val, res2.val)))

    parser.__name__ = label
    return parser


def either(
    p1: ParserFunction[_T], p2: ParserFunction[_T2], label: str
) -> ParserFunction[_T | _T2]:
    def parser(data: FileData) -> ExtractionResult[_T | _T2]:
        d1, res1 = p1(data)
        if isinstance(res1, Success):
            return (d1, Success(res1.val))

        (d2, res2) = p2(data)
        if isinstance(res2, Success):
            return (d2, Success(res2.val))
        else:
            return (
                data,
                Error(
                    f"{parser.__name__} failed parsing from {data.cursor}\n"
                    + f"-> {res1}\n"
                    + f"-> {res2}\n"
                ),
            )

    parser.__name__ = label
    return parser


def transform(p: ParserFunction[_T], f: Callable[[_T], _T2]) -> ParserFunction[_T2]:
    def parser(data: FileData):
        (d, res) = p(data)
        if isinstance(res, Success):
            return (d, Success(f(res.val)))
        else:
            return (data, res)

    return parser


def multiple(
    p: ParserFunction[_T], number: int, label: str
) -> ParserFunction[tuple[_T]]:
    # p_new = reduce(lambda p1, p2: andthen(p1, p2, ""), [p for _ in range(1, number)])

    def parser(data: FileData):
        d = data
        collection: list[_T] = []
        for i in range(1, number):
            (d, res) = p(d)
            if isinstance(res, Error):
                errmsg = f"Parsing failed for {label} at iteration {i} -> {res}"
                return (data, Error(errmsg))
            else:
                collection.append(res.val)
        return (d, Success(tuple(collection)))

    parser.__name__ = label
    return parser


def seperate(
    seperator: ParserFunction[Any], p: ParserFunction[_T], label: str
) -> ParserFunction[_T]:
    def parser(data: FileData):
        (d, res) = seperator(data)
        if isinstance(res, Error):
            errmsg = f"Parsing failed for {parser.__name__} -> {res}"
            return (data, Error(errmsg))

        return p(d)

    parser.__name__ = label
    return parser
