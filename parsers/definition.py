from __future__ import annotations
from functools import reduce
from result.result import Result, Error, Success
from filedata.filedata import FileData

from typing import Any, Callable, Iterable, Optional, Tuple, TypeVar

_T = TypeVar("_T")

ExtractionResult = Tuple[FileData, Result[_T]]

_T2 = TypeVar("_T2")

ParserFunction = Callable[[FileData], ExtractionResult[_T]]

# ------------------------------------------------------------


def generic_errmsg(label: str, data: FileData, reason: Optional[str] = None):
    return (
        f"Failed to parse {label} at {data.cursor}" + ""
        if reason is None
        else f"-> {reason}"
    )


def satisfy(predicate: Callable[[str], bool], label: str):
    def parser(data: FileData):
        new_data = data.copy()

        try:
            char = data._current_character()
            if predicate(char):
                new_data._next_character_cursor()
                return (new_data, Success(char))
            else:
                errmsg = f"Predicate {label} failed at {data.cursor}"

                return (data, Error(errmsg))
        except IndexError:
            return (data, Error("EOF"))

    return parser


def character(c: str) -> ParserFunction[str]:
    def parser(data: FileData) -> ExtractionResult[str]:
        new_data = data.copy()
        try:
            if new_data._current_character() == c:
                new_data._next_character_cursor()
                return (new_data, Success(c))
            else:
                return (data, Error(f"{c} not found at {data.cursor}"))
        except IndexError:
            return (data, Error("EOF"))

    parser.__name__ = "Parse" + c
    return parser


def andthen(
    p1: ParserFunction[_T], p2: ParserFunction[_T2], label: str = ""
) -> ParserFunction[tuple[_T, _T2]]:
    """define that 2 parsers are applied in succession"""
    if not label:
        label = f"{p1.__name__} and then {p2.__name__}"

    def parser(data: FileData) -> ExtractionResult[tuple[_T, _T2]]:
        d = data.copy()
        d, res1 = p1(d)
        if isinstance(res1, Error):
            return (data, Error(generic_errmsg(label, data, res1.val)))

        (d, res2) = p2(d)
        if isinstance(res2, Error):
            return (data, Error(generic_errmsg(label, data, res2.val)))
        else:
            return (d, Success((res1.val, res2.val)))

    parser.__name__ = label
    return parser


def _or(p1: ParserFunction[_T], p2: ParserFunction[_T2]):
    def parser(data: FileData):
        (d, res) = p1(data)
        if res:
            return (d, res)
        else:
            return p2(data)

    parser.__name__ = f"Either {p1.__name__} or {p2.__name__}"
    return parser


def either(parsers: list[ParserFunction[Any]], label: str) -> ParserFunction[Any]:
    p = reduce(_or, parsers)

    def parser(data: FileData):
        return p(data)

    parser.__name__ = label
    return parser


def left_seperate(optional: ParserFunction[Any], mandatory: ParserFunction[_T]):
    def parser(data: FileData):
        (d, res) = optional(data)
        if not res:
            return (data, res)

        (d, res) = mandatory(d)
        if isinstance(res, Error):
            return (data, res)
        else:
            return (d, res)

    return parser


def transform(p: ParserFunction[_T], f: Callable[[_T], _T2]) -> ParserFunction[_T2]:
    def parser(data: FileData):
        (d, res) = p(data)
        if isinstance(res, Success):
            return (d, Success(f(res.val)))
        else:
            return (data, res)

    return parser


def right_seperate(mandatory: ParserFunction[_T], opt: ParserFunction[_T2]):
    def parser(data: FileData):
        (d, res) = mandatory(data)
        if isinstance(res, Error):
            return (data, res)

        (d, opt_res) = opt(d)
        if isinstance(opt_res, Error):
            return (d, opt_res)
        else:
            return (d, res)

    return parser


def optional(p: ParserFunction[_T]) -> ParserFunction[Optional[_T]]:
    none: ParserFunction[None] = lambda data: (data, Success(None))
    return either([p, none], f"Optional {p.__name__}")


def many(p: ParserFunction[_T], label: str) -> ParserFunction[tuple[_T]]:
    def parser(data: FileData):
        d = data.copy()
        collection: list[_T] = []
        while not d.isEOF():
            (d, res) = p(d)
            if isinstance(res, Success):
                collection.append(res.val)
            else:
                break
        if collection:
            return (d, Success(tuple(collection)))
        else:
            return (data, Error(generic_errmsg(label, data)))

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
            return (data, Error(generic_errmsg(label, data)))

    parser.__name__ = label
    return parser


_CHAINT = Tuple[_T, _T]


def flatten(
    t: "_CHAINT[_T]| tuple[_CHAINT[_T], _T]", coll: "list[_T]" = []
) -> "list[_T]":
    if isinstance(t[0], Tuple):
        c = [t[1]]
        c.extend(coll)
        return flatten(t[0], c)
    else:
        c = [t[0], t[1]]
        c.extend(coll)
        return c


def chain(parsers: Iterable[ParserFunction[Any]], label: str):
    p = reduce(andthen, parsers)

    def parser(data: FileData):
        return p(data)

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

            return (data, Error(generic_errmsg(label, data, res.val)))

        return p(d)

    parser.__name__ = label
    return parser


def seperate(
    seperator: ParserFunction[Any],
    p: ParserFunction[_T],
    p2: ParserFunction[_T2],
    label: str,
) -> ParserFunction[tuple[_T, _T2]]:
    e = transform(chain([p, seperator, p2], ""), lambda res: (res[0][0], res[1]))

    def parser(data: FileData):
        return e(data)

    parser.__name__ = label
    return parser


def atmost(p: ParserFunction[_T], n: int):
    def parser(data: FileData):
        d = data.copy()
        coll: list[_T] = []
        for _ in range(n):
            (d, res) = p(d)
            if isinstance(res, Success):
                coll.append(res.val)
            else:
                return (d, Success(tuple(coll)))
        (d, res) = p(d)
        if res:
            reason = f"Found {n+1} matches for {p.__name__} but only expected {n} in {data.cursor}"
            return (
                data,
                Error(generic_errmsg(f"Atmost {n+1} {p.__name__}", data, reason)),
            )
        else:
            return (d, Success(tuple(coll)))

    parser.__name__ = f"Maximal {n} times {p.__name__}"
    return parser


def string(reference: str) -> ParserFunction[tuple[str]]:
    parsers = [character(c) for c in reference]
    p = chain(parsers, reference)

    def parser(data: FileData):
        return p(data)

    return parser


def any(data: FileData):
    return satisfy(lambda c: True, "Anything")(data)


def skip(p: ParserFunction[Any]):
    def parser(data: FileData):
        (d, _) = p(data)
        return (d, Success(None))

    parser.__name__ = f"Skip {p.__name__}"
    return parser
