#!/usr/bin/env python3
"""Jours de fermeture et conseils d'affluence, vérifiés le 29 octobre 2026.
Jours au format JavaScript : 0 = dimanche, 1 = lundi … 6 = samedi.
À relancer après modification : python scripts/affluence.py"""
import json
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

FERME = {
    "paris": {"louvre": [2], "evolution": [2], "cite-sciences": [1], "arts-metiers": [1], "catacombes": [1]},
    "rome": {"saint-ange": ([1], "sauf le premier lundi du mois, l'après-midi"), "explora": [1], "ostie": [1], "borghese": [1],
             "vatican": ([0], "sauf le dernier dimanche du mois, gratuit mais très chargé")},
    "barcelone": {"museublau": [1], "boqueria": [0]},
    "lisbonne": {"jeronimos": [1], "torre": [1], "coches": [1], "pavilhao": [1], "marioneta": [1]},
    "amsterdam": {"nemo": ([1], "sauf quelques lundis de vacances scolaires")},
    "prague": {"hracky": [1], "ntm": [1], "planetarium": [1],
               "karlstejn": ([1], "de juillet à octobre ; de novembre à mars, ouverture réduite, surtout le week-end")},
    "vienne": {"nhm": [2], "zoom": [1], "wienmuseum": [1]},
    "bruxelles": {"museum": [1], "trainworld": [1], "mim": [1], "egouts": [1]},
    "madrid": {"naturales": [1], "debod": [1]},
}

