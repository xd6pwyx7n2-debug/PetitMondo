#!/usr/bin/env python3
"""Génère toutes les pages statiques de PetitMondo à partir des données.

Usage : python scripts/build.py
Entrées : data/villes/*.json (activités sélectionnées), data/osm/*.json (services OpenStreetMap)
"""
import html
import json
import math
import pathlib
import urllib.parse
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "https://xd6pwyx7n2-debug.github.io/petitmondo/"
e = html.escape
PAGES = []  # (chemin, indexable)

VILLES_A_VENIR = [("Paris", "France"), ("Rome", "Italie"), ("Londres", "Royaume-Uni"),
                  ("Amsterdam", "Pays-Bas"), ("Lisbonne", "Portugal")]
INTERETS = {"animaux": "Animaux", "sciences": "Sciences", "aventure": "Aventure", "culture": "Culture",
            "parc": "Parcs", "plage": "Plage", "gourmand": "Gourmand"}
CAT_ICO = {"toilettes": "toilettes", "aire_jeux": "jeux", "table_langer": "langer",
           "pharmacie": "pharmacie", "resto_enfants": "resto"}
CAT_NOM = {"toilettes": "Toilettes", "aire_jeux": "Aire de jeux", "table_langer": "Table à langer",
           "pharmacie": "Pharmacie", "resto_enfants": "Restaurant équipé"}


# ---------------------------------------------------------------- outils
def rel(depth):
    return "../" * depth


def ico(nom, cls="i", base=""):
    return f'<svg class="{cls}" aria-hidden="true"><use href="{base}assets/sprite.svg#i-{nom}"/></svg>'


def dist(a, b):
    r = math.pi / 180
    dlat, dlon = (b["lat"] - a["lat"]) * r, (b["lon"] - a["lon"]) * r
    x = math.sin(dlat / 2) ** 2 + math.cos(a["lat"] * r) * math.cos(b["lat"] * r) * math.sin(dlon / 2) ** 2
    return 2 * 6371e3 * math.asin(math.sqrt(x))


def fmt_dist(m):
    return f"{round(m / 10) * 10} m" if m < 1000 else f"{m / 1000:.1f} km".replace(".", ",")


def duree(m):
    return f"{m} min" if m < 60 else f"{m // 60} h {m % 60:02d}".replace(" 00", "")


def maps(nom, adresse=None, lat=None, lon=None):
    q = f"{nom}, {adresse}" if adresse else f"{lat},{lon}"
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(q)


def date_fr(iso):
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    y, m, d = map(int, iso.split("-"))
    return f"{d} {mois[m - 1]} {y}"


def nom_point(p):
    return p["t"].get("name") or {"toilettes": "Toilettes publiques", "aire_jeux": "Aire de jeux",
                                  "table_langer": "Toilettes avec table à langer", "pharmacie": "Pharmacie",
                                  "resto_enfants": "Restaurant"}[p["c"]]


def detail_point(p):
    t, d = p["t"], []
    if t.get("fee") == "no": d.append("gratuit")
    elif t.get("fee") == "yes": d.append("payant")
    if t.get("changing_table") == "yes": d.append("table à langer")
    loc = t.get("changing_table:location", "")
    if "male_toilet" in loc and "female" not in loc or "unisex" in loc or "dedicated" in loc or "wheelchair" in loc:
        d.append("accessible aux papas")
    if t.get("highchair") == "yes": d.append("chaise haute")
    if t.get("kids_area") == "yes": d.append("coin enfants")
    if t.get("wheelchair") in ("yes", "designated"): d.append("accès fauteuil")
    return " · ".join(d)


def page(chemin, titre, desc, corps, depth, *, head="", scripts="", indexable=True, actif="", og_titre=None):
    b = rel(depth)
    PAGES.append((chemin, indexable))
    robots = "" if indexable else '<meta name="robots" content="noindex">'
    nav = [("barcelone/", "Barcelone", "barcelone"), ("valise/", "Valise", "valise"), ("barcelone/jeux/", "Jeux", "jeux")]
    nav_html = "".join(f'<a class="hide-m" href="{b}{h}"{" aria-current=page" if actif == k else ""}>{n}</a>' for h, n, k in nav)
    html_page = f'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(titre)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{URL}{chemin}">
{robots}
<meta name="pm-base" content="{b}">
<meta name="theme-color" content="#FFF8EC">
<meta property="og:title" content="{e(og_titre or titre)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{URL}{chemin}">
<meta property="og:image" content="{URL}assets/partage.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{b}assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{b}assets/icone-180.png">
<link rel="manifest" href="{b}manifest.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Figtree:wght@400;500;600;700;800&display=swap" rel="stylesheet">
{head}
<link rel="stylesheet" href="{b}assets/style.css">
</head>
<body>
<header class="top"><div class="wrap">
  <a class="logo" href="{b}"><img src="{b}assets/mondo.svg" alt="" width="36" height="42"><span>Petit<b>Mondo</b></span></a>
  <nav class="nav" aria-label="Navigation principale">{nav_html}<a class="cta-nav" href="{b}carnet/">Créer mon carnet</a></nav>
</div></header>
<main>
{corps}
</main>
<footer><div class="wrap">
  <div>
    <a class="logo" href="{b}"><img src="{b}assets/mondo.svg" alt="" width="36" height="42"><span>Petit<b style="color:var(--soleil)">Mondo</b></span></a>
    <p>Le monde à découvrir en famille. Des carnets de voyage gratuits, pensés du point de vue des parents.</p>
    <small>Données cartographiques © <a href="https://www.openstreetmap.org/copyright">contributeurs OpenStreetMap</a>, licence ODbL. Aucun cookie, aucun compte, rien n'est enregistré sur nos serveurs.</small>
  </div>
  <div><h4>Destinations</h4><ul><li><a href="{b}barcelone/">Barcelone en famille</a></li><li><a href="{b}barcelone/avec-un-bebe/">Barcelone avec un bébé</a></li><li><a href="{b}barcelone/quand-il-pleut/">Barcelone quand il pleut</a></li><li><a href="{b}barcelone/gratuit/">Barcelone gratuit</a></li></ul></div>
  <div><h4>Outils</h4><ul><li><a href="{b}carnet/">Créer mon carnet</a></li><li><a href="{b}valise/">Valise des enfants</a></li><li><a href="{b}barcelone/jeux/">Jeux à imprimer</a></li><li><a href="{b}barcelone/lexique/">Phrases utiles</a></li><li><a href="{b}methode/">Notre méthode</a></li></ul></div>
</div></footer>
{scripts}
<script>if('serviceWorker' in navigator)addEventListener('load',()=>navigator.serviceWorker.register('{b}sw.js').catch(()=>{{}}));</script>
</body>
</html>
'''
    cible = ROOT / chemin / "index.html" if not chemin.endswith(".html") else ROOT / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(html_page, encoding="utf-8")


def leaflet_head():
    return '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">'


def leaflet_scripts(b, ville_id, calques=None, extra=""):
    c = f"window.PM_CALQUES={json.dumps(calques)};" if calques else ""
    return (f'<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
            f'<script src="{b}assets/commun.js"></script>'
            f'<script>window.PM_VILLE="{ville_id}";{c}</script>{extra}'
            f'<script src="{b}assets/ville.js"></script>')


# ---------------------------------------------------------------- blocs
def badges(a):
    b = ['<span class="badge b">Couvert</span>' if a["interieur"] else '<span class="badge">Plein air</span>']
    if a["gratuit"] is True: b.append('<span class="badge s">Gratuit</span>')
    elif a["gratuit"] == "partiel": b.append('<span class="badge s">En partie gratuit</span>')
    if a["reservation"]: b.append('<span class="badge c">Réserver</span>')
    b.append({"facile": '<span class="badge l">Poussette OK</span>',
              "moyen": '<span class="badge g">Poussette possible</span>',
              "difficile": '<span class="badge c">Porte-bébé conseillé</span>'}[a["poussette"]])
    return "".join(b)


def carte_act(a, v, osm=None, b="../"):
    site = f'<a href="{e(a["site"])}" target="_blank" rel="noopener">Site officiel</a>' if a.get("site") else ""
    prox = ""
    if osm:
        li = []
        for c in ("toilettes", "aire_jeux", "table_langer"):
            pr = proches(osm, a, c, 1, 600)
            if pr:
                li.append(f'<li>{ico(CAT_ICO[c], "i s", b)}{CAT_NOM[c]} à {fmt_dist(pr[0][1])}</li>')
        if li:
            prox = f'<div class="proches"><ul>{"".join(li)}</ul></div>'
    return f'''<article class="carte act" data-min="{a["ages"][0]}" data-max="{a["ages"][1]}" data-int="{" ".join(a["interets"])}" data-couvert="{int(a["interieur"])}" data-gratuit="{int(a["gratuit"] is not False)}">
  <span class="badge tampon ages">{a["ages"][0]}–{a["ages"][1]} ans</span>
  <h3>{e(a["nom"])}</h3>
  <div class="meta">Environ {duree(a["duree"])} · {e(v["zones"][a["zone"]]["nom"])}</div>
  <div class="badges">{badges(a)}</div>
  <p>{e(a["conseil"])}</p>{prox}
  <div class="liens"><a href="{maps(a["nom"], a["adresse"])}" target="_blank" rel="noopener">Voir sur la carte</a>{site}</div>
