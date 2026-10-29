#!/usr/bin/env python3
"""Génère toutes les pages statiques de PetitMondo à partir des données.

Usage : python scripts/build.py
Entrées : data/villes/*.json (destinations), data/osm/*.json (services OpenStreetMap),
          data/photos.json (photos libres et crédits, voir fetch_photos.py)
Sorties : toutes les pages index.html, data/enfants/<ville>.html (pages enfants du carnet), sitemap.xml
"""
import html
import json
import math
import pathlib
import sys
import urllib.parse
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from contenu import P, drapeau, LEXIQUES  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "https://xd6pwyx7n2-debug.github.io/PetitMondo/"
e = html.escape
PAGES = []
PHOTOS = {}
VILLES = []

INTERETS = {"animaux": "Animaux", "sciences": "Sciences", "aventure": "Aventure", "culture": "Culture",
            "parc": "Parcs", "plage": "Plage", "gourmand": "Gourmand"}
CAT_ICO = {"toilettes": "toilettes", "aire_jeux": "jeux", "table_langer": "langer", "pharmacie": "pharmacie", "resto_enfants": "resto"}
CAT_NOM = {"toilettes": "Toilettes", "aire_jeux": "Aire de jeux", "table_langer": "Table à langer", "pharmacie": "Pharmacie", "resto_enfants": "Restaurant équipé"}
VILLES_A_VENIR = [("Amsterdam", "Pays-Bas"), ("Lisbonne", "Portugal")]
SEO = {
    "avec-un-bebe": "{n} avec un bébé : visites, tables à langer et conseils",
    "quand-il-pleut": "Que faire à {n} avec des enfants quand il pleut",
    "gratuit": "{n} gratuit en famille : sorties sans billet",
    "avec-des-ados": "{n} avec des ados : que faire et que voir",
    "poussette": "Visiter {n} en poussette : ce qui roule et ce qui coince",
    "aires-de-jeux": "Aires de jeux à {n} : les plus proches de chaque visite",
    "toilettes-et-tables-a-langer": "Toilettes publiques et tables à langer à {n}",
    "restaurants-enfants": "Restaurants avec table à langer et chaise haute à {n}",
}


# ---------------------------------------------------------------- outils
def rel(depth):
    return "../" * depth


def ico(nom, cls="i", base=""):
    return f'<svg class="{cls}" aria-hidden="true"><use href="{base}assets/sprite.svg#i-{nom}"/></svg>'


def ico_btn(nom, base):
    return f'<svg aria-hidden="true"><use href="{base}assets/sprite.svg#i-{nom}"/></svg>'


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


def de(groupe):
    """« le Royaume-Uni » → « du Royaume-Uni », « la France » → « de la France », « l'Italie » → « de l'Italie »."""
    if groupe.startswith("le "):
        return "du " + groupe[3:]
    if groupe.startswith("les "):
        return "des " + groupe[4:]
    return "de " + groupe


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
    if ("male_toilet" in loc and "female" not in loc) or any(k in loc for k in ("unisex", "dedicated", "wheelchair")):
        d.append("accessible aux papas")
    if t.get("highchair") == "yes": d.append("chaise haute")
    if t.get("kids_area") == "yes": d.append("coin enfants")
    if t.get("wheelchair") in ("yes", "designated"): d.append("accès fauteuil")
    return " · ".join(d)


def credit(cle):
    c = PHOTOS.get(cle)
    if not c:
        return ""
    return f'Photo : {e(c["auteur"])} · <a href="{e(c["source"])}" target="_blank" rel="noopener">{e(c["licence"])}</a>'


def photo(cle, alt, b, cls="photo", ill=None, legende=True):
    """Photo libre avec crédit, sinon illustration PetitMondo."""
    c = PHOTOS.get(cle)
    if c:
        dims = f' width="{c["l"]}" height="{c["h"]}"' if c.get("l") else ""
        cap = f"<figcaption>{credit(cle)}</figcaption>" if legende else ""
        return f'<figure class="{cls}"><img src="{b}{c["fichier"]}" alt="{e(alt)}" loading="lazy"{dims}>{cap}</figure>'
    if ill:
        return f'<figure class="{cls} ill"><img src="{b}{ill}" alt="" loading="lazy"></figure>'
    return ""


def page(chemin, titre, desc, corps, depth, *, head="", scripts="", indexable=True, actif="", og_titre=None):
    b = rel(depth)
    PAGES.append((chemin, indexable))
    robots = "" if indexable else '<meta name="robots" content="noindex">'
    nav = [(f"{b}#destinations", "Destinations", "dest"), (f"{b}jeux/", "Jeux enfants", "jeux"), (f"{b}valise/", "Valise", "valise")]
    nav_html = "".join(f'<a class="hide-m" href="{h}"{" aria-current=page" if actif == k else ""}>{n}</a>' for h, n, k in nav)
    villes_pied = "".join(f'<li><a href="{b}{v["id"]}/">{e(v["nom"])} en famille</a></li>' for v in VILLES)
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
  <a class="logo" href="{b}"><img src="{b}assets/mondo.svg" alt="" width="40" height="44"><span>Petit<b>Mondo</b></span></a>
  <nav class="nav" aria-label="Navigation principale">{nav_html}<a class="cta-nav" href="{b}carnet/">Créer mon carnet</a></nav>
</div></header>
<main>
{corps}
</main>
<footer><div class="wrap">
  <div>
    <a class="logo" href="{b}"><img src="{b}assets/mondo.svg" alt="" width="40" height="44"><span>Petit<b style="color:var(--soleil)">Mondo</b></span></a>
    <p>Le monde à découvrir en famille. Des carnets de voyage gratuits, pensés pour les parents et pour les enfants, utilisables en mode avion.</p>
    <small>Cartes © <a href="https://www.openstreetmap.org/copyright">contributeurs OpenStreetMap</a>. Photos libres de droits via Wikimedia Commons, <a href="{b}credits/">crédits détaillés</a>. Aucun cookie, aucun compte.</small>
  </div>
  <div><h4>Destinations</h4><ul>{villes_pied}</ul></div>
  <div><h4>Outils</h4><ul><li><a href="{b}carnet/">Créer mon carnet</a></li><li><a href="{b}jeux/">Jeux à imprimer</a></li><li><a href="{b}valise/">Valise des enfants</a></li><li><a href="{b}mode-avion/">Utiliser en mode avion</a></li><li><a href="{b}methode/">Notre méthode</a></li></ul></div>
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


def leaflet_scripts(b, ville_id, calques=None):
    c = f"window.PM_CALQUES={json.dumps(calques)};" if calques else ""
    return (f'<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
            f'<script src="{b}assets/commun.js"></script>'
            f'<script>window.PM_VILLE="{ville_id}";{c}</script>'
            f'<script src="{b}assets/ville.js"></script>')


def proches(osm, lieu, cat, n=3, maxi=800):
    if not osm:
        return []
    r = sorted(((p, dist(lieu, p)) for p in osm["points"] if p["c"] == cat), key=lambda x: x[1])
    return [x for x in r if x[1] <= maxi][:n]


def badges(a):
    b = ['<span class="badge b">Couvert</span>' if a["interieur"] else '<span class="badge">Plein air</span>']
    if a["gratuit"] is True: b.append('<span class="badge s">Gratuit</span>')
    elif a["gratuit"] == "partiel": b.append('<span class="badge s">En partie gratuit</span>')
    if a["reservation"]: b.append('<span class="badge c">Réserver</span>')
    if a.get("excursion"): b.append('<span class="badge l">Excursion</span>')
    b.append({"facile": '<span class="badge l">Poussette OK</span>', "moyen": '<span class="badge g">Poussette possible</span>',
              "difficile": '<span class="badge c">Porte-bébé conseillé</span>'}[a["poussette"]])
    return "".join(b)


def carte_act(a, v, osm, b):
    site = f'<a href="{e(a["site"])}" target="_blank" rel="noopener">Site officiel</a>' if a.get("site") else ""
    li = []
    for c in ("toilettes", "aire_jeux", "table_langer"):
        pr = proches(osm, a, c, 1, 600)
        if pr:
            li.append(f'<li>{ico(CAT_ICO[c], "i s", b)}{CAT_NOM[c]} à {fmt_dist(pr[0][1])}</li>')
    prox = f'<div class="proches"><ul>{"".join(li)}</ul></div>' if li else ""
    ph = photo(f'{v["id"]}/{a["id"]}', a["nom"], b, "photo carte-photo", f'assets/villes/{v["id"]}.svg')
    return f'''<article class="carte act" data-min="{a["ages"][0]}" data-max="{a["ages"][1]}" data-int="{" ".join(a["interets"])}" data-couvert="{int(a["interieur"])}" data-gratuit="{int(a["gratuit"] is not False)}">
  {ph}<span class="badge tampon ages">{a["ages"][0]}–{a["ages"][1]} ans</span>
  <h3>{e(a["nom"])}</h3>
  <div class="meta">Environ {duree(a["duree"])} · {e(v["zones"][a["zone"]]["nom"])}</div>
  <div class="badges">{badges(a)}</div>
  <p>{e(a["conseil"])}</p>
  <p class="acces">{ico("carte", "i s", b)}<span><strong>{e(a["adresse"])}</strong><br>{e(a["transport"])}</span></p>{prox}
  <div class="liens"><a href="{maps(a["nom"], a["adresse"])}" target="_blank" rel="noopener">Voir sur la carte</a>{site}</div>
</article>'''


