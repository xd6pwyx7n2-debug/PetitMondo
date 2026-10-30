#!/usr/bin/env python3
"""Récupère des photos libres de droits (Wikimedia Commons) pour chaque lieu et chaque ville.

Pour chaque lieu, les champs « wiki » donnent des articles Wikipédia candidats
(« fr:Tour Eiffel », « en:Eiffel Tower »…). On prend l'image principale de l'article,
on vérifie sur Wikimedia Commons que sa licence est libre (CC0, domaine public, CC BY,
CC BY-SA), puis on télécharge une version de 1000 px de large avec son auteur et sa licence.

Sortie : assets/photos/<ville>/<lieu>.jpg et data/photos.json (crédits).
Lancé par GitHub Actions (.github/workflows/photos.yml). Les photos déjà présentes sont conservées.
"""
import html
import io
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "PetitMondo/1.0 (https://github.com/xd6pwyx7n2-debug/PetitMondo; guide de voyage familial)"
LICENCES_OK = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? ?\d|cc-by(-sa)?-\d|attribution)", re.I)
LARGEUR = 1000


def api(url, params):
    q = url + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    for essai in range(3):
        try:
            req = urllib.request.Request(q, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as exc:  # noqa: BLE001
            print("   réessai", exc, file=sys.stderr)
            time.sleep(3 * (essai + 1))
    return {}


def texte(v):
    """Retire le HTML des métadonnées Commons."""
    v = re.sub(r"<[^>]+>", "", v or "")
    return html.unescape(re.sub(r"\s+", " ", v)).strip()


def image_article(cand):
    lang, titre = cand.split(":", 1)
    d = api(f"https://{lang}.wikipedia.org/w/api.php",
            {"action": "query", "prop": "pageimages", "piprop": "name", "titles": titre, "redirects": 1})
    pages = d.get("query", {}).get("pages", [])
    if pages and pages[0].get("pageimage"):
        return pages[0]["pageimage"], f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(titre.replace(' ', '_'))}"
    return None, None


def infos_commons(nom):
    d = api("https://commons.wikimedia.org/w/api.php",
            {"action": "query", "prop": "imageinfo", "titles": "File:" + nom,
             "iiprop": "url|extmetadata|mime", "iiurlwidth": LARGEUR})
    pages = d.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing") or not pages[0].get("imageinfo"):
        return None  # image non hébergée sur Commons (souvent non libre) : on l'écarte
    ii = pages[0]["imageinfo"][0]
    # Seulement des photos : les PNG et les fichiers nommés « carte », « logo »… sont presque toujours
    # des cartes, des logos ou des schémas, qu'on ne veut pas en illustration.
    if ii.get("mime") not in ("image/jpeg", "image/webp"):
        return None
    if re.search(r"(map|mapa|karte|carte|plan|logo|locator|location|wappen|coat.of.arms|flag|drapeau)", nom, re.I):
        return None
    m = ii.get("extmetadata", {})
    licence = texte(m.get("LicenseShortName", {}).get("value"))
    if not LICENCES_OK.search(licence):
        return None
    return {
        "url": ii.get("thumburl") or ii.get("url"),
        "auteur": texte(m.get("Artist", {}).get("value")) or "Auteur inconnu",
        "licence": licence,
        "lien_licence": m.get("LicenseUrl", {}).get("value", ""),
        "source": ii.get("descriptionurl", ""),
    }


def telecharger(url, cible):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        brut = r.read()
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(brut)).convert("RGB")
        if im.width > LARGEUR:
            im = im.resize((LARGEUR, round(im.height * LARGEUR / im.width)))
        cible.parent.mkdir(parents=True, exist_ok=True)
        im.save(cible, "JPEG", quality=78, optimize=True, progressive=True)
        return im.width, im.height
    except ImportError:
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_bytes(brut)
        return None, None


def traiter(cle, candidats, cible, credits):
    if cle in credits and cible.exists():
        return
    for cand in candidats:
        nom, article = image_article(cand)
        if not nom:
            continue
        info = infos_commons(nom)
        if not info:
            print(f"   {cand} : image non libre ou absente, on passe")
            continue
        try:
            w, h = telecharger(info["url"], cible)
        except Exception as exc:  # noqa: BLE001
            print(f"   {cand} : téléchargement impossible ({exc})")
            continue
        credits[cle] = {"fichier": cible.relative_to(ROOT).as_posix(), "auteur": info["auteur"][:120],
                        "licence": info["licence"], "lien_licence": info["lien_licence"],
                        "source": info["source"], "article": article, "l": w, "h": h}
        print(f"   ok {cle} ← {nom} ({info['licence']})")
        time.sleep(0.5)
        return
    print(f"   aucune photo libre pour {cle}")


def main():
    fichier = ROOT / "data" / "photos.json"
    credits = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else {}
    for f in sorted((ROOT / "data" / "villes").glob("*.json")):
        v = json.loads(f.read_text(encoding="utf-8"))
        print("→", v["nom"])
        if v.get("photo"):
            traiter(f"{v['id']}/_ville", v["photo"], ROOT / "assets" / "photos" / v["id"] / "_ville.jpg", credits)
        for a in v["activites"]:
            if a.get("wiki"):
                traiter(f"{v['id']}/{a['id']}", a["wiki"], ROOT / "assets" / "photos" / v["id"] / f"{a['id']}.jpg", credits)
    fichier.write_text(json.dumps(credits, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(len(credits), "photos référencées")


if __name__ == "__main__":
    main()