</article>'''


def proches(osm, lieu, cat, n=3, maxi=800):
    if not osm:
        return []
    r = sorted(((p, dist(lieu, p)) for p in osm["points"] if p["c"] == cat), key=lambda x: x[1])
    return [x for x in r if x[1] <= maxi][:n]


def cartes_liens(liens, b):
    return '<div class="grille">' + "".join(
        f'<a class="carte {c}" href="{b}{h}">{ico(i, "i l", b)}<h3>{e(t)}</h3><p>{e(d)}</p><span class="suite">Voir {ico("fleche", "", b).replace("class=\"\"", "")}</span></a>'
        for h, i, t, d, c in liens) + "</div>"


def faq_html(faq):
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in faq]}
    return ("".join(f'<details class="carte"><summary>{e(q)}</summary><p>{e(r)}</p></details>' for q, r in faq)
            + f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>')


def carte_section(titre, texte, b, calques_ids=None):
    return f'''<section id="carte"><div class="wrap">
  <div class="tete-section"><div><h2>{titre}</h2><p>{texte}</p></div></div>
  <div class="filtres" id="calques"></div>
  <div id="map" aria-label="Carte interactive"></div>
  <p class="note" id="osm-info" style="margin-top:16px">Chargement des données OpenStreetMap…</p>
</div></section>'''


SEO = {
    "avec-un-bebe": "{n} avec un bébé : visites, tables à langer et conseils",
    "quand-il-pleut": "Que faire à {n} avec des enfants quand il pleut",
    "gratuit": "{n} gratuit en famille : parcs, plages et sorties sans billet",
    "avec-des-ados": "{n} avec des ados : que faire et que voir",
    "poussette": "Visiter {n} en poussette : ce qui roule et ce qui coince",
    "aires-de-jeux": "Aires de jeux à {n} : les plus proches de chaque visite",
    "toilettes-et-tables-a-langer": "Toilettes publiques et tables à langer à {n}",
    "restaurants-enfants": "Restaurants avec table à langer et chaise haute à {n}",
}


# ---------------------------------------------------------------- pages ville
def pages_ville(v, osm):
    vid, n = v["id"], v["nom"]
    acts = v["activites"]
    d1, d2 = 1, 2
    b1, b2 = rel(d1), rel(d2)
    compte = (osm or {}).get("compte", {})
    lien_carnet = lambda q, b: f"{b}carnet/#v={vid}&{q}"
    pluie = [a for a in acts if a["interieur"]]
    gratuits = [a for a in acts if a["gratuit"] is not False]
    bebe = [a for a in acts if a["ages"][0] <= 1]
    ados = [a for a in acts if a["ages"][1] >= 15 and a["ages"][0] >= 3]
    faciles = [a for a in acts if a["poussette"] == "facile"]
    difficiles = [a for a in acts if a["poussette"] == "difficile"]
    illu = f"{{b}}assets/villes/{vid}.svg"

    thematiques = [
        (f"{vid}/avec-un-bebe/", "bebe", f"{n} avec un bébé", "Lieux plats, siestes, tables à langer et toilettes.", "corail"),
        (f"{vid}/quand-il-pleut/", "pluie", "Quand il pleut", f"{len(pluie)} lieux couverts pour sauver la journée.", "ciel"),
        (f"{vid}/gratuit/", "gratuit", f"{n} gratuit", f"{len(gratuits)} sorties gratuites ou en partie gratuites.", "soleil"),
        (f"{vid}/avec-des-ados/", "ado", "Avec des ados", "Panoramas, Gaudí et aventure.", "menthe"),
        (f"{vid}/poussette/", "poussette", "En poussette", "Ce qui roule, ce qui coince, et les alternatives.", "lilas"),
        (f"{vid}/aires-de-jeux/", "jeux", "Aires de jeux", f"{compte.get('aire_jeux', 'Les')} aires recensées, les plus proches de chaque visite.", "menthe"),
        (f"{vid}/toilettes-et-tables-a-langer/", "langer", "Toilettes et tables à langer", "Où se changer et où trouver des toilettes.", "lilas"),
        (f"{vid}/restaurants-enfants/", "resto", "Restaurants équipés", "Table à langer, chaise haute ou coin enfants signalés.", "soleil"),
        (f"{vid}/jeux/", "jeu", "Jeux à imprimer", "Bingo, chasse au trésor et carnet d'explorateur.", "corail"),
        (f"{vid}/lexique/", "bulle", "Phrases utiles", "Espagnol et catalan pour les parents.", "ciel"),
    ]

    def hero(depth, surtitre, titre_html, lead, cta_q="j=3&a=5&r=equilibre"):
        b = rel(depth)
        return f'''<section class="hero"><div class="wrap grid">
  <div>
    <span class="etiquette"><i></i>{e(surtitre)}</span>
    <h1>{titre_html}</h1>
    <p class="lead">{lead}</p>
    <div class="cta"><a class="btn" href="{lien_carnet(cta_q, b)}">{ico("pdf", "", b).replace('class=""', '')}Créer mon carnet pour {e(n)}</a><a class="btn sec" href="#carte">Voir la carte pratique</a></div>
  </div>
  <div class="visuel"><img src="{illu.format(b=b)}" alt="" width="640" height="320" style="border-radius:22px;border:2.5px solid var(--nuit);box-shadow:var(--ombre)"><img class="mondo" src="{b}assets/mondo.svg" alt=""></div>
</div></section>'''

    def chiffres(b):
        items = [("activite", len(acts), "activités sélectionnées"), ("jeux", compte.get("aire_jeux", "–"), "aires de jeux"),
                 ("toilettes", compte.get("toilettes", "–"), "toilettes publiques"), ("langer", compte.get("table_langer", 0) + compte.get("resto_enfants", 0), "lieux avec table à langer ou équipés")]
        return '<div class="chiffres">' + "".join(f'<div class="chiffre">{ico(i, "i", b)}<div><b>{c}</b><span>{t}</span></div></div>' for i, c, t in items) + "</div>"

    # ---------- page guide principale
    filtres = "".join(f'<button class="chip" type="button" data-f="int:{k}" aria-pressed="false">{l}</button>' for k, l in INTERETS.items())
    programmes = [
        ("j=3&a=1&r=calme&p=1", "bebe", "3 jours avec un bébé", "Rythme tranquille, poussette, sieste prévue chaque jour.", "corail"),
        ("j=3&a=4-7&r=equilibre&i=animaux-plage", "jeux", "3 jours avec 4 et 7 ans", "Animaux, plage et pauses aires de jeux.", "menthe"),
        ("j=4&a=12-15&r=intense&i=aventure-culture", "ado", "4 jours avec des ados", "Gaudí, panoramas, téléphérique.", "ciel"),
        ("j=2&a=6&r=equilibre&b=serre", "gratuit", "Week-end petit budget", "Priorité aux parcs, plages et lieux gratuits.", "soleil"),
    ]
    faq = [
        (f"Combien de jours prévoir à {n} avec des enfants ?", "Trois jours permettent de voir le port et l'aquarium, Gaudí, Montjuïc et une demi-journée de plage sans courir. Avec un bébé ou un rythme tranquille, comptez quatre jours ou retirez une visite par jour."),
        (f"Que faire à {n} avec un bébé ?", "Privilégiez les lieux plats et ombragés : " + ", ".join(a["nom"] for a in bebe if a["poussette"] == "facile") + "."),
        (f"Que faire à {n} quand il pleut ?", "Les meilleures options couvertes : " + ", ".join(a["nom"] for a in pluie) + "."),
        (f"Quelles activités gratuites à {n} avec des enfants ?", "Sans payer ou presque : " + ", ".join(a["nom"] for a in gratuits) + "."),
        (f"{n} est-elle adaptée à la poussette ?", "En grande partie oui dans le centre et en bord de mer. Les difficultés : certaines stations de métro sans ascenseur, les ruelles anciennes et les sites en pente comme " + ", ".join(a["nom"] for a in difficiles) + "."),
    ]
    corps = hero(d1, f"{v['pays']} · guide famille", f'{e(n)} avec <span class="hl">des enfants</span>',
                 f"{len(acts)} activités classées par âge, un plan B pour chaque jour de pluie, et la carte des toilettes, aires de jeux et tables à langer de la ville.")
    corps += f'<section style="padding-top:8px"><div class="wrap">{chiffres(b1)}</div></section>'
    corps += f'''<section class="sable"><div class="wrap">
  <div class="tete-section"><div><h2>Programmes <span class="hl c">prêts à partir</span></h2><p>Un clic, et le carnet complet se prépare. Vous pourrez ensuite ajuster les âges, le rythme et les envies.</p></div></div>
  {cartes_liens([(lien_carnet(q, "")[0:], i, t, d, c) for q, i, t, d, c in programmes], b1)}