def cartes_liens(liens, b):
    return '<div class="grille">' + "".join(
        f'<a class="carte {c}" href="{h}">{ico(i, "i l", b)}<h3>{e(t)}</h3><p>{e(d)}</p><span class="suite">Voir {ico_btn("fleche", b)}</span></a>'
        for h, i, t, d, c in liens) + "</div>"


def faq_html(faq):
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in faq]}
    return ("".join(f'<details class="carte"><summary>{e(q)}</summary><p>{e(r)}</p></details>' for q, r in faq)
            + f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>')


def carte_section(titre, texte):
    return f'''<section id="carte"><div class="wrap">
  <div class="tete-section"><div><h2>{titre}</h2><p>{texte}</p></div></div>
  <div class="filtres" id="calques"></div>
  <div id="map" aria-label="Carte interactive"></div>
  <p class="note" id="osm-info" style="margin-top:16px">Chargement des données OpenStreetMap…</p>
</div></section>'''


def bloc_avion(b):
    return f'''<div class="avion carte">{ico("avion", "i l", b)}<div><h3>Utilisable en mode avion</h3>
<p>Enregistrez le carnet en PDF avant de partir : programme, adresses, transports, numéros d'urgence et jeux des enfants s'ouvrent ensuite sans aucun réseau. Les pages PetitMondo déjà consultées restent aussi disponibles hors connexion.</p>
<a class="suite" href="{b}mode-avion/">Comment faire {ico_btn("fleche", b)}</a></div></div>'''


# ---------------------------------------------------------------- pages enfants (partagées : carnet PDF + site)
CHASSE = [
    "Trouve un animal sculpté sur un bâtiment, une fontaine ou une statue. Dessine-le.",
    "Écris le nom d'une rue, d'une place ou d'une station que tu as aimée.",
    "Trouve quelque chose de rouge, quelque chose de bleu et quelque chose de doré.",
    "Goûte un aliment que tu ne connaissais pas. C'était comment ?",
    "Compte les marches d'un escalier que tu as monté aujourd'hui.",
    "Repère un mot que tu ne comprends pas et demande ce qu'il veut dire.",
    "Avec l'aide d'un adulte, prends une photo de ton endroit préféré.",
]


def svg_picto(body):
    return f'<svg viewBox="0 0 48 48" fill="none" stroke="#1B2A4A" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" aria-hidden="true">{body}</svg>'


def pages_enfants(v, b, nb_journal=3):
    """Renvoie (page découverte + mots, pages de jeux)."""
    n, k = v["nom"], v["enfants"]
    dr = "".join(drapeau(c, f'{v["id"]}{i}') for i, c in enumerate(k["drapeaux"]))
    francais = v["pays"] == "France"
    tuiles = [("Le pays", k["pays"][0].upper() + k["pays"][1:]), (f"La capitale {de(k['pays'])}", k["capitale"]),
              ("On y parle", k["langue"]), ("On paie avec", k["monnaie"])]
    decouvre = f'''<section class="page-enfant decouvre">
  <div class="pe-tete"><img src="{b}assets/mondo-coucou.svg" alt="" class="pe-mondo"><div><span class="etiquette"><i></i>Le carnet de l'explorateur</span><h2>Découvre {e(n)}</h2></div></div>
  <div class="drapeaux">{dr}</div>
  <div class="tuiles">{"".join(f'<div class="tuile"><small>{e(t)}</small><b>{e(val)}</b></div>' for t, val in tuiles)}</div>
  <h3>Le savais-tu ?</h3>
  <ol class="faits">{"".join(f"<li>{e(f)}</li>" for f in k["faits"])}</ol>
</section>'''
    if k.get("mots_type") == "definitions":
        lignes = "".join(f'<div class="mot def"><b>{e(m)}</b><span>{e(d)}</span></div>' for m, d in k["mots"])
        decouvre += f'''<section class="page-enfant mots">
  <div class="pe-tete"><img src="{b}assets/mondo.svg" alt="" class="pe-mondo"><div><span class="etiquette"><i></i>Petit dictionnaire</span><h2>{e(k["mots_titre"])}</h2></div></div>
  <p class="pe-consigne">Ces mots, tu vas les entendre ou les voir pendant le voyage. Coche ceux que tu as rencontrés.</p>
  <div class="liste-mots">{lignes}</div>
</section>'''
    else:
        lignes = "".join(f'<div class="mot"><span class="fr">{e(fr)}</span><b>{e(loc)}</b><span class="pr">« {e(pr)} »</span></div>' for fr, loc, pr in k["mots"])
        bonus = f'<p class="pe-consigne" style="margin-top:14px">{e(k["mots_bonus"])}</p>' if k.get("mots_bonus") else ""
        decouvre += f'''<section class="page-enfant mots">
  <div class="pe-tete"><img src="{b}assets/mondo.svg" alt="" class="pe-mondo"><div><span class="etiquette"><i></i>Parle comme un habitant</span><h2>{e(k["mots_titre"])}</h2></div></div>
  <p class="pe-consigne">Lis le mot en gras à voix haute, comme il est écrit entre guillemets. Essaie de le dire à quelqu'un pendant le voyage !</p>
  <div class="liste-mots">{lignes}</div>{bonus}
</section>'''
    bingo = "".join(f"<div>{svg_picto(P[c][1])}<span>{e(P[c][0])}</span></div>" for c in v["bingo"])
    jeux = f'''<section class="page-enfant">
  <div class="pe-tete"><img src="{b}assets/mondo-coucou.svg" alt="" class="pe-mondo"><div><span class="etiquette"><i></i>Jeu</span><h2>Le bingo de {e(n)}</h2></div></div>
  <p class="pe-consigne">Coche chaque case quand tu l'as vue. Une ligne complète : tu as gagné !</p>
  <div class="bingo">{bingo}</div>
</section>
<section class="page-enfant">
  <div class="pe-tete"><img src="{b}assets/mondo.svg" alt="" class="pe-mondo"><div><span class="etiquette"><i></i>Jeu</span><h2>La chasse au trésor</h2></div></div>
  <ol class="chasse">{"".join(f"<li>{e(q)}<div class=ligne-ecrire></div></li>" for q in CHASSE + ([] if francais else ["Dis bonjour et merci à quelqu'un dans la langue du pays."]))}</ol>
</section>
<section class="page-enfant">
  <div class="pe-tete"><img src="{b}assets/mondo-coucou.svg" alt="" class="pe-mondo"><div><span class="etiquette"><i></i>Coloriage</span><h2>Colorie Mondo</h2></div></div>
  <p class="pe-consigne">Mondo part à {e(n)} avec toi. De quelles couleurs sera-t-elle ?</p>
  <img src="{b}assets/mondo-coloriage.svg" alt="Mondo à colorier" class="coloriage">
</section>'''
    for i in range(1, nb_journal + 1):
        jeux += f'''<section class="page-enfant journal" data-jour="{i}">
  <div class="pe-tete"><img src="{b}assets/mondo.svg" alt="" class="pe-mondo"><div><span class="etiquette"><i></i>Journal de bord</span><h2>Mon jour {i} à {e(n)}</h2></div></div>
  <p class="pe-consigne">Aujourd'hui, il fait : ☐ soleil &nbsp; ☐ nuages &nbsp; ☐ pluie &nbsp; ☐ vent</p>
  <h4>Ce que j'ai vu</h4><div class="ligne-ecrire"></div><div class="ligne-ecrire"></div>
  <h4>Ce que j'ai mangé</h4><div class="ligne-ecrire"></div>
  <h4>Mon dessin du jour</h4><div class="cadre-dessin"></div>
  <h4>Ma note de la journée</h4><p class="etoiles">☆ ☆ ☆ ☆ ☆</p>
</section>'''
    return decouvre, jeux


# ---------------------------------------------------------------- pages ville
def pages_ville(v, osm):
    vid, n = v["id"], v["nom"]
    parc = v.get("type") == "parc"
    acts = v["activites"]
    d1, d2 = 1, 2
    b1, b2 = rel(d1), rel(d2)
    compte = (osm or {}).get("compte", {})
    lien_carnet = lambda q, b: f"{b}carnet/#v={vid}&{q}"
    pluie = [a for a in acts if a["interieur"]]
    gratuits = [a for a in acts if a["gratuit"] is not False]
    bebe = [a for a in acts if a["ages"][0] <= 1]
    ados = sorted([a for a in acts if a["ages"][1] >= 15 and a["ages"][0] >= 4], key=lambda a: -a["ages"][0])
    faciles = [a for a in acts if a["poussette"] == "facile"]
    difficiles = [a for a in acts if a["poussette"] == "difficile"]
    illu = f"assets/villes/{vid}.svg"
    conseil_poussette = next((c for c in v["conseils"] if "poussette" in (c["titre"] + c["texte"]).lower()), None)
    noms = lambda l, k=2: ", ".join(a["nom"] for a in l[:k])
    restos = [p for p in (osm or {}).get("points", []) if p["c"] == "resto_enfants"]

    themes = []
    if len(bebe) >= 3: themes.append(("avec-un-bebe", "bebe", "Avec un bébé", "Lieux adaptés dès la naissance, sieste et change.", "corail"))
    if len(pluie) >= 3: themes.append(("quand-il-pleut", "pluie", "Quand il pleut", f"{len(pluie)} lieux couverts pour sauver la journée.", "ciel"))
    if len(gratuits) >= 4: themes.append(("gratuit", "gratuit", f"{n} gratuit", f"{len(gratuits)} sorties gratuites ou en partie gratuites.", "soleil"))
    if len(ados) >= 3: themes.append(("avec-des-ados", "ado", "Avec des ados", f"{noms(ados)} et d'autres idées pour les grands.", "menthe"))
    if len(faciles) >= 3 and difficiles: themes.append(("poussette", "poussette", "En poussette", "Ce qui roule, ce qui coince, et les alternatives.", "lilas"))
    if compte.get("aire_jeux", 0) >= 20: themes.append(("aires-de-jeux", "jeux", "Aires de jeux", f"{compte['aire_jeux']} aires recensées, les plus proches de chaque lieu.", "menthe"))
    if compte.get("toilettes", 0) >= 20: themes.append(("toilettes-et-tables-a-langer", "langer", "Toilettes et tables à langer", "Où se changer et où trouver des toilettes.", "lilas"))
    if len(restos) >= 5: themes.append(("restaurants-enfants", "resto", "Restaurants équipés", "Table à langer, chaise haute ou coin enfants signalés.", "soleil"))
    themes.append(("jeux", "jeu", "Jeux à imprimer", "Bingo, chasse au trésor, coloriage et journal de voyage.", "corail"))
    themes.append(("decouvrir", "enfant", f"{n} pour les enfants", "Le pays, la langue, les premiers mots et les secrets du lieu.", "soleil"))
    if vid in LEXIQUES: themes.append(("lexique", "bulle", "Phrases des parents", f"En {' et '.join(LEXIQUES[vid][0]).lower()} : table à langer, pharmacie, fièvre…", "ciel"))

    def liens_themes(depuis_ville, sauf=None):
        pref = "" if depuis_ville else "../"
        return [(f"{pref}{s}/", i, t, d, c) for s, i, t, d, c in themes if s != sauf]

    def hero(depth, surtitre, titre_html, lead, cta_q="j=3&a=5&r=equilibre"):
        b = rel(depth)
        ph = photo(f"{vid}/_ville", f"Vue de {n}", b, "photo hero-photo")
        visuel = ph or f'<img src="{b}{illu}" alt="" width="640" height="320" class="hero-illu">'
        return f'''<section class="hero"><div class="wrap grid">
  <div>
    <span class="etiquette"><i></i>{e(surtitre)}</span>
    <h1>{titre_html}</h1>
    <p class="lead">{lead}</p>
    <div class="cta"><a class="btn" href="{lien_carnet(cta_q, b)}">{ico_btn("pdf", b)}Créer mon carnet pour {e(n)}</a><a class="btn sec" href="#carte">Voir la carte pratique</a></div>
  </div>
  <div class="visuel">{visuel}<img class="mondo" src="{b}assets/mondo-coucou.svg" alt=""></div>
</div></section>'''

    def chiffres(b):
        if parc:
            items = [("activite", len(acts), "zones et spectacles"), ("horloge", "2", "parcs"),
                     ("bebe", "2", "Baby Care Centres"), ("enfant", "– de 3 ans", "entrée gratuite")]
        else:
            items = [("activite", len(acts), "lieux sélectionnés"), ("jeux", compte.get("aire_jeux", "–"), "aires de jeux"),
                     ("toilettes", compte.get("toilettes", "–"), "toilettes publiques"),
                     ("langer", (compte.get("table_langer", 0) + compte.get("resto_enfants", 0)) or "–", "lieux avec table à langer ou équipés")]
        return '<div class="chiffres">' + "".join(f'<div class="chiffre">{ico(i, "i", b)}<div><b>{c}</b><span>{t}</span></div></div>' for i, c, t in items) + "</div>"

    if parc:
        programmes = [("j=1&a=5&r=intense", "horloge", "Une journée au château", "Disneyland Park, de l'ouverture au spectacle du soir.", "corail"),
                      ("j=2&a=4-7&r=equilibre", "jeux", "Deux jours, deux parcs", "Un jour par parc, avec les pauses des enfants.", "menthe"),
                      ("j=2&a=1&r=calme&p=1", "bebe", "Avec un bébé", "Rythme tranquille, sieste et Baby Care Centre.", "lilas"),
                      ("j=2&a=12-15&r=intense", "ado", "Avec des ados", "Sensations, super-héros et spectacles.", "ciel")]
    else:
        top_int = sorted(INTERETS, key=lambda k: -sum(1 for a in acts if k in a["interets"] and a["ages"][0] <= 4))[:2]
        programmes = [("j=3&a=1&r=calme&p=1", "bebe", "3 jours avec un bébé", f"Rythme tranquille, poussette et sieste. {noms([a for a in bebe if a['poussette'] == 'facile'])}…", "corail"),
                      (f"j=3&a=4-7&r=equilibre&i={'-'.join(top_int)}", "jeux", "3 jours avec 4 et 7 ans", f"{INTERETS[top_int[0]]} et {INTERETS[top_int[1]].lower()}, avec des pauses aires de jeux.", "menthe"),
                      ("j=4&a=12-15&r=intense&i=aventure-culture", "ado", "4 jours avec des ados", f"{noms(ados)}…", "ciel")]
        if sum(1 for a in acts if a["gratuit"] is True) >= 4:
            programmes.append(("j=2&a=6&r=equilibre&b=serre", "gratuit", "Week-end petit budget", "Priorité aux parcs et aux lieux gratuits.", "soleil"))

    if parc:
        faq = [("Combien de jours prévoir à Disneyland Paris avec des enfants ?", "Une journée permet de profiter de Disneyland Park. Deux jours, un par parc, laissent le temps de souffler avec des enfants. Au-delà, alternez avec une demi-journée calme, par exemple à l'aquarium de Val d'Europe."),
               ("Disneyland Paris est-il gratuit pour les bébés ?", "Oui, l'entrée est gratuite pour les moins de 3 ans. Un Baby Care Centre est installé dans chacun des deux parcs."),
               ("Peut-on faire les attractions à tour de rôle avec un petit ?", "Oui, avec le service Rider Switch : un parent monte, l'autre garde l'enfant, puis ils échangent sans refaire la file."),
               ("Comment venir à Disneyland Paris sans voiture ?", "La gare Marne-la-Vallée-Chessy, desservie par le RER A et le TGV, se trouve juste devant l'entrée des parcs.")]
    else:
        faq = [(f"Combien de jours prévoir à {n} avec des enfants ?", "Trois jours permettent de voir l'essentiel sans courir, avec une visite majeure le matin et une pause l'après-midi. Avec un bébé ou un rythme tranquille, comptez un jour de plus."),
               (f"Que faire à {n} avec un bébé ?", "Privilégiez les lieux plats et ombragés : " + ", ".join(a["nom"] for a in bebe if a["poussette"] == "facile") + "."),
               (f"Que faire à {n} quand il pleut ?", "Les meilleures options couvertes : " + ", ".join(a["nom"] for a in pluie) + "."),
               (f"Quelles activités gratuites à {n} avec des enfants ?", "Sans payer ou presque : " + ", ".join(a["nom"] for a in gratuits) + "."),
               (f"Quels papiers pour {n} avec des enfants ?", v["papiers"])]

    filtres = "".join(f'<button class="chip" type="button" data-f="int:{k}" aria-pressed="false">{l}</button>' for k, l in INTERETS.items() if any(k in a["interets"] for a in acts))
    titre_h1 = f'{e(n)} <span class="hl">en famille</span>' if parc else f'{e(n)} avec <span class="hl">des enfants</span>'
    corps = hero(d1, f"{v['pays']} · guide famille", titre_h1,
                 f"{len(acts)} lieux choisis et décrits pour les familles, un plan B pour chaque jour de pluie, la carte des services utiles et un carnet PDF avec les jeux des enfants.")
    corps += f'<section style="padding-top:8px"><div class="wrap">{chiffres(b1)}</div></section>'
    corps += f'''<section class="sable"><div class="wrap">
  <div class="tete-section"><div><h2>Programmes <span class="hl c">prêts à partir</span></h2><p>Un clic, et le carnet complet se prépare, avec les pages de jeux pour les enfants. Vous pourrez ensuite ajuster les âges, le rythme et les envies.</p></div></div>
  {cartes_liens([(lien_carnet(q, b1), i, t, d, c) for q, i, t, d, c in programmes], b1)}
</div></section>'''
    gratuit_chip = '<button class="chip" type="button" data-f="gratuit" aria-pressed="false">Gratuit</button>' if len(gratuits) > 1 else ""
    corps += f'''<section><div class="wrap">
  <div class="tete-section"><div><h2>Les lieux <span class="hl m">par âge</span></h2><p>Choisissez l'âge de votre enfant ou une envie. Chaque fiche donne l'adresse, le transport et les services les plus proches.</p></div></div>
  <div class="filtres" role="group" aria-label="Filtrer les lieux">
    <label class="chip">Âge <select id="f-age"><option value="">tous</option>{"".join(f'<option value="{i}">{i} an{"s" if i > 1 else ""}</option>' for i in range(18))}</select></label>
    <button class="chip" type="button" data-f="couvert" aria-pressed="false">Couvert</button>
    {gratuit_chip}
    {filtres}
  </div>
  <p id="f-vide" class="note" hidden>Aucun lieu ne correspond à ces filtres.</p>
  <div class="grille g-act" id="liste">{"".join(carte_act(a, v, osm, b1) for a in acts)}</div>
</div></section>'''
    corps += f'''<section class="ciel"><div class="wrap">
  <div class="tete-section"><div><h2>{e(n)} <span class="hl">côté parents et enfants</span></h2><p>Des pages pensées pour une question précise.</p></div></div>
  {cartes_liens(liens_themes(True), b1)}
</div></section>'''
    corps += carte_section('La carte <span class="hl">pratique</span>', "Tous les lieux du guide, et les toilettes, aires de jeux, tables à langer, pharmacies et restaurants équipés signalés. Touchez un point pour lancer l'itinéraire.")
    corps += f'''<section class="sable"><div class="wrap">
  <h2>Bon à savoir</h2>
  <div class="grille" style="margin-top:20px">{"".join(f'<div class="carte"><h3>{e(c["titre"])}</h3><p>{e(c["texte"])}</p></div>' for c in v["conseils"])}</div>
  <div class="grille g2" style="margin-top:24px">
    <div class="carte corail">{ico("urgence", "i", b1)}<h3>Urgences</h3>{"".join(f"<p><strong>{e(u['nom'])}</strong> : {e(u['detail'])}</p>" for u in v["urgences"])}</div>
    <div class="carte">{ico("valise", "i", b1)}<h3>Papiers</h3><p>{e(v["papiers"])}</p><p><a href="{b1}valise/"><strong>La valise complète des enfants</strong></a></p></div>
  </div>
  <div style="margin-top:24px">{bloc_avion(b1)}</div>
</div></section>
<section><div class="wrap etroit">
  <h2>Questions fréquentes</h2>
  {faq_html(faq)}
  <p class="note" style="margin-top:20px">Fiches vérifiées le {date_fr(v["verification"])}. {e(v["avertissement"])}</p>
</div></section>'''
    page(f"{vid}/", f"{n} avec des enfants : lieux, itinéraires et carte pratique | PetitMondo",
         f"Visiter {n} en famille : {len(acts)} lieux classés par âge avec adresse et transport, plan B pluie, services utiles sur la carte et carnet PDF gratuit avec jeux pour les enfants.",
         corps, d1, head=leaflet_head(), scripts=leaflet_scripts(b1, vid), actif="dest")

    # ---------- pages thématiques
    def theme(slug, titre, h1, lead, liste, intro, extra="", calques=None, cta="j=3&a=5&r=equilibre"):
        b = b2
        c = hero(d2, f"{n} · {titre}", h1, lead, cta)
        c += f'<section style="padding-top:8px"><div class="wrap"><p class="muted" style="max-width:46em;font-size:1.05rem">{intro}</p></div></section>'
        if liste:
            c += f'<section style="padding-top:0"><div class="wrap"><div class="grille g-act">{"".join(carte_act(a, v, osm, b) for a in liste)}</div></div></section>'
        c += extra
        c += carte_section('La carte <span class="hl">pratique</span>', "Touchez un point pour lancer l'itinéraire.")
        c += f'''<section class="ciel"><div class="wrap"><h2>Continuer</h2>{cartes_liens(liens_themes(False, slug)[:4], b)}
<p class="note" style="margin-top:22px">Fiches vérifiées le {date_fr(v["verification"])}. Services issus d'OpenStreetMap, non vérifiés sur place. {e(v["avertissement"])}</p></div></section>'''
        page(f"{vid}/{slug}/", SEO[slug].format(n=n) + " | PetitMondo", lead[:155], c, d2,
             head=leaflet_head(), scripts=leaflet_scripts(b, vid, calques), actif="dest")

    def table_services(cat, titre_col, maxi=600):
        lignes = []
        for a in acts:
            pr = proches(osm, a, cat, 2, maxi)
            cell = "<br>".join(f'<a href="{maps("", lat=p["lat"], lon=p["lon"])}" target="_blank" rel="noopener">{e(nom_point(p))}</a> · {fmt_dist(dd)}{" · " + e(detail_point(p)) if detail_point(p) else ""}' for p, dd in pr) or f'<span class="muted">Aucun signalé à moins de {fmt_dist(maxi)}</span>'
            lignes.append(f'<div class="fr">{e(a["nom"])}</div><div style="grid-column:span 2">{cell}</div>')
        return f'<div class="lex" style="margin-top:20px"><div class="t">Lieu</div><div class="t" style="grid-column:span 2">{titre_col} le plus proche</div>{"".join(lignes)}</div>'

    slugs = {t[0] for t in themes}
    if "avec-un-bebe" in slugs:
        theme("avec-un-bebe", "avec un bébé", f'{e(n)} avec <span class="hl c">un bébé</span>',
              "Les lieux qui conviennent dès la naissance, où changer bébé, et des journées qui laissent la place à la sieste.",
              bebe, "Avec un bébé, on visite surtout le matin et en fin d'après-midi. Le carnet PetitMondo prévoit automatiquement un temps calme après le déjeuner pour les moins de 4 ans.",
              extra=(f'<section class="sable"><div class="wrap"><h2>Où changer bébé</h2><p class="muted">Tables à langer signalées dans OpenStreetMap autour de chaque lieu. Le recensement est encore partiel : gardez un tapis à langer nomade dans le sac.</p>{table_services("table_langer", "Table à langer", 1500)}</div></section>' if osm and not parc else ""),
              calques=["activite", "table_langer", "toilettes", "pharmacie"], cta="j=3&a=1&r=calme&p=1" if not parc else "j=2&a=1&r=calme&p=1")
    if "quand-il-pleut" in slugs:
        theme("quand-il-pleut", "quand il pleut", f'{e(n)} <span class="hl">quand il pleut</span>',
              f"{len(pluie)} lieux couverts pour une matinée ou une après-midi, classés par âge.",
              pluie, "Chaque journée du carnet PetitMondo propose déjà un plan B couvert à proximité. Voici la liste complète, pour réorganiser une journée en un instant.",
              calques=["activite", "toilettes"], cta="j=2&a=5&r=equilibre&i=sciences")
    if "gratuit" in slugs:
        theme("gratuit", "gratuit", f'{e(n)} <span class="hl">gratuit</span> en famille',
              "Parcs, promenades et lieux gratuits ou en partie gratuits : de quoi remplir des journées entières sans billet.",
              gratuits, "Les lieux marqués « en partie gratuit » ont un accès libre mais certaines zones ou activités payantes. Les conditions de gratuité changent : vérifiez sur le site officiel avant de vous déplacer.",
              calques=["activite", "aire_jeux", "toilettes"], cta="j=2&a=6&r=equilibre&b=serre")
    if "avec-des-ados" in slugs:
        resa = [a["nom"] for a in ados if a["reservation"]]
        theme("avec-des-ados", "avec des ados", f'{e(n)} avec <span class="hl m">des ados</span>',
              f"{noms(ados, 3)} : les visites qui tiennent les plus grands en éveil.",
              ados[:12], "Avec des adolescents, laissez-les choisir une activité par jour et gardez du temps libre en fin de journée." + (f" Pensez à réserver à l'avance : {', '.join(resa)}." if resa else ""),
              calques=["activite"], cta="j=2&a=12-15&r=intense" if parc else "j=4&a=12-15&r=intense&i=aventure-culture")
    if "poussette" in slugs:
        astuce = f'<div class="carte" style="margin-top:24px">{ico("poussette", "i", b2)}<h3>{e(conseil_poussette["titre"])}</h3><p>{e(conseil_poussette["texte"])}</p></div>' if conseil_poussette else ""
        theme("poussette", "en poussette", f'{e(n)} <span class="hl">en poussette</span>',
              "Ce qui roule sans effort, ce qui demande un porte-bébé, et comment se déplacer.",
              faciles, "Ces lieux se visitent sans difficulté avec une poussette. Plus bas, ceux où le porte-bébé sera bien plus confortable.",
              extra=f'<section class="sable"><div class="wrap"><h2>Plutôt en porte-bébé</h2><div class="grille g-act" style="margin-top:20px">{"".join(carte_act(a, v, osm, b2) for a in difficiles)}</div>{astuce}</div></section>',
              calques=["activite", "toilettes"], cta="j=3&a=1&r=calme&p=1")
    if "aires-de-jeux" in slugs:
        jeux_proches = "".join(
            f'<div class="carte"><h3>{e(a["nom"])}</h3>' + ("".join(f'<p>{ico("jeux", "i s", b2)} <a href="{maps("", lat=p["lat"], lon=p["lon"])}" target="_blank" rel="noopener">{e(nom_point(p))}</a>, à {fmt_dist(dd)}</p>' for p, dd in proches(osm, a, "aire_jeux", 3, 700)) or '<p class="muted">Aucune aire signalée à moins de 700 m.</p>') + "</div>"
            for a in acts)
        theme("aires-de-jeux", "aires de jeux", f'Les aires de jeux <span class="hl m">à {e(n)}</span>',
              f"{compte['aire_jeux']} aires de jeux recensées, et les plus proches de chaque lieu pour la récréation entre deux visites.",
              [], "Le bon réflexe : une aire de jeux entre deux visites, même dix minutes. Voici celles qui se trouvent à quelques pas des lieux du guide.",
              extra=f'<section style="padding-top:0"><div class="wrap"><div class="grille">{jeux_proches}</div></div></section>', calques=["aire_jeux", "activite"])
    if "toilettes-et-tables-a-langer" in slugs:
        theme("toilettes-et-tables-a-langer", "toilettes et tables à langer", f'Toilettes et <span class="hl c">tables à langer</span> à {e(n)}',
              f"{compte['toilettes']} toilettes publiques recensées et les tables à langer signalées, autour de chaque lieu.",
              [], "Repérez les toilettes à l'avance, surtout dans les quartiers anciens. Les musées, centres commerciaux et grandes gares disposent généralement de toilettes avec table à langer, même si elles ne sont pas toutes recensées.",
              extra=f'<section style="padding-top:0"><div class="wrap"><h2>Toilettes</h2>{table_services("toilettes", "Toilettes")}<h2 style="margin-top:36px">Tables à langer</h2>{table_services("table_langer", "Table à langer", 1500)}</div></section>',
              calques=["toilettes", "table_langer", "activite"])
    if "restaurants-enfants" in slugs:
        def resto_carte(p):
            t = p["t"]
            site = f'<a href="{e(t["website"])}" target="_blank" rel="noopener">Site</a>' if t.get("website") else ""
            heures = f'<p class="muted">{e(t["opening_hours"])}</p>' if t.get("opening_hours") else ""
            return (f'<div class="carte act">{ico("resto", "i", b2)}<h3>{e(nom_point(p))}</h3><p>{e(detail_point(p)) or "Équipement famille signalé"}</p>{heures}'
                    f'<div class="liens"><a href="{maps("", lat=p["lat"], lon=p["lon"])}" target="_blank" rel="noopener">Voir sur la carte</a>{site}</div></div>')
        theme("restaurants-enfants", "restaurants pour enfants", f'Restaurants <span class="hl">équipés pour les enfants</span> à {e(n)}',
              "Les restaurants et cafés signalés avec table à langer, chaise haute ou coin enfants dans OpenStreetMap.",
              [], "Cette liste ne reflète que ce que les contributeurs ont signalé : beaucoup d'autres restaurants accueillent bien les familles. Appelez avant pour confirmer l'équipement.",
              extra=f'<section style="padding-top:0"><div class="wrap"><div class="grille">{"".join(resto_carte(p) for p in sorted(restos, key=nom_point))}</div></div></section>',
              calques=["resto_enfants", "activite"])

    # ---------- pages enfants : fragment du carnet PDF + pages web
    dec_f, jeux_f = pages_enfants(v, "{{BASE}}", 5)
    (ROOT / "data" / "enfants").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "enfants" / f"{vid}.html").write_text(dec_f + jeux_f, encoding="utf-8")
    dec_w, jeux_w = pages_enfants(v, b2)
    autres_lien = "../jeux/"
    c = f'''<section class="hero no-print"><div class="wrap grid">
  <div><span class="etiquette"><i></i>À lire avec les enfants</span>
  <h1>{e(n)} <span class="hl">pour les enfants</span></h1>
  <p class="lead">Le pays, la capitale, la langue, les premiers mots et ce qu'il faut savoir avant de partir, en phrases simples. Ces pages sont aussi dans le carnet PDF.</p>
  <div class="cta"><button class="btn" type="button" onclick="print()">{ico_btn("pdf", b2)}Imprimer ces pages</button><a class="btn sec" href="{autres_lien}">Les jeux de {e(n)}</a></div></div>
  <div class="visuel"><img src="{b2}{illu}" alt="" class="hero-illu"><img class="mondo" src="{b2}assets/mondo-coucou.svg" alt=""></div>
</div></section>
<section style="padding-top:0"><div class="wrap etroit">{dec_w}</div></section>'''
    page(f"{vid}/decouvrir/", f"{n} expliqué aux enfants : pays, langue, premiers mots | PetitMondo",
         f"Préparer les enfants au voyage à {n} : le pays, la capitale, la langue, les mots à connaître et les secrets du lieu, à lire ou à imprimer.",
         c, 2, actif="jeux")
    c = f'''<section class="hero no-print"><div class="wrap grid">
  <div><span class="etiquette"><i></i>À imprimer · 3 à 10 ans</span>
  <h1>Les jeux de <span class="hl">{e(n)}</span></h1>
  <p class="lead">Bingo à cocher, chasse au trésor, coloriage de Mondo et trois pages de journal de bord. Imprimez, glissez dans le sac : les visites deviennent un jeu. Ces pages sont aussi incluses dans le carnet PDF.</p>
  <div class="cta"><button class="btn" type="button" onclick="print()">{ico_btn("pdf", b2)}Imprimer les jeux</button><a class="btn sec" href="../decouvrir/">{e(n)} pour les enfants</a></div></div>
  <div class="visuel"><img src="{b2}assets/mondo-coucou.svg" alt="Mondo, la chouette de PetitMondo" style="max-width:260px;display:block;margin:0 auto"></div>
</div></section>
<section style="padding-top:0"><div class="wrap etroit">{jeux_w}</div></section>'''
    page(f"{vid}/jeux/", f"Jeux à imprimer pour visiter {n} avec des enfants | PetitMondo",
         f"Bingo, chasse au trésor, coloriage et journal de voyage à imprimer gratuitement pour occuper les enfants pendant les visites à {n}.",
         c, 2, actif="jeux")

    if vid in LEXIQUES:
        langues, lignes = LEXIQUES[vid]
        tete = "".join(f'<div class="t">{x}</div>' for x in ["Français"] + langues)
        corps_l = "".join("".join(f'<div class="{"fr" if i == 0 else ""}">{e(x)}</div>' for i, x in enumerate(l)) for l in lignes)
        cols = " ".join(["1.1fr"] + ["1fr"] * len(langues))
        c = f'''<section class="hero"><div class="wrap etroit">
  <span class="etiquette"><i></i>{e(n)} · phrases utiles</span>
  <h1>Les phrases <span class="hl">des parents</span></h1>
  <p class="lead">Les phrases qui servent vraiment avec des enfants, à lire ou à montrer sur votre téléphone. Elles restent consultables en mode avion une fois la page ouverte.</p>
</div></section>
<section style="padding-top:0"><div class="wrap etroit">
  <div class="lex l{len(langues)}" style="grid-template-columns:{cols}">{tete}{corps_l}</div>
  <p style="margin-top:22px"><button class="btn sec" type="button" onclick="print()">Imprimer les phrases</button> <a class="btn jaune" href="../decouvrir/">Les mots des enfants</a></p>
</div></section>'''
        page(f"{vid}/lexique/", f"Phrases utiles pour voyager à {n} avec des enfants | PetitMondo",
             f"Table à langer, chaise haute, pharmacie, fièvre, allergie : les phrases en {' et '.join(langues).lower()} dont les parents ont besoin à {n}.",
             c, 2, actif="dest")


