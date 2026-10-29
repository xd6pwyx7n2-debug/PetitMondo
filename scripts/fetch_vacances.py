#!/usr/bin/env python3
"""Télécharge le calendrier officiel des vacances scolaires (zones A, B, C) et l'enregistre en JSON.

Source : Éducation nationale, fichiers iCal publiés via data.gouv.fr.
Sortie : data/vacances.json  [{"nom": "Vacances de Printemps", "zone": "A", "debut": "2027-04-10", "fin": "2027-04-26"}, …]
"""
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://fr.ftp.opendatasoft.com/openscol/fr-en-calendrier-scolaire/Zone-{}.ics"
UA = "PetitMondo/1.0 (github.com/xd6pwyx7n2-debug/PetitMondo)"


def lire(zone):
    req = urllib.request.Request(BASE.format(zone), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        brut = r.read().decode("utf-8", "replace")
    brut = re.sub(r"\r?\n[ \t]", "", brut)  # lignes repliées du format iCal
    out = []
    for ev in brut.split("BEGIN:VEVENT")[1:]:
        champ = lambda k: (re.search(rf"^{k}[^:\n]*:(.*)$", ev, re.M) or [None, ""])[1].strip()
        d1, d2, nom = champ("DTSTART"), champ("DTEND"), champ("SUMMARY") or champ("DESCRIPTION")
        m1, m2 = re.match(r"(\d{4})(\d{2})(\d{2})", d1), re.match(r"(\d{4})(\d{2})(\d{2})", d2)
        if not m1 or not nom:
            continue
        debut = "-".join(m1.groups())
        fin = "-".join(m2.groups()) if m2 else debut
        if "vacances" not in nom.lower() and "pont" not in nom.lower():
            continue
        out.append({"nom": nom.replace("\\,", ",").strip(), "zone": zone, "debut": debut, "fin": fin})
    return out


def main():
    tout = []
    for z in "ABC":
        try:
            tout += lire(z)
        except Exception as exc:  # noqa: BLE001
            print(f"zone {z} : échec ({exc})", file=sys.stderr)
    if not tout:
        sys.exit(0)  # on garde l'ancien fichier
    tout.sort(key=lambda x: (x["debut"], x["zone"]))
    (ROOT / "data" / "vacances.json").write_text(json.dumps(tout, ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(tout), "périodes")


if __name__ == "__main__":
    main()