</div></section>'''
    corps += f'''<section><div class="wrap">
  <div class="tete-section"><div><h2>Activités <span class="hl m">par âge</span></h2><p>Choisissez l'âge de votre enfant ou une envie. Chaque fiche indique les services les plus proches.</p></div></div>
  <div class="filtres" role="group" aria-label="Filtrer les activités">
    <label class="chip">Âge <select id="f-age"><option value="">tous</option>{"".join(f'<option value="{i}">{i} an{"s" if i > 1 else ""}</option>' for i in range(18))}</select></label>
    <button class="chip" type="button" data-f="couvert" aria-pressed="false">Couvert</button>
    <button class="chip" type="button" data-f="gratuit" aria-pressed="false">Gratuit</button>
    {filtres}
  </div>
  <p id="f-vide" class="note" hidden>Aucune activité ne correspond à ces filtres.</p>
  <div class="grille" id="liste" style="row-gap:28px">{"".join(carte_act(a, v, osm, b1) for a in acts)}</div>
</div></section>'''
    corps += f'''<section class="ciel"><div class="wrap">
  <div class="tete-section"><div><h2>Toute la ville <span class="hl">côté parents</span></h2><p>Des pages pensées pour une question précise.</p></div></div>
  {cartes_liens([(h, i, t, d, c) for h, i, t, d, c in thematiques], b1.replace("../", "../"))}
</div></section>'''.replace(f'href="{b1}{vid}/', 'href="./').replace('href="./', 'href="./')
    corps += carte_section('La carte <span class="hl">pratique</span>', "Toutes les activités, toilettes, aires de jeux, tables à langer, pharmacies et restaurants équipés. Touchez un point pour lancer l'itinéraire.", b1)
    corps += f'''<section class="sable"><div class="wrap">
  <h2>Bon à savoir</h2>
  <div class="grille" style="margin-top:20px">{"".join(f'<div class="carte"><h3>{e(c["titre"])}</h3><p>{e(c["texte"])}</p></div>' for c in v["conseils"])}</div>
  <div class="carte corail" style="margin-top:24px">{ico("urgence", "i", b1)}<h3>Urgences</h3>{"".join(f"<p><strong>{e(u['nom'])}</strong> : {e(u['detail'])}</p>" for u in v["urgences"])}</div>
</div></section>
<section><div class="wrap etroit">
  <h2>Questions fréquentes</h2>
  {faq_html(faq)}
  <p class="note" style="margin-top:20px">Fiches vérifiées le {date_fr(v["verification"])}. {e(v["avertissement"])}</p>
</div></section>'''
    page(f"{vid}/", f"{n} avec des enfants : activités, itinéraires et carte pratique | PetitMondo",
         f"Visiter {n} en famille : {len(acts)} activités classées par âge, jours de pluie, sorties gratuites, toilettes, aires de jeux et tables à langer sur la carte. Carnet PDF gratuit.",
         corps, d1, head=leaflet_head(), scripts=leaflet_scripts(b1, vid), actif=vid)

    # ---------- pages thématiques
    def theme(slug, titre, h1, lead, liste, intro, extra="", calques=None, cta="j=3&a=5&r=equilibre", faq_t=None):
        b = b2
        c = hero(d2, f"{n} · {titre}", h1, lead, cta)
        c += f'<section style="padding-top:8px"><div class="wrap"><p class="muted" style="max-width:46em;font-size:1.05rem">{intro}</p></div></section>'
        if liste:
            c += f'<section style="padding-top:0"><div class="wrap"><div class="grille" style="row-gap:28px">{"".join(carte_act(a, v, osm, b) for a in liste)}</div></div></section>'
        c += extra
        c += carte_section('La carte <span class="hl">pratique</span>', "Touchez un point pour lancer l'itinéraire.", b)
        if faq_t:
            c += f'<section><div class="wrap etroit"><h2>Questions fréquentes</h2>{faq_html(faq_t)}</div></section>'
        c += f'''<section class="ciel"><div class="wrap"><h2>Continuer</h2>{cartes_liens([(h.replace(vid + "/", ""), i, t, d, cc) for h, i, t, d, cc in thematiques if not h.endswith(slug + "/")][:4], "../")}
<p class="note" style="margin-top:22px">Fiches vérifiées le {date_fr(v["verification"])}. Services issus d'OpenStreetMap, non vérifiés sur place. {e(v["avertissement"])}</p></div></section>'''
        page(f"{vid}/{slug}/", SEO.get(slug, f"{n} {titre}").format(n=n) + " | PetitMondo",
             lead.replace("<b>", "").replace("</b>", "")[:155], c, d2, head=leaflet_head(),
             scripts=leaflet_scripts(b, vid, calques), actif=vid)

    def table_services(cat, titre_col, maxi=600):
        lignes = []
        for a in acts:
            pr = proches(osm, a, cat, 2, maxi)
            cell = "<br>".join(f'<a href="{maps("", lat=p["lat"], lon=p["lon"])}" target="_blank" rel="noopener">{e(nom_point(p))}</a> · {fmt_dist(dd)}{" · " + e(detail_point(p)) if detail_point(p) else ""}' for p, dd in pr) or '<span class="muted">Aucun signalé à moins de 600 m</span>'
            lignes.append(f'<div class="fr">{e(a["nom"])}</div><div style="grid-column:span 2">{cell}</div>')
        return f'<div class="lex" style="margin-top:20px"><div class="t">Visite</div><div class="t" style="grid-column:span 2">{titre_col} le plus proche</div>{"".join(lignes)}</div>'

    theme("avec-un-bebe", "avec un bébé", f'{e(n)} avec <span class="hl c">un bébé</span>',
          f"Les visites qui conviennent dès la naissance, les tables à langer signalées et une journée qui laisse la place à la sieste.",
          [a for a in bebe], "Avec un bébé, la ville se visite surtout le matin et en fin d'après-midi. Le programme PetitMondo prévoit automatiquement un temps calme après le déjeuner pour les moins de 4 ans. Les lieux ci-dessous sont adaptés dès les premiers mois.",
          extra=f'<section class="sable"><div class="wrap"><h2>Où changer bébé</h2><p class="muted">Tables à langer signalées dans OpenStreetMap autour de chaque visite. Le recensement est encore partiel : gardez un tapis à langer nomade dans le sac.</p>{table_services("table_langer", "Table à langer", 1500)}</div></section>',
          calques=["activite", "table_langer", "toilettes", "pharmacie"], cta="j=3&a=1&r=calme&p=1",
          faq_t=[(f"Peut-on visiter {n} avec un nouveau-né ?", "Oui, à condition d'adopter un rythme lent, d'éviter les heures chaudes en été et de privilégier les lieux plats et couverts. Un porte-bébé complète utilement la poussette pour le métro et les ruelles."),
                 ("Où trouver des couches et du lait infantile ?", "Dans les pharmacies (croix verte « Farmàcia ») et les supermarchés. Les références de lait diffèrent de celles vendues en France : emportez assez de votre lait habituel pour tout le séjour si votre bébé y est sensible.")])

    theme("quand-il-pleut", "quand il pleut", f'{e(n)} <span class="hl">quand il pleut</span>',
          f"{len(pluie)} lieux couverts pour une matinée ou une après-midi entière, classés par âge.",
          pluie, "Chaque journée du carnet PetitMondo propose déjà un plan B couvert à proximité. Voici la liste complète, pour réorganiser une journée en un instant.",
          calques=["activite", "toilettes"], cta="j=2&a=5&r=equilibre&i=sciences")

    theme("gratuit", "gratuit", f'{e(n)} <span class="hl">gratuit</span> en famille',
          f"Parcs, plages, promenades et lieux en partie gratuits : de quoi remplir des journées entières sans billet.",
          gratuits, "Les lieux marqués « en partie gratuit » ont un accès libre mais certaines zones ou activités payantes. Les conditions de gratuité des musées changent : vérifiez sur le site officiel avant de vous déplacer.",
          calques=["activite", "aire_jeux", "toilettes"], cta="j=2&a=6&r=equilibre&b=serre")

    theme("avec-des-ados", "avec des ados", f'{e(n)} avec <span class="hl m">des ados</span>',
          "Panoramas, architecture spectaculaire, téléphérique et parc d'attractions : les visites qui tiennent les plus grands en éveil.",
          sorted(ados, key=lambda a: -a["ages"][0])[:12], "Avec des adolescents, laissez-les choisir une activité par jour et gardez du temps libre en fin de journée. Les visites sur réservation (Sagrada Família, Casa Batlló, Park Güell) se prennent plusieurs jours à l'avance en haute saison.",
          calques=["activite"], cta="j=4&a=12-15&r=intense&i=aventure-culture")

    theme("poussette", "en poussette", f'{e(n)} <span class="hl">en poussette</span>',
          f"Ce qui roule sans effort, ce qui demande un porte-bébé, et comment se déplacer.",
          faciles, "Ces visites se font sans difficulté avec une poussette. Plus bas, celles où le porte-bébé sera bien plus confortable.",
          extra=f'<section class="sable"><div class="wrap"><h2>Plutôt en porte-bébé</h2><div class="grille" style="margin-top:20px;row-gap:28px">{"".join(carte_act(a, v, osm, b2) for a in difficiles)}</div><div class="carte" style="margin-top:24px">{ico("poussette", "i", b2)}<h3>Se déplacer</h3><p>{e(v["conseils"][0]["texte"])}</p></div></div></section>',
          calques=["activite", "toilettes"], cta="j=3&a=1&r=calme&p=1")

    jeux_proches = "".join(
        f'<div class="carte"><h3>{e(a["nom"])}</h3>' + ("".join(f'<p>{ico("jeux", "i s", b2)} <a href="{maps("", lat=p["lat"], lon=p["lon"])}" target="_blank" rel="noopener">{e(nom_point(p))}</a>, à {fmt_dist(dd)}</p>' for p, dd in proches(osm, a, "aire_jeux", 3, 700)) or '<p class="muted">Aucune aire signalée à moins de 700 m.</p>') + "</div>"
        for a in acts)
    theme("aires-de-jeux", "aires de jeux", f'Les aires de jeux de <span class="hl m">{e(n)}</span>',
          f"{compte.get('aire_jeux', 'Toutes les')} aires de jeux recensées dans la ville, et les plus proches de chaque visite pour la récréation entre deux activités.",
          [], "Le bon réflexe : une aire de jeux entre deux visites, même dix minutes. Voici celles qui se trouvent à quelques pas des activités du guide.",
          extra=f'<section style="padding-top:0"><div class="wrap"><div class="grille">{jeux_proches}</div></div></section>',
          calques=["aire_jeux", "activite"])

    theme("toilettes-et-tables-a-langer", "toilettes et tables à langer", f'Toilettes et <span class="hl c">tables à langer</span> à {e(n)}',
          f"{compte.get('toilettes', 'Les')} toilettes publiques recensées et les tables à langer signalées, autour de chaque visite.",
          [], "Les toilettes publiques sont rares dans le centre historique : repérez-les à l'avance. Les musées, centres commerciaux et grandes gares disposent généralement de toilettes avec table à langer, même si elles ne sont pas toutes recensées.",
          extra=f'<section style="padding-top:0"><div class="wrap"><h2>Toilettes</h2>{table_services("toilettes", "Toilettes")}<h2 style="margin-top:36px">Tables à langer</h2>{table_services("table_langer", "Table à langer", 1500)}</div></section>',
          calques=["toilettes", "table_langer", "activite"])

    restos = [p for p in (osm or {}).get("points", []) if p["c"] == "resto_enfants"]
    def resto_carte(p):
        t = p["t"]
        site = f'<a href="{e(t["website"])}" target="_blank" rel="noopener">Site</a>' if t.get("website") else ""
        heures = f'<p class="muted">{e(t["opening_hours"])}</p>' if t.get("opening_hours") else ""
        return (f'<div class="carte act">{ico("resto", "i", b2)}<h3>{e(nom_point(p))}</h3>'
                f'<p>{e(detail_point(p)) or "Équipement famille signalé"}</p>{heures}'
                f'<div class="liens"><a href="{maps("", lat=p["lat"], lon=p["lon"])}" target="_blank" rel="noopener">Voir sur la carte</a>{site}</div></div>')
    restos_html = "".join(resto_carte(p) for p in sorted(restos, key=lambda p: nom_point(p)))
    theme("restaurants-enfants", "restaurants pour enfants", f'Restaurants <span class="hl">équipés pour les enfants</span> à {e(n)}',
          "Les restaurants et cafés signalés avec table à langer, chaise haute ou coin enfants dans OpenStreetMap.",
          [], "Cette liste ne reflète que ce que les contributeurs ont signalé : beaucoup d'autres restaurants accueillent bien les familles. Appelez avant pour confirmer l'équipement. Astuce : arrivez dès l'ouverture, vers 13 h pour le déjeuner et 20 h pour le dîner.",
          extra=f'<section style="padding-top:0"><div class="wrap"><div class="grille">{restos_html or "<p class=muted>Aucun restaurant signalé pour l’instant.</p>"}</div></div></section>',
          calques=["resto_enfants", "activite"])

    pages_jeux(v)
    page_lexique(v)