# ---------------------------------------------------------------- pages générales
def accueil():
    total = sum(len(v["activites"]) for v in VILLES)
    dest = ""
    for v in VILLES:
        visuel = photo(f'{v["id"]}/_ville', v["nom"], "", "photo", legende=False) or f'<img src="assets/villes/{v["id"]}.svg" alt="">'
        dest += f'''<a class="ville" href="{v["id"]}/"><div class="illu">{visuel}</div>
<div class="txt"><div><strong>{e(v["nom"])}</strong><small>{e(v["accroche"])}</small></div><span class="badge tampon">{len(v["activites"])} lieux</span></div></a>'''
    dest += "".join(f'<div class="ville off"><div class="illu vide">{e(nv)}</div><div class="txt"><div><strong>{e(nv)}</strong><small>{e(pays)}</small></div><span class="badge g">Bientôt</span></div></div>' for nv, pays in VILLES_A_VENIR)
    rome = next((v for v in VILLES if v["id"] == "rome"), VILLES[0])
    mots_demo = "".join(f'<div class="mot"><span class="fr">{e(fr)}</span><b>{e(loc)}</b><span class="pr">« {e(pr)} »</span></div>' for fr, loc, pr in rome["enfants"]["mots"][:3])
    corps = f'''<section class="hero"><div class="wrap grid">
  <div>
    <span class="etiquette"><i></i>Gratuit · sans compte · utilisable en mode avion</span>
    <h1>Votre séjour en famille, <span class="hl">prêt à partir.</span></h1>
    <p class="lead">Choisissez la destination et l'âge de vos enfants. PetitMondo prépare un carnet complet : programme jour par jour, lieux faciles à retrouver, toilettes et aires de jeux à proximité, et des pages de jeux pour les enfants.</p>
    <div class="cta"><a class="btn" href="carnet/">{ico_btn("pdf", "")}Créer mon carnet gratuit</a><a class="btn sec" href="#destinations">Voir les destinations</a></div>
  </div>
  <div class="visuel collage">
    <img src="assets/villes/paris.svg" alt="" class="c1"><img src="assets/villes/rome.svg" alt="" class="c2"><img src="assets/villes/londres.svg" alt="" class="c3">
    <img class="mondo" src="assets/mondo-coucou.svg" alt="Mondo, la chouette guide de PetitMondo">
  </div>
</div></section>
<div class="bandeau"><div class="wrap"><span>Adapté à l'âge de chaque enfant</span><span>Jeux et pages enfants inclus</span><span>Plan B pluie chaque jour</span><span>Fonctionne en mode avion</span></div></div>

<section id="destinations"><div class="wrap">
  <div class="tete-section"><div><h2>Où partez-vous <span class="hl m">en famille</span> ?</h2><p>{total} lieux choisis un par un, avec adresse, transport et services utiles autour.</p></div></div>
  <div class="grille g-villes">{dest}</div>
</div></section>

<section class="sable"><div class="wrap">
  <div class="tete-section"><div><h2>Un carnet, <span class="hl c">deux lecteurs</span></h2><p>Le PDF se partage en deux : une partie pour organiser, une partie pour que les enfants vivent le voyage.</p></div></div>
  <div class="grille g2">
    <div class="carte">{ico("parents", "i l", "")}<h3>Pour les parents</h3>
      <ul class="liste-ok"><li>Programme jour par jour, horaires et temps de marche</li><li>Chaque lieu numéroté comme sur la carte, avec photo, adresse, transport et QR code vers l'itinéraire</li><li>Toilettes, aire de jeux et table à langer les plus proches</li><li>Un plan B couvert pour chaque journée</li><li>Checklist de départ, papiers, urgences</li><li>Carte à importer dans Google My Maps</li></ul></div>
    <div class="carte soleil">{ico("enfant", "i l", "")}<h3>Pour les enfants</h3>
      <ul class="liste-ok"><li>« Découvre la ville » : pays, capitale, langue et secrets, en phrases simples</li><li>Ses premiers mots dans la langue du pays, avec la prononciation</li><li>« Ce que je vais voir » : les lieux du séjour en grand, à cocher</li><li>Bingo des rues, chasse au trésor et coloriage</li><li>Un journal de bord pour chaque jour</li></ul></div>
  </div>
  <div class="apercu" aria-hidden="true">
    <div class="feuille f1">{drapeau("it", "demo")}<b class="ft">Découvre Rome</b><div class="tuiles mini"><div class="tuile"><small>On y parle</small><b>l'italien</b></div><div class="tuile"><small>On paie avec</small><b>l'euro (€)</b></div></div></div>
    <div class="feuille f2"><b class="ft">Mes premiers mots en italien</b><div class="liste-mots mini">{mots_demo}</div></div>
    <div class="feuille f3"><b class="ft">Le bingo de Rome</b><div class="bingo mini">{"".join(f"<div>{svg_picto(P[c][1])}</div>" for c in ["casque-romain", "glace", "fontaine", "pizza", "chat", "scooter"])}</div></div>
  </div>
</div></section>

<section><div class="wrap">
  <div class="tete-section"><div><h2>Comment ça <span class="hl m">marche</span></h2><p>Trente secondes, et le séjour est organisé.</p></div></div>
  <div class="etapes3">
    <div class="carte">{ico("carte", "i l", "")}<h3>Vous choisissez</h3><p>La destination, le nombre de jours, l'âge de chaque enfant, la poussette et vos envies.</p></div>
    <div class="carte soleil">{ico("horloge", "i l", "")}<h3>PetitMondo organise</h3><p>Lieux groupés par quartier, temps de marche, déjeuner, sieste des petits et plan B pluie.</p></div>
    <div class="carte menthe">{ico("avion", "i l", "")}<h3>Vous partez</h3><p>Enregistrez le PDF : il s'ouvre en mode avion, sans réseau, du départ au retour.</p></div>
  </div>
</div></section>

<section class="ciel"><div class="wrap">
  <div class="tete-section"><div><h2>Ce que les autres guides <span class="hl c">oublient</span></h2><p>Un guide touristique dit où aller. PetitMondo dit aussi comment tenir la journée avec des enfants.</p></div></div>
  <div class="grille">
    <div class="carte">{ico("bebe", "i", "")}<h3>L'âge réel de chaque enfant</h3><p>Un bébé, un enfant de 5 ans et un ado n'ont pas le même voyage. Le programme s'équilibre entre eux.</p></div>
    <div class="carte">{ico("toilettes", "i", "")}<h3>Les toilettes les plus proches</h3><p>Pour chaque lieu, avec la distance à pied.</p></div>
    <div class="carte">{ico("langer", "i", "")}<h3>Où changer bébé</h3><p>Tables à langer signalées, y compris celles accessibles aux papas.</p></div>
    <div class="carte">{ico("jeux", "i", "")}<h3>La récré entre deux visites</h3><p>L'aire de jeux la plus proche, pour se défouler dix minutes.</p></div>
    <div class="carte">{ico("pluie", "i", "")}<h3>Un plan B chaque jour</h3><p>Pluie, fatigue ou fermeture : un lieu couvert à proximité.</p></div>
    <div class="carte">{ico("poussette", "i", "")}<h3>Poussette ou porte-bébé</h3><p>Chaque lieu indique s'il roule ou s'il vaut mieux porter.</p></div>
  </div>
</div></section>

<section><div class="wrap">{bloc_avion("")}</div></section>

<section class="sable"><div class="wrap">
  <div class="tete-section"><div><h2>Les <span class="hl m">outils</span> du voyage</h2><p>Gratuits, à utiliser seuls ou avec le carnet.</p></div></div>
  {cartes_liens([("jeux/", "jeu", "Les jeux des enfants", "Bingo, chasse au trésor, coloriage et journal pour chaque destination.", "corail"),
                 ("valise/", "valise", "La valise des enfants", "La liste à cocher selon l'âge et la saison.", "soleil"),
                 ("mode-avion/", "avion", "En mode avion", "Tout garder sur le téléphone, sans réseau.", "ciel"),
                 ("methode/", "loupe", "Notre méthode", "D'où viennent les informations et ce qui est vérifié.", "menthe")], "")}
</div></section>

<section><div class="wrap etroit">
  <h2>Questions fréquentes</h2>
  {faq_html([("PetitMondo est-il vraiment gratuit ?", "Oui. Le carnet, le PDF, la carte et les jeux sont gratuits, sans compte et sans abonnement."),
             ("Le carnet fonctionne-t-il sans internet ?", "Oui. Enregistrez-le en PDF avant de partir : il s'ouvre ensuite en mode avion, avec tous les lieux, adresses, numéros d'urgence et jeux. Seule la carte interactive du site a besoin d'une connexion."),
             ("À partir de quel âge les pages enfants sont-elles utiles ?", "Le bingo, le coloriage et les lieux « Ce que je vais voir » conviennent dès 3 ans. Les pages « Découvre la ville » et les premiers mots sont écrites pour les enfants qui commencent à lire, vers 6 ans, ou à lire avec un adulte."),
             ("Mes informations sont-elles enregistrées ?", "Non. Les réponses du formulaire restent dans le lien de votre carnet, sur votre appareil. Aucun cookie publicitaire, aucun compte."),
             ("Comment importer la carte dans Google Maps ?", "Téléchargez le fichier KML depuis votre carnet, ouvrez Google My Maps, créez une carte et choisissez Importer. Vous retrouverez un calque par journée et par type de service.")])}
</div></section>'''
    page("", "PetitMondo — Carnets de voyage en famille gratuits, avec jeux pour les enfants",
         "Disneyland Paris, Paris, Rome, Londres, Barcelone : un carnet de voyage familial gratuit adapté à l'âge des enfants, avec programme, lieux faciles à retrouver, jeux et pages enfants, utilisable en mode avion.",
         corps, 0, og_titre="PetitMondo — Le monde à découvrir en famille")


