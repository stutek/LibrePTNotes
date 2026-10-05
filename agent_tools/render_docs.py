"""`python -m agent_tools.render_docs` — iz markdowna za uporabnika zgenerira HTML, ki se objavi.

Zakaj: stran o zasebnosti mora delovati brez povezave (aplikacija je namenjena delu v telovadnici
brez signala) in živeti na domeni, ki je naša; povezava na github.com ne izpolni nobenega od
obeh in odpelje trenerja na razvijalsko stran. Zato `PRIVACY.md` ostane izvor (v grafu dokumentov, z
doclinks), v `src/` pa se objavi samo generirana `privacy.html`.

**Markdown ostane kanoničen in zunaj `src/`**, ker se `src/` objavi in predpomni v celoti. Izhod gre
v `src/` in je commitan: strežnik za razvoj streže `src/`, stran samo v `dist/` bi bila nevidna
lokalnemu delu in testom. Commit generiranega izhoda je manjše zlo, `main()` pa ga naredi pošteno:
vedno ponovno izriše in pade ob razliki, kot preverjanje oblike.

**Varnostna drža** — izhod gre v produkcijo, zato je izris nastavljen na najožje, ne najbogatejše:

  * `html=False`: surov HTML v izvoru se ZAMENJA (escape), nikoli ne preide. Podan izrecno, ker
    predloga `commonmark` HTML omogoča in posodobitev knjižnice ga ne sme tiho vklopiti.
  * markdown-it sam zavrne `javascript:` in druge nevarne sheme povezav.
  * Ovojnica strani ima `default-src 'none'` in ne nalaga skript: dokumenti ne potrebujejo
    nobenega izvajanja, strožje kot lastna politika aplikacije.

Uporaba: `python -m agent_tools.render_docs` preveri (0 = ažurno), `--write` zapiše strani.
`main(["--write"])` zapiše, `main()` samo preveri.
"""

import html
import re
import sys
from pathlib import Path, PurePosixPath

from markdown_it import MarkdownIt

from agent_tools._tree import ROOT
from agent_tools.doclinks import split_frontmatter

# (izvor, izhod, <title>). Vrstica pomeni objavljen dokument; kontrola ga drži usklajenega.
# Samo to, do česar trener pride iz aplikacije; README, TODO in docs/ so za razvijalce.
DOCUMENTS = (("PRIVACY.md", "src/privacy.html", "LibrePTNotes: zasebnost"),)

REPO_BLOB_URL = "https://github.com/stutek/LibrePTNotes/blob/main"
BACK_LINK_TEXT = "Nazaj v LibrePTNotes"
PAGE_CSP = (
    "default-src 'none'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
    "base-uri 'none'; form-action 'none'"
)
FENCE_LINE = re.compile(r"^\s*(```|~~~)")
COMMENT = re.compile(r"<!--.*?-->[ \t]*\n?", re.DOTALL)


def build_renderer():
    """markdown-it za izhod, ki se objavi: brez surovega HTML, brez pametnih zamenjav, tabele da.

    `linkify` in `typographer` sta izključena: oba prepišeta besedilo, ki ga avtor ni napisal, in
    pri izjavi o zasebnosti je natančno besedilo del dogovora.
    """
    renderer = MarkdownIt(
        "commonmark", {"html": False, "linkify": False, "typographer": False}
    )
    renderer.enable("table")
    return renderer


def strip_comments(body):
    """Brez `<!-- … -->` zunaj kodnih blokov: opomba urejevalcu ni besedilo za bralca."""
    kept, prose, in_fence = [], [], False
    for line in body.splitlines(keepends=True):
        if FENCE_LINE.match(line):
            if not in_fence:
                kept.append(COMMENT.sub("", "".join(prose)))
                prose = []
            in_fence = not in_fence
            kept.append(line)
        elif in_fence:
            kept.append(line)
        else:
            prose.append(line)
    kept.append(COMMENT.sub("", "".join(prose)))
    return "".join(kept)