AFFLUENCE = {
    "bruxelles": {
        "atomium": "Le plus calme : à l'ouverture ou un jour de semaine. Le week-end et pendant les vacances, l'attente peut dépasser une heure : réservez un créneau.",
        "minieurope": "Le plus calme : à l'ouverture en semaine. Ouvert en saison seulement : vérifiez les dates avant de venir.",
        "grandplace": "Le plus calme : tôt le matin. Le soir, la place illuminée est magique.",
        "manneken": "Toujours une petite foule devant la statue : venez tôt le matin pour la photo.",
        "museum": "Le plus calme : en semaine l'après-midi ; le matin, les classes sont nombreuses.",
        "trainworld": "Le plus calme : un matin en semaine.",
        "centrebd": "Rarement bondé, sauf les jours de pluie le week-end.",
        "choco": "Le plus calme : en matinée. Les démonstrations ont lieu à heures fixes.",
    },
    "madrid": {
        "prado": "Le plus calme : à l'ouverture. Les deux dernières heures sont gratuites, mais la file d'attente est alors longue.",
        "palacio": "Le plus calme : à l'ouverture. Réservez en ligne, surtout le week-end.",
        "retiro": "Le week-end, le parc est très animé : idéal pour les marionnettes et les musiciens. Barques plus rapides à louer le matin.",
        "sangines": "La file est la plus longue en fin d'après-midi et le soir : venez le matin.",
        "sanmiguel": "Le plus calme : en fin de matinée. Le soir, il est bondé.",
        "zoo": "Le plus calme : un matin en semaine. Évitez l'après-midi en été, il fait très chaud.",
        "naturales": "Créneaux gratuits certains après-midi : l'entrée est alors plus chargée.",
        "bernabeu": "L'accès est modifié les jours de match : vérifiez le calendrier avant de réserver.",
        "debod": "Le coucher du soleil attire beaucoup de monde : venez un peu avant.",
    },
    "disneyland-paris": {
        "fantasyland": "Les files sont les plus courtes dans la première heure après l'ouverture : commencez par ici avec les petits.",
        "frozen": "L'un des secteurs les plus demandés : allez-y dès l'ouverture du parc ou en fin de journée.",
        "avengers": "Les files sont plus courtes en fin de journée, pendant que le public se place pour le spectacle du soir.",
        "chateau": "Pour une photo sans foule, passez juste après l'ouverture.",
    },
    "paris": {
        "eiffel": "Le plus calme : à l'ouverture ou après 20 h. Réservez un créneau en ligne, les files sans billet sont longues.",
        "louvre": "Le plus calme : à l'ouverture, ou en nocturne le mercredi et le vendredi. Réservez un créneau, même pour les moins de 18 ans, qui entrent gratuitement.",
        "notredame": "Le plus calme : tôt le matin ou en fin de journée. La file avance vite, mais elle est longue entre 11 h et 16 h.",
        "aquarium": "Très fréquenté le mercredi après-midi, le week-end et pendant les vacances scolaires. Préférez un matin en semaine.",
        "evolution": "Le plus calme : un matin en semaine. Fermé le mardi.",
        "cite-sciences": "Le plus calme : le matin en semaine, hors vacances. La Cité des enfants fonctionne par séances : réservez la vôtre.",
        "grevin": "Le plus calme : à l'ouverture en semaine. Billets moins chers en ligne.",
        "catacombes": "Réservation obligatoire, créneaux souvent complets plusieurs jours à l'avance. Fermé le lundi.",
        "arc": "Le plus calme : à l'ouverture ou au coucher du soleil. Accès par le passage souterrain, jamais en traversant la place.",
        "croisiere": "Le plus calme : le premier départ du matin. Au coucher du soleil, les bateaux sont pleins.",
        "acclimatation": "Le plus calme : un matin en semaine. Le mercredi et le week-end, les files aux manèges s'allongent.",
        "menagerie": "Le plus calme : à l'ouverture. Combinable avec la Grande Galerie de l'Évolution, à côté.",
        "montmartre": "Le plus calme : avant 10 h. L'après-midi, la butte est très chargée ; attention aux vendeurs de bracelets.",
        "arts-metiers": "Rarement bondé : une bonne option quand tout le reste est plein. Fermé le lundi.",
    },
    "rome": {
        "colisee": "Créneau horaire obligatoire, à réserver tôt. Le plus calme : le premier créneau du matin ou la fin d'après-midi.",
        "forum": "Prévoyez le matin, avant la chaleur : peu d'ombre sur le site.",
        "trevi": "Le plus calme : avant 8 h ou tard le soir. En journée, la foule est très dense.",
        "pantheon": "Le plus calme : à l'ouverture. Réservation conseillée le week-end.",
        "vatican": "Réservez le premier créneau du matin. Le dernier dimanche du mois, l'entrée est gratuite mais l'attente est très longue.",
        "saint-pierre": "Le mercredi matin, l'audience du pape occupe la place et la basilique ouvre plus tard. Le plus calme : tôt le matin.",
        "saint-ange": "Le plus calme : en fin d'après-midi. Fermé le lundi, sauf le premier lundi du mois l'après-midi.",
        "borghese": "Réservation obligatoire, par créneaux de deux heures, souvent complets : réservez dès l'ouverture des ventes.",
        "bocca": "Les groupes se succèdent en journée : venez tôt le matin, la file est alors courte.",
        "espagne": "Interdit de s'asseoir sur les marches. Le plus calme : tôt le matin.",
        "bioparco": "Le plus calme : un matin en semaine. Très chargé le dimanche.",
        "explora": "Visites par séances à heure fixe : réservez la vôtre, surtout le week-end. Fermé le lundi.",
        "ostie": "Rarement bondé. Évitez le cœur de l'été en milieu de journée : le site a très peu d'ombre. Fermé le lundi.",
    },
    "londres": {
        "nhm": "Le plus calme : un après-midi en semaine. Le matin, les sorties scolaires sont nombreuses ; l'entrée d'Exhibition Road est souvent plus rapide.",
        "science": "Le plus calme : un après-midi en semaine. La galerie Wonderlab est payante : réservez un créneau.",
        "british": "Le plus calme : à l'ouverture ou le vendredi soir. Réservation gratuite conseillée.",
        "eye": "Le plus calme : le premier tour du matin. Billets moins chers en ligne.",
        "tower": "Allez d'abord voir les joyaux de la Couronne, dès l'ouverture : la file grossit vite.",
        "buckingham": "Pour la relève de la garde, arrivez 45 minutes avant. Elle n'a pas lieu tous les jours : vérifiez le calendrier.",
        "harrypotter": "Billets uniquement en ligne, à réserver longtemps à l'avance pendant les vacances scolaires.",
        "zoo": "Le plus calme : un matin en semaine. Les repas des animaux, affichés à l'entrée, sont les meilleurs moments.",
        "sealife": "Le plus calme : à l'ouverture ou après 16 h. Billets moins chers en ligne.",
        "transport": "Le plus calme : un après-midi en semaine. Le billet reste valable un an.",
        "youngva": "Très chargé le week-end et pendant les vacances : venez à l'ouverture.",
        "greenwich": "Le plus calme : un matin en semaine. La vue depuis la colline est gratuite.",
    },
    "barcelone": {
        "sagrada": "Créneau horaire obligatoire, à réserver en ligne. Le premier créneau du matin est le plus calme ; la lumière des vitraux est plus belle l'après-midi.",
        "batllo": "Le plus calme : à l'ouverture ou en soirée. Réservez en ligne.",
        "guell": "Créneau horaire obligatoire pour la zone monumentale, à réserver plusieurs jours à l'avance en été.",
        "aquarium": "Le plus calme : à l'ouverture en semaine. Très chargé le dimanche et les jours de pluie.",
        "boqueria": "Le plus calme : avant 10 h. Certains étals ferment aussi le lundi.",
        "teleferic": "La file s'allonge vers midi : montez le matin.",
        "tibidabo": "Le grand parc n'ouvre pas tous les jours : surtout les week-ends et pendant l'été. Vérifiez le calendrier avant de monter.",
        "cosmocaixa": "Le plus calme : un après-midi en semaine. Le matin, les groupes scolaires sont nombreux.",
        "zoo": "Le plus calme : un matin en semaine. Prévoyez de l'ombre et de l'eau en été.",
        "barceloneta": "En été, venez avant 11 h pour trouver de la place sur le sable.",
        "fontmagica": "Spectacle seulement certains soirs, selon la saison, et parfois suspendu en cas de sécheresse : vérifiez le calendrier.",
    },
    "lisbonne": {
        "oceanario": "Le plus calme : à l'ouverture ou en fin d'après-midi en semaine. Billets en ligne.",
        "torre": "Visite par créneaux et nombre de visiteurs limité : réservez. Fermé le lundi.",
        "jeronimos": "Le plus calme : à l'ouverture. Combinez avec la tour de Belém, mais pas le lundi : les deux sont fermés.",
        "pasteis": "La file au comptoir de vente à emporter est longue ; la salle à l'intérieur est souvent plus rapide.",
        "castelo": "Le plus calme : à l'ouverture ou en fin de journée, quand la lumière est belle.",
        "telecabine": "Rarement d'attente en semaine.",
        "pavilhao": "Le plus calme : un après-midi en semaine. Fermé le lundi.",
        "zoo": "Le plus calme : un matin en semaine.",
        "coches": "Rarement bondé. Fermé le lundi.",
        "marioneta": "Rarement bondé, idéal quand il pleut. Fermé le lundi.",
    },
    "amsterdam": {
        "annefrank": "Billets uniquement en ligne, mis en vente six semaines à l'avance et vite complets.",
        "rijks": "Le plus calme : à l'ouverture ou en fin d'après-midi. Billet à heure fixe, gratuit pour les moins de 18 ans.",
        "nemo": "Le plus calme : un jour de semaine après 14 h. Fermé le lundi, sauf quelques jours de vacances.",
        "artis": "Le plus calme : un matin en semaine.",
        "canaux": "Le plus calme : le premier départ du matin. Les petits bateaux ouverts sont plus amusants pour les enfants.",
        "adam": "Le plus calme : en semaine en journée. Au coucher du soleil, la terrasse est pleine.",
        "micropia": "Rarement bondé ; une bonne option près d'Artis.",
        "scheepvaart": "Rarement bondé en semaine. Montez à bord du navire en premier.",
        "bloemenmarkt": "Le plus calme : le matin.",
    },
    "prague": {
        "horloge": "À chaque heure pile, la foule se masse devant l'horloge : arrivez cinq minutes avant. Le plus calme : 9 h.",
        "karluvmost": "Le plus calme : avant 8 h. Entre 11 h et 18 h, le pont est bondé.",
        "hrad": "Le plus calme : à l'ouverture. Relève de la garde avec fanfare à midi.",
        "zoo": "Le plus calme : un matin en semaine. Très chargé le week-end quand il fait beau.",
        "ntm": "Le plus calme : un matin en semaine. Fermé le lundi.",
        "planetarium": "Séances sous le dôme à heure fixe : réservez. Fermé le lundi.",
        "kralovstvi": "Moins cher en semaine et en ligne. Le plus calme : un matin en semaine.",
        "lego": "Le plus calme : le matin. Bonne option par temps de pluie.",
        "petrin": "File d'attente au funiculaire le week-end : montez tôt.",
        "karlstejn": "Visite guidée à heure fixe : réservez en ligne, surtout en été.",
    },
    "vienne": {
        "zoo": "Le plus calme : un matin en semaine. Les repas des animaux sont affichés à l'entrée.",
        "schonbrunn": "Le parc ouvre tôt : venez le matin avant les groupes. Le labyrinthe ouvre d'avril à début novembre.",
        "prater": "Le plus calme : un matin en semaine. La grande roue tourne toute l'année.",
        "nhm": "Le plus calme : en semaine l'après-midi. Fermé le mardi.",
        "zoom": "Visites par créneaux, souvent complets le week-end : réservez. Fermé le lundi.",
        "hausdesmeeres": "Très chargé les jours de pluie et le week-end : venez à l'ouverture.",
        "tmw": "Le plus calme : un après-midi en semaine.",
        "hausdermusik": "Le plus calme : en matinée.",
        "stephansdom": "Le plus calme : tôt le matin, avant les groupes.",
        "wienmuseum": "Rarement bondé. Fermé le lundi.",
        "kindermuseum": "Visites guidées pour enfants le week-end et pendant les vacances : réservez.",
    },
}


def main():
    for f in sorted((ROOT / "data" / "villes").glob("*.json")):
        v = json.loads(f.read_text(encoding="utf-8"))
        fe, af = FERME.get(v["id"], {}), AFFLUENCE.get(v["id"], {})
        for a in v["activites"]:
            for k in ("ferme", "ferme_note", "affluence"):
                a.pop(k, None)
            if a["id"] in fe:
                x = fe[a["id"]]
                jours, note = (x, None) if isinstance(x, list) else x
                a["ferme"] = jours
                if note:
                    a["ferme_note"] = note
            if a["id"] in af:
                # le jour de fermeture est affiché à part : on ne le répète pas dans le conseil
                a["affluence"] = re.sub(r"\s*Fermé le [^.]*\.", "", af[a["id"]]).strip()
        inconnus = (set(fe) | set(af)) - {a["id"] for a in v["activites"]}
        assert not inconnus, (v["id"], inconnus)
        f.write_text(json.dumps(v, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(v["id"], sum(1 for a in v["activites"] if "affluence" in a), "conseils,", sum(1 for a in v["activites"] if "ferme" in a), "fermetures")


if __name__ == "__main__":
    main()