def carnet():
    b = "../"
    opts = "".join(f'<option value="{v["id"]}">{e(v["nom"])}</option>' for v in VILLES)
    interets = "".join(f'<input type="checkbox" id="i-{k}" name="interets" value="{k}"><label for="i-{k}">{l}</label>' for k, l in INTERETS.items())
    corps = f'''<div class="wrap" style="padding-top:36px">
  <div class="no-print" style="display:flex;gap:18px;align-items:flex-end;flex-wrap:wrap">
    <img src="{b}assets/mondo.svg" alt="" style="width:96px">
    <div><span class="etiquette"><i></i>Gratuit · sans compte · mode avion</span>
    <h1 style="margin-bottom:.2em">Créer mon <span class="hl">carnet</span></h1>
    <p class="muted" style="max-width:40em;margin:0">Trente secondes pour un séjour organisé, avec les pages des enfants. Rien n'est enregistré : vos réponses restent dans le lien du carnet.</p></div>
  </div>
  <form class="form no-print" id="form-carnet" style="margin-top:26px">
    <div class="deux">
      <div class="champ"><label for="ville">Destination</label><select id="ville" name="ville">{opts}</select></div>
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
    <div class="deux">
      <div class="champ"><label for="depart">Date d'arrivée <span class="muted" style="font-weight:600;font-size:.9rem">(facultatif)</span></label><input type="date" id="depart" name="depart"></div>
      <div class="champ"><span class="lbl">Pages enfants</span><div class="segment"><input type="checkbox" id="pe" name="pe" value="1" checked><label for="pe">Inclure les jeux et la découverte</label></div></div>
    </div>
    <button class="btn" id="b-generer" type="submit">Créer mon carnet</button>
  </form>
  <div class="carnet" id="carnet" hidden aria-live="polite"></div>
</div>'''
    page("carnet/", "Créer mon carnet de voyage en famille, avec jeux pour les enfants | PetitMondo",
         "Générez gratuitement un carnet de voyage familial : programme adapté à l'âge des enfants, lieux numérotés avec photos, services à proximité, pages de jeux, PDF utilisable en mode avion.",
         corps, 1, head=leaflet_head(),
         scripts=f'<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script><script src="{b}assets/commun.js"></script><script src="{b}assets/carnet.js"></script>')


