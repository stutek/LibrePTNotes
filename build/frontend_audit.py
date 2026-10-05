# build/frontend_audit.py — HAND-WRITTEN, repo-specific static checks. This is NOT a third-party
# security scanner and nothing installs it: stdlib Python (os + re) living in this repo.
#
# Single responsibility: find unescaped user text reaching an HTML sink, and prove the production
# CSP is not weaker than the one the dev server serves.
#
# What it is NOT: it does not parse JavaScript and performs no dataflow or taint analysis. It is a
# regex heuristic over template literals, tuned for PRECISION (a maintained list of free-text field
# names) so that its findings are always worth acting on.
#
# Why these two:
#   • The OWASP ZAP baseline is a PASSIVE scan of what crosses the network; it never sees client
#     text (client names, notes, an imported backup) being rendered. The app builds DOM through
#     textContent today (src/ui/dom.js), so this audit is the tripwire for the day someone
#     reaches for innerHTML.
#   • ZAP scans the DEV SERVER, which sends security headers as real HTTP headers. GitHub Pages
#     cannot send custom headers at all, so production's policy is only the <meta> CSP in
#     index.html. A green scan would otherwise certify a posture production does not have.

import os
import re

# Fields a trainer (or an imported backup file) controls the text of. Interpolating one of these
# into HTML without escapeHTML is the bug class this audit exists to stop.
# MAINTENANCE: a precision-first allowlist, not a taint analysis; add a field here when the data
# model gains a new free-text property.
USER_TEXT_FIELDS = (
    "name",
    "clientName",
    "text",
    "body",
    "content",
    "note",
    "notes",
    "title",
    "label",
)

HTML_SINK = re.compile(r"(innerHTML\s*=|insertAdjacentHTML\()")
INTERPOLATION = re.compile(r"\$\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")
FIELD_REFERENCE = re.compile(r"\b(?:%s)\b" % "|".join(USER_TEXT_FIELDS))
# Escaped at the sink.
ALREADY_SAFE = re.compile(r"escapeHTML\(")
# `const title = escapeHTML(item.title)` then `${title}` is safe. Without this, escaping-at-assignment
# reads as a finding, and an audit that cries wolf gets suppressed rather than fixed.
ESCAPED_ASSIGNMENT = (
    r"(?:const|let|var)\s+%s\s*=[^;]*escapeHTML\(|%s\s*=[^;]*escapeHTML\("
)
BARE_IDENTIFIER = re.compile(r"^[A-Za-z_$][\w$]*$")


def _walk_js_files(root):
    for directory, _subdirs, names in os.walk(root):
        for name in sorted(names):
            if name.endswith(".js"):
                yield os.path.join(directory, name)


def _escaped_locally(expression, source):
    if not BARE_IDENTIFIER.match(expression):
        return False
    name = re.escape(expression)
    return re.search(ESCAPED_ASSIGNMENT % (name, name), source) is not None


def _scan_sink_line(lines, index, source):
    """Walk the template literal that follows a sink line (line `index`) for unescaped user-text
    interpolations, from the sink until its closing backtick (bounded, so a malformed file cannot
    run away with the scan). Returns [(line_number, expression), ...]."""
    findings = []
    backticks = 0
    for offset in range(index, min(index + 80, len(lines))):
        text = lines[offset]
        backticks += text.count("`")
        for expression in INTERPOLATION.findall(text):
            expression = expression.strip()
            if ALREADY_SAFE.search(expression) or _escaped_locally(expression, source):
                continue
            if FIELD_REFERENCE.search(expression):
                findings.append((offset + 1, expression[:90]))
        if backticks >= 2 and offset > index:
            break
    return findings


def _scan_file_for_unescaped_sinks(path):
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    lines = source.splitlines()
    findings = []
    for index, line in enumerate(lines):
        if not HTML_SINK.search(line):
            continue
        for line_no, expression in _scan_sink_line(lines, index, source):
            findings.append((path, line_no, expression))
    return findings


def _dedupe_by_expression(findings):
    """One report per distinct expression; the same helper repeated is one problem, not five."""
    seen = set()
    unique = []
    for finding in findings:
        if finding[2] in seen:
            continue
        seen.add(finding[2])
        unique.append(finding)
    return unique


def audit_html_sinks(root="src"):
    """Every unescaped interpolation of a user-text field into an HTML sink, as
    (path, line_number, expression) — empty when the tree is clean."""
    findings = []
    for path in _walk_js_files(root):
        findings.extend(_scan_file_for_unescaped_sinks(path))
    return _dedupe_by_expression(findings)


def parse_csp(policy):
    """A CSP string as {directive: value}."""
    directives = {}
    for part in policy.split(";"):
        part = part.strip()
        if not part:
            continue
        name, _, value = part.partition(" ")
        directives[name.strip()] = value.strip()
    return directives


# A <meta http-equiv> CSP cannot express these; the browser ignores them there. They therefore exist
# ONLY on the dev server, and production (GitHub Pages, which cannot send headers) goes without.
META_UNSUPPORTED = ("frame-ancestors", "report-uri", "report-to", "sandbox")


def compare_csp(header_policy, meta_policy):
    """(weaker, header_only) — directives where the production <meta> policy is weaker than the dev
    header, and directives that a meta tag structurally cannot carry.

    `weaker` is a build failure: it means the scanned posture is better than the shipped one.
    `header_only` is reported, not failed — it is a hosting limitation to accept knowingly.
    """
    header = parse_csp(header_policy)
    meta = parse_csp(meta_policy)
    weaker = []
    header_only = []
    for directive, value in header.items():
        if directive in META_UNSUPPORTED:
            header_only.append(directive)
        elif directive not in meta:
            weaker.append(f"{directive} missing from the <meta> policy")
        elif set(meta[directive].split()) > set(value.split()):
            weaker.append(
                f"{directive} is more permissive in <meta>: {meta[directive]!r}"
            )
    return weaker, header_only


META_CSP_TAG = re.compile(
    r"<meta\b[^>]*http-equiv\s*=\s*[\"']Content-Security-Policy[\"'][^>]*>", re.I
)
META_CONTENT = re.compile(
    r"\bcontent\s*=\s*\"([^\"]*)\"|\bcontent\s*=\s*'([^']*)'", re.I
)


def meta_csp(html):
    """The policy in index.html's <meta http-equiv="Content-Security-Policy"> tag, whatever order
    its attributes are in, or None when the page ships none."""
    tag = META_CSP_TAG.search(html)
    content = META_CONTENT.search(tag.group(0)) if tag else None
    return (content.group(1) or content.group(2) or "") if content else None
