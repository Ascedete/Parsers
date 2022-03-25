from __future__ import annotations

from filedata.result import Result, Error, Success
from filedata.filedata import FileData

from typing import Any, Callable, Tuple, TypeVar

_T = TypeVar("_T")

ExtractionResult = Tuple[FileData, Result[_T]]

_T2 = TypeVar("_T2")

ParserFunction = Callable[[FileData], ExtractionResult[_T]]


def satisfy(predicate: Callable[[str], bool], label: str):
    def parser(data: FileData):
        new_data = data.copy()
        if (char := data.read()) and predicate(char):
            new_data.consume()
            return (new_data, Success(char))
        else:
            errmsg = f"Predicate {label} failed at {data.cursor}"
            return (data, Error(errmsg))

    return parser


def character(c: str) -> ParserFunction[str]:
    def parser(data: FileData) -> ExtractionResult[str]:
        new_data = data.copy()
        if (char := data.read()) and char == c:
            new_data.consume()
            return (new_data, Success(f"{c}"))
        else:
            return (data, Error(f"{c} not found at {data.cursor}"))

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


def either(parsers: list[ParserFunction[Any]], label: str) -> ParserFunction[Any]:
    def parser(data: FileData):
        for p in parsers:
            (d, res) = p(data)
            if isinstance(res, Success):
                return (d, res)
        errmsg = f"Failed to parse {parser.__name__} -> {res}"
        return (data, Error(errmsg))

    parser.__name__ = label
    return parser


def optional(mandatory: ParserFunction[_T], opt: ParserFunction[_T2], label: str):
    def parser(data: FileData):
        (d, res) = mandatory(data)
        if isinstance(res, Error):
            return (data, Error(f"Failed to parse {mandatory.__name__} -> {res}"))

        (d, opt_res) = opt(d)
        if isinstance(opt_res, Error):
            return (d, Success(res.val))
        else:
            return (d, Success((res.val, opt_res.val)))

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


def many(p: ParserFunction[_T], label: str) -> ParserFunction[tuple[_T]]:
    def parser(data: FileData):
        d = data.copy()
        collection: list[_T] = []
        while 1:
            (d, res) = p(d)
            if isinstance(res, Success):
                collection.append(res.val)
            else:
                break
        if collection:
            return (d, Success(tuple(collection)))
        else:
            return (data, Error(f"Failed to parse {parser.__name__}"))

    parser.__name__ = label
    return parser


def atleast_one(p: ParserFunction[_T], label: str) -> ParserFunction[tuple[_T]]:
    def parser(data: FileData):
        d = data.copy()
        collection: list[_T] = []
        while 1:
            (d, res) = p(d)
            if isinstance(res, Success):
                collection.append(res.val)
            else:
                break
        if collection:
            return (d, Success(tuple(collection)))
        else:
            return (data, Error(f"Failed to parse {parser.__name__}"))

    parser.__name__ = label
    return parser


def chain(parsers: list[ParserFunction[Any]], label: str):
    def parser(data: FileData):
        collection: list[Any] = []
        d = data.copy()
        for p in parsers:
            (d, res) = p(d)
            if isinstance(res, Error):
                errmsg = f"Parsing failed for {p.__name__} -> {res}"
                return (data, Error(errmsg))
            else:
                collection.append(res.val)
        return (d, Success(tuple(collection)))

    parser.__name__ = label
    return parser


def multiple(
    p: ParserFunction[_T], number: int, label: str
) -> ParserFunction[tuple[_T]]:

    parser = chain(list(map(lambda _: p, range(number))), label)

    parser.__name__ = label
    return parser


def ignore(
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


def seperate(
    seperator: ParserFunction[Any],
    p: ParserFunction[_T],
    p2: ParserFunction[_T2],
    label: str,
) -> ParserFunction[tuple[_T, _T2]]:

    e = chain([p, seperator, p2], "")

    def parser(data: FileData):
        (d, res) = e(data)
        if isinstance(res, Error):
            errmsg = f"Parsing failed for {parser.__name__} -> {res}"
            return (data, Error(errmsg))
        else:
            items = (res.val[0], res.val[2])
            return (d, Success(items))

    parser.__name__ = label
    return parser


def atmost(p: ParserFunction[_T], n: int):
    def parser(data: FileData):
        d = data.copy()
        coll: list[_T] = []
        for _ in range(n):
            (d2, res) = p(d)
            if isinstance(res, Success):
                coll.append(res.val)
            else:
                return (d, Success(tuple(coll)))
            d = d2
        (d2, res) = p(d)
        if res:
            errmsg = f"Found {n+1} matches for {p.__name__} but only expected {n} in {d.cursor}"
            return (data, Error(errmsg))
        else:
            return (d2, Success(coll))

    return parser
