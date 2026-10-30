"""Сайттың толық статикалық көшірмесін docs/ ішіне жасайды (GitHub Pages үшін).

    python freeze.py

Әр бет үш күйде (қонақ, aruzhan пайдаланушысы, admin) және екі тілде (kk, ru)
сақталады. Сілтемелер салыстырмалы, сондықтан сайт кез келген папкадан ашылады.
Серверсіз жұмыс істемейтін бөліктерді (сүзгі, кіру, формалар) static.js алмастырады.
"""

import html
import json
import os
import posixpath
import re
import shutil
import sys
import tempfile
from collections import Counter, deque
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit

from config import Config

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs")
KEEP = {"screenshots", "about", ".nojekyll"}  # docs/ ішінде қолмен жасалған файлдар
BASE_URL = "/jobboard-mini/docs/"  # 404.html кез келген тереңдікте ашылады, сондықтан <base> керек

STATES = {"guest": None, "user": "aruzhan", "admin": "admin"}
STATE_PREFIX = {"guest": "", "user": "u/", "admin": "a/"}
LANGS = ("kk", "ru")
NOT_FOUND = "/__not_found__"
SEEDS = ["/", "/vacancies", "/companies", "/auth/login", "/auth/register", "/auth/profile", NOT_FOUND]
CLIENT_SIDE = {"/vacancies"}  # бұл беттің сүзгісін static.js браузерде жасайды
MAX_VARIANTS = 100  # бір бет үшін ?параметрлі нұсқалар саны
FILE_TYPES = {"application/json": ".json", "application/pdf": ".pdf"}


def norm(path):
    return path.rstrip("/") or "/"


def canonical(query):
    pairs = sorted((k, v) for k, v in parse_qsl(query) if v and k != "csrf_token")
    return "&".join(f"{k}={v}" for k, v in pairs)


def fnv(text):
    """FNV-1a 32 бит — static.js ішіндегімен бірдей."""
    h = 0x811C9DC5
    for b in text.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def prefix(state, lang):
    return ("ru/" if lang == "ru" else "") + STATE_PREFIX[state]


def file_path(state, lang, npath, key, kind):
    if kind == "file":
        stem = prefix(state, lang) + npath.strip("/")
        return stem + (f"-q-{fnv(key)}" if key else "")
    folder = prefix(state, lang) + ("" if npath == "/" else npath.strip("/") + "/")
    return folder + (f"q-{fnv(key)}.html" if key else "index.html")


def relative(target, current):
    cur_dir = posixpath.dirname(current) or "."
    if target.endswith("index.html"):
        r = posixpath.relpath(posixpath.dirname(target) or ".", cur_dir)
        return "./" if r == "." else r + "/"
    return posixpath.relpath(target, cur_dir)


class LinkParser(HTMLParser):
    """<a href> сілтемелерін және GET формалардың әр select мәнімен жіберілетін URL-дерін жинайды."""

    def __init__(self, page_path):
        super().__init__()
        self.page_path = page_path
        self.links = []
        self.form = None  # (action, өрістер, select-тер)
        self.select = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href", "").startswith("/") and not a["href"].startswith("//"):
            self.links.append(a["href"])
        elif tag == "form" and (a.get("method") or "get").lower() == "get":
            self.form = (a.get("action") or self.page_path, {}, {})
        elif not self.form or not a.get("name") and tag != "option":
            return
        elif tag == "input" and a.get("type") not in ("checkbox", "radio", "submit", "button"):
            self.form[1][a["name"]] = a.get("value") or ""
        elif tag == "select":
            self.select = a["name"]
            self.form[2][self.select] = []
            self.form[1][self.select] = None
        elif tag == "option" and self.select:
            value = a.get("value") or ""
            self.form[2][self.select].append(value)
            if self.form[1][self.select] is None or "selected" in a:
                self.form[1][self.select] = value

    def handle_endtag(self, tag):
        if tag == "select":
            self.select = None
        elif tag == "form" and self.form:
            action, fields, selects = self.form
            self.form = None
            if urlsplit(action).path in CLIENT_SIDE:
                return
            # браузер жіберетіндей: басқа өрістер ағымдағы мәнімен, бір select өзгереді
            for name, options in selects.items():
                for value in options:
                    query = {**fields, name: value}
                    self.links.append(action + "?" + urlencode({k: v for k, v in query.items() if v}))


def crawl(app, state, lang):
    from app.models import User

    client = app.test_client()
    client.set_cookie("lang", lang)
    if STATES[state]:
        with app.app_context():
            user_id = User.query.filter_by(username=STATES[state]).one().id
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True

    found, seen, variants = {}, set(), Counter()
    queue = deque(SEEDS)
    while queue:
        url = queue.popleft()
        parts = urlsplit(url)
        npath, key = norm(parts.path), canonical(parts.query)
        if (npath, key) in seen or parts.path.startswith(("/static/", "/lang/")):
            continue
        if key and (npath in CLIENT_SIDE or variants[npath] >= MAX_VARIANTS):
            continue
        seen.add((npath, key))
        variants[npath] += bool(key)

        res = client.get(url)
        if 300 <= res.status_code < 400:
            loc = urlsplit(res.headers["Location"])
            target = loc.path + (f"?{loc.query}" if loc.query else "")
            if (norm(loc.path), canonical(loc.query)) == (npath, key):  # тек соңғы «/» айырмасы
                res = client.get(target)
            else:
                found[(npath, key)] = {"kind": "redirect", "location": target}
                queue.append(target)
                with client.session_transaction() as sess:  # flash келесі бетке өтпеуі үшін
                    sess.pop("_flashes", None)
                continue

        if res.mimetype == "text/html":
            text = res.get_data(as_text=True)
            found[(npath, key)] = {"kind": "html", "body": text}
            parser = LinkParser(parts.path)
            parser.feed(text)
            queue.extend(parser.links)
        else:
            found[(npath, key)] = {"kind": "file", "body": res.data, "ext": FILE_TYPES.get(res.mimetype, "")}
    return found