def hub_jeux():
    b = "../"
    cartes = "".join(f'''<div class="carte"><img src="{b}assets/villes/{v["id"]}.svg" alt="" class="mini-illu"><h3>{e(v["nom"])}</h3>
<p class="liens-btn"><a class="btn petit" href="{b}{v["id"]}/jeux/">Jeux à imprimer</a><a class="btn sec petit" href="{b}{v["id"]}/decouvrir/">Découvrir</a></p></div>''' for v in VILLES)
    corps = f'''<section class="hero"><div class="wrap grid">
  <div><span class="etiquette"><i></i>Pour les enfants · à imprimer</span>
  <h1>Le carnet du <span class="hl">petit explorateur</span></h1>
  <p class="lead">Pour chaque destination : un bingo à cocher dans les rues, une chasse au trésor, un coloriage de Mondo, un journal de bord, et une page pour découvrir le pays, sa langue et ses premiers mots. Tout est aussi inclus dans le carnet PDF.</p></div>
  <div class="visuel"><img src="{b}assets/mondo-coucou.svg" alt="Mondo" style="max-width:260px;display:block;margin:0 auto"></div>
</div></section>
<section style="padding-top:0"><div class="wrap"><div class="grille">{cartes}</div></div></section>'''
    page("jeux/", "Jeux de voyage à imprimer pour les enfants | PetitMondo",
         "Bingo des rues, chasse au trésor, coloriage, journal de voyage et découverte du pays à imprimer gratuitement pour Disneyland Paris, Paris, Rome, Londres et Barcelone.", corps, 1, actif="jeux")


