"""render_docs: varen izris, popravljene povezave, preverjanje ažurnosti in zapis."""

from agent_tools import render_docs

DOC = '---\ntype: policy\ntitle: "Zasebnost"\ndescription: "D"\ntags: [a]\n---\n\n# Naslov\n\nBesedilo.\n'
DOCS = (("PRIVACY.md", "src/privacy.html", "Rezervni naslov"),)


def project(tmp_path, text=DOC):
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "PRIVACY.md").write_text(text, encoding="utf-8")
    return tmp_path


def page(text, source="PRIVACY.md"):
    return render_docs.render_page(text, "Rezervni naslov", source)


def test_page_is_slovenian_with_title_from_frontmatter_and_no_scripts():
    html = page(DOC)
    assert '<html lang="sl">' in html
    assert "<title>Zasebnost</title>" in html
    assert "<h1>Naslov</h1>" in html
    assert "<script" not in html
    assert "default-src 'none'" in html
    assert "./docs.css" in html


def test_title_falls_back_when_there_is_no_frontmatter():
    assert "<title>Rezervni naslov</title>" in page("# Samo naslov\n")


def test_raw_html_in_the_source_is_escaped_not_passed_through():
    html = page("# T\n\n<script>alert(1)</script> in <b>krepko</b>\n")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_dangerous_link_scheme_is_neutralised():
    html = page("[klik](javascript:alert(1))\n")
    assert 'href="javascript:' not in html


def test_editor_comments_never_reach_the_reader():
    html = page("Vidno.\n\n<!-- opomba urejevalcu -->\n\nTudi vidno.\n")
    assert "opomba" not in html
    assert "Tudi vidno." in html


def test_comment_inside_a_code_block_is_an_example_and_stays():
    html = page("```\n<!-- primer -->\n```\n")
    assert "&lt;!-- primer --&gt;" in html


def test_links_to_other_documents_become_absolute_but_published_ones_stay_siblings():
    assert (
        render_docs.rewrite_link("docs/modules.md#x", "PRIVACY.md")
        == f"{render_docs.REPO_BLOB_URL}/docs/modules.md#x"
    )
    assert (
        render_docs.rewrite_link("PRIVACY.md", "docs/x.md")
        == f"{render_docs.REPO_BLOB_URL}/docs/PRIVACY.md"
    )
    assert (
        render_docs.rewrite_link("../PRIVACY.md#kje", "docs/x.md")
        == "./privacy.html#kje"
    )
    assert (
        render_docs.rewrite_link("https://a.si/?x=1&y=2", "PRIVACY.md")
        == "https://a.si/?x=1&y=2"
    )
    assert render_docs.rewrite_link("#sidro", "PRIVACY.md") == "#sidro"


def test_ampersand_in_a_link_is_escaped_exactly_once():
    html = page("[a](https://a.si/?x=1&y=2)\n")
    assert 'href="https://a.si/?x=1&amp;y=2"' in html
    assert "&amp;amp;" not in html


def test_rendering_is_deterministic():
    assert page(DOC) == page(DOC)


def test_check_reports_missing_and_stale_pages_and_write_fixes_them(tmp_path):
    root = project(tmp_path)
    assert render_docs.render_all(root, documents=DOCS) == ["src/privacy.html"]
    assert render_docs.render_all(root, write=True, documents=DOCS) == [
        "src/privacy.html"
    ]
    assert render_docs.render_all(root, documents=DOCS) == []
    (root / "PRIVACY.md").write_text(DOC + "\nNov stavek.\n", encoding="utf-8")
    assert render_docs.render_all(root, documents=DOCS) == ["src/privacy.html"]


def test_main_check_fails_when_stale_and_write_makes_it_pass(tmp_path, monkeypatch):
    root = project(tmp_path)
    monkeypatch.setattr(render_docs, "DOCUMENTS", DOCS)
    assert render_docs.main(root=root) == 1
    assert render_docs.main(["--write"], root=root) == 0
    assert render_docs.main(root=root) == 0
    assert (root / "src" / "privacy.html").exists()
