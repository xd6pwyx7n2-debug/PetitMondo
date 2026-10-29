# PetitMondo

Carnets de voyage en famille, gratuits et prêts à partir : programme jour par jour adapté à l'âge des enfants, services utiles autour de chaque visite (toilettes, aires de jeux, tables à langer, restaurants équipés), PDF imprimable et carte KML pour Google My Maps.

Site statique hébergé sur GitHub Pages, sans serveur ni base de données.

## Structure

- `index.html` : accueil
- `carnet/` : générateur de carnet (tout se calcule dans le navigateur, les paramètres sont dans le lien)
- `barcelone/` : page guide de la ville, générée par `scripts/build_villes.py`
- `data/villes/<ville>.json` : activités sélectionnées à la main (source de vérité)
- `data/osm/<ville>.json` : services OpenStreetMap, régénérés chaque lundi par GitHub Actions
- `scripts/fetch_osm.py` : extraction OpenStreetMap (API Overpass)

## Ajouter ou modifier une ville

1. Créer ou modifier `data/villes/<ville>.json` (même format que `barcelone.json`).
2. Lancer `python scripts/build_villes.py` pour régénérer la page guide et le sitemap.
3. Pousser : l'action « Mise à jour des données OpenStreetMap » se lance automatiquement.

Données cartographiques © contributeurs OpenStreetMap, licence ODbL.