# ---------------------------------------------------------------- jeux imprimables
PICTOS = {
    "Un palmier": '<path d="M24 44V22M24 22c-8-6-16-2-18 4 6-4 12-3 18-4zm0 0c8-6 16-2 18 4-6-4-12-3-18-4zm0 0c-2-8-8-12-14-11 6 2 10 6 14 11zm0 0c2-8 8-12 14-11-6 2-10 6-14 11z" fill="#2FB59A"/>',
    "Une perruche verte": '<ellipse cx="22" cy="28" rx="10" ry="12" fill="#2FB59A"/><circle cx="26" cy="18" r="7" fill="#2FB59A"/><path d="M32 18l5 3-5 2z" fill="#FF6B4A"/><circle cx="27" cy="17" r="1.5" fill="#1B2A4A"/><path d="M16 38l-6 6" />',
    "Une mosaïque": '<path d="M8 8h14v14H8zM26 8h14v14H26zM8 26h14v14H8zM26 26h14v14H26z" fill="#6EC6F0"/><path d="M8 8h14v14H8zM26 26h14v14H26z" fill="#FFC93C"/>',
    "Un dragon": '<path d="M8 34c4-10 14-14 22-10s10-6 12-10c2 6-2 14-8 16 4 2 6 6 4 10-6-4-12-2-18 0s-10-2-12-6z" fill="#2FB59A"/><circle cx="36" cy="16" r="1.5" fill="#1B2A4A"/>',
    "Un bateau": '<path d="M6 30h36l-6 10H12z" fill="#FF6B4A"/><path d="M24 8v22M24 10l12 16H24z" fill="#FFF8EC"/>',
    "Un téléphérique": '<path d="M4 8l40 8M24 12v8"/><rect x="14" y="20" width="20" height="18" rx="4" fill="#FF6B4A"/><path d="M18 24h12v6H18z" fill="#DDF1FB"/>',
    "Une tour pointue": '<path d="M18 44V20l6-16 6 16v24z" fill="#FFC93C"/><circle cx="24" cy="24" r="2" fill="#1B2A4A"/>',
    "Un château de sable": '<path d="M8 42V26h6v4h6v-8h8v8h6v-4h6v16z" fill="#FFE7A8"/><path d="M22 42v-6h4v6"/>',
    "Une glace": '<path d="M16 22l8 22 8-22z" fill="#FFC93C"/><circle cx="20" cy="18" r="6" fill="#FF9F8A"/><circle cx="28" cy="18" r="6" fill="#A88BEB"/>',
    "Un bus rouge": '<rect x="6" y="12" width="36" height="24" rx="5" fill="#FF6B4A"/><path d="M10 16h28v8H10z" fill="#DDF1FB"/><circle cx="14" cy="38" r="3" fill="#1B2A4A"/><circle cx="34" cy="38" r="3" fill="#1B2A4A"/>',
    "Une fontaine": '<path d="M10 40h28l-4-8H14z" fill="#6EC6F0"/><path d="M24 32V14M24 14c-6 0-10 6-10 10M24 14c6 0 10 6 10 10"/>',
    "Une mouette": '<path d="M6 24q9-10 18 0 9-10 18 0"/>',
    "Un drapeau catalan": '<path d="M10 44V6"/><rect x="10" y="8" width="28" height="20" fill="#FFC93C"/><path d="M10 12h28M10 17h28M10 22h28" stroke="#FF6B4A" stroke-width="2.5"/>',
    "Un singe au zoo": '<circle cx="24" cy="22" r="12" fill="#FFE7A8"/><circle cx="20" cy="20" r="1.6" fill="#1B2A4A"/><circle cx="28" cy="20" r="1.6" fill="#1B2A4A"/><path d="M20 27q4 3 8 0"/><circle cx="12" cy="20" r="4" fill="#FFE7A8"/><circle cx="36" cy="20" r="4" fill="#FFE7A8"/>',
    "Un musicien de rue": '<path d="M14 36l14-24 6 4-14 24z" fill="#FFC93C"/><circle cx="16" cy="36" r="6" fill="#FF6B4A"/>',
    "Un vélo": '<circle cx="13" cy="32" r="7" fill="#DDF1FB"/><circle cx="35" cy="32" r="7" fill="#DDF1FB"/><path d="M13 32l8-12h10l4 12M21 20l6 12h-14M29 16h5"/>',
    "Un cerf-volant": '<path d="M24 6l12 14-12 14-12-14z" fill="#FF6B4A"/><path d="M24 34c-2 4 2 6 0 10"/>',
    "Des churros": '<path d="M12 40l8-30M22 40l6-30M32 40l2-30" stroke="#D9A441" stroke-width="5"/><path d="M8 40h32" />',
}


