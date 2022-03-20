from parsers.definition import *


def test_character():
    nd = FileData("ac")

    a = character("a")
    c = character("c")
    assert isinstance(c(nd)[1], Error)
    assert isinstance(a(nd)[1], Success)
    assert isinstance(c(nd)[1], Success)


def test_multiple():
    nd = FileData(".....a.....")

    a = character("a")
    dot = character(".")
    mul_dots = multiple(dot, 5, "5-Dots")
    print("First Test -> Mul Dots")

    expression = andthen(andthen(mul_dots, a, ""), mul_dots, "Expression")
    assert isinstance(expression(nd), Success)
