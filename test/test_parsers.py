from os import remove

import pytest
from parsers.definition import *


def test_character():
    nd = FileData("ac")

    a = character("a")
    c = character("c")

    res1 = a(nd)
    assert isinstance(res1, Success)
    res2 = c(res1.val[0])
    assert isinstance(res2, Success)


def test_repeat_until():
    nd = FileData("1111112")
    one = character("1")
    two = character("2")
    parser = one.repeat_until(two)
    res = parser(nd)
    assert len(res.expect()[1]) == 7

    nd = FileData("111")
    with pytest.raises(ValueError):
        parser(nd).expect()


def test_logger():
    nd = FileData("aac")

    def log_err(r: PResult[Any]):
        if isinstance(r, Error):
            with open("log.txt", "w+") as fd:
                fd.write(str(r.val))

    ap = character("a")
    bp = character("b") @ log_err
    cp = character("c")

    p = ap & (bp | ap) & cp
    res = p(nd)
    try:
        assert res
        with open("log.txt", "r") as fd:
            d = FileData(fd)
            assert len(d.text) == 2
    finally:
        remove("log.txt")


def test_andthen():
    nd = FileData("a-c")
    a = character("a")
    sub = character("-")
    c = character("c")

    asub = a & sub
    assert isinstance(asub(nd), Success)
    expr = asub & c

    r = expr(nd)

    assert isinstance(r, Success)
    assert r.val[1] == (("a", "-"), "c")


def test_multiple():
    nd = FileData(".....a.....")

    a = character("a")
    dot = character(".")
    mul_dots = atleast(dot, 5)
    print("First Test -> Mul Dots")
    res = mul_dots(nd)
    assert isinstance(res, Success)
    assert sum("." == e for e in res.val[1]) == 5
    expression = mul_dots & a & mul_dots
    assert isinstance(expression(nd), Success)


def test_ignore():
    nd = FileData(".....a.....")
    a = character("a")
    dot = character(".")
    mul_dots = atleast(dot, 5)

    p = (mul_dots >= a) <= mul_dots
    res = p(nd)
    assert res and res.val[1] == "a"


def test_seperate():
    nd = FileData("a,b")
    _a = character("a")
    _b = character("b")
    _comma = character(",")
    res = ((_a <= _comma) & _b)(nd)

    assert isinstance(res, Success)
    assert res.val[1] == ("a", "b")


def test_greedy_either():
    chrs = either(character(c) for c in [chr(i) for i in range(32, 127)])
    _ascii = many(chrs)
    nd = FileData("aBc#")
    res = _ascii(nd)
    assert res.val[1] == ["a", "B", "c", "#"]


def test_optional():
    num = FileData("1.23")
    _nums = either([character(str(e)) for e in range(10)])
    _dot = character(".")
    _number = (_nums & ~(_dot >= atleast(_nums, 1))) >> (
        lambda x: float(f"{x[0]}.{''.join(x[1])}") if x[1] else float(x[0])
    )
    res = _number(num)
    assert isinstance(res, Success)
    assert res.val[1] == 1.23

    num = FileData("2")
    res = _number(num)
    assert res.val[1] == 2


def test_proxy():
    nd = FileData("(1(23))")
    (number, _number_inner) = Parser.proxy(float)
    _number_inner[0] = (
        satisfy(lambda c: c.isnumeric(), "Number") >> (lambda x: float("".join(x)))
        | ((character("(") >= atleast(number, 1)) <= character(")"))
    ) >> (lambda x: sum(x) if isinstance(x, list) else x)

    res = number(nd)
    assert res.val[1] == 6


def test_move_to():
    txt = """//psl HVDIFF_USAGE_check : assert
// always ( rose(hvdiff_cp) && adc_sel==11 && adc_en ->
//            ((selsc_sig >0  && selsc_sig<15  && selsc_ref==0) ||
//             (selsc_sig==0                   && selsc_ref==7) ||
//             (selsc_sig==15 && (selsc_ref==0 || selsc_ref==7))))
//          @(negedge CLK)
//          report "Incorrect SCAMP configuration (combination of signal and reference)."
//          severity warning;"""

    data = FileData(txt)
    _space = character(" ")
    _word = (
        many(satisfy(lambda c: c.isalnum(), "Char")) >> (lambda x: "".join(x))
    ) % "Word"
    p = ((move_to("@") & character("@") & character("(")) >= _word) & (
        many(character(" ")) >= _word
    )
    res = p(data)
    assert res
    assert res.val[1] == ("negedge", "CLK")


def test_satisfy():
    expr = FileData(" \n\tc")
    space = satisfy(lambda c: c.isspace(), "Whitespace")
    spaces = many(space)
    res = spaces(expr)
    assert isinstance(res, Success)
    res = character("c")(res.val[0])
    assert res


