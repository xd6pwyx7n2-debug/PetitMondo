#!/usr/bin/env python3
"""Génère la page guide statique de chaque ville (bon pour le référencement) à partir de data/villes/*.json.

Usage : python scripts/build_villes.py
"""
import html
import json
import pathlib
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "https://xd6pwyx7n2-debug.github.io/petitmondo/"
e = html.escape

INTERETS = {"animaux": "Animaux", "sciences": "Sciences", "aventure": "Aventure", "culture": "Culture",
            "parc": "Parcs", "plage": "Plage", "gourmand": "Gourmand"}


def badges(a):
    b = ['<span class="badge b">Couvert</span>' if a["interieur"] else '<span class="badge">Plein air</span>']
    if a["gratuit"] is True:
        b.append('<span class="badge o">Gratuit</span>')
    elif a["gratuit"] == "partiel":
        b.append('<span class="badge o">En partie gratuit</span>')
    if a["reservation"]:
        b.append('<span class="badge t">Réserver</span>')
    b.append({"facile": '<span class="badge">Poussette OK</span>',
              "moyen": '<span class="badge g">Poussette possible</span>',
              "difficile": '<span class="badge t">Porte-bébé conseillé</span>'}[a["poussette"]])
    return "".join(b)


def duree(m):
    return f"{m} min" if m < 60 else f"{m // 60} h {m % 60:02d}".replace(" 00", "")


def carte_act(a, v):
    maps = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(f"{a['nom']}, {a['adresse']}")
    site = f' <a href="{e(a["site"])}" target="_blank" rel="noopener">Site officiel</a>' if a.get("site") else ""
    return f'''<article class="carte act" data-min="{a["ages"][0]}" data-max="{a["ages"][1]}" data-int="{" ".join(a["interets"])}" data-couvert="{int(a["interieur"])}" data-gratuit="{int(a["gratuit"] is not False)}">
  <h3>{e(a["nom"])}</h3>
  <div class="meta">{a["ages"][0]} à {a["ages"][1]} ans · environ {duree(a["duree"])} · {e(v["zones"][a["zone"]]["nom"])}</div>
  <div class="badges">{badges(a)}</div>
  <p>{e(a["conseil"])}</p>
  <div class="liens"><a href="{maps}" target="_blank" rel="noopener">Voir sur la carte</a>{site}</div>
</article>'''


def page(v):
    n = v["nom"]
    acts = v["activites"]
    pluie = [a for a in acts if a["interieur"]]
    gratuits = [a for a in acts if a["gratuit"] is True]
    lien = lambda q: f"../carnet/#v={v['id']}&{q}"
    faq = [
        (f"Que faire à {n} avec un bébé ou un tout-petit ?",
         "Privilégiez les lieux plats et ombragés : " + ", ".join(a["nom"] for a in acts if a["ages"][0] <= 1 and a["poussette"] == "facile")
         + ". Prévoyez une pause sieste en début d'après-midi et un porte-bébé pour les sites en pente ou très fréquentés."),
        (f"Que faire à {n} avec des enfants quand il pleut ?",
         "Les meilleures options couvertes sont : " + ", ".join(a["nom"] for a in pluie) + "."),
        (f"Quelles activités gratuites à {n} avec des enfants ?",
         "Sans payer : " + ", ".join(a["nom"] for a in gratuits) + "."),
        (f"{n} est-elle adaptée à la poussette ?",
         "En grande partie oui dans le centre et en bord de mer. Les difficultés viennent de certaines stations de métro sans ascenseur, des ruelles anciennes et des sites en pente. "
         "Sites où le porte-bébé est plus pratique : " + ", ".join(a["nom"] for a in acts if a["poussette"] == "difficile") + "."),
    ]
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in faq]}
    filtres = "".join(f'<button class="chip" type="button" data-f="int:{k}" aria-pressed="false">{l}</button>' for k, l in INTERETS.items())
    return f'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(n)} avec des enfants : activités, itinéraires et carte pratique — PetitMondo</title>
<meta name="description" content="Visiter {e(n)} en famille : {len(acts)} activités classées par âge, jours de pluie, plages et parcs, toilettes, aires de jeux et tables à langer sur la carte. Carnet PDF gratuit.">
<link rel="canonical" href="{URL}{v["id"]}/">
<meta name="pm-base" content="../">
<meta name="theme-color" content="#FBF6EE">
<link rel="icon" href="../assets/logo.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="../assets/style.css">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<header class="top"><div class="wrap">
  <a class="logo" href="../"><img src="../assets/logo.svg" alt="" width="34" height="34">PetitMondo</a>
  <nav class="nav"><a class="hide-m" href="./">{e(n)}</a><a href="../carnet/">Créer mon carnet</a></nav>
</div></header>

<main>
<section class="hero" style="padding-bottom:16px"><div class="wrap">
  <span class="surtitre">{e(v["pays"])} · guide famille</span>
  <h1>{e(n)} avec des enfants</h1>
  <p class="lead">{len(acts)} activités sélectionnées et classées par âge, un plan B pour chaque jour de pluie, et la carte des toilettes, aires de jeux et tables à langer de la ville.</p>
  <div class="cta"><a class="btn" href="{lien("j=3&a=5&r=equilibre")}">Créer mon carnet pour {e(n)}</a><a class="btn sec" href="#carte">Voir la carte pratique</a></div>
</div></section>