def pages_jeux(v):
    n, b = v["nom"], rel(2)
    svg = lambda body: f'<svg viewBox="0 0 48 48" fill="none" stroke="#1B2A4A" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round">{body}</svg>'
    bingo = "".join(f"<div>{svg(p)}<span>{e(t)}</span></div>" for t, p in PICTOS.items())
    coloriage = (ROOT / "assets" / "mondo.svg").read_text(encoding="utf-8")
    for c in ("#6EC6F0", "#2FB59A", "#FFC93C", "#FF6B4A", "#FF8C7A", "#FFF8EC"):
        coloriage = coloriage.replace(f'fill="{c}"', 'fill="#fff"')
    coloriage = coloriage.replace('<svg ', '<svg style="width:100%;max-width:420px;display:block;margin:0 auto" ', 1)
    chasse = [
        "Trouve une salamandre ou un dragon en mosaïque. De quelles couleurs est-il ?",
        "Compte les tours pointues de la Sagrada Família que tu vois depuis la rue.",
        "Repère un animal sculpté sur un bâtiment ou une fontaine. Dessine-le.",
        "Trouve une plaque de rue écrite en catalan. Recopie un mot.",
        "Cherche une perruche verte dans un parc. Combien en vois-tu ?",
        "Trouve un bateau dans le port. Quel est son nom ?",
        "Sur la plage, ramasse trois coquillages de formes différentes (et repose-les).",
        "Goûte un aliment que tu ne connaissais pas. C'était comment ?",
    ]
    jours = "".join(f'''<div class="page-jeu"><h2>Mon jour {i} à {e(n)}</h2>
  <p class="muted">Aujourd'hui, il fait :  ☐ soleil   ☐ nuages   ☐ pluie   ☐ vent</p>
  <h4 style="margin-top:16px">Ce que j'ai vu</h4><div class="ligne-ecrire"></div><div class="ligne-ecrire"></div>
  <h4 style="margin-top:16px">Ce que j'ai mangé</h4><div class="ligne-ecrire"></div>
  <h4 style="margin-top:16px">Mon dessin du jour</h4><div style="height:220px;border:2.5px dashed var(--nuit);border-radius:16px;margin-top:8px"></div>
  <h4 style="margin-top:16px">Ma note de la journée</h4><p style="font-size:2rem;letter-spacing:.3em">☆☆☆☆☆</p>
</div>''' for i in range(1, 4))
    corps = f'''<section class="hero no-print"><div class="wrap grid">
  <div><span class="etiquette"><i></i>À imprimer · 3 à 10 ans</span>
  <h1>Le carnet du <span class="hl">petit explorateur</span></h1>
  <p class="lead">Un bingo à cocher dans les rues, une chasse au trésor, un coloriage de Mondo et trois pages de journal de bord. Imprimez, glissez dans le sac, et les visites deviennent un jeu.</p>
  <div class="cta"><button class="btn" type="button" onclick="print()">{ico("pdf", "", b).replace('class=""', '')}Imprimer les jeux</button><a class="btn sec" href="../../carnet/#v={v["id"]}&j=3&a=6&r=equilibre">Créer le carnet des parents</a></div></div>
  <div class="visuel"><img src="{b}assets/mondo.svg" alt="Mondo, la mascotte PetitMondo" style="max-width:260px;display:block;margin:0 auto"></div>
</div></section>
<section style="padding-top:0"><div class="wrap etroit">
  <div class="page-jeu"><h2>Le bingo de {e(n)}</h2><p class="muted">Coche chaque case quand tu l'as vue. Une ligne complète : tu as gagné une glace (à négocier avec les parents).</p><div class="bingo" style="margin-top:16px">{bingo}</div></div>
  <div class="page-jeu"><h2>La chasse au trésor</h2><ol style="font-size:1.05rem;line-height:2.1">{"".join(f"<li>{e(q)}<div class=ligne-ecrire></div></li>" for q in chasse)}</ol></div>
  <div class="page-jeu"><h2>Colorie Mondo</h2><p class="muted">Mondo part en voyage avec toi. De quelles couleurs sera-t-il à {e(n)} ?</p>{coloriage}</div>
  {jours}
</div></section>'''
    page(f"{v['id']}/jeux/", f"Jeux à imprimer pour visiter {n} avec des enfants | PetitMondo",
         f"Bingo des rues, chasse au trésor, coloriage et journal de voyage à imprimer gratuitement pour occuper les enfants pendant les visites à {n}.",
         corps, 2, actif="jeux")


# ---------------------------------------------------------------- lexique
LEXIQUE = [
    ("Bonjour", "Hola / Buenos días", "Hola / Bon dia"),
    ("Merci beaucoup", "Muchas gracias", "Moltes gràcies"),
    ("Où sont les toilettes ?", "¿Dónde está el baño?", "On és el lavabo?"),
    ("Avez-vous une table à langer ?", "¿Tienen cambiador?", "Teniu canviador?"),
    ("Une chaise haute, s'il vous plaît", "Una trona, por favor", "Una trona, si us plau"),
    ("Avez-vous un menu enfant ?", "¿Tienen menú infantil?", "Teniu menú infantil?"),
    ("Pouvez-vous chauffer ce biberon ?", "¿Puede calentar este biberón?", "Em pot escalfar aquest biberó?"),
    ("Un verre d'eau, s'il vous plaît", "Un vaso de agua, por favor", "Un got d'aigua, si us plau"),
    ("L'addition, s'il vous plaît", "La cuenta, por favor", "El compte, si us plau"),
    ("Y a-t-il un ascenseur ?", "¿Hay ascensor?", "Hi ha ascensor?"),
    ("Où y a-t-il une aire de jeux ?", "¿Dónde hay un parque infantil?", "On hi ha un parc infantil?"),
    ("Combien ça coûte ?", "¿Cuánto cuesta?", "Quant costa?"),
    ("Où est la pharmacie la plus proche ?", "¿Dónde está la farmacia más cercana?", "On és la farmàcia més propera?"),
    ("Mon enfant a de la fièvre", "Mi hijo / mi hija tiene fiebre", "El meu fill / la meva filla té febre"),
    ("Mon enfant est allergique à…", "Mi hijo / mi hija es alérgico / alérgica a…", "El meu fill / la meva filla és al·lèrgic / al·lèrgica a…"),
    ("Nous nous sommes perdus", "Nos hemos perdido", "Ens hem perdut"),
    ("Aidez-moi, s'il vous plaît", "Ayúdeme, por favor", "Ajudi'm, si us plau"),
    ("Appelez une ambulance", "Llame a una ambulancia", "Truqui una ambulància"),
]


def page_lexique(v):
    n = v["nom"]
    lignes = "".join(f'<div class="fr">{e(fr)}</div><div>{e(es)}</div><div>{e(ca)}</div>' for fr, es, ca in LEXIQUE)
    corps = f'''<section class="hero"><div class="wrap etroit">
  <span class="etiquette"><i></i>{e(n)} · phrases utiles</span>
  <h1>Les phrases <span class="hl">des parents</span></h1>
  <p class="lead">À {e(n)}, on parle catalan et espagnol, et tout le monde comprend l'espagnol. Les phrases qui servent vraiment avec des enfants, à montrer sur votre téléphone si besoin.</p>
</div></section>
<section style="padding-top:0"><div class="wrap etroit">
  <div class="lex"><div class="t">Français</div><div class="t">Espagnol</div><div class="t">Catalan</div>{lignes}</div>
  <div class="carte soleil" style="margin-top:28px"><h3>Pour les enfants</h3><p><strong>Hola</strong> (bonjour), <strong>gràcies</strong> (merci en catalan), <strong>adéu</strong> (au revoir en catalan). Trois mots suffisent pour faire sourire les commerçants.</p></div>
  <p style="margin-top:22px"><button class="btn sec" type="button" onclick="print()">Imprimer le lexique</button></p>
</div></section>'''
    page(f"{v['id']}/lexique/", f"Phrases utiles en espagnol et catalan pour voyager à {n} avec des enfants | PetitMondo",
         f"Table à langer, chaise haute, pharmacie, fièvre, allergie : les phrases en espagnol et en catalan dont les parents ont besoin à {n}.",
         corps, 2, actif=v["id"])