def rewrite_link(href, source_name):
    """Poveži povezavo tako, da deluje s objavljene strani.

    Dokumenti se povezujejo kot datoteke repozitorija (`index.md`, `docs/modules.md`); na ravnem
    `src/` je vsaka taka pot 404. Dva cilja, ki sta izčrpna za relativne povezave: objavljen
    dokument postane sosednja stran (trener ostane v aplikaciji, brez povezave), vse drugo
    absolutna povezava na GitHub (izven aplikacije, pravilno za datoteko za razvijalce).
    Absolutne povezave, `mailto:` in sidra ostanejo.
    """
    if not href or href.startswith(("http://", "https://", "mailto:", "#")):
        return href
    href, _, anchor = href.partition("#")
    anchor = f"#{anchor}" if anchor else ""
    if not href:
        return anchor
    parts = []
    for part in (PurePosixPath(source_name).parent / href).parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    repo_relative = "/".join(parts)
    for source, output, _title in DOCUMENTS:
        if source == repo_relative:
            return f"./{PurePosixPath(output).name}{anchor}"
    return f"{REPO_BLOB_URL}/{repo_relative}{anchor}"


def rewrite_links(rendered, source_name):
    """`rewrite_link` na vsakem href; razkodira pred in zakodira enkrat po, da `&` ne postane `&amp;amp;`."""
    return re.sub(
        r'href="([^"]*)"',
        lambda m: 'href="{}"'.format(
            html.escape(
                rewrite_link(html.unescape(m.group(1)), source_name), quote=True
            )
        ),
        rendered,
    )


def render_page(markdown_text, title, source_name="PRIVACY.md"):
    """Celoten HTML dokument za en izvor; pri vsakem zagonu bajt za bajtom isti."""
    metadata, body = split_frontmatter(markdown_text)
    page_title = metadata.get("title", "").strip("\"'") or title
    content = rewrite_links(
        build_renderer().render(strip_comments(body.lstrip("\n"))), source_name
    )
    return (
        "<!doctype html>\n"
        '<html lang="sl">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta http-equiv="Content-Security-Policy" content="{PAGE_CSP}">\n'
        f"<title>{html.escape(page_title)}</title>\n"
        '<link rel="stylesheet" href="./docs.css">\n'
        "</head>\n"
        "<body>\n"
        '<main class="doc">\n'
        f"{content}"
        "</main>\n"
        f'<p class="doc-back"><a href="./index.html">{BACK_LINK_TEXT}</a></p>\n'
        "</body>\n"
        "</html>\n"
    )


def render_all(root=None, write=False, documents=None):
    """Zapiši (ali preveri) vsako stran. Vrne poti, ki so bile zastarele ali jih ni bilo."""
    root = Path(root if root is not None else ROOT)
    stale = []
    for source_name, output_name, title in (
        documents if documents is not None else DOCUMENTS
    ):
        rendered = render_page(
            (root / source_name).read_text(encoding="utf-8"), title, source_name
        )
        output = root / output_name
        if output.exists() and output.read_text(encoding="utf-8") == rendered:
            continue
        stale.append(output_name)
        if write:
            output.write_text(rendered, encoding="utf-8")
    return stale


def main(argv=None, root=None):
    write = "--write" in (argv or [])
    stale = render_all(root, write=write)
    if write:
        for path in stale:
            print(f"  ✓ Zapisano {path}")
        if not stale:
            print(f"  ✓ Dokumenti: {len(DOCUMENTS)} stran ažurnih.")
        return 0
    if stale:
        print("  ✗ Generirane strani dokumentov niso ažurne:")
        for path in stale:
            print(f"      {path}")
        print("    Zapiši jih: python -m agent_tools.render_docs --write")
        return 1
    print(f"  ✓ Dokumenti: {len(DOCUMENTS)} stran ažurnih.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
