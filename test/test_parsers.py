from parsers.definition import *


def test_character():
    nd = FileData("ac")

    a = character("a")
    c = character("c")

    # assert isinstance(c(nd)[1], Error)
    res1 = a(nd)
    assert isinstance(res1[1], Success)
    res2 = c(res1[0])
    assert isinstance(res2[1], Success)
    # assert isinstance(c(nd)[1], Success)


def test_andthen():
    nd = FileData("a-c")

    a = character("a")
    sub = character("-")
    c = character("c")

    asub = andthen(a, sub, "")
    assert isinstance(asub(nd)[1], Success)
    expr = andthen(asub, c, "")
    (_, res) = expr(nd)

    assert isinstance(res, Success)
    assert res.val == (("a", "-"), "c")


def test_multiple():
    nd = FileData(".....a.....")

    a = character("a")
    dot = character(".")
    mul_dots = multiple(dot, 5, "5-Dots")
    print("First Test -> Mul Dots")
    (_, res) = mul_dots(nd)
    assert isinstance(res, Success)
    assert sum("." == e for e in res.val) == 5

    expression = andthen(andthen(mul_dots, a, ""), mul_dots, "Expression")
    assert isinstance(expression(nd)[1], Success)


def test_transform():
    nd = FileData(".....a.....")

    a = character("a")
    dot = character(".")
    mul_dots = transform(multiple(dot, 5, "5-Dots"), lambda _: 5)
    (_, res) = mul_dots(nd)
    assert res.val == 5


def test_ignore():
    nd = FileData(".....a.....")
    a = character("a")
    dot = character(".")
    mul_dots = multiple(dot, 5, "5-Dots")

    sep_a = ignore(mul_dots, a, "sep_a")
    (_, res) = sep_a(nd)
    assert isinstance(res, Success)
    assert res.val == "a"


def test_seperate():
    nd = FileData("a,b")
    _a = character("a")
    _b = character("b")
    _comma = character(",")
    p = seperate(_comma, _a, _b, "csv")
    (_, res) = p(nd)
    assert isinstance(res, Success)
    assert res.val == ("a", "b")


def test_greedy_either():
    chrs = [chr(i) for i in range(32, 127)]
    _ascii = many(either([character(c) for c in chrs], "Ascii Characters"), "Words")
    nd = FileData("aBc#")
    (_, res) = _ascii(nd)
    assert res.val == ("a", "B", "c", "#")


def test_optional():
    num = FileData("1.23")
    _nums = either([character(str(e)) for e in range(10)], "Numbers")
    _dot = character(".")
    _number = optional(
        _nums, andthen(_dot, many(_nums, "fractions"), "Fraction"), "Number"
    )
    (_, res) = _number(num)
    assert isinstance(res, Success)
    assert res.val == ("1", (".", ("2", "3")))

    num = FileData("2")
    (_, res) = _number(num)
    assert res.val == ("2")


def test_atmost():
    expr = FileData("  ")
    p = atmost(character(" "), 1)
    (_, res) = p(expr)
    assert isinstance(res, Error)

    expr = FileData(" d")
    (d, res) = p(expr)
    assert res
    (_, res) = character("d")(d)
    assert res


def test_satisfy():
    expr = FileData(" \n\tc")
    space = satisfy(lambda c: c.isspace(), "Whitespace")
    spaces = many(space, "Spaces")
    (d, res) = spaces(expr)
    assert res
    (_, res) = character("c")(d)
    assert res


def test_termination():
    """Make sure that parsing terminates with error after input parsed"""
    nd = FileData("Alle lieben Leute")
    char = either(
        [satisfy(lambda c: c.isalnum(), "Alphanumeric Character"), character("_")],
        "Character",
    )
    word = atleast_one(char, "Word")
    seperated_words = many(
        andthen(character(" "), word, "Seperated Word"), "Seperated Words"
    )

    sentence = optional(
        word,
        seperated_words,
        "Sentence",
    )
    (_, res) = sentence(nd)
    assert res


def test_long_text():
    nd = FileData(
        """Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.
    Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat.
    Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.
    Nam liber tempor cum soluta nobis eleifend option congue nihil imperdiet doming id quod mazim placerat facer possim assum. Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat.
    Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis.
    At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, At accusam aliquyam diam diam dolore dolores duo eirmod eos erat, et nonumy sed tempor et et invidunt justo labore Stet clita ea et gubergren, kasd magna no rebum. sanctus sea sed takimata ut vero voluptua. est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur."""
    )

    char = either(
        [satisfy(lambda c: c.isalnum(), "Alphanumeric Character"), character("_")],
        "Character",
    )
    space = either([character(" "), character("\n"), character(",")], "Space")
    spaces = atleast_one(space, "Spaces")
    word = atleast_one(char, "Word")
    seperated_words = many(
        andthen(
            spaces,
            word,
            "Seperated Word",
        ),
        "Seperated Words",
    )
    sentence_body = optional(
        word,
        seperated_words,
        "Sentence Body",
    )

    sentence = andthen(sentence_body, character("."), "Sentence")
    text = optional(
        sentence,
        many(andthen(spaces, sentence, "Sentences"), "seperated sentences"),
        "Text",
    )

    (d, res) = text(nd)
    assert res
    assert d.consume() and d.isEOF()
