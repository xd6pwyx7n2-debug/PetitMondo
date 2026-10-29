#!/usr/bin/env python3
"""Récupère depuis OpenStreetMap les services et l'accessibilité utiles aux familles, pour chaque ville.

Lancé chaque semaine par GitHub Actions (.github/workflows/osm.yml).
Sorties :
  data/osm/<ville>.json   services (toilettes, aires de jeux, tables à langer, pharmacies,
                          restaurants équipés, eau potable, stations, ascenseurs)
  data/acces/<ville>.json fiche poussette de chaque lieu du guide (pavés, escaliers,
                          station la plus proche et son accessibilité, ascenseurs)
Données © contributeurs OpenStreetMap, licence ODbL.
"""
import json
import math
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "PetitMondo/1.0 (github.com/xd6pwyx7n2-debug/PetitMondo)"
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Services affichés sur les cartes
CATEGORIES = {
    "toilettes": ['nwr["amenity"="toilets"]'],
    "aire_jeux": ['nwr["leisure"="playground"]'],
    "table_langer": ['nwr["changing_table"="yes"]', 'nwr["diaper"="yes"]'],
    "pharmacie": ['nwr["amenity"="pharmacy"]'],
    "resto_enfants": [
        'nwr["amenity"~"^(restaurant|cafe|fast_food)$"]["highchair"="yes"]',
        'nwr["amenity"~"^(restaurant|cafe|fast_food)$"]["kids_area"="yes"]',
    ],
    "eau": ['nwr["amenity"="drinking_water"]'],
    "ascenseur": ['node["highway"="elevator"]'],
    "station": ['nwr["railway"="station"]', 'nwr["public_transport"="station"]["subway"="yes"]'],
}

# Terrain autour des lieux : seulement compté, pas affiché point par point
TERRAIN = {
    "paves": 'way["highway"]["surface"~"^(sett|cobblestone|unhewn_cobblestone)$"]',
    "marches": 'way["highway"="steps"]',
}

TAGS_UTILES = [
    "name", "opening_hours", "fee", "wheelchair", "changing_table",
    "changing_table:location", "changing_table:fee", "diaper", "unisex",
    "highchair", "kids_area", "access", "amenity", "leisure", "website",
    "railway", "station", "subway", "network", "highway",
]

RAYON_TERRAIN = 250   # m autour du lieu pour compter pavés et escaliers
RAYON_STATION = 900   # m pour chercher la station la plus proche
RAYON_ASCENSEUR = 400


def appel(q):
    data = urllib.parse.urlencode({"data": q}).encode()
    derniere = None
    for url in ENDPOINTS:
        for essai in range(3):
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=300) as r:
                    return json.load(r)
            except Exception as exc:  # noqa: BLE001
                derniere = exc
                time.sleep(15 * (essai + 1))
    raise RuntimeError(f"Overpass injoignable : {derniere}")


def bloc(filtres, bbox):
    s, w, n, e = bbox
    return "".join(f"{f}({s},{w},{n},{e});" for f in filtres)


def categorie(tags):
    resto = tags.get("amenity") in ("restaurant", "cafe", "fast_food")
    if (tags.get("changing_table") == "yes" or tags.get("diaper") == "yes") and not resto:
        return "table_langer"
    if tags.get("amenity") == "toilets":
        return "toilettes"
    if tags.get("leisure") == "playground":
        return "aire_jeux"
    if tags.get("amenity") == "pharmacy":
        return "pharmacie"
    if resto:
        return "resto_enfants"
    if tags.get("amenity") == "drinking_water":
        return "eau"
    if tags.get("highway") == "elevator":
        return "ascenseur"
    if tags.get("railway") == "station" or (tags.get("public_transport") == "station" and tags.get("subway") == "yes"):
        nom = tags.get("name", "")
        # écarte les gares de petits trains touristiques (parcs d'attractions, musées)
        if not nom or "railroad" in nom.lower() or tags.get("usage") == "tourism" or tags.get("railway:preserved") == "yes":
            return None
        return "station"
    return None


def position(el):
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lon = el.get("lon") or el.get("center", {}).get("lon")
    return (lat, lon) if lat is not None and lon is not None else None