def test_ignore_left():
    p = (character(",") >= string("Hello")) >> (lambda x: "".join(x))
    nd = FileData(",Hello")
    res = p(nd)
    assert res.val[1] == "Hello"


def test_step_over():
    nd = FileData("Not relevantHere nicey")
    _skip = step_over(0, len("Not relevant"))
    _word = (
        many(satisfy(lambda c: c.isalnum(), "Char")) >> (lambda x: "".join(x))
    ) % "Word"
    _space = character(" ")
    p = (_skip >= (_word <= _space)) & _word
    res = p(nd)
    assert res
    assert res.val[1] == ("Here", "nicey")

    nd = FileData("\n\nHere interesting")
    _skip = step_over(2, 0)
    p = (_skip >= (_word <= _space)) & _word
    res = p(nd)
    assert res
    assert res.val[1] == ("Here", "interesting")


def test_error():
    _a_b = character("a") & character("b")
    nd = FileData("ac")
    res = _a_b(nd)
    assert not res
    assert repr(res.val)


def test_termination():
    """Make sure that parsing terminates with error after input parsed"""
    nd = FileData("Alle lieben Leute")
    char = satisfy(lambda c: c.isalnum(), "Alphanumeric Character") | character("_")

    word = atleast(char, 1) >> (lambda x: "".join(x))
    seperated_words = many(character(" ") >= word)

    sentence = (word & ~(seperated_words)) >> (lambda x: [x[0]] + x[1])
    res = sentence(nd)
    assert res.val[1] == ["Alle", "lieben", "Leute"]


def test_if_else():
    trigger = string("-->")
    a = string("Hello")
    b = string("olleH")

    a_if_trigger_else_b = trigger.branch(a, b) >> (lambda x: "".join(x))

    res = a_if_trigger_else_b(FileData("-->Hello"))
    assert res
    assert res.expect()[1] == "Hello"

    data = FileData("olleH")
    res = a_if_trigger_else_b(data)
    assert res
    assert res.expect()[1] == "olleH"