VALISE = {
    "Papiers et santé": [("Pièce d'identité de chaque enfant (passeport obligatoire pour le Royaume-Uni)", "tous"), ("Pour le Royaume-Uni : autorisation électronique ETA pour chacun, bébés compris", "tous"),
                          ("Carte européenne d'assurance maladie (CEAM) pour chacun", "tous"), ("Carnet de santé ou ordonnances en cours", "tous"),
                          ("Antipyrétique adapté au poids, avec sa pipette doseuse", "tous"), ("Thermomètre", "tous"), ("Sérum physiologique et pansements", "tous"), ("Crème solaire enfant", "ete")],
    "Bébé (0–2 ans)": [("Couches pour les 48 premières heures", "bebe"), ("Lingettes et tapis à langer nomade", "bebe"), ("Lait infantile habituel en quantité suffisante", "bebe"),
                       ("Biberons, goupillon et boîte doseuse", "bebe"), ("Porte-bébé", "bebe"), ("Gigoteuse et doudou", "bebe"), ("Body de rechange dans le sac de journée", "bebe")],
    "Enfants": [("Doudou et son remplaçant", "petit"), ("Gourde par enfant", "tous"), ("En-cas pour chaque journée", "tous"), ("Petit sac à dos par enfant", "enfant"),
                ("Pages de jeux PetitMondo imprimées et crayons", "enfant"), ("Livre ou jeu pour le trajet", "tous"), ("Bracelet avec le numéro de téléphone des parents", "petit")],
    "Vêtements": [("Chapeau ou casquette", "ete"), ("Maillot de bain et serviette", "ete"), ("Bonnet, gants et écharpe", "hiver"), ("Coupe-vent ou vêtement de pluie léger", "tous"),
                  ("Une tenue de rechange par jour et par enfant", "tous"), ("Chaussures déjà portées, confortables pour marcher", "tous"), ("Pull pour les soirées", "tous")],
    "Pratique": [("Poussette pliable et légère", "petit"), ("Batterie externe", "tous"), ("Carnet PetitMondo enregistré en PDF sur le téléphone, pour le mode avion", "tous"),
                 ("Copie des réservations hors connexion", "tous"), ("Sacs pour le linge sale", "tous"), ("Pour le Royaume-Uni : adaptateur de prise", "tous")],
}


