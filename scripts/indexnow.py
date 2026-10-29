#!/usr/bin/env python3
"""Signale à Bing (et aux moteurs IndexNow) les pages modifiées récemment, d'après sitemap.xml."""
import datetime
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLE = "770a5fbe2bf2e1bdcfe11d254e19ee23"
HOTE = "xd6pwyx7n2-debug.github.io"
URL = f"https://{HOTE}/PetitMondo/"


def main():
    jours = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    limite = (datetime.date.today() - datetime.timedelta(days=jours)).isoformat()
    xml = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    urls = [u for u, d in re.findall(r"<loc>(.*?)</loc><lastmod>(.*?)</lastmod>", xml) if d >= limite]
    if not urls:
        print("Rien à signaler.")
        return
    corps = json.dumps({"host": HOTE, "key": CLE, "keyLocation": f"{URL}{CLE}.txt", "urlList": urls[:10000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=corps,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"{len(urls)} pages signalées, réponse {r.status}")


if __name__ == "__main__":
    main()
