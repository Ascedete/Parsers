from __future__ import annotations
from dataclasses import dataclass
from functools import reduce
from result.result import Error, Success, Result
from filedata.filedata import FileData, FilePosition
from typing import Any, Callable, Generic, Iterable, Optional, Tuple, TypeVar

_T = TypeVar("_T")
_T2 = TypeVar("_T2")

ParseResult = Result[Tuple[FileData, _T]]
PFunc = Callable[[FileData], Optional[Tuple[FileData, _T]]]


@dataclass(frozen=True)
class Parser(Generic[_T]):

    purpose: str
    fn: PFunc[_T]

    def _errmsg(self, position: FilePosition):
        return f"Failed to parse {self.purpose} at {position}"

    def __call__(self, data: FileData) -> ParseResult[_T]:
        try:
            if res := self.fn(data):
                return Success(res)
            else:
                return Error(self._errmsg(data.cursor))
        except (KeyError, IndexError):
            return Error(f"Cannot parse from given file at position {data.cursor}")

    def __mod__(self, label: str) -> "Parser[_T]":
        return Parser(label, self.fn)

    # Define Combinators
    def __or__(self, o: "Parser[_T2]") -> "Parser[_T|_T2]":
        def parser(data: FileData):
            res = self(data)
            if isinstance(res, Success):
                return (res.val[0], res.val[1])
            else:
                res = o(data)
                if isinstance(res, Success):
                    return (res.val[0], res.val[1])

        return Parser(f"Either {self.purpose} or {o.purpose}", parser)

    def __and__(self, o: "Parser[_T2]"):
        def parser(data: FileData):
            r1 = self(data)
            if not isinstance(r1, Success):
                return

            r2 = o(r1.val[0])
            if not isinstance(r2, Success):
                return
            else:
                return (r2.val[0], (r1.val[1], r2.val[1]))

        return Parser(f"{self.purpose} then {o.purpose}", parser)

    def __rshift__(self, f: "Callable[[_T], _T2]"):
        def parser(data: FileData):
            if isinstance(r := self(data), Success):
                return (r.val[0], f(r.val[1]))
            else:
                return

        return Parser(self.purpose, parser)

    def __invert__(self):
        """Optional Parser"""
        none = Parser("None", lambda data: (data, None))
        _p = (self | none) % f"Optional {self.purpose}"

        return _p

    def __le__(self: "Parser[_T]", o: "Parser[_T2]") -> "Parser[_T]":
        _p = ((self & o) >> (lambda x: x[0])) % f"only {self.purpose}"
        return _p

    def __ge__(self: "Parser[_T]", o: "Parser[_T2]") -> "Parser[_T2]":
        _p = ((self & o) >> (lambda x: x[1])) % f"only {o.purpose}"
        return _p


# ------------------------------------------------------------


def satisfy(predicate: Callable[[str], bool], label: str):
    def parser(data: FileData):
        new_data = data.copy()
        char = data._current_character()
        if predicate(char):
            new_data._next_character_cursor()
            return (new_data, char)
        else:
            return

    return Parser(label, parser)


def character(c: str) -> Parser[str]:
    def parser(data: FileData):
        new_data = data.copy()

        if new_data._current_character() == c:
            new_data._next_character_cursor()
            return (new_data, c)
        else:
            return

    return Parser(f"Parse {c}", parser)


def either(l: Iterable[Parser[Any]]):
    return reduce(Parser.__or__, l)


def chain(l: Iterable[Parser[Any]]):
    p = reduce(Parser.__and__, l) >> flatten

    def parser(data: FileData):
        return p.fn(data)

    return Parser(p.purpose, parser)


def repeat(p: Parser[_T], n: int) -> "Parser[list[_T]]":
    _p = chain([p for _ in range(n)])
    return Parser(f"{n} times {p.purpose}", _p.fn)


def many(p: Parser[_T]):
    def parser(data: FileData):
        coll: "list[_T]" = []
        last = data
        while isinstance((r_new := p(last)), Success):
            coll.append(r_new.val[1])
            last = r_new.val[0]
        return (last, coll)

    return Parser(f"Many {p.purpose}", parser)


def atleast(p: Parser[_T], n: int):
    _p = many(p)

    def parser(data: FileData):
        res = _p(data)
        if not res or len(res.val[1]) < n:
            return
        else:
            assert isinstance(res, Success)
            return (res.val[0], res.val[1])

    return Parser(f"Atleast {n} times {p.purpose}", parser)


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


def string(reference: str):
    parsers = [character(c) for c in reference]
    p = chain(parsers)

    def parser(data: FileData):
        return p.fn(data)

    return Parser(f"Parse {reference}", parser)


def any():
    return satisfy(lambda c: True, "Anything")


def ignore(p: Parser[Any]):
    return p >> (lambda _: None)