def valise():
    b = "../"
    groupes = ""
    for t, items in VALISE.items():
        li = "".join(f'<li data-k="{e(x)}" data-p="{p}">{e(x)}</li>' for x, p in items)
        groupes += f'<div class="carte" style="margin-bottom:22px"><h3>{e(t)}</h3><ul class="check valise">{li}</ul></div>'
    corps = f'''<section class="hero"><div class="wrap grid">
  <div><span class="etiquette"><i></i>Liste à cocher · à imprimer</span>
  <h1>La valise <span class="hl">des enfants</span></h1>
  <p class="lead">Touchez un objet pour le cocher. La liste s'adapte à l'âge de vos enfants et à la saison, et reste enregistrée sur ce téléphone, même en mode avion.</p></div>
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
let n=0,ok=0;lis.forEach(li=>{const p=li.dataset.p;const vis=p==='tous'||(p==='ete'||p==='hiver'?sais===p:prof.includes(p));li.hidden=!vis;li.classList.toggle('ok',!!s[li.dataset.k]);if(vis){n++;if(s[li.dataset.k])ok++}});
document.getElementById('v-compte').textContent=ok+' sur '+n+' dans la valise';document.getElementById('v-barre').style.width=(n?ok/n*100:0)+'%'}
lis.forEach(li=>li.addEventListener('click',()=>{s[li.dataset.k]=!s[li.dataset.k];save();maj()}));
document.querySelectorAll('.form input').forEach(i=>i.addEventListener('change',maj));
document.getElementById('v-raz').onclick=()=>{s={};save();maj()};maj()})();</script>'''
    page("valise/", "Valise des enfants : la liste à cocher pour voyager en famille | PetitMondo",
         "La liste de valise pour voyager avec un bébé ou des enfants : papiers, santé, vêtements, objets pratiques. Adaptée à l'âge et à la saison, à cocher ou à imprimer.",
         corps, 1, scripts=js, actif="valise")


def mode_avion():
    b = "../"
    etapes = [("pdf", "Créez votre carnet", "Sur la page « Créer mon carnet », choisissez la destination et les âges, puis touchez « Enregistrer en PDF »."),
              ("check", "Gardez le PDF sur le téléphone", "Sur iPhone : Imprimer, puis Partager › Enregistrer dans Fichiers. Sur Android : Imprimer › Enregistrer au format PDF."),
              ("carte", "Ajoutez PetitMondo à l'écran d'accueil", "Dans Safari : Partager › Sur l'écran d'accueil. Dans Chrome : menu › Ajouter à l'écran d'accueil. Les pages déjà ouvertes restent disponibles sans réseau."),
              ("avion", "Partez l'esprit tranquille", "En mode avion, le PDF s'ouvre avec le programme, les adresses, les transports, les numéros d'urgence et toutes les pages de jeux.")]
    corps = f'''<section class="hero"><div class="wrap grid">
  <div><span class="etiquette"><i></i>Sans réseau, sans forfait</span>
  <h1>PetitMondo <span class="hl">en mode avion</span></h1>
  <p class="lead">Dans l'avion, à l'étranger sans forfait ou dans un musée sans réseau : votre carnet reste lisible. Quatre gestes avant de partir.</p></div>
  <div class="visuel"><img src="{b}assets/mondo-coucou.svg" alt="" style="max-width:240px;display:block;margin:0 auto"></div>
</div></section>
<section style="padding-top:0"><div class="wrap"><div class="etapes3 e4">{"".join(f'<div class="carte">{ico(i, "i l", b)}<h3>{e(t)}</h3><p>{e(d)}</p></div>' for i, t, d in etapes)}</div>
<div class="grille g2" style="margin-top:30px">
  <div class="carte menthe"><h3>Ce qui marche sans réseau</h3><ul class="liste-ok"><li>Le carnet PDF complet, jeux compris</li><li>Les pages PetitMondo déjà ouvertes</li><li>La valise cochée et les phrases utiles</li></ul></div>
  <div class="carte corail"><h3>Ce qui demande une connexion</h3><ul class="liste-ok"><li>La carte interactive et les itinéraires Google Maps</li><li>Les QR codes et liens des sites officiels (horaires, billets)</li><li>La création d'un carnet pour une autre destination</li></ul></div>
</div>
<p style="margin-top:26px"><a class="btn" href="{b}carnet/">{ico_btn("pdf", b)}Créer mon carnet</a></p></div></section>'''
    page("mode-avion/", "Utiliser son carnet de voyage en mode avion | PetitMondo",
         "Comment garder le carnet de voyage PetitMondo sur le téléphone et l'utiliser en mode avion, sans réseau ni forfait à l'étranger.", corps, 1)


def methode():
    b = "../"
    blocs = [("activite", "Les lieux : choisis un par un", "Chaque lieu est sélectionné pour son intérêt avec des enfants, puis décrit avec les âges conseillés, la durée, l'adresse, le transport, l'accès en poussette et le besoin de réserver. Nous ne publions ni horaires ni tarifs détaillés, qui changent trop souvent : chaque fiche renvoie au site officiel. La date de vérification figure sur chaque page."),
             ("carte", "Les services : OpenStreetMap", "Toilettes, aires de jeux, tables à langer, pharmacies et restaurants équipés proviennent d'OpenStreetMap, la carte collaborative mondiale, actualisés chaque semaine. Ils ne sont pas vérifiés sur place et sont toujours présentés comme « signalés ». Les tables à langer y sont encore peu recensées."),
             ("loupe", "Les photos : libres de droits", "Les photos des lieux proviennent de Wikimedia Commons, sous licences libres (domaine public, CC0, CC BY, CC BY-SA). L'auteur et la licence sont indiqués sous chaque photo, dans le PDF et sur la page des crédits. Pour Disneyland Paris, seules nos propres illustrations sont utilisées."),
             ("horloge", "Les programmes : calculés, pas inventés", "Le générateur ne crée aucun lieu. Il choisit parmi les lieux du guide selon l'âge de chaque enfant, vos envies, la poussette et le budget, les regroupe par quartier, calcule les distances à pied et place le déjeuner et la sieste des moins de 4 ans. Les excursions hors de la ville ne sont proposées qu'à partir de 4 jours."),
             ("enfant", "Les pages enfants", "Écrites en phrases courtes pour les enfants qui commencent à lire. Les informations sur chaque pays (capitale, langue, monnaie) et les anecdotes sont vérifiées ; la prononciation est écrite « à la française », pour être lue facilement."),
             ("check", "Vie privée", "Aucun compte, aucun cookie publicitaire. Les réponses du formulaire restent dans le lien de votre carnet. La liste de valise cochée reste dans la mémoire de votre navigateur.")]
    corps = f'''<section class="hero"><div class="wrap etroit">
  <span class="etiquette"><i></i>Transparence</span>
  <h1>Notre <span class="hl m">méthode</span></h1>
  <p class="lead">Un guide pour parents n'a de valeur que si on peut lui faire confiance. Voici d'où viennent les informations et ce qui est vérifié.</p>
</div></section>
<section style="padding-top:0"><div class="wrap etroit">{"".join(f'<div class="carte" style="margin-bottom:22px">{ico(i, "i", b)}<h3>{e(t)}</h3><p>{e(d)}</p></div>' for i, t, d in blocs)}
<p><a href="{b}credits/"><strong>Voir les crédits photos</strong></a></p></div></section>'''
    page("methode/", "Notre méthode : d'où viennent les informations | PetitMondo",
         "Comment PetitMondo sélectionne les lieux, d'où viennent les données sur les toilettes et tables à langer, les photos libres de droits et le calcul des programmes.", corps, 1)