# ---------------------------------------------------------------- pages générales
def accueil(villes, osm_par_ville):
    b = ""
    v = villes[0]
    compte = osm_par_ville.get(v["id"], {}).get("compte", {})
    corps = f'''<section class="hero"><div class="wrap grid">
  <div>
    <span class="etiquette"><i></i>Gratuit · sans compte · sans appli</span>
    <h1>Votre séjour en famille, <span class="hl">prêt à partir.</span></h1>
    <p class="lead">Indiquez la ville et l'âge de vos enfants. PetitMondo prépare un programme réaliste jour par jour, avec les toilettes, aires de jeux et tables à langer autour de chaque visite. À imprimer, ou à garder sur le téléphone.</p>
    <div class="cta"><a class="btn" href="carnet/">{ico("pdf", "", b).replace('class=""', '')}Créer mon carnet gratuit</a><a class="btn sec" href="barcelone/">Barcelone en famille</a></div>
  </div>
  <div class="visuel"><img src="assets/villes/barcelone.svg" alt="" width="640" height="320" style="border-radius:22px;border:2.5px solid var(--nuit);box-shadow:var(--ombre)"><img class="mondo" src="assets/mondo.svg" alt="Mondo, la mascotte PetitMondo"></div>
</div></section>
<div class="bandeau"><div class="wrap"><span>Adapté à l'âge de chaque enfant</span><span>Plan B pluie chaque jour</span><span>PDF imprimable</span><span>Carte Google My Maps</span></div></div>

<section><div class="wrap">
  <div class="tete-section"><div><h2>Comment ça <span class="hl m">marche</span></h2><p>Trente secondes, et le séjour est organisé.</p></div></div>
  <div class="etapes3">
    <div class="carte">{ico("carte", "i l", b)}<h3>Vous choisissez</h3><p>La ville, le nombre de jours, l'âge de chaque enfant, la poussette et vos envies.</p></div>
    <div class="carte soleil">{ico("horloge", "i l", b)}<h3>PetitMondo organise</h3><p>Visites groupées par quartier, temps de marche, déjeuner, sieste des petits et plan B pluie.</p></div>
    <div class="carte menthe">{ico("pdf", "i l", b)}<h3>Vous partez</h3><p>Carnet à imprimer avec QR codes, carte à importer dans Google My Maps, lien à partager.</p></div>
  </div>
</div></section>

<section class="sable"><div class="wrap">
  <div class="tete-section"><div><h2>Ce que les autres guides <span class="hl c">oublient</span></h2><p>Un guide touristique vous dit où aller. PetitMondo vous dit aussi comment tenir la journée avec des enfants.</p></div></div>
  <div class="grille">
    <div class="carte">{ico("bebe", "i", b)}<h3>L'âge réel de chaque enfant</h3><p>Un bébé, un enfant de 5 ans et un ado n'ont pas le même voyage. Le programme s'équilibre entre eux.</p></div>
    <div class="carte penche2">{ico("toilettes", "i", b)}<h3>Les toilettes les plus proches</h3><p>Pour chaque visite, avec la distance à pied. Fini la course de dernière minute.</p></div>
    <div class="carte">{ico("langer", "i", b)}<h3>Où changer bébé</h3><p>Tables à langer signalées, y compris celles accessibles aux papas.</p></div>
    <div class="carte penche">{ico("jeux", "i", b)}<h3>La récré entre deux visites</h3><p>L'aire de jeux la plus proche, pour se défouler dix minutes.</p></div>
    <div class="carte">{ico("pluie", "i", b)}<h3>Un plan B chaque jour</h3><p>Pluie, fatigue ou fermeture : un lieu couvert à proximité pour sauver la journée.</p></div>
    <div class="carte penche2">{ico("poussette", "i", b)}<h3>Poussette ou porte-bébé</h3><p>Chaque lieu indique s'il roule ou s'il vaut mieux porter.</p></div>
  </div>
</div></section>

<section><div class="wrap">
  <div class="tete-section"><div><h2>Barcelone, <span class="hl">ville pilote</span></h2><p>Chaque destination est préparée lieu par lieu avant d'être publiée.</p></div><a class="btn jaune petit" href="barcelone/">Explorer Barcelone</a></div>
  <div class="chiffres">
    <div class="chiffre">{ico("activite", "i", b)}<div><b>{len(v["activites"])}</b><span>activités sélectionnées</span></div></div>
    <div class="chiffre">{ico("jeux", "i", b)}<div><b>{compte.get("aire_jeux", "–")}</b><span>aires de jeux</span></div></div>
    <div class="chiffre">{ico("toilettes", "i", b)}<div><b>{compte.get("toilettes", "–")}</b><span>toilettes publiques</span></div></div>
    <div class="chiffre">{ico("pharmacie", "i", b)}<div><b>{compte.get("pharmacie", "–")}</b><span>pharmacies</span></div></div>
  </div>
</div></section>

<section class="ciel"><div class="wrap">
  <div class="tete-section"><div><h2>Destinations</h2><p>Les prochaines villes arrivent, une par une, quand elles sont prêtes.</p></div></div>
  <div class="grille">
    <a class="ville" href="barcelone/"><div class="illu"><img src="assets/villes/barcelone.svg" alt=""></div><div class="txt"><div><strong>Barcelone</strong><small>Espagne</small></div><span class="badge tampon">Disponible</span></div></a>
    {"".join(f'<div class="ville off"><div class="illu vide">{e(nv)}</div><div class="txt"><div><strong>{e(nv)}</strong><small>{e(pays)}</small></div><span class="badge g">Bientôt</span></div></div>' for nv, pays in VILLES_A_VENIR)}
  </div>
</div></section>

<section><div class="wrap">
  <div class="tete-section"><div><h2>Les <span class="hl m">outils</span> du voyage</h2><p>Gratuits, à utiliser seuls ou avec le carnet.</p></div></div>
  {cartes_liens([("valise/", "valise", "La valise des enfants", "La liste à cocher selon l'âge, la saison et la destination.", "soleil"),
                 ("barcelone/jeux/", "jeu", "Le carnet du petit explorateur", "Bingo des rues, chasse au trésor, coloriage et journal de voyage.", "corail"),
                 ("barcelone/lexique/", "bulle", "Les phrases des parents", "Table à langer, chaise haute, pharmacie : en espagnol et en catalan.", "ciel"),
                 ("methode/", "loupe", "Notre méthode", "D'où viennent les informations et comment elles sont vérifiées.", "menthe")], b)}
</div></section>

<section class="sable"><div class="wrap etroit">
  <h2>Questions fréquentes</h2>
  {faq_html([("PetitMondo est-il vraiment gratuit ?", "Oui. Le carnet, le PDF, la carte et les jeux sont gratuits, sans compte et sans abonnement."),
             ("Faut-il installer une application ?", "Non. Tout fonctionne dans le navigateur du téléphone. Vous pouvez ajouter PetitMondo à l'écran d'accueil et enregistrer le carnet en PDF pour l'avoir hors connexion."),
             ("Mes informations sont-elles enregistrées ?", "Non. Les réponses au formulaire restent dans le lien de votre carnet, sur votre appareil. Aucun cookie publicitaire, aucun compte."),
             ("Comment importer la carte dans Google Maps ?", "Téléchargez le fichier KML depuis votre carnet, ouvrez Google My Maps, créez une carte et choisissez Importer. Vous retrouverez un calque par journée et par type de service, consultable ensuite dans l'application Google Maps."),
             ("Les informations sont-elles fiables ?", "Les activités sont sélectionnées et décrites une par une, avec un lien vers leur site officiel pour les horaires et les tarifs. Les toilettes, aires de jeux et tables à langer viennent d'OpenStreetMap et sont signalées comme non vérifiées sur place.")])}
</div></section>'''
    page("", "PetitMondo — Carnets de voyage en famille gratuits, prêts à partir",
         "Un carnet de voyage familial gratuit, adapté à l'âge de vos enfants : programme jour par jour, toilettes, aires de jeux et tables à langer à proximité, PDF imprimable et carte Google My Maps.",
         corps, 0, og_titre="PetitMondo — Le monde à découvrir en famille")


