"""Static, protocol-independent publication of the resident Commons."""
import html
import json
import time
import xml.etree.ElementTree as ET

import workshoplib as w

E = html.escape
SOURCE = "https://github.com/crypto-frog/kinwilder-workshop"


def publish(works, write, web, gemini, gopher, html_page, host="outpost.kinwilder.com"):
    cards, gmi, text = [], [], []
    for work in works:
        ident = work["author"] + "-" + work["slug"]
        picture = w.painted(work["frames"][0], work["colors"][0]) if work["frames"] else E("   .\n  /|\\\n /_|_\\\n   |\n  / \\")
        frames = []
        for i, frame in enumerate(work["frames"]):
            frames.append(f'<pre class="exhibit-frame" data-frame="{i}" aria-hidden="true"{ " hidden" if i else ""}>{w.painted(frame, work["colors"][i])}</pre>')
        preview = "".join(frames) if frames else f'<pre aria-hidden="true">{picture}</pre>'
        links = "".join(f'<li><a href="{E(link["url"], quote=True)}" rel="noreferrer">{E(link["title"])}</a><br>{E(link["note"])}</li>' for link in work["links"])
        downloads = " ".join(f'<a href="{work["url"]}{E(name, quote=True)}">[ {E(name)} ]</a>' for name in work["downloads"])
        archive = f'<a href="{work["url"]}source.zip">[ portable source ]</a>' if work["archive"] else ""
        cards.append(f'''<article class="commons-card" id="{ident}">
<p class="eyebrow">{E(work['kind'].upper())} / <a href="/~{work['author']}/">~{work['author']}</a></p>
<h2>{E(work['title'])}</h2><p>{E(work['summary'])}</p>
<div class="exhibit" data-interval="{work['interval_ms']}" role="img" aria-label="{E(work['title'], quote=True)}: resident-made ASCII exhibit">{preview}</div>
<p class="work-licence">{E(work['license'])}</p>
<details><summary>[ field notes / how it was made ]</summary><pre class="work-note">{E(work['note'])}</pre>{f'<ul>{links}</ul>' if links else ''}
<p class="work-downloads">{archive} {downloads}</p></details>
<p class="work-terminal"><code>workshop view {work['id']} --animate</code></p></article>''')
        lines = [f"## {work['title']}", f"by ~{work['author']} / {work['kind']} / {work['license']}", work["summary"], ""]
        if work["frames"]:
            lines += ["```ASCII exhibit", *work["frames"][0], "```", ""]
        lines += [work["note"], ""]
        for link in work["links"]:
            lines += [f"=> {link['url']} {link['title']}", link["note"]]
        if work["archive"]:
            lines += [f"=> https://{host}{work['url']}source.zip Portable source"]
        for name in work["downloads"]:
            lines += [f"=> https://{host}{work['url']}{name} {name}"]
        gmi += lines + [""]
        text += [f"{work['title']} — ~{work['author']}", work["summary"], ""]
        if work["frames"]:
            text += work["frames"][0] + [""]
        text += [work["note"], f"Licence: {work['license']}", f"Source: https://{host}{work['url']}source.zip" if work["archive"] else "", "-" * 40, ""]
    body = f'''<header class="commons-intro"><p class="eyebrow">A FIELD STATION FOR THE SMALL INTERNET</p>
<h1>The Kinwilder Commons</h1><p>Resident-built ASCII machines, field notes, tools and sound postcards.</p>
<p>The opening collection is by the sysop. Follow the source, then build your own.</p>
<p><a class="button" href="/fieldguide.html">[ start a project ]</a> <a href="/join">[ ask for a cabin ]</a></p>
<p class="commons-links"><a href="/contribute.html">contribute</a> / <a href="/community.html">the arrangement</a> / <a href="/commons/feed.xml">Atom feed</a> / <a href="gemini://{host}/commons.gmi">Gemini</a> / <a href="gopher://{host}/0/commons.txt">Gopher</a></p>
<aside class="weekly-invitation"><span class="eyebrow">THIS WEEK'S BRIEF</span><p>{E(w.prompt())}</p><small>Use it, bend it, ignore it.</small></aside>
<button id="commons-motion" hidden type="button">[ pause exhibits ]</button></header>
<div class="commons-grid">{''.join(cards) or '<p>The first projects are on their way.</p>'}</div>
<p>Made with <a href="{SOURCE}">the open-source Kinwilder Workshop</a>. Your account can build something that lives here.</p>
<script src="/commons.js?v=workshop1" defer></script>'''
    write(web / "commons/index.html", html_page("The Commons · Kinwilder Outpost", body,
          extra_head='<link rel="stylesheet" href="/commons.css?v=workshop1"><link rel="alternate" type="application/atom+xml" title="Kinwilder Commons" href="/commons/feed.xml">'))
    write(web / "commons/catalogue.json", json.dumps(dict(version=1, works=works), ensure_ascii=True, indent=1) + "\n")
    write(gemini / "commons.gmi", "# The Kinwilder Commons\n\nResident-built work.\n\n" + "\n".join(gmi) + f"\n=> https://{host}/fieldguide.html Open the field guide\n=> / Return to the Outpost\n")
    write(gopher / "commons.txt", "THE KINWILDER COMMONS\n\n" + "\n".join(text) + f"\nMake something: https://{host}/fieldguide.html\n")
    # No reader tracking or third-party feed service. Stable work IDs, actual update dates.
    ET.register_namespace("", "http://www.w3.org/2005/Atom")
    ns = "{http://www.w3.org/2005/Atom}"
    feed = ET.Element(ns + "feed")
    def add(parent, tag, value):
        ET.SubElement(parent, ns + tag).text = value
    add(feed, "title", "Kinwilder Commons")
    add(feed, "id", f"https://{host}/commons/")
    ET.SubElement(feed, ns + "link", href=f"https://{host}/commons/")
    ET.SubElement(feed, ns + "link", href=f"https://{host}/commons/feed.xml", rel="self")
    latest = max((work["updated"] for work in works), default=0)
    stamp = lambda value: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(value))
    add(feed, "updated", stamp(latest))
    for work in sorted(works, key=lambda item: item["updated"], reverse=True):
        item = ET.SubElement(feed, ns + "entry")
        add(item, "id", f"urn:kinwilder:workshop:{work['author']}:{work['slug']}")
        add(item, "title", work["title"])
        add(item, "updated", stamp(work["updated"]))
        author = ET.SubElement(item, ns + "author")
        add(author, "name", work["author"])
        ET.SubElement(item, ns + "link", href=f"https://{host}/commons/#{work['author']}-{work['slug']}")
        add(item, "summary", work["summary"])
    write(web / "commons/feed.xml", '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(feed, encoding="unicode") + "\n")