def credits():
    lignes = []
    for v in VILLES:
        noms = {a["id"]: a["nom"] for a in v["activites"]}
        noms["_ville"] = f"vue de {v['nom']}"
        for cle, c in sorted(PHOTOS.items()):
            if cle.split("/")[0] != v["id"]:
                continue
            lieu = noms.get(cle.split("/")[1], cle)
            lien_l = f' · <a href="{e(c["lien_licence"])}" target="_blank" rel="noopener">texte de la licence</a>' if c.get("lien_licence") else ""
            lignes.append(f'<div class="fr">{e(v["nom"])} · {e(lieu)}</div><div>{e(c["auteur"])}</div><div><a href="{e(c["source"])}" target="_blank" rel="noopener">{e(c["licence"])}</a>{lien_l}</div>')
    tableau = f'<div class="lex"><div class="t">Photo</div><div class="t">Auteur</div><div class="t">Licence et source</div>{"".join(lignes)}</div>' if lignes else '<p class="note">Les photos sont en cours de récupération.</p>'
    corps = f'''<section class="hero"><div class="wrap etroit"><span class="etiquette"><i></i>Merci aux photographes</span><h1>Crédits <span class="hl">photos</span></h1>
<p class="lead">Les photos des lieux proviennent de Wikimedia Commons, sous licences libres. Les illustrations, la mascotte Mondo et les pictogrammes sont des créations PetitMondo. Les données cartographiques sont © contributeurs OpenStreetMap, licence ODbL.</p></div></section>
<section style="padding-top:0"><div class="wrap">{tableau}</div></section>'''
    page("credits/", "Crédits photos | PetitMondo", "Auteurs et licences des photos libres de droits utilisées sur PetitMondo.", corps, 1, indexable=False)


def charte():
    b = "../"
    couleurs = [("Nuit", "#1B2A4A", "Texte, contours, ombres"), ("Papier", "#FFF8EC", "Fond du site"), ("Sable", "#FFE7A8", "Sections"),
                ("Soleil", "#FFC93C", "Surlignage, tampons"), ("Corail", "#FF6B4A", "Bouton principal, Mondo"),
                ("Menthe", "#2FB59A", "Aires de jeux, validation"), ("Ciel", "#6EC6F0", "Toilettes, pluie"), ("Lilas", "#A88BEB", "Tables à langer, bébé")]
    nuancier = "".join(f'<div><i style="background:{c}"></i><p>{n}<small>{c} · {u}</small></p></div>' for n, c, u in couleurs)
    icones = "".join(f'<div style="text-align:center">{ico(i, "i l", b)}<p style="font-size:.8rem;font-weight:700;margin-top:4px">{i}</p></div>' for i in
                     ["activite", "toilettes", "jeux", "langer", "pharmacie", "resto", "pluie", "gratuit", "poussette", "bebe", "ado", "enfant", "parents", "carte", "pdf", "valise", "jeu", "horloge", "bulle", "loupe", "check", "urgence", "avion"])
    corps = f'''<section class="hero"><div class="wrap grid">
  <div><span class="etiquette"><i></i>Usage interne</span><h1>Charte <span class="hl">PetitMondo</span></h1>
  <p class="lead">Le style « autocollant » : contours bleu nuit épais, ombres décalées pleines, couleurs franches et ligne pointillée d'itinéraire. Chaleureux pour les enfants, net et rassurant pour les parents.</p></div>
  <div class="visuel"><img src="{b}assets/mondo-coucou.svg" alt="Mondo" style="max-width:240px;display:block;margin:0 auto"></div>
</div></section>
<section style="padding-top:0"><div class="wrap">
  <h2>Mondo, la chouette guide</h2>
  <div class="grille g2" style="margin:20px 0 40px">
    <div class="carte soleil" style="display:flex;gap:16px;justify-content:center;align-items:flex-end;flex-wrap:wrap"><img src="{b}assets/mondo.svg" alt="" style="max-width:140px"><img src="{b}assets/mondo-coucou.svg" alt="" style="max-width:140px"><img src="{b}assets/mondo-coloriage.svg" alt="" style="max-width:110px"></div>
    <div class="carte"><h3>Pourquoi une chouette</h3><p>La chouette voit tout, de jour comme de nuit : c'est la guide qui repère pour les parents les toilettes, la sieste et le plan B. Pour les enfants, c'est une copine de voyage aux grands yeux, qui tient la carte et porte un foulard d'aviateur. Sa silhouette ronde se reconnaît même en tout petit, sur l'icône du téléphone.</p>
    <p><strong>Trois poses :</strong> la guide avec sa carte, le coucou (accueil, pages enfants) et le coloriage. Toujours avec ses contours nuit, jamais déformée ni recolorée, sauf en coloriage. Une seule apparition par écran.</p></div>
  </div>
  <h2>Couleurs</h2><div class="nuancier" style="margin:20px 0 40px">{nuancier}</div>
  <h2>Typographies</h2>
  <div class="grille g2" style="margin:20px 0 40px">
    <div class="carte"><p class="muted">Titres · Bricolage Grotesque 800</p><p style="font:800 2.6rem/1 var(--titre);letter-spacing:-.03em;color:var(--nuit)">Le monde à découvrir en famille</p></div>
    <div class="carte"><p class="muted">Texte · Figtree 400 à 800</p><p style="font-size:1.1rem;color:var(--nuit)">Un programme réaliste, avec les toilettes, aires de jeux et tables à langer autour de chaque visite.</p></div>
  </div>
  <h2>Icônes</h2><div class="grille" style="grid-template-columns:repeat(auto-fill,minmax(90px,1fr));margin:20px 0 40px">{icones}</div>
  <h2>Illustrations des destinations</h2><div class="grille" style="margin:20px 0 40px">{"".join(f'<img src="{b}assets/villes/{v["id"]}.svg" alt="{e(v["nom"])}" style="border:2.5px solid var(--nuit);border-radius:20px">' for v in VILLES)}</div>
  <h2>Ton éditorial</h2>
  <div class="grille g2" style="margin-top:20px">
    <div class="carte menthe"><h3>Oui</h3><p>Phrases courtes et concrètes. On parle aux parents comme un ami qui connaît la ville, on dit ce qui coince, on signale ce qui n'est pas vérifié. Aux enfants, on parle directement : « tu vas voir… ».</p></div>
    <div class="carte corail"><h3>Non</h3><p>Superlatifs creux, émojis en série, prix ou horaires non vérifiés, promesses de sécurité ou d'absence d'allergènes, personnages ou logos de marques.</p></div>
  </div>
</div></section>'''
    page("charte/", "Charte graphique PetitMondo", "Couleurs, typographies, mascotte, icônes et composants de PetitMondo.", corps, 1, indexable=False)


def page_404():
    corps = '''<section class="hero"><div class="wrap etroit" style="text-align:center">
  <img src="assets/mondo-coucou.svg" alt="" style="width:170px">
  <h1>Mondo s'est <span class="hl">perdue</span>.</h1>
  <p class="lead" style="margin:0 auto">Cette page n'existe pas, ou plus. Reprenons depuis le départ.</p>
  <div class="cta" style="justify-content:center"><a class="btn" href="./">Retour à l'accueil</a><a class="btn sec" href="carnet/">Créer mon carnet</a></div>
</div></section>'''
    page("404.html", "Page introuvable | PetitMondo", "Cette page n'existe pas.", corps, 0, indexable=False)
    p = ROOT / "404.html"
    s = p.read_text(encoding="utf-8").replace("<head>", '<head>\n<base href="/PetitMondo/">', 1)  # servie à n'importe quelle profondeur
    p.write_text(s, encoding="utf-8")


def main():
    global PHOTOS
    fp = ROOT / "data" / "photos.json"
    brut = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}
    PHOTOS = {k: c for k, c in brut.items() if (ROOT / c["fichier"]).exists()}
    osm_par_ville = {}
    for f in sorted((ROOT / "data" / "villes").glob("*.json")):
        v = json.loads(f.read_text(encoding="utf-8"))
        VILLES.append(v)
        fo = ROOT / "data" / "osm" / f"{v['id']}.json"
        osm_par_ville[v["id"]] = json.loads(fo.read_text(encoding="utf-8")) if fo.exists() else None
    VILLES.sort(key=lambda v: v.get("ordre", 99))
    (ROOT / "data" / "villes.json").write_text(json.dumps([{"id": v["id"], "nom": v["nom"]} for v in VILLES], ensure_ascii=False), encoding="utf-8")
    accueil()
    carnet()
    for v in VILLES:
        pages_ville(v, osm_par_ville[v["id"]])
    hub_jeux()
    valise()
    mode_avion()
    methode()
    credits()
    charte()
    page_404()
    aujourdhui = date.today().isoformat()
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{URL}{c}</loc><lastmod>{aujourdhui}</lastmod></url>\n" for c, idx in PAGES if idx)
        + "</urlset>\n", encoding="utf-8")
    print(f"{len(PAGES)} pages générées, {len(PHOTOS)} photos")


if __name__ == "__main__":
    main()
