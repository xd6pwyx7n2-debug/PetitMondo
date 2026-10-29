#!/usr/bin/env python3
"""Récupère depuis OpenStreetMap les services utiles aux familles pour chaque ville.

Lancé chaque semaine par GitHub Actions (.github/workflows/osm.yml).
Sortie : data/osm/<ville>.json, lu par le site.
Données © contributeurs OpenStreetMap, licence ODbL.
"""
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Catégorie -> filtres Overpass
CATEGORIES = {
    "toilettes": ['nwr["amenity"="toilets"]'],
    "aire_jeux": ['nwr["leisure"="playground"]'],
    "table_langer": ['nwr["changing_table"="yes"]', 'nwr["diaper"="yes"]'],
    "pharmacie": ['nwr["amenity"="pharmacy"]'],
    "resto_enfants": [
        'nwr["amenity"~"^(restaurant|cafe|fast_food)$"]["highchair"="yes"]',
        'nwr["amenity"~"^(restaurant|cafe|fast_food)$"]["kids_area"="yes"]',
    ],
}

TAGS_UTILES = [
    "name", "opening_hours", "fee", "wheelchair", "changing_table",
    "changing_table:location", "changing_table:fee", "diaper", "unisex",
    "highchair", "kids_area", "min_age", "max_age", "surface", "access",
    "amenity", "leisure", "website",
]


def requete(bbox):
    s, w, n, e = bbox
    corps = []
    for filtres in CATEGORIES.values():
        for f in filtres:
            corps.append(f"{f}({s},{w},{n},{e});")
    return "[out:json][timeout:180];(" + "".join(corps) + ");out center tags;"


def appel(q):
    data = urllib.parse.urlencode({"data": q}).encode()
    derniere = None
    for url in ENDPOINTS:
        for essai in range(3):
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "PetitMondo/1.0 (github.com/xd6pwyx7n2-debug/PetitMondo)"})
                with urllib.request.urlopen(req, timeout=240) as r:
                    return json.load(r)
            except Exception as exc:  # noqa: BLE001
                derniere = exc
                time.sleep(10 * (essai + 1))
    raise RuntimeError(f"Overpass injoignable : {derniere}")


def categorie(tags):
    if tags.get("changing_table") == "yes" or tags.get("diaper") == "yes":
        if tags.get("amenity") == "toilets":
            return "table_langer"
        if tags.get("amenity") not in ("restaurant", "cafe", "fast_food"):
            return "table_langer"
    if tags.get("amenity") == "toilets":
        return "toilettes"
    if tags.get("leisure") == "playground":
        return "aire_jeux"
    if tags.get("amenity") == "pharmacy":
        return "pharmacie"
    if tags.get("amenity") in ("restaurant", "cafe", "fast_food"):
        return "resto_enfants"
    return None


def main():
    villes = sorted((ROOT / "data" / "villes").glob("*.json"))
    sortie = ROOT / "data" / "osm"
    sortie.mkdir(parents=True, exist_ok=True)
    erreurs = 0
    for fichier in villes:
        ville = json.loads(fichier.read_text(encoding="utf-8"))
        print(f"→ {ville['nom']}")
        try:
            res = appel(requete(ville["bbox"]))
        except RuntimeError as exc:
            print(f"  échec : {exc}", file=sys.stderr)
            erreurs += 1
            continue
        points = []
        vus = set()
        for el in res.get("elements", []):
            tags = el.get("tags", {})
            cat = categorie(tags)
            if not cat:
                continue
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if lat is None or lon is None:
                continue
            cle = (el["type"], el["id"])
            if cle in vus:
                continue
            vus.add(cle)
            points.append({
                "c": cat,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "osm": f"{el['type']}/{el['id']}",
                "t": {k: tags[k] for k in TAGS_UTILES if k in tags},
            })
        compte = {}
        for p in points:
            compte[p["c"]] = compte.get(p["c"], 0) + 1
        print("  ", compte)
        (sortie / f"{ville['id']}.json").write_text(json.dumps({
            "ville": ville["id"],
            "maj": time.strftime("%Y-%m-%d"),
            "source": "© contributeurs OpenStreetMap (ODbL)",
            "compte": compte,
            "points": points,
        }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    sys.exit(1 if erreurs == len(villes) else 0)


if __name__ == "__main__":
    main()