def dist(a, b):
    r = math.pi / 180
    dlat, dlon = (b[0] - a[0]) * r, (b[1] - a[1]) * r
    x = math.sin(dlat / 2) ** 2 + math.cos(a[0] * r) * math.cos(b[0] * r) * math.sin(dlon / 2) ** 2
    return 2 * 6371e3 * math.asin(math.sqrt(x))


def services(ville):
    q = "[out:json][timeout:240];(" + "".join(bloc(f, ville["bbox"]) for f in CATEGORIES.values()) + ");out center tags;"
    res = appel(q)
    points, vus = [], set()
    for el in res.get("elements", []):
        tags = el.get("tags", {})
        cat = categorie(tags)
        pos = position(el)
        cle = (el["type"], el["id"])
        if not cat or not pos or cle in vus:
            continue
        vus.add(cle)
        points.append({"c": cat, "lat": round(pos[0], 6), "lon": round(pos[1], 6), "osm": f"{el['type']}/{el['id']}",
                       "t": {k: tags[k] for k in TAGS_UTILES if k in tags}})
    return points


def terrain(ville):
    q = "[out:json][timeout:240];(" + "".join(bloc([f], ville["bbox"]) for f in TERRAIN.values()) + ");out center tags;"
    res = appel(q)
    paves, marches = [], []
    for el in res.get("elements", []):
        pos = position(el)
        if not pos:
            continue
        (marches if el.get("tags", {}).get("highway") == "steps" else paves).append(pos)
    return paves, marches


def fiche_acces(ville, points, paves, marches):
    stations = [p for p in points if p["c"] == "station"]
    ascenseurs = [(p["lat"], p["lon"]) for p in points if p["c"] == "ascenseur"]
    fiches = {}
    for a in ville["activites"]:
        lieu = (a["lat"], a["lon"])
        f = {"paves": sum(1 for p in paves if dist(lieu, p) <= RAYON_TERRAIN),
             "marches": sum(1 for p in marches if dist(lieu, p) <= RAYON_TERRAIN),
             "ascenseurs": sum(1 for p in ascenseurs if dist(lieu, p) <= RAYON_ASCENSEUR)}
        proches = sorted(((dist(lieu, (s["lat"], s["lon"])), s) for s in stations), key=lambda x: x[0])
        if proches and proches[0][0] <= RAYON_STATION:
            d, s = proches[0]
            f["station"] = {"nom": s["t"].get("name"), "d": round(d), "fauteuil": s["t"].get("wheelchair", "inconnu"),
                            "lat": s["lat"], "lon": s["lon"], "osm": s["osm"]}
        fiches[a["id"]] = f
    return fiches


def main():
    villes = sorted((ROOT / "data" / "villes").glob("*.json"))
    (ROOT / "data" / "osm").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "acces").mkdir(parents=True, exist_ok=True)
    erreurs = 0
    for fichier in villes:
        ville = json.loads(fichier.read_text(encoding="utf-8"))
        print(f"→ {ville['nom']}")
        try:
            points = services(ville)
        except RuntimeError as exc:
            print(f"  services : échec ({exc})", file=sys.stderr)
            erreurs += 1
            continue
        compte = {}
        for p in points:
            compte[p["c"]] = compte.get(p["c"], 0) + 1
        print("  ", compte)
        (ROOT / "data" / "osm" / f"{ville['id']}.json").write_text(json.dumps({
            "ville": ville["id"], "maj": time.strftime("%Y-%m-%d"), "source": "© contributeurs OpenStreetMap (ODbL)",
            "compte": compte, "points": points,
        }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        time.sleep(5)
        try:
            paves, marches = terrain(ville)
            print(f"   terrain : {len(paves)} voies pavées, {len(marches)} escaliers")
        except RuntimeError as exc:
            print(f"  terrain : échec ({exc}), fiches poussette conservées", file=sys.stderr)
            continue
        (ROOT / "data" / "acces" / f"{ville['id']}.json").write_text(json.dumps({
            "ville": ville["id"], "maj": time.strftime("%Y-%m-%d"), "rayon": RAYON_TERRAIN,
            "lieux": fiche_acces(ville, points, paves, marches),
        }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        time.sleep(5)
    sys.exit(1 if erreurs == len(villes) else 0)


if __name__ == "__main__":
    main()