def test_long_text():
    txt = """Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Gravida arcu ac tortor dignissim. Maecenas sed enim ut sem viverra aliquet eget sit amet. Quam id leo in vitae turpis. Risus nec feugiat in fermentum posuere urna nec. Vulputate enim nulla aliquet porttitor lacus. Id interdum velit laoreet id. Metus aliquam eleifend mi in nulla posuere sollicitudin aliquam ultrices. Nunc id cursus metus aliquam. Pulvinar sapien et ligula ullamcorper malesuada proin libero nunc. Id eu nisl nunc mi. Cursus mattis molestie a iaculis at. Id ornare arcu odio ut sem nulla pharetra diam. Malesuada nunc vel risus commodo viverra. Est placerat in egestas erat imperdiet sed euismod nisi porta. A condimentum vitae sapien pellentesque habitant morbi tristique senectus. Aliquet bibendum enim facilisis gravida neque convallis a. Massa enim nec dui nunc mattis. Risus nec feugiat in fermentum posuere. Proin fermentum leo vel orci porta. Porttitor rhoncus dolor purus non enim praesent. Scelerisque purus semper eget duis. At volutpat diam ut venenatis tellus in metus. Semper auctor neque vitae tempus quam pellentesque nec. Nisl nisi scelerisque eu ultrices vitae. Et magnis dis parturient montes nascetur ridiculus mus mauris vitae. In vitae turpis massa sed. Purus non enim praesent elementum facilisis leo vel fringilla est. Sit amet nisl suscipit adipiscing bibendum est ultricies integer. Ultrices gravida dictum fusce ut placerat orci nulla pellentesque dignissim. Pretium vulputate sapien nec sagittis. Mattis nunc sed blandit libero volutpat sed cras ornare arcu. Sit amet consectetur adipiscing elit duis tristique sollicitudin nibh. Libero justo laoreet sit amet cursus. Suspendisse in est ante in. Faucibus a pellentesque sit amet porttitor eget dolor morbi non. Pretium vulputate sapien nec sagittis aliquam malesuada bibendum. Elementum nibh tellus molestie nunc non blandit massa enim. Nec ullamcorper sit amet risus nullam. Enim diam vulputate ut pharetra sit. Dignissim suspendisse in est ante in nibh mauris. Convallis a cras semper auctor neque vitae tempus quam pellentesque. Vel risus commodo viverra maecenas accumsan lacus vel facilisis volutpat. Et egestas quis ipsum suspendisse ultrices gravida. Vulputate ut pharetra sit amet. Habitant morbi tristique senectus et netus. Metus aliquam eleifend mi in nulla posuere sollicitudin. Dictum at tempor commodo ullamcorper a lacus vestibulum sed arcu. Justo nec ultrices dui sapien eget mi proin. Orci ac auctor augue mauris augue neque gravida in. Pharetra et ultrices neque ornare aenean euismod elementum nisi. Mi tempus imperdiet nulla malesuada. Aliquam ut porttitor leo a. Ullamcorper velit sed ullamcorper morbi. Viverra ipsum nunc aliquet bibendum enim facilisis gravida neque convallis. Eros in cursus turpis massa tincidunt. Varius sit amet mattis vulputate enim nulla. Mauris in aliquam sem fringilla ut. Augue neque gravida in fermentum. Parturient montes nascetur ridiculus mus mauris vitae ultricies. Magnis dis parturient montes nascetur ridiculus mus mauris vitae. Vel facilisis volutpat est velit egestas dui id ornare. Enim praesent elementum facilisis leo vel fringilla est. Vel quam elementum pulvinar etiam non quam lacus suspendisse faucibus. Urna id volutpat lacus laoreet non curabitur gravida. Gravida rutrum quisque non tellus orci ac auctor augue. Quis viverra nibh cras pulvinar mattis. Risus ultricies tristique nulla aliquet enim tortor. Placerat vestibulum lectus mauris ultrices eros. Quisque non tellus orci ac auctor augue mauris. Aliquet sagittis id consectetur purus ut faucibus. Mauris pellentesque pulvinar pellentesque habitant. A iaculis at erat pellentesque adipiscing commodo elit at imperdiet. Eget aliquet nibh praesent tristique magna sit amet purus. Proin nibh nisl condimentum id venenatis a condimentum. Volutpat ac tincidunt vitae semper quis lectus nulla at volutpat. Platea dictumst quisque sagittis purus sit amet volutpat consequat. A diam maecenas sed enim ut sem viverra aliquet eget. Iaculis eu non diam phasellus. Nullam eget felis eget nunc lobortis mattis. Cursus mattis molestie a iaculis at erat pellentesque adipiscing. Volutpat lacus laoreet non curabitur gravida arcu ac tortor. Ut porttitor leo a diam. Sed nisi lacus sed viverra tellus in hac habitasse platea. Odio ut sem nulla pharetra diam sit. Netus et malesuada fames ac turpis egestas integer eget. Enim facilisis gravida neque convallis a cras semper. Nunc sed id semper risus in hendrerit gravida. Egestas quis ipsum suspendisse ultrices gravida dictum. Adipiscing vitae proin sagittis nisl rhoncus mattis. Ut tortor pretium viverra suspendisse potenti nullam. In fermentum et sollicitudin ac. Ipsum dolor sit amet consectetur. In egestas erat imperdiet sed euismod nisi porta lorem. Pulvinar neque laoreet suspendisse interdum. Urna id volutpat lacus laoreet non curabitur gravida arcu. Ultricies tristique nulla aliquet enim tortor at auctor. Euismod quis viverra nibh cras pulvinar mattis. Quisque id diam vel quam elementum pulvinar etiam non quam. Enim eu turpis egestas pretium aenean pharetra magna ac placerat. Turpis nunc eget lorem dolor sed viverra ipsum. Morbi tristique senectus et netus et malesuada. Tincidunt dui ut ornare lectus sit amet est. Nunc consequat interdum varius sit amet mattis. Tristique risus nec feugiat in fermentum posuere urna nec tincidunt. Malesuada bibendum arcu vitae elementum curabitur. Sit amet facilisis magna etiam tempor orci eu lobortis. Et tortor consequat id porta. Varius duis at consectetur lorem donec massa sapien faucibus. Urna condimentum mattis pellentesque id nibh. Sit amet mauris commodo quis imperdiet massa tincidunt nunc pulvinar. Egestas sed tempus urna et pharetra pharetra massa massa ultricies. Purus in massa tempor nec feugiat. Auctor augue mauris augue neque gravida in fermentum et sollicitudin. Nunc congue nisi vitae suscipit tellus mauris a diam maecenas. Pretium viverra suspendisse potenti nullam ac tortor vitae purus faucibus. Felis bibendum ut tristique et egestas quis ipsum. Id venenatis a condimentum vitae sapien pellentesque. Aenean sed adipiscing diam donec. Imperdiet proin fermentum leo vel orci porta non pulvinar. Bibendum arcu vitae elementum curabitur vitae. Sit amet nulla facilisi morbi tempus iaculis urna. Consectetur a erat nam at lectus urna duis convallis. Scelerisque fermentum dui faucibus in ornare quam viverra orci. Ac turpis egestas integer eget aliquet nibh praesent tristique magna. Aenean et tortor at risus viverra adipiscing at. Vitae sapien pellentesque habitant morbi. Suspendisse interdum consectetur libero id faucibus nisl tincidunt eget nullam. Mattis rhoncus urna neque viverra justo nec ultrices dui sapien. Nunc vel risus commodo viverra maecenas accumsan lacus vel facilisis. Facilisis leo vel fringilla est. Cursus euismod quis viverra nibh cras pulvinar mattis. Nisl condimentum id venenatis a condimentum vitae. Nunc eget lorem dolor sed viverra ipsum nunc aliquet bibendum. Tristique senectus et netus et malesuada fames ac turpis egestas. At urna condimentum mattis pellentesque id nibh tortor. In nisl nisi scelerisque eu ultrices vitae. Est sit amet facilisis magna etiam. Pellentesque habitant morbi tristique senectus et netus et malesuada. Amet nisl purus in mollis nunc sed id. Et leo duis ut diam quam nulla. Integer quis auctor elit sed vulputate mi. Eu ultrices vitae auctor eu. Pretium vulputate sapien nec sagittis aliquam malesuada. Fringilla urna porttitor rhoncus dolor purus. Eu augue ut lectus arcu bibendum at varius vel pharetra. Diam sit amet nisl suscipit adipiscing bibendum est. Velit euismod in pellentesque massa. Mauris vitae ultricies leo integer. Lectus arcu bibendum at varius. Porttitor rhoncus dolor purus non enim. Eget mi proin sed libero enim. Ultricies integer quis auctor elit sed vulputate mi. Sit amet risus nullam eget. Faucibus scelerisque eleifend donec pretium vulputate sapien nec. Ac tincidunt vitae semper quis lectus nulla at volutpat. Tristique senectus et netus et malesuada fames ac turpis. Amet venenatis urna cursus eget nunc scelerisque viverra mauris. Platea dictumst quisque sagittis purus sit. Sed pulvinar proin gravida hendrerit lectus a. Odio ut enim blandit volutpat maecenas volutpat blandit aliquam. Dictum fusce ut placerat orci nulla pellentesque. Leo urna molestie at elementum eu facilisis sed. Felis imperdiet proin fermentum leo vel. Pretium vulputate sapien nec sagittis aliquam. Tincidunt arcu non sodales neque sodales ut etiam sit amet. Enim praesent elementum facilisis leo vel fringilla est. Quam viverra orci sagittis eu volutpat odio. Ridiculus mus mauris vitae ultricies leo integer malesuada nunc vel. Iaculis eu non diam phasellus vestibulum lorem sed risus ultricies. Enim ut sem viverra aliquet eget sit amet tellus. Quis commodo odio aenean sed adipiscing diam donec adipiscing tristique. Dignissim convallis aenean et tortor at risus viverra adipiscing. Augue ut lectus arcu bibendum. Quis hendrerit dolor magna eget est lorem. Ornare massa eget egestas purus viverra accumsan in nisl nisi. Est ullamcorper eget nulla facilisi etiam dignissim. Felis bibendum ut tristique et egestas quis ipsum. Nisi porta lorem mollis aliquam ut porttitor leo. Suscipit adipiscing bibendum est ultricies integer quis auctor elit sed. Duis ultricies lacus sed turpis tincidunt id. Tellus pellentesque eu tincidunt tortor aliquam. Quis risus sed vulputate odio ut enim blandit volutpat. Nullam ac tortor vitae purus faucibus. Tempus quam pellentesque nec nam aliquam sem et tortor. Mattis aliquam faucibus purus in massa tempor nec feugiat. In cursus turpis massa tincidunt. Egestas purus viverra accumsan in nisl. Aenean pharetra magna ac placerat vestibulum lectus mauris ultrices. Sit amet massa vitae tortor condimentum lacinia quis. Arcu dictum varius duis at consectetur lorem donec massa sapien. Urna nunc id cursus metus aliquam eleifend mi. Eget nunc lobortis mattis aliquam faucibus purus in. Cras adipiscing enim eu turpis egestas pretium aenean pharetra magna. Senectus et netus et malesuada fames. Tortor at auctor urna nunc id cursus metus aliquam eleifend. Dignissim sodales ut eu sem integer vitae justo eget. Massa sapien faucibus et molestie. Cursus metus aliquam eleifend mi in nulla posuere. Velit egestas dui id ornare arcu odio ut sem. Ornare lectus sit amet est placerat in egestas. Volutpat lacus laoreet non curabitur gravida arcu ac tortor. Sed euismod nisi porta lorem mollis aliquam ut porttitor. Nulla facilisi nullam vehicula ipsum. Erat velit scelerisque in dictum. Scelerisque purus semper eget duis at tellus at urna condimentum. Quam vulputate dignissim suspendisse in est ante in. Mi in nulla posuere sollicitudin aliquam. Vitae semper quis lectus nulla at volutpat diam ut venenatis. Nulla pharetra diam sit amet nisl suscipit. Facilisis mauris sit amet massa vitae tortor condimentum. Sit amet nisl suscipit adipiscing bibendum est ultricies integer quis. Vel elit scelerisque mauris pellentesque pulvinar pellentesque habitant. Sed nisi lacus sed viverra tellus. Aliquet bibendum enim facilisis gravida neque convallis a cras semper. In fermentum et sollicitudin ac orci phasellus egestas tellus. Etiam sit amet nisl purus. Viverra nibh cras pulvinar mattis nunc. Sed vulputate mi sit amet. Sodales ut eu sem integer vitae justo eget. In hac habitasse platea dictumst quisque sagittis. Imperdiet proin fermentum leo vel orci. Amet mauris commodo quis imperdiet massa tincidunt. Eget nulla facilisi etiam dignissim. Morbi tristique senectus et netus et malesuada. Ipsum dolor sit amet consectetur adipiscing elit pellentesque. Eu turpis egestas pretium aenean. Tellus in metus vulputate eu scelerisque felis. Metus aliquam eleifend mi in nulla posuere sollicitudin. Donec massa sapien faucibus et molestie ac feugiat sed lectus. Egestas pretium aenean pharetra magna ac placerat vestibulum lectus mauris. Turpis egestas maecenas pharetra convallis posuere morbi leo. Vulputate dignissim suspendisse in est ante in nibh. Vitae ultricies leo integer malesuada nunc vel risus. Venenatis tellus in metus vulputate eu scelerisque felis. Nulla facilisi nullam vehicula ipsum a arcu cursus vitae congue. In pellentesque massa placerat duis ultricies lacus. Odio ut enim blandit volutpat maecenas. Duis at consectetur lorem donec massa sapien faucibus. In dictum non consectetur a erat nam at lectus urna. Etiam non quam lacus suspendisse faucibus interdum posuere. Pellentesque sit amet porttitor eget dolor morbi non. Id aliquet risus feugiat in ante. Nisl nunc mi ipsum faucibus vitae aliquet nec. Quis vel eros donec ac odio. Senectus et netus et malesuada. Convallis tellus id interdum velit laoreet id donec. Porttitor lacus luctus accumsan tortor posuere ac ut consequat. Ut ornare lectus sit amet est placerat in. Quis auctor elit sed vulputate mi sit amet. Nulla facilisi nullam vehicula ipsum a arcu cursus. In fermentum et sollicitudin ac orci phasellus. Sagittis purus sit amet volutpat consequat. Sagittis orci a scelerisque purus. Quisque non tellus orci ac auctor augue mauris. Mattis molestie a iaculis at erat pellentesque adipiscing commodo. Diam sit amet nisl suscipit adipiscing bibendum est ultricies. Montes nascetur ridiculus mus mauris vitae. Lacus vel facilisis volutpat est velit egestas dui id. Purus gravida quis blandit turpis cursus in. Pretium aenean pharetra magna ac. Lobortis elementum nibh tellus molestie nunc non. At auctor urna nunc id cursus metus aliquam eleifend. Nam at lectus urna duis. Venenatis urna cursus eget nunc. Dignissim cras tincidunt lobortis feugiat vivamus at augue eget. Interdum posuere lorem ipsum dolor. Aliquet lectus proin nibh nisl condimentum id. Libero id faucibus nisl tincidunt eget nullam non nisi est. Ut ornare lectus sit amet. Eu consequat ac felis donec et odio pellentesque diam volutpat. Sed ullamcorper morbi tincidunt ornare massa eget egestas purus. Ullamcorper dignissim cras tincidunt lobortis feugiat vivamus. Sociis natoque penatibus et magnis dis parturient montes. Libero justo laoreet sit amet cursus sit amet dictum. Diam maecenas ultricies mi eget mauris pharetra et ultrices. Ut lectus arcu bibendum at varius vel pharetra vel. Ac felis donec et odio pellentesque diam. Molestie at elementum eu facilisis sed. Velit aliquet sagittis id consectetur purus. Quis auctor elit sed vulputate mi sit amet. Urna et pharetra pharetra massa massa ultricies mi. Condimentum mattis pellentesque id nibh tortor. Accumsan in nisl nisi scelerisque eu ultrices vitae. Nunc lobortis mattis aliquam faucibus purus in massa tempor nec. Tempus iaculis urna id volutpat lacus laoreet non. Lectus sit amet est placerat in egestas erat imperdiet sed. Faucibus pulvinar elementum integer enim neque volutpat ac tincidunt vitae. Odio ut enim blandit volutpat maecenas volutpat. Velit laoreet id donec ultrices tincidunt arcu non sodales. Porttitor rhoncus dolor purus non enim praesent elementum. Neque egestas congue quisque egestas diam in arcu cursus. Tellus id interdum velit laoreet id. Pharetra vel turpis nunc eget lorem dolor sed viverra. Sollicitudin nibh sit amet commodo nulla. Nulla facilisi morbi tempus iaculis urna id volutpat lacus. Pretium viverra suspendisse potenti nullam ac tortor vitae. Arcu risus quis varius quam quisque id diam vel quam. Donec ultrices tincidunt arcu non sodales neque. In cursus turpis massa tincidunt dui ut ornare lectus sit. Quis vel eros donec ac odio. Netus et malesuada fames ac turpis egestas maecenas pharetra convallis. In nulla posuere sollicitudin aliquam ultrices sagittis orci. Scelerisque viverra mauris in aliquam sem fringilla. Sit amet aliquam id diam maecenas ultricies mi eget mauris. Eros in cursus turpis massa. Integer vitae justo eget magna fermentum. Mauris a diam maecenas sed. Faucibus interdum posuere lorem ipsum dolor sit amet consectetur adipiscing. Sapien et ligula ullamcorper malesuada proin libero nunc. Rhoncus aenean vel elit scelerisque mauris pellentesque. Ut diam quam nulla porttitor massa id neque aliquam vestibulum. Integer feugiat scelerisque varius morbi enim nunc faucibus a. Dictum varius duis at consectetur lorem donec massa sapien. Faucibus turpis in eu mi. Nec feugiat nisl pretium fusce. Sit amet risus nullam eget. Et malesuada fames ac turpis egestas integer eget. Massa vitae tortor condimentum lacinia quis vel eros donec ac. Netus et malesuada fames ac turpis. Odio aenean sed adipiscing diam donec adipiscing. Adipiscing elit ut aliquam purus. Pellentesque diam volutpat commodo sed egestas egestas fringilla. Eu facilisis sed odio morbi. Dignissim diam quis enim lobortis scelerisque. Gravida neque convallis a cras. Gravida neque convallis a cras. Egestas integer eget aliquet nibh praesent tristique magna. Tempus egestas sed sed risus pretium quam vulputate. Gravida quis blandit turpis cursus in hac habitasse platea. Id aliquet lectus proin nibh. Urna id volutpat lacus laoreet non curabitur gravida arcu ac. Maecenas volutpat blandit aliquam etiam erat velit scelerisque in. Cras semper auctor neque vitae. Convallis convallis tellus id interdum velit laoreet id donec. Nam libero justo laoreet sit amet cursus sit amet. Etiam dignissim diam quis enim lobortis. Tortor at risus viverra adipiscing at in tellus. Sagittis aliquam malesuada bibendum arcu. Nisi scelerisque eu ultrices vitae auctor eu augue. Magna eget est lorem ipsum dolor sit amet consectetur adipiscing. A diam maecenas sed enim. Quam id leo in vitae turpis massa sed elementum tempus. Nec nam aliquam sem et tortor consequat. Aenean sed adipiscing diam donec adipiscing tristique risus. Turpis egestas maecenas pharetra convallis posuere morbi leo urna molestie. Elementum eu facilisis sed odio morbi. Massa sed elementum tempus egestas. Habitant morbi tristique senectus et netus et malesuada. Amet commodo nulla facilisi nullam vehicula ipsum. Tristique magna sit amet purus gravida quis. Euismod quis viverra nibh cras pulvinar. At lectus urna duis convallis convallis tellus id. Neque egestas congue quisque egestas diam in arcu cursus euismod. Laoreet suspendisse interdum consectetur libero id faucibus nisl tincidunt eget. Elit ullamcorper dignissim cras tincidunt. Tristique risus nec feugiat in fermentum posuere urna. Arcu dictum varius duis at consectetur lorem donec massa. Auctor eu augue ut lectus arcu bibendum at varius vel. Sit amet commodo nulla facilisi nullam vehicula ipsum a. Placerat duis ultricies lacus sed turpis tincidunt id aliquet risus. Diam volutpat commodo sed egestas egestas. Felis bibendum ut tristique et egestas quis ipsum suspendisse ultrices. Adipiscing enim eu turpis egestas pretium aenean pharetra magna ac. Semper eget duis at tellus at urna condimentum. Fames ac turpis egestas integer eget aliquet. Scelerisque mauris pellentesque pulvinar pellentesque habitant. Vitae congue eu consequat ac. At urna condimentum mattis pellentesque id nibh tortor id aliquet. Leo in vitae turpis massa sed elementum tempus egestas. Arcu cursus euismod quis viverra. Aliquet sagittis id consectetur purus ut faucibus pulvinar elementum. Molestie nunc non blandit massa enim nec dui nunc mattis. Diam quis enim lobortis scelerisque fermentum dui faucibus in. Vivamus arcu felis bibendum ut tristique. Sed odio morbi quis commodo odio aenean. Viverra maecenas accumsan lacus vel facilisis volutpat. Elementum tempus egestas sed sed risus pretium. Tristique senectus et netus et. Dictum at tempor commodo ullamcorper. Ac ut consequat semper viverra nam libero justo. Nec ullamcorper sit amet risus nullam eget. Tortor vitae purus faucibus ornare. Sollicitudin aliquam ultrices sagittis orci a scelerisque. Risus commodo viverra maecenas accumsan. Ullamcorper morbi tincidunt ornare massa eget egestas. Et netus et malesuada fames ac turpis egestas maecenas. Blandit cursus risus at ultrices mi tempus imperdiet. Pellentesque sit amet porttitor eget. Euismod in pellentesque massa placerat duis ultricies lacus sed. Quisque egestas diam in arcu cursus euismod quis. Amet venenatis urna cursus eget nunc scelerisque. Porttitor rhoncus dolor purus non enim praesent elementum. Diam donec adipiscing tristique risus nec feugiat in fermentum. Eu turpis egestas pretium aenean pharetra magna ac. Elit ut aliquam purus sit amet luctus. Porttitor rhoncus dolor purus non enim praesent elementum. Vulputate sapien nec sagittis aliquam malesuada bibendum arcu. Et pharetra pharetra massa massa. A arcu cursus vitae congue mauris. Sagittis id consectetur purus ut faucibus pulvinar elementum integer. Porttitor massa id neque aliquam vestibulum. Scelerisque eleifend donec pretium vulputate sapien nec sagittis. Habitasse platea dictumst quisque sagittis purus sit. Bibendum arcu vitae elementum curabitur vitae. Sed velit dignissim sodales ut eu sem integer vitae justo. Proin nibh nisl condimentum id. Leo duis ut diam quam nulla. Pharetra massa massa ultricies mi quis hendrerit. Quis ipsum suspendisse ultrices gravida. Lorem ipsum dolor sit amet consectetur adipiscing elit ut aliquam. Lacus sed viverra tellus in. Aliquam etiam erat velit scelerisque in dictum non. Lectus mauris ultrices eros in cursus. Nulla facilisi morbi tempus iaculis urna id volutpat lacus laoreet. In est ante in nibh mauris cursus mattis molestie a. Sapien eget mi proin sed libero. Orci phasellus egestas tellus rutrum tellus pellentesque eu. Mauris rhoncus aenean vel elit scelerisque mauris pellentesque pulvinar pellentesque. Sed odio morbi quis commodo odio. Malesuada fames ac turpis egestas. Commodo nulla facilisi nullam vehicula ipsum a. Consectetur adipiscing elit ut aliquam purus sit amet luctus. Nunc non blandit massa enim nec dui nunc mattis. Lorem ipsum dolor sit amet consectetur adipiscing elit duis. Malesuada proin libero nunc consequat interdum varius sit. Sit amet est placerat in egestas erat. Pellentesque massa placerat duis ultricies lacus sed turpis tincidunt. Turpis cursus in hac habitasse platea dictumst. Eu ultrices vitae auctor eu augue. Sed blandit libero volutpat sed cras ornare arcu dui vivamus. Aliquam sem et tortor consequat id porta nibh venenatis. Justo laoreet sit amet cursus sit amet. Neque viverra justo nec ultrices dui sapien. Dapibus ultrices in iaculis nunc sed. Lectus quam id leo in vitae turpis. Adipiscing vitae proin sagittis nisl rhoncus mattis. Nulla facilisi nullam vehicula ipsum a. Felis bibendum ut tristique et egestas quis. Viverra ipsum nunc aliquet bibendum enim facilisis gravida. Consequat interdum varius sit amet. Ut aliquam purus sit amet luctus venenatis lectus. Feugiat sed lectus vestibulum mattis ullamcorper. Ut tellus elementum sagittis vitae et leo duis. Id cursus metus aliquam eleifend mi in nulla. Amet est placerat in egestas erat imperdiet sed. Erat velit scelerisque in dictum non consectetur a. Risus nec feugiat in fermentum posuere urna. Suspendisse sed nisi lacus sed viverra tellus. Neque volutpat ac tincidunt vitae semper quis. Pretium lectus quam id leo in vitae. Mattis molestie a iaculis at erat. Ante metus dictum at tempor. Nulla pharetra diam sit amet nisl suscipit adipiscing bibendum. Ut lectus arcu bibendum at varius vel pharetra vel turpis. Tellus rutrum tellus pellentesque eu tincidunt tortor aliquam nulla. Amet purus gravida quis blandit turpis cursus in hac habitasse. Turpis nunc eget lorem dolor sed viverra ipsum. Vulputate ut pharetra sit amet aliquam. Leo integer malesuada nunc vel risus commodo viverra. Amet cursus sit amet dictum sit amet. Faucibus ornare suspendisse sed nisi lacus. Euismod lacinia at quis risus. Nec feugiat nisl pretium fusce id velit ut. Faucibus in ornare quam viverra orci sagittis eu volutpat odio. Magna fermentum iaculis eu non diam phasellus vestibulum lorem. Dui id ornare arcu odio. Enim eu turpis egestas pretium. Sit amet tellus cras adipiscing enim eu. Ultrices mi tempus imperdiet nulla malesuada. Nunc mattis enim ut tellus elementum sagittis vitae et leo. Lectus nulla at volutpat diam. Risus at ultrices mi tempus imperdiet. Amet est placerat in egestas erat imperdiet sed. Et malesuada fames ac turpis egestas sed tempus. Erat imperdiet sed euismod nisi porta lorem. Interdum posuere lorem ipsum dolor sit amet consectetur adipiscing elit. Habitant morbi tristique senectus et netus et. Tortor pretium viverra suspendisse potenti nullam. Netus et malesuada fames ac turpis egestas sed tempus urna. Aliquet risus feugiat in ante. Adipiscing elit duis tristique sollicitudin. Facilisis mauris sit amet massa vitae tortor. Eleifend donec pretium vulputate sapien nec sagittis aliquam malesuada bibendum. Urna neque viverra justo nec ultrices dui sapien eget. Commodo nulla facilisi nullam vehicula. Morbi tristique senectus et netus. Enim sed faucibus turpis in. Cras pulvinar mattis nunc sed blandit libero volutpat sed. Volutpat maecenas volutpat blandit aliquam etiam erat velit. Dui vivamus arcu felis bibendum ut tristique et. Vitae nunc sed velit dignissim sodales ut eu sem. Tempor commodo ullamcorper a lacus vestibulum sed arcu. In metus vulputate eu scelerisque felis imperdiet proin. Convallis tellus id interdum velit laoreet id donec ultrices tincidunt. Tortor consequat id porta nibh. In egestas erat imperdiet sed euismod nisi porta lorem mollis. Mattis molestie a iaculis at. Diam maecenas ultricies mi eget mauris pharetra. Id cursus metus aliquam eleifend mi."""
    txt = txt.replace(".", ".\n")
    nd = FileData(txt)

    # Definition of Parsers

    char = either(
        [satisfy(lambda c: c.isalnum(), "Alphanumeric Character"), character("_")]
    )
    space = either([character(" "), character("\n"), character(",")])
    spaces = atleast(space, 1) % "Spaces" >> (lambda x: "".join(x))
    word = atleast(char, 1) % "Word" >> (lambda x: "".join(x))
    seperated_words = (
        many((spaces & word) >> (lambda x: "".join(x))) % "Seperated Words"
    )
    sentence_body = (
        (word & ~(seperated_words))
        >> (lambda x: "".join([x[0]] + x[1]) if x[1] else x[0])
    ) % "Sentence Body"

    sentence = ((sentence_body <= character(".")) >> (lambda x: f"{x}.")) % "Sentence"

    text: Parser[list[str]] = (
        (sentence & many(spaces >= sentence)) >> (lambda x: [x[0]] + x[1])
    ) % "text"
    res = text(nd)
    assert isinstance(res, Success)
    assert res.val[1][-1] == "Id cursus metus aliquam eleifend mi."
    d = res.val[0]
    d._next_character_cursor()
    assert d.isEOF()


def test_string():
    nd = FileData("Reference!")
    parser = string("Reference!")
    res = parser(nd)
    assert res


def test_any():
    input = "123ojmfälasdkas+ ;-:"
    nd = FileData(input)
    res = many(any())(nd)
    assert res
    assert len(res.val[1]) == len(input)


def test_skip():
    space = satisfy(lambda c: c.isspace(), "Space")
    spaces = ignore(atleast(space, 1)) % "Spaces"

    p = many(satisfy(lambda c: c.isalnum(), "Character") | spaces) >> (
        lambda x: "".join([e for e in x if e])
    )
    nd = FileData("    asnbs   \n")
    res = p(nd)
    assert res.val[1] == "asnbs"
