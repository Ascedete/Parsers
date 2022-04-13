from __future__ import annotations
from dataclasses import dataclass
from functools import reduce
from result.type_defines import Error, Success, Result
from filedata.filedata import FileData, FilePosition, seek
from typing import Any, Callable, Generic, Iterable, Tuple, TypeVar

_T = TypeVar("_T")
_T2 = TypeVar("_T2")

PSuccess = Tuple[FileData, _T]


@dataclass(frozen=True, eq=True)
class PError:
    position: FilePosition
    label: str
    reason: str = ""

    def __repr__(self) -> str:
        return (
            f"Failed to parse {self.label} at {self.position}\n"
            f"{'' if self.reason == '' else '-> ' + self.reason}"
        )


PResult = Result[PSuccess[_T], PError]
PFunc = Callable[[FileData], PResult[_T]]


@dataclass(frozen=True)
class Parser(Generic[_T]):

    purpose: str
    fn: PFunc[_T]

    def __call__(self, data: FileData) -> PResult[_T]:
        res = self.fn(data)
        if isinstance(res, Success):
            return res
        else:
            return self._create_error(res)

    def _create_error(self, res: Error[PError], label: str = ""):
        reason = (
            res.val.reason
            if res.val.reason != ""
            else f"during parsing of {res.val.label}"
        )
        if not label:
            _label = self.purpose
        else:
            _label = label
        return Error(PError(res.val.position, _label, reason))

    def __mod__(self, label: str) -> "Parser[_T]":
        return Parser(label, self.fn)

    # Define Combinators
    def __or__(self, o: "Parser[_T2]") -> "Parser[_T|_T2]":
        def parser(data: FileData) -> "PResult[_T|_T2]":
            res = self(data)
            if isinstance(res, Success):
                return res
            else:
                res = o(data)
                if isinstance(res, Error):
                    return Error(
                        PError(data.cursor, f"Either {self.purpose} or {o.purpose}")
                    )
                else:
                    return res

        return Parser(f"Either {self.purpose} or {o.purpose}", parser)

    def __and__(self, o: "Parser[_T2]") -> Parser[tuple[_T, _T2]]:
        _label = f"{self.purpose} then {o.purpose}"

        def parser(data: FileData):
            r1 = self(data)
            if not isinstance(r1, Success):
                return self._create_error(r1, _label)

            r2 = o(r1.val[0])
            if not isinstance(r2, Success):
                return self._create_error(r2, _label)
            else:
                return Success((r2.val[0], (r1.val[1], r2.val[1])))

        return Parser(_label, parser)

    def __rshift__(self, f: "Callable[[_T], _T2]") -> Parser[_T2]:
        def parser(data: FileData):
            if isinstance(r := self(data), Success):
                return Success((r.val[0], f(r.val[1])))
            else:
                return self._create_error(r)

        return Parser(self.purpose, parser)

    def __invert__(self):
        """Optional Parser"""

        _p = (self | _none_parser) % f"Optional {self.purpose}"

        return _p

    def __le__(self: "Parser[_T]", o: "Parser[_T2]") -> "Parser[_T]":
        _p = ((self & o) >> (lambda x: x[0])) % f"only {self.purpose}"
        return _p

    def __ge__(self: "Parser[_T]", o: "Parser[_T2]") -> "Parser[_T2]":
        _p: Parser[_T2] = ((self & o) >> (lambda x: x[1])) % f"only {o.purpose}"
        return _p

    def __matmul__(self, f: Callable[[PResult[_T]], None]) -> Parser[_T]:
        def parser(data: FileData):
            res = self(data)
            f(res)
            return res

        return Parser(self.purpose, parser)

    @classmethod
    def proxy(cls, t: _T = Any):
        dummy: "list[Parser[_T]]" = [
            Parser(
                "Unknown",
                lambda data: Error(PError(data.cursor, "Unknown", "Not Implemented!")),
            )
        ]
        wrapper: Parser[_T] = Parser(dummy[0].purpose, lambda data: dummy[0].fn(data))
        return (wrapper, dummy)


_none_parser = Parser("None", lambda data: Success((data, None)))

# ------------------------------------------------------------


def satisfy(predicate: Callable[[str], bool], label: str):
    def parser(data: FileData):
        new_data = data.copy()
        try:
            char = data._current_character()
            if predicate(char):
                new_data._next_character_cursor()
                return Success((new_data, char))
            else:
                return Error(
                    PError(data.cursor, label, f"found {char} didn't fulfill {label}")
                )
        except (KeyError, IndexError):
            return Error(PError(data.cursor, label, "EOF"))

    return Parser(label, parser)


def character(c: str) -> Parser[str]:
    def parser(data: FileData):
        new_data = data.copy()
        try:
            if new_data._current_character() == c:
                new_data._next_character_cursor()
                return Success((new_data, c))
            else:
                return Error(
                    PError(
                        data.cursor,
                        f"Parse {c}",
                        f"got {new_data._current_character()} but expected {c}",
                    )
                )

        except (KeyError, IndexError):
            return Error(PError(data.cursor, f"parse {c}", "EOF"))

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
        return Success((last, coll))

    return Parser(f"Many {p.purpose}", parser)


def atleast(p: Parser[_T], n: int):
    _p = many(p)
    _label = f"Atleast {n} times {p.purpose}"

    def parser(data: FileData):
        res = _p(data)
        if not isinstance(res, Success):
            return p._create_error(res, _label)
        elif len(res.val[1]) < n:
            return Error(
                PError(
                    data.cursor,
                    _label,
                    f"expected atleast {n} but got only {len(res.val[1])}",
                )
            )
        else:
            return Success((res.val[0], res.val[1]))

    return Parser(_label, parser)


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


def step_over(lines: int, columns: int):
    def parser(data: FileData):
        nd = data.copy()
        nd.move_cursor(nd.cursor + (lines, columns))
        return Success((nd, None))

    return Parser(f"Skip over lines: {lines}, columns: {columns}", parser)


def move_to(trigger: str):
    def parser(data: FileData):
        if not (pos := seek(data, trigger)):
            return Error(
                PError(
                    data.cursor,
                    f"Move to {trigger}",
                    f"{trigger} not found from {data.cursor}",
                )
            )

        nd = data.copy()
        nd.move_cursor(pos)
        return Success((nd, None))

    return Parser(f"Move to {trigger}", parser)
