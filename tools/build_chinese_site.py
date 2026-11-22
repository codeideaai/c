#!/usr/bin/env python3
"""Build the Chinese edition from the rendered English pages and a translation catalog."""

import copy
import json
import posixpath
import re
from html import escape
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from lxml import etree, html

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CATALOG = ROOT / "books/zh-CN/translations.json"
HOME = "index.html"
ENGLISH_HOME = "en/index.html"
ENGLISH_BOOK = "books/en-US/book.html"
CHINESE_HOME_ALIAS = "zh/index.html"
CHINESE_BOOK = "zh/book.html"
INLINE = {"a", "abbr", "b", "br", "code", "em", "i", "img", "kbd", "s",
          "small", "span", "strong", "sub", "sup", "u", "wbr"}
SKIP = {"pre", "script", "style", "svg", "code", "kbd", "samp", "template"}
TOKEN = re.compile(r"⟦(\d+)⟧")
UI = {
    "The Little Book of C": "C 语言小书",
    "The Book": "教程正文",
    "Content": "内容",
    "Table of contents": "目录",
    "Author": "作者",
    "Published": "发布日期",
    "May 26, 2026": "2026 年 5 月 26 日",
    "Version 0.5.0": "版本 0.5.0",
    "Duc-Tam Nguyen": "Duc-Tam Nguyen",
    "No results": "没有结果",
    "matching documents": "篇匹配文档",
    "Copy link to search": "复制搜索链接",
    "Hide additional matches": "隐藏其他匹配项",
    "more match in this document": "项其他匹配",
    "more matches in this document": "项其他匹配",
    "Clear": "清除",
    "Cancel": "取消",
    "Submit": "提交",
    "Search": "搜索",
    "Toggle dark mode": "切换深色模式",
    "Toggle sidebar navigation": "切换侧栏导航",
    "Copy to Clipboard": "复制到剪贴板",
    "Toggle reader mode": "切换阅读模式",
    "Previous page": "上一页",
    "Next page": "下一页",
    "breadcrumb": "当前位置",
    "navigation": "导航",
    "Download PDF": "下载英文 PDF",
    "Download EPUB": "下载英文 EPUB",
    "View LaTex": "查看英文 LaTeX",
    "Source code (Github)": "原作源码（GitHub）",
    "Read on GitHub Pages": "在线阅读英文原作",
    "A concise, structured guide to the C programming language.": "一本简明、结构清晰的 C 语言教程。",
    "Tiny Code": "代码示例",
    "Why It Matters": "为什么重要",
    "Try It Yourself": "动手练习",
}


def serialize(element, *, tail=False):
    return etree.tostring(element, encoding="unicode", method="html", with_tail=tail)


def text_key(text):
    return re.sub(r"\s+", " ", text).strip()


def segments(element):
    """Yield runs of text and inline markup. Leave code and scripts untouched."""
    if not isinstance(element.tag, str) or element.tag in SKIP:
        return
    start = None
    inline = []
    for child in element:
        if child.tag in INLINE and not any(
            descendant.tag == "svg" or descendant.tag not in INLINE
            for descendant in child.iterdescendants() if isinstance(descendant.tag, str)
        ):
            inline.append(child)
        else:
            yield element, start, inline
            yield from segments(child)
            start, inline = child, []
    yield element, start, inline


def segment_text(element, start, inline):
    tokens = []

    def marker(markup, opening=None):
        tokens.append((markup, opening))
        return f" ⟦{len(tokens) - 1}⟧ "

    def encode(child):
        if child.tag in SKIP or not child.text_content().strip():
            return marker(serialize(child))
        shell = copy.copy(child)
        shell.text = None
        del shell[:]
        markup = serialize(shell)
        opening, closing = markup.rsplit("</", 1)
        first_index = len(tokens)
        first = marker(opening, True)
        return (first + (child.text or "")
                + "".join(encode(item) + (item.tail or "") for item in child)
                + marker("</" + closing, first_index))

    initial = element.text if start is None else start.tail
    raw = (initial or "") + "".join(encode(child) + (child.tail or "") for child in inline)
    return text_key(raw), tokens


def restore(text, tokens):
    matches = [int(match[1]) for match in TOKEN.finditer(text)]
    if sorted(matches) != list(range(len(tokens))):
        raise ValueError("missing or duplicated markup in translation")
    stack = []
    for index in matches:
        kind = tokens[index][1]
        if kind is True:
            stack.append(index)
        elif kind is not None and (not stack or stack.pop() != kind):
            raise ValueError("unbalanced markup in translation")
    if stack:
        raise ValueError("unbalanced markup in translation")
    # Markers are padded for the translation engine. Trim padding next to
    # Chinese punctuation while leaving ordinary word boundaries in place.
    text = re.sub(r"(⟦\d+⟧) +([，。；：、！？）》）])", r"\1\2", text)
    text = re.sub(r"([（《]) +(⟦\d+⟧)", r"\1\2", text)
    return TOKEN.sub(lambda match: tokens[int(match[1])][0], escape(text))