class Site:
    def __init__(self, results):
        self.results = results

    def target(self, state, lang, url):
        """URL → (docs/ ішіндегі файл, сақталатын query)."""
        parts = urlsplit(url)
        if parts.path.startswith("/static/"):
            return parts.path.lstrip("/"), None
        if parts.path.startswith("/lang/"):
            code = parts.path.rsplit("/", 1)[-1]
            nxt = dict(parse_qsl(parts.query)).get("next") or "/"
            return self.target(state, code if code in LANGS else lang, nxt)
        npath, key = norm(parts.path), canonical(parts.query)
        found = self.results[(state, lang)]
        if npath in CLIENT_SIDE:
            return file_path(state, lang, npath, "", "html"), parts.query or None
        if (npath, key) not in found:
            key = ""
        item = found.get((npath, key), {"kind": "html"})
        return file_path(state, lang, npath, key, item["kind"]) + item.get("ext", ""), None

    def link(self, state, lang, url, current):
        if not url.startswith("/") or url.startswith("//"):
            return url
        frag = "#" + url.split("#", 1)[1] if "#" in url else ""
        target, query = self.target(state, lang, url.split("#", 1)[0])
        return relative(target, current) + (f"?{query}" if query else "") + frag

    def render(self, state, lang, npath, body, current):
        def form_tag(m):
            tag = m.group(0)
            if 'method="post"' not in tag:
                return tag
            action = re.search(r'\saction="([^"]*)"', tag)
            original = urlsplit(html.unescape(action.group(1))).path if action else npath
            tag = re.sub(r'\saction="[^"]*"', "", tag)
            return tag[:-1] + f' data-static-action="{html.escape(original)}">'

        def attr(m):
            url = self.link(state, lang, html.unescape(m.group(2)), current)
            return f'{m.group(1)}{html.escape(url)}"'

        body = re.sub(r"<form\b[^>]*>", form_tag, body)
        body = re.sub(r'(\s(?:href|src|action)=")([^"]*)"', attr, body)
        root = relative("index.html", current)
        info = {"root": root, "lang": lang, "state": state, "path": npath}
        body = body.replace("</head>", f"<script>window.STATIC_SITE = {json.dumps(info, ensure_ascii=False)};</script>\n</head>", 1)
        return body.replace("</body>", f'<script src="{root}static/js/static.js"></script>\n</body>', 1)

    def write(self):
        for (state, lang), found in self.results.items():
            for (npath, key), item in found.items():
                if npath == NOT_FOUND:
                    continue
                name = file_path(state, lang, npath, key, item["kind"]) + item.get("ext", "")
                if item["kind"] == "html":
                    data = self.render(state, lang, npath, item["body"], name).encode("utf-8")
                elif item["kind"] == "redirect":
                    url = html.escape(self.link(state, lang, item["location"], name))
                    data = (f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={url}">'
                            f'<script>location.replace("{url}")</script>').encode("utf-8")
                else:
                    data = item["body"]
                save(name, data)

        page = self.results[("guest", "kk")][(NOT_FOUND, "")]["body"]
        page = self.render("guest", "kk", NOT_FOUND, page, "404.html")
        page = page.replace("<head>", f'<head>\n  <base href="{BASE_URL}">', 1)
        save("404.html", page.encode("utf-8"))
        # GitHub Pages репозиторий түбірінен берілгенде де 404 жұмыс істеуі үшін
        with open(os.path.join(ROOT, "404.html"), "wb") as fh:
            fh.write(page.encode("utf-8"))


def save(name, data):
    path = os.path.join(OUT, *name.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def main():
    tmp = tempfile.mkdtemp()

    class StaticConfig(Config):
        STATIC_EXPORT = True
        SECRET_KEY = "static-export"
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(tmp, "static.db").replace("\\", "/")
        UPLOAD_FOLDER = os.path.join(tmp, "cv")

    from app import create_app

    app = create_app(StaticConfig)
    result = app.test_cli_runner().invoke(args=["seed"])
    if result.exit_code:
        sys.exit(result.output)

    results = {(state, lang): crawl(app, state, lang) for state in STATES for lang in LANGS}

    os.makedirs(OUT, exist_ok=True)
    for entry in os.listdir(OUT):
        if entry not in KEEP:
            path = os.path.join(OUT, entry)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    shutil.copytree(os.path.join(ROOT, "app", "static"), os.path.join(OUT, "static"))
    Site(results).write()
    shutil.rmtree(tmp, ignore_errors=True)

    total = sum(len(found) for found in results.values())
    print(f"✓ docs/ ішіне {total} бет сақталды.")
    for (state, lang), found in results.items():
        print(f"  {state:6} {lang}: {len(found)}")


if __name__ == "__main__":
    main()
