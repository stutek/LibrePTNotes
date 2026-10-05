"""Urejevalnik z barvanjem: poravnava prosojnega textarea nad barvanim pre in barve Dark+/Light+."""

import pytest
from app_helpers import seed, wait_for_saved

MARKDOWN = (
    "# Naslov\n"
    "**krepko** in *ležeče* ter `koda`\n"
    "- seznam\n"
    "> citat\n"
    "[povezava](https://primer.si)\n"
    "```\nblok\n```\n"
    "Zelo dolga vrstica, ki se mora prelomiti na več vrstic, ker je ožja od telefona, "
    "in še ena, brez presledkov: " + "abcdefghij" * 12 + "\n"
)

COLORS = {
    # razred: (Dark+, Light+)
    "md-heading": ("rgb(86, 156, 214)", "rgb(128, 0, 0)"),
    "md-bold": ("rgb(86, 156, 214)", "rgb(0, 0, 128)"),
    "md-quote": ("rgb(106, 153, 85)", "rgb(0, 128, 0)"),
    "md-code": ("rgb(206, 145, 120)", "rgb(163, 21, 21)"),
    "md-link": ("rgb(55, 148, 255)", "rgb(0, 0, 255)"),
}


@pytest.fixture
def editor(page, base_url):
    seed(
        page,
        base_url,
        [{"name": "Ana", "notes": [{"date": "2026-10-01 09:00", "text": MARKDOWN}]}],
        tabs={"open": ["Ana"], "active": "Ana"},
    )
    page.wait_for_selector(".plan-peek-blanket .md-input")
    return page


def test_odseki_markdowna_imajo_razrede(editor):
    for cls in (
        "md-heading",
        "md-bold",
        "md-italic",
        "md-code",
        "md-marker",
        "md-quote",
        "md-link",
        "md-fence",
    ):
        assert editor.locator(f".plan-peek-blanket pre .{cls}").count() > 0, cls


def test_barvano_besedilo_je_enako_vpisanemu(editor):
    shown = editor.locator(".plan-peek-blanket pre").text_content()
    typed = editor.locator(".plan-peek-blanket .md-input").input_value()
    # pre ima za zaključnim prelomom vrstice presledek, da prelom vidi tudi pre.
    assert shown.removesuffix(" ") == typed


SIZES_JS = """() => {
  const pre = document.querySelector('.plan-peek-blanket pre');
  const area = document.querySelector('.plan-peek-blanket .md-input');
  return { scroll: area.scrollHeight, client: area.clientHeight,
           pre: pre.getBoundingClientRect().height, area: area.getBoundingClientRect().height };
}"""


def test_kratko_besedilo_ne_drsi_v_textarea(editor):
    sizes = editor.evaluate(SIZES_JS)
    assert sizes["scroll"] == sizes["client"]


def test_dolgo_besedilo_ima_pre_in_textarea_enako_visoko(editor):
    # Isti prelomi vrstic dajo isto višino; razlika bi pomenila, da kazalec ne stoji pod črko.
    editor.locator(".plan-peek-blanket .md-input").fill(
        "\n".join(MARKDOWN.splitlines() * 8)
    )
    sizes = editor.evaluate(SIZES_JS)
    assert sizes["scroll"] == sizes["client"]
    assert sizes["pre"] == sizes["area"]
    assert sizes["pre"] > 780


def test_zaključni_prelom_vrstice_ne_razvali_poravnave(editor):
    editor.locator(".plan-peek-blanket .md-input").fill(
        "\n".join(["vrstica"] * 40) + "\n\n\n"
    )
    sizes = editor.evaluate(SIZES_JS)
    assert sizes["scroll"] == sizes["client"]
    assert sizes["pre"] == sizes["area"]


@pytest.mark.parametrize("scheme,index", [("dark", 0), ("light", 1)])
def test_barve_sledijo_temi_telefona(editor, scheme, index):
    editor.emulate_media(color_scheme=scheme)
    for cls, colors in COLORS.items():
        color = editor.locator(f".plan-peek-blanket pre .{cls}").first.evaluate(
            "e => getComputedStyle(e).color"
        )
        assert color == colors[index], f"{cls} v temi {scheme}"


def test_tipkanje_obarva_in_shrani(editor):
    area = editor.locator(".plan-peek-blanket .md-input")
    area.fill("# Novo\nnavadno")
    assert editor.locator(".plan-peek-blanket pre .md-heading").inner_text() == "# Novo"
    wait_for_saved(editor, "Ana", ["# Novo\nnavadno"])


def test_besedilo_textarea_je_prosojno_a_vidno_kazalce(editor):
    style = editor.locator(".plan-peek-blanket .md-input").evaluate(
        "e => ({ color: getComputedStyle(e).color, caret: getComputedStyle(e).caretColor })"
    )
    assert style["color"] in ("rgba(0, 0, 0, 0)", "transparent")
    assert style["caret"] != style["color"]