def plain_segments(element, start, inline):
    """Provide individual strings when a translation cannot preserve inline markup."""
    yield (start if start is not None else element), ("tail" if start is not None else "text")
    for child in inline:
        for descendant in child.iter():
            if not any(parent.tag in SKIP for parent in [descendant, *descendant.iterancestors()]):
                yield descendant, "text"
            if descendant is child or not any(parent.tag in SKIP for parent in descendant.iterancestors()):
                yield descendant, "tail"


def translation_eligible(text):
    return bool(re.search(r"[A-Za-z]", TOKEN.sub("", text)))


def localize(document, lookup):
    sections = document.xpath("//main | //body//nav[not(ancestor::nav or ancestor::main)]")
    for section in sections:
        for element, start, inline in list(segments(section)):
            key, tokens = segment_text(element, start, inline)
            if not translation_eligible(key):
                continue
            translated = lookup(key)
            try:
                markup = restore(translated, tokens)
            except ValueError:
                translate_plain_segment(element, start, inline, lookup)
            else:
                replace_segment(element, start, inline, markup)


def translate_plain_segment(element, start, inline, lookup):
    for node, attribute in plain_segments(element, start, inline):
        value = getattr(node, attribute) or ""
        key = text_key(value)
        if translation_eligible(key):
            result = lookup(key)
            leading = value[:len(value) - len(value.lstrip())]
            trailing = value[len(value.rstrip()):]
            setattr(node, attribute, leading + result + trailing)


def replace_segment(element, start, inline, markup):
    fragment = html.fragment_fromstring(markup, create_parent="div")
    insertion = 0 if start is None else element.index(start) + 1
    if start is None:
        element.text = fragment.text
    else:
        start.tail = fragment.text
    for child in inline:
        element.remove(child)
    for offset, child in enumerate(list(fragment)):
        element.insert(insertion + offset, child)


def originals():
    root = (DOCS / HOME).read_text(encoding="utf-8")
    # Quarto renders the English landing page at the root. Between Quarto
    # builds, the retained English landing page is the translation source.
    home_source = HOME if html.document_fromstring(root).get("lang") == "en" else ENGLISH_HOME
    for source, english, chinese_pages in (
        (home_source, ENGLISH_HOME, (HOME, CHINESE_HOME_ALIAS)),
        (ENGLISH_BOOK, ENGLISH_BOOK, (CHINESE_BOOK,)),
    ):
        data = root if source == HOME else (DOCS / source).read_text(encoding="utf-8")
        data = re.sub(r'<nav class="edition-switch"[^>]*>.*?</nav>\n?', "", data, flags=re.S)
        data = re.sub(r'<script src="(?:\.\./)*edition-switch\.js" defer></script>\n?', "", data)
        yield source, english, chinese_pages, data


def rebase(document, source, destination, routes, search_offset):
    origin = posixpath.dirname(source) or "."
    target = posixpath.dirname(destination) or "."
    for element in document.xpath("//*[@href or @src]"):
        for attribute in ("href", "src"):
            url = urlsplit(element.get(attribute, ""))
            if not url.path or url.scheme or url.netloc or url.path.startswith("/"):
                continue
            resolved = posixpath.normpath(posixpath.join(origin, url.path))
            resolved = routes.get(HOME if resolved == "." else resolved, resolved)
            relative = posixpath.relpath(resolved, target)
            element.set(attribute, urlunsplit(("", "", relative, url.query, url.fragment)))
    document.xpath('//meta[@name="quarto:offset"]')[0].set("content", search_offset)


def chooser(source, destination, chinese=False, sidebar=False):
    target = posixpath.dirname(source) or "."
    if destination.endswith("index.html"):
        href = posixpath.relpath(posixpath.dirname(destination) or ".", target) + "/"
    else:
        href = posixpath.relpath(destination, target)
    label = "English" if chinese else "简体中文"
    language = "en" if chinese else "zh-CN"
    aria = "语言切换" if chinese else "Language switch"
    spacing = "mt-2" if sidebar else "mb-3"
    return (f'<nav class="edition-switch" aria-label="{aria}">'
            f'<a class="btn btn-outline-secondary btn-sm {spacing}" href="{href}" '
            f'hreflang="{language}" lang="{language}">{label}</a></nav>\n')