<section style="padding-top:8px"><div class="wrap">
  <h2>Programmes prêts à partir</h2>
  <div class="carte-grille" style="margin-top:14px">
    <a class="carte" style="text-decoration:none;color:inherit" href="{lien("j=3&a=1&r=calme&p=1")}"><div class="ico s"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="7" r="3"/><path d="M7 21a5 5 0 0 1 10 0"/></svg></div><h3>3 jours avec un bébé</h3><p>Rythme tranquille, poussette, sieste prévue.</p></a>
    <a class="carte" style="text-decoration:none;color:inherit" href="{lien("j=3&a=4-7&r=equilibre&i=animaux-plage")}"><div class="ico t"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M12 3v18"/></svg></div><h3>3 jours avec 4 et 7 ans</h3><p>Animaux, plage et pauses aires de jeux.</p></a>
    <a class="carte" style="text-decoration:none;color:inherit" href="{lien("j=4&a=12-15&r=intense&i=aventure-culture")}"><div class="ico b"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 20 6-12 4 7 3-4 5 9z"/></svg></div><h3>4 jours avec des ados</h3><p>Gaudí, panoramas et aventure.</p></a>
    <a class="carte" style="text-decoration:none;color:inherit" href="{lien("j=2&a=6&r=equilibre&b=serre")}"><div class="ico o"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M9 9h5a2 2 0 0 1 0 4h-4a2 2 0 0 0 0 4h5M12 6v2m0 9v1"/></svg></div><h3>Week-end petit budget</h3><p>Priorité aux parcs, plages et lieux gratuits.</p></a>
  </div>
</div></section>

<section><div class="wrap">
  <h2>Activités par âge</h2>
  <div class="filtres" role="group" aria-label="Filtrer les activités">
    <label class="chip" style="display:inline-flex;align-items:center;gap:6px">Âge <select id="f-age" style="width:auto;padding:2px 6px;border:0;background:none"><option value="">tous</option>{"".join(f'<option value="{i}">{i} an{"s" if i > 1 else ""}</option>' for i in range(0, 18))}</select></label>
    <button class="chip" type="button" data-f="couvert" aria-pressed="false">Couvert</button>
    <button class="chip" type="button" data-f="gratuit" aria-pressed="false">Gratuit</button>
    {filtres}
  </div>
  <p id="f-vide" class="note" hidden>Aucune activité ne correspond à ces filtres.</p>
  <div class="carte-grille" id="liste">{"".join(carte_act(a, v) for a in acts)}</div>
</div></section>

<section><div class="wrap">
  <h2>{e(n)} avec des enfants quand il pleut</h2>
  <p style="color:var(--gris);max-width:46em">Les lieux couverts qui tiennent une matinée ou une après-midi entière, à garder en réserve :</p>
  <ul>{"".join(f"<li><strong>{e(a['nom'])}</strong> ({a['ages'][0]}–{a['ages'][1]} ans, environ {duree(a['duree'])}) : {e(a['conseil'])}</li>" for a in pluie)}</ul>
</div></section>

<section id="carte"><div class="wrap">
  <h2>La carte pratique des parents</h2>
  <p style="color:var(--gris);max-width:46em">Toilettes publiques, aires de jeux, tables à langer, pharmacies et restaurants signalés avec chaise haute ou coin enfants. Touchez un point pour lancer l'itinéraire.</p>
  <div class="filtres" id="calques"></div>
  <div id="map" aria-label="Carte des services pour les familles à {e(n)}"></div>
  <p class="note" id="osm-info" style="margin-top:12px">Chargement des données OpenStreetMap…</p>
</div></section>

<section><div class="wrap">
  <h2>Bon à savoir</h2>
  <div class="carte-grille">{"".join(f'<div class="carte"><h3>{e(c["titre"])}</h3><p>{e(c["texte"])}</p></div>' for c in v["conseils"])}</div>
  <h3 style="margin-top:28px">Urgences</h3>
  <ul>{"".join(f"<li><strong>{e(u['nom'])}</strong> : {e(u['detail'])}</li>" for u in v["urgences"])}</ul>
</div></section>

<section><div class="wrap">
  <h2>Questions fréquentes</h2>
  {"".join(f"<details class='carte' style='margin-bottom:10px'><summary style='font-weight:600;cursor:pointer'>{e(q)}</summary><p>{e(r)}</p></details>" for q, r in faq)}
  <p class="note" style="margin-top:18px">Fiches vérifiées le {"/".join(reversed(v["verification"].split("-")))}. {e(v["avertissement"])}</p>
  <div class="cta" style="margin-top:20px"><a class="btn" href="{lien("j=3&a=5&r=equilibre")}">Créer mon carnet pour {e(n)}</a></div>
</div></section>
</main>

<footer><div class="wrap">PetitMondo · Données cartographiques © <a href="https://www.openstreetmap.org/copyright">contributeurs OpenStreetMap</a></div></footer>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="../assets/commun.js"></script>
<script>window.PM_VILLE = "{v["id"]}";</script>
<script src="../assets/ville.js"></script>
</body>
</html>
'''


def main():
    urls = [URL, URL + "carnet/"]
    for f in sorted((ROOT / "data" / "villes").glob("*.json")):
        v = json.loads(f.read_text(encoding="utf-8"))
        d = ROOT / v["id"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(page(v), encoding="utf-8")
        urls.append(f"{URL}{v['id']}/")
        print("page :", d / "index.html")
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")


if __name__ == "__main__":
    main()