def carnet(villes):
    b = "../"
    opts = "".join(f'<option value="{v["id"]}">{e(v["nom"])}</option>' for v in villes)
    interets = "".join(f'<input type="checkbox" id="i-{k}" name="interets" value="{k}"><label for="i-{k}">{l}</label>' for k, l in INTERETS.items())
    corps = f'''<div class="wrap" style="padding-top:36px">
  <div class="no-print" style="display:flex;gap:18px;align-items:flex-end;flex-wrap:wrap">
    <img src="{b}assets/mondo.svg" alt="" style="width:84px">
    <div><span class="etiquette"><i></i>Gratuit · sans compte</span>
    <h1 style="margin-bottom:.2em">Créer mon <span class="hl">carnet</span></h1>
    <p class="muted" style="max-width:40em;margin:0">Trente secondes pour un séjour organisé. Rien n'est enregistré : vos réponses restent dans le lien du carnet.</p></div>
  </div>
  <form class="form no-print" id="form-carnet" style="margin-top:26px">
    <div class="deux">
      <div class="champ"><label for="ville">Destination</label><select id="ville" name="ville">{opts}</select><div class="aide">Paris, Rome, Londres, Amsterdam et Lisbonne arrivent.</div></div>
      <div class="champ"><label for="jours">Nombre de jours</label><select id="jours" name="jours"><option>1</option><option>2</option><option selected>3</option><option>4</option><option>5</option></select></div>
    </div>
    <div class="champ"><span class="lbl">Âge des enfants</span><div class="enfants" id="enfants"><button type="button" class="btn sec petit" id="ajout-enfant">+ Ajouter un enfant</button></div><div class="aide">Mettez 0 pour un bébé de moins d'un an.</div></div>
    <div class="champ"><span class="lbl">Rythme</span><div class="segment">
      <input type="radio" id="r1" name="rythme" value="calme"><label for="r1">Tranquille</label>
      <input type="radio" id="r2" name="rythme" value="equilibre" checked><label for="r2">Équilibré</label>
      <input type="radio" id="r3" name="rythme" value="intense"><label for="r3">Soutenu</label></div></div>
    <div class="champ"><span class="lbl">Envies <span class="muted" style="font-weight:600;font-size:.9rem">(facultatif)</span></span><div class="segment">{interets}</div></div>
    <div class="deux">
      <div class="champ"><span class="lbl">Poussette</span><div class="segment"><input type="radio" id="p1" name="poussette" value="oui"><label for="p1">Oui</label><input type="radio" id="p2" name="poussette" value="non" checked><label for="p2">Non</label></div></div>
      <div class="champ"><span class="lbl">Budget</span><div class="segment"><input type="radio" id="b1" name="budget" value="tous" checked><label for="b1">Normal</label><input type="radio" id="b2" name="budget" value="serre"><label for="b2">Priorité au gratuit</label></div></div>
    </div>
    <div class="champ" style="max-width:280px"><label for="depart">Date d'arrivée <span class="muted" style="font-weight:600;font-size:.9rem">(facultatif)</span></label><input type="date" id="depart" name="depart"></div>
    <button class="btn" id="b-generer" type="submit">Créer mon carnet</button>
  </form>
  <div class="carnet" id="carnet" hidden aria-live="polite"></div>
</div>'''
    page("carnet/", "Créer mon carnet de voyage en famille | PetitMondo",
         "Générez gratuitement un carnet de voyage familial : programme jour par jour adapté à l'âge des enfants, services à proximité, PDF imprimable et carte KML pour Google My Maps.",
         corps, 1, head=leaflet_head(),
         scripts=f'<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script><script src="{b}assets/commun.js"></script><script src="{b}assets/carnet.js"></script>')


VALISE = {
    "Papiers et santé": [("Pièces d'identité de chaque enfant", "tous"), ("Carte européenne d'assurance maladie (CEAM) pour chacun", "tous"),
                          ("Carnet de santé ou ordonnances en cours", "tous"), ("Antipyrétique adapté au poids, pipette ou seringue doseuse", "tous"),
                          ("Thermomètre", "tous"), ("Sérum physiologique et pansements", "tous"), ("Crème solaire enfant et pommade apaisante", "ete")],
    "Bébé (0–2 ans)": [("Couches pour les 48 premières heures", "bebe"), ("Lingettes et tapis à langer nomade", "bebe"),
                       ("Lait infantile habituel en quantité suffisante", "bebe"), ("Biberons, goupillon et boîte doseuse", "bebe"),
                       ("Porte-bébé", "bebe"), ("Gigoteuse et doudou", "bebe"), ("Body de rechange dans le sac de journée", "bebe")],
    "Enfants": [("Doudou et son remplaçant", "petit"), ("Gourde par enfant", "tous"), ("En-cas pour chaque journée", "tous"),
                ("Petit sac à dos par enfant", "enfant"), ("Carnet du petit explorateur et crayons", "enfant"), ("Livre ou jeu pour le trajet", "tous"),
                ("Bracelet avec le numéro de téléphone des parents", "petit")],
    "Vêtements": [("Chapeau ou casquette", "ete"), ("Maillot de bain et serviette", "ete"), ("Coupe-vent léger", "tous"),
                  ("Une tenue de rechange par jour et par enfant", "tous"), ("Chaussures déjà portées, confortables pour marcher", "tous"), ("Pull pour les soirées", "tous")],
    "Pratique": [("Poussette pliable et légère", "petit"), ("Batterie externe", "tous"), ("Carnet PetitMondo imprimé ou enregistré en PDF", "tous"),
                 ("Copie des réservations hors connexion", "tous"), ("Sacs pour le linge sale", "tous"), ("Adaptateur de prise si hors zone européenne", "tous")],
}


def valise():
    b = "../"
    groupes = ""
    for titre, items in VALISE.items():
        li = "".join(f'<li data-k="{e(t)}" data-p="{p}">{e(t)}</li>' for t, p in items)
        groupes += f'<div class="carte" style="margin-bottom:22px"><h3>{e(titre)}</h3><ul class="check valise">{li}</ul></div>'
    corps = f'''<section class="hero"><div class="wrap grid">
  <div><span class="etiquette"><i></i>Liste à cocher · à imprimer</span>
  <h1>La valise <span class="hl">des enfants</span></h1>
  <p class="lead">Touchez un objet pour le cocher. La liste s'adapte à l'âge de vos enfants et à la saison, et reste enregistrée sur ce téléphone.</p></div>
  <div class="visuel"><img src="{b}assets/mondo.svg" alt="" style="max-width:220px;display:block;margin:0 auto"></div>
</div></section>
<section style="padding-top:0"><div class="wrap etroit">
  <div class="form no-print" style="margin-bottom:24px">
    <div class="champ"><span class="lbl">Qui part ?</span><div class="segment">
      <input type="checkbox" id="v-bebe" value="bebe" checked><label for="v-bebe">Bébé 0–2 ans</label>
      <input type="checkbox" id="v-petit" value="petit" checked><label for="v-petit">Petit 3–5 ans</label>
      <input type="checkbox" id="v-enfant" value="enfant" checked><label for="v-enfant">Enfant 6–12 ans</label></div></div>
    <div class="champ" style="margin:0"><span class="lbl">Saison</span><div class="segment">
      <input type="radio" name="saison" id="s-ete" value="ete" checked><label for="s-ete">Printemps, été</label>
      <input type="radio" name="saison" id="s-hiver" value="hiver"><label for="s-hiver">Automne, hiver</label></div></div>
  </div>
  <p style="font-weight:800" id="v-compte"></p><div class="progres"><i id="v-barre"></i></div>
  {groupes}
  <div class="actions no-print"><button class="btn" type="button" onclick="print()">Imprimer la liste</button><button class="btn sec" type="button" id="v-raz">Tout décocher</button></div>
</div></section>'''
    js = '''<script>(()=>{const K='pm-valise';let s={};try{s=JSON.parse(localStorage.getItem(K))||{}}catch{}
const save=()=>{try{localStorage.setItem(K,JSON.stringify(s))}catch{}};
const lis=[...document.querySelectorAll('.valise li')];
function maj(){const prof=[...document.querySelectorAll('.form input[type=checkbox]:checked')].map(i=>i.value);const sais=document.querySelector('input[name=saison]:checked').value;
let n=0,ok=0;lis.forEach(li=>{const p=li.dataset.p;const vis=p==='tous'||(p==='ete'?sais==='ete':prof.includes(p));li.hidden=!vis;li.classList.toggle('ok',!!s[li.dataset.k]);if(vis){n++;if(s[li.dataset.k])ok++}});
document.getElementById('v-compte').textContent=ok+' sur '+n+' dans la valise';document.getElementById('v-barre').style.width=(n?ok/n*100:0)+'%'}
lis.forEach(li=>li.addEventListener('click',()=>{s[li.dataset.k]=!s[li.dataset.k];save();maj()}));
document.querySelectorAll('.form input').forEach(i=>i.addEventListener('change',maj));
document.getElementById('v-raz').onclick=()=>{s={};save();maj()};maj()})();</script>'''
    page("valise/", "Valise des enfants : la liste à cocher pour voyager en famille | PetitMondo",
         "La liste de valise pour voyager avec un bébé ou des enfants : papiers, santé, vêtements, objets pratiques. Adaptée à l'âge et à la saison, à cocher ou à imprimer.",
         corps, 1, scripts=js, actif="valise")