def edition_controls(data, source, destination, chinese=False):
    data, main_count = re.subn(
        r'(<main\b[^>]*>\s*)',
        lambda match: match[1] + chooser(source, destination, chinese), data, count=1,
    )
    data, sidebar_count = re.subn(
        r'(<div class="sidebar-title\b[^"]*"[^>]*>\s*<a\b[^>]*>.*?</a>)(\s*)',
        lambda match: match[1] + match[2] + chooser(source, destination, chinese, sidebar=True),
        data, count=1, flags=re.S,
    )
    if main_count != 1 or sidebar_count != 1:
        raise ValueError(f"could not install language links in {source}")
    script = posixpath.relpath("edition-switch.js", posixpath.dirname(source) or ".")
    return data.replace("</head>", f'<script src="{script}" defer></script>\n</head>', 1)


def search_entries(document, destination):
    href = posixpath.basename(destination)
    title = document.xpath("//main//h1")[0].text_content().strip()
    sections = document.xpath("//main//section[h2 or h3]")
    if not sections:
        sections = document.xpath("//main/section[h1]")
    for section in sections:
        heading = next(child for child in section if child.tag in {"h1", "h2", "h3"})
        chapter = text_key(heading.text_content())
        paragraphs = " ".join(text_key(p.text_content()) for p in section.xpath(".//p"))
        url = f"{href}#{section.get('id')}"
        yield {"href": url, "title": title, "section": chapter, "text": paragraphs, "objectID": url}


def clean_generated_html(data):
    # Preserve significant spacing in code blocks when removing HTML padding.
    def protect_code(match):
        return re.sub(r"[ ]+$", lambda padding: "&#32;" * len(padding[0]), match[0], flags=re.M)

    data = re.sub(r"<pre\b[^>]*>.*?</pre>", protect_code, data, flags=re.S)
    return re.sub(r"[ \t]+$", "", data, flags=re.M)


def build():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    search = []
    output = {}

    def lookup(key):
        try:
            return UI[key] if key in UI else catalog[key]
        except KeyError:
            raise ValueError(f"missing Chinese translation for {key!r}") from None

    for source, english, chinese_pages, data in originals():
        document = html.document_fromstring(data)
        localize(document, lookup)
        document.set("lang", "zh-CN")
        document.set("xml:lang", "zh-CN")
        document.find(".//title").text = (
            "C 语言小书" if english == ENGLISH_HOME else "教程正文 – C 语言小书"
        )
        for element in document.xpath("//*[@aria-label or @title]"):
            for attribute in ("aria-label", "title"):
                if element.get(attribute) in UI:
                    element.set(attribute, UI[element.get(attribute)])
        options = document.get_element_by_id("quarto-search-options")
        config = json.loads(options.text)
        config["language"] = {key: UI.get(value, value) for key, value in config["language"].items()}
        options.text = json.dumps(config, ensure_ascii=False, indent=2)
        main = document.find(".//main")
        main.insert(0, html.fragment_fromstring(
            '<p class="small text-body-secondary">简体中文译本（机器初译，经术语与文字校订） · 原著 Duc-Tam Nguyen · '
            '<a href="https://github.com/little-book-of/c">英文原作</a> · '
            '<a rel="license" href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a></p>'))

        for chinese in chinese_pages:
            page = copy.deepcopy(document)
            chinese_home = CHINESE_HOME_ALIAS if chinese == CHINESE_HOME_ALIAS else HOME
            routes = {HOME: chinese_home, ENGLISH_HOME: chinese_home, ENGLISH_BOOK: CHINESE_BOOK}
            rebase(page, source, chinese, routes, "./zh/" if chinese == HOME else "./")
            if chinese != HOME:
                search.extend(search_entries(page, chinese))
            markup = edition_controls(serialize(page), chinese, english, chinese=True)
            output[chinese] = "<!DOCTYPE html>\n" + clean_generated_html(markup) + "\n"

        if source == HOME:
            english_page = html.document_fromstring(data)
            rebase(english_page, source, english, {HOME: ENGLISH_HOME}, "../")
            data = "<!DOCTYPE html>\n" + clean_generated_html(serialize(english_page)) + "\n"
        elif source == ENGLISH_BOOK:
            data = re.sub(r'href="\.\./\.\./(?:index\.html)?"', 'href="../../en/index.html"', data)
            data = re.sub(r'(<a href="\.\./\.\./en/index\.html">[^<]+</a>)[ \t]+$', r"\1", data, flags=re.M)
        output[english] = edition_controls(data, english, chinese_pages[0])

    output["zh/search.json"] = json.dumps(search, ensure_ascii=False, indent=2) + "\n"
    english_search = (DOCS / "search.json").read_text(encoding="utf-8")
    output["search.json"] = re.sub(
        r'("(?:href|objectID)": ")index\.html(?=[#"])', r'\1en/index.html', english_search,
    )

    for relative_path, content in output.items():
        path = DOCS / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    build()
