# PetitMondo

Carnets de voyage en famille, gratuits et prêts à partir : programme jour par jour adapté à l'âge des enfants, services utiles autour de chaque visite (toilettes, aires de jeux, tables à langer, restaurants équipés), PDF imprimable et carte KML pour Google My Maps.

Site statique hébergé sur GitHub Pages, sans serveur ni base de données.

## Structure

- `index.html` : accueil
- `carnet/` : générateur de carnet (tout se calcule dans le navigateur, les paramètres sont dans le lien)
- `barcelone/` : guide de la ville et ses pages thématiques (bébé, pluie, gratuit, ados, poussette, aires de jeux, toilettes, restaurants, jeux à imprimer, lexique)
- `valise/`, `methode/`, `charte/` : outils et pages générales
- `assets/` : styles, scripts, mascotte Mondo (`mondo.svg`), icônes (`sprite.svg`), illustrations des villes
- `data/villes/<ville>.json` : activités sélectionnées à la main (source de vérité)
- `data/osm/<ville>.json` : services OpenStreetMap, régénérés chaque lundi par GitHub Actions
- `scripts/fetch_osm.py` : extraction OpenStreetMap (API Overpass)

## Ajouter ou modifier une ville

1. Créer ou modifier `data/villes/<ville>.json` (même format que `barcelone.json`).
2. Lancer `python scripts/build.py` : toutes les pages et le sitemap sont régénérés.
   Ajouter l'illustration `assets/villes/<ville>.svg` dans le style de `barcelone.svg`.
3. Pousser : l'action « Mise à jour des données OpenStreetMap » récupère les services et régénère les pages.

Toutes les pages HTML sont générées : on modifie `scripts/build.py`, jamais les fichiers `index.html` à la main.

## Direction artistique

Style « autocollant » : contours bleu nuit `#1B2A4A`, ombres décalées pleines, couleurs soleil, corail, menthe, ciel et lilas, titres en Bricolage Grotesque, texte en Figtree, mascotte Mondo. Détails sur la page `/charte/`.

Données cartographiques © contributeurs OpenStreetMap, licence ODbL.