def methode(villes):
    corps = f'''<section class="hero"><div class="wrap etroit">
  <span class="etiquette"><i></i>Transparence</span>
  <h1>Notre <span class="hl m">méthode</span></h1>
  <p class="lead">Un guide pour parents n'a de valeur que si on peut lui faire confiance. Voici exactement d'où viennent les informations et ce qui est vérifié.</p>
</div></section>
<section style="padding-top:0"><div class="wrap etroit">
  <div class="carte" style="margin-bottom:22px">{ico("activite", "i", "../")}<h3>Les activités : sélectionnées à la main</h3><p>Chaque lieu est choisi pour son intérêt avec des enfants, puis décrit avec les âges conseillés, la durée de visite, l'accès en poussette et le besoin de réserver. Nous ne publions ni horaires ni tarifs, qui changent trop souvent : chaque fiche renvoie au site officiel. La date de vérification figure sur chaque page.</p></div>
  <div class="carte" style="margin-bottom:22px">{ico("carte", "i", "../")}<h3>Les services : OpenStreetMap</h3><p>Toilettes, aires de jeux, tables à langer, pharmacies et restaurants équipés proviennent d'<a href="https://www.openstreetmap.org">OpenStreetMap</a>, la carte collaborative mondiale, actualisés chaque semaine. Ces informations ne sont pas vérifiées sur place et sont toujours présentées comme « signalées ». Les tables à langer y sont encore peu recensées : leur absence sur la carte ne veut pas dire qu'il n'y en a pas.</p></div>
  <div class="carte" style="margin-bottom:22px">{ico("horloge", "i", "../")}<h3>Les programmes : calculés, pas inventés</h3><p>Le générateur ne crée aucun lieu. Il choisit parmi les activités du guide selon l'âge de chaque enfant, vos envies, la poussette et le budget, les regroupe par quartier, calcule les distances à pied (à environ 3 km/h, majorées pour les détours) et place le déjeuner et la sieste des moins de 4 ans.</p></div>
  <div class="carte" style="margin-bottom:22px">{ico("loupe", "i", "../")}<h3>Une erreur ?</h3><p>Sur la carte, chaque service a un lien « Corriger » qui ouvre la fiche dans OpenStreetMap. Toute correction profite ensuite à tous, sur PetitMondo comme ailleurs.</p></div>
  <div class="carte" style="margin-bottom:22px">{ico("check", "i", "../")}<h3>Vie privée</h3><p>Aucun compte, aucun cookie publicitaire. Les réponses du formulaire restent dans le lien de votre carnet. La liste de valise cochée reste dans la mémoire de votre navigateur.</p></div>
</div></section>'''
    page("methode/", "Notre méthode : d'où viennent les informations | PetitMondo",
         "Comment PetitMondo sélectionne les activités, d'où viennent les données sur les toilettes et tables à langer, et comment sont calculés les programmes.",
         corps, 1)


def charte():
    b = "../"
    couleurs = [("Nuit", "#1B2A4A", "Texte, contours, ombres"), ("Papier", "#FFF8EC", "Fond du site"), ("Sable", "#FFE7A8", "Sections, illustrations"),
                ("Soleil", "#FFC93C", "Surlignage, tampons, appel secondaire"), ("Corail", "#FF6B4A", "Bouton principal, activités"),
                ("Menthe", "#2FB59A", "Aires de jeux, validation"), ("Ciel", "#6EC6F0", "Toilettes, pluie"), ("Lilas", "#A88BEB", "Tables à langer, bébé")]
    nuancier = "".join(f'<div><i style="background:{c}"></i><p>{n}<small>{c} · {u}</small></p></div>' for n, c, u in couleurs)
    icones = "".join(f'<div style="text-align:center">{ico(i, "i l", b)}<p style="font-size:.8rem;font-weight:700;margin-top:4px">{i}</p></div>' for i in
                     ["activite", "toilettes", "jeux", "langer", "pharmacie", "resto", "pluie", "gratuit", "poussette", "bebe", "ado", "carte", "pdf", "valise", "jeu", "horloge", "bulle", "loupe", "check", "urgence"])
    corps = f'''<section class="hero"><div class="wrap grid">
  <div><span class="etiquette"><i></i>Usage interne</span><h1>Charte <span class="hl">PetitMondo</span></h1>
  <p class="lead">Le style « autocollant » : contours bleu nuit épais, ombres décalées pleines, couleurs franches et ligne pointillée d'itinéraire. Chaleureux pour les enfants, net et rassurant pour les parents.</p></div>
  <div class="visuel"><img src="{b}assets/mondo.svg" alt="Mondo" style="max-width:240px;display:block;margin:0 auto"></div>
</div></section>
<section style="padding-top:0"><div class="wrap">
  <h2>Couleurs</h2><div class="nuancier" style="margin:20px 0 40px">{nuancier}</div>
  <h2>Typographies</h2>
  <div class="grille g2" style="margin:20px 0 40px">
    <div class="carte"><p class="muted">Titres · Bricolage Grotesque 800</p><p style="font:800 2.6rem/1 var(--titre);letter-spacing:-.03em;color:var(--nuit)">Le monde à découvrir en famille</p></div>
    <div class="carte"><p class="muted">Texte · Figtree 400 à 800</p><p style="font-size:1.1rem;color:var(--nuit)">Un programme réaliste, avec les toilettes, aires de jeux et tables à langer autour de chaque visite.</p></div>
  </div>
  <h2>Mondo, la mascotte</h2>
  <div class="grille g2" style="margin:20px 0 40px">
    <div class="carte soleil" style="text-align:center"><img src="{b}assets/mondo.svg" alt="" style="max-width:200px"></div>
    <div class="carte"><h3>Règles</h3><p>Un petit globe explorateur, chapeau soleil, joues corail, chaussures corail. Toujours avec ses contours nuit. Il accompagne, il ne domine pas : une apparition par écran, en coin d'illustration ou à côté d'un titre. Jamais déformé, jamais recoloré, sauf en coloriage.</p></div>
  </div>
  <h2>Icônes</h2><p class="muted">Pastille de couleur de la catégorie, pictogramme au trait nuit 2,2 px.</p>
  <div class="grille" style="grid-template-columns:repeat(auto-fill,minmax(90px,1fr));margin:20px 0 40px">{icones}</div>
  <h2>Composants</h2>
  <div style="display:flex;gap:14px;flex-wrap:wrap;margin:20px 0">
    <a class="btn" href="#">Bouton principal</a><a class="btn sec" href="#">Secondaire</a><a class="btn jaune" href="#">Mise en avant</a>
    <span class="badge tampon">Tampon</span><span class="badge">Plein air</span><span class="badge b">Couvert</span><span class="badge s">Gratuit</span><span class="badge c">Réserver</span>
  </div>
  <div class="trace"></div><div class="trace c"></div>
  <h2 style="margin-top:30px">Ton éditorial</h2>
  <div class="grille g2" style="margin-top:20px">
    <div class="carte menthe"><h3>Oui</h3><p>Phrases courtes et concrètes. On parle aux parents comme un ami qui connaît la ville. On dit ce qui coince (pentes, foule, chaleur). On signale ce qui n'est pas vérifié.</p></div>
    <div class="carte corail"><h3>Non</h3><p>Superlatifs creux (« incontournable magique »), émojis en série, informations de prix ou d'horaires non vérifiées, promesses de sécurité ou d'absence d'allergènes.</p></div>
  </div>
</div></section>'''
    page("charte/", "Charte graphique PetitMondo", "Couleurs, typographies, mascotte, icônes et composants de PetitMondo.", corps, 1, indexable=False)


def page_404():
    p = ROOT / "404.html"
    corps = '''<section class="hero"><div class="wrap etroit" style="text-align:center">
  <img src="/petitmondo/assets/mondo.svg" alt="" style="width:160px">
  <h1>Mondo s'est <span class="hl">perdu</span>.</h1>
  <p class="lead" style="margin:0 auto">Cette page n'existe pas, ou plus. Reprenons depuis le départ.</p>
  <div class="cta" style="justify-content:center"><a class="btn" href="/petitmondo/">Retour à l'accueil</a><a class="btn sec" href="/petitmondo/carnet/">Créer mon carnet</a></div>
</div></section>'''
    page("404.html", "Page introuvable | PetitMondo", "Cette page n'existe pas.", corps, 0, indexable=False)
    # chemins absolus : la page 404 est servie à n'importe quelle profondeur
    s = p.read_text(encoding="utf-8").replace('href="assets/', 'href="/petitmondo/assets/').replace('src="assets/', 'src="/petitmondo/assets/') \
        .replace('href="carnet/', 'href="/petitmondo/carnet/').replace('href="barcelone/', 'href="/petitmondo/barcelone/') \
        .replace('href="valise/', 'href="/petitmondo/valise/').replace('href="methode/', 'href="/petitmondo/methode/') \
        .replace('href=""', 'href="/petitmondo/"').replace("register('sw.js')", "register('/petitmondo/sw.js')").replace('href="manifest', 'href="/petitmondo/manifest')
    p.write_text(s, encoding="utf-8")


def main():
    villes, osm_par_ville = [], {}
    for f in sorted((ROOT / "data" / "villes").glob("*.json")):
        v = json.loads(f.read_text(encoding="utf-8"))
        villes.append(v)
        fo = ROOT / "data" / "osm" / f"{v['id']}.json"
        osm_par_ville[v["id"]] = json.loads(fo.read_text(encoding="utf-8")) if fo.exists() else None
    accueil(villes, osm_par_ville)
    carnet(villes)
    for v in villes:
        pages_ville(v, osm_par_ville[v["id"]])
    valise()
    methode(villes)
    charte()
    page_404()
    aujourdhui = date.today().isoformat()
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{URL}{c}</loc><lastmod>{aujourdhui}</lastmod></url>\n" for c, idx in PAGES if idx)
        + "</urlset>\n", encoding="utf-8")
    print(f"{len(PAGES)} pages générées")


if __name__ == "__main__":
    main()
