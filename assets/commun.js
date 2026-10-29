/* PetitMondo — fonctions partagées */
const PM = (() => {
  const base = document.querySelector('meta[name="pm-base"]')?.content || '/';

  const CATS = {
    activite:      { nom: 'Activités',          couleur: '#FF6B4A', ico: 'activite' },
    aire_jeux:     { nom: 'Aires de jeux',      couleur: '#2FB59A', ico: 'jeux' },
    toilettes:     { nom: 'Toilettes',          couleur: '#6EC6F0', ico: 'toilettes' },
    table_langer:  { nom: 'Tables à langer',    couleur: '#A88BEB', ico: 'langer' },
    pharmacie:     { nom: 'Pharmacies',         couleur: '#7BD389', ico: 'pharmacie' },
    resto_enfants: { nom: 'Restos équipés',     couleur: '#FFC93C', ico: 'resto' },
    eau:           { nom: 'Eau potable',        couleur: '#3FA7E0', ico: 'eau' },
    station:       { nom: 'Stations',           couleur: '#1B2A4A', ico: 'station' },
    ascenseur:     { nom: 'Ascenseurs',         couleur: '#FF9F8A', ico: 'ascenseur' },
  };

  const INTERETS = {
    animaux: 'Animaux', sciences: 'Sciences', aventure: 'Aventure', culture: 'Culture',
    parc: 'Parcs', plage: 'Plage', gourmand: 'Gourmand',
  };

  const store = {
    get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* stockage indisponible */ } },
  };

  async function ville(id) {
    const r = await fetch(`${base}data/villes/${id}.json`);
    if (!r.ok) throw new Error('Ville introuvable');
    return r.json();
  }

  /* Services OSM : fichier hebdomadaire généré par GitHub Actions, sinon requête directe à Overpass */
  async function acces(v) {
    try { const r = await fetch(`${base}data/acces/${v.id}.json`); if (r.ok) return r.json(); } catch { /* sans fiche poussette */ }
    return null;
  }

  async function osm(v) {
    try {
      const r = await fetch(`${base}data/osm/${v.id}.json`, { cache: 'no-cache' });
      if (r.ok) return r.json();
    } catch { /* on tente en direct */ }
    const cle = `pm-osm-${v.id}`;
    const cache = store.get(cle);
    if (cache && Date.now() - cache.t < 7 * 864e5) return cache.d;
    const [s, w, n, e] = v.bbox;
    const b = `(${s},${w},${n},${e})`;
    const q = `[out:json][timeout:60];(nwr["amenity"="toilets"]${b};nwr["leisure"="playground"]${b};nwr["changing_table"="yes"]${b};nwr["amenity"="pharmacy"]${b};nwr["amenity"~"^(restaurant|cafe|fast_food)$"]["highchair"="yes"]${b};nwr["amenity"~"^(restaurant|cafe|fast_food)$"]["kids_area"="yes"]${b};nwr["amenity"="drinking_water"]${b};);out center tags;`;
    const r = await fetch('https://overpass-api.de/api/interpreter', { method: 'POST', body: new URLSearchParams({ data: q }) });
    if (!r.ok) throw new Error('OpenStreetMap indisponible');
    const j = await r.json();
    const points = [];
    for (const el of j.elements || []) {
      const t = el.tags || {};
      const lat = el.lat ?? el.center?.lat, lon = el.lon ?? el.center?.lon;
      if (lat == null) continue;
      let c = null;
      const resto = ['restaurant', 'cafe', 'fast_food'].includes(t.amenity);
      if ((t.changing_table === 'yes' || t.diaper === 'yes') && !resto) c = 'table_langer';
      else if (t.amenity === 'toilets') c = 'toilettes';
      else if (t.leisure === 'playground') c = 'aire_jeux';
      else if (t.amenity === 'pharmacy') c = 'pharmacie';
      else if (resto) c = 'resto_enfants';
      else if (t.amenity === 'drinking_water') c = 'eau';
      if (c) points.push({ c, lat, lon, osm: `${el.type}/${el.id}`, t });
    }
    const d = { ville: v.id, maj: new Date().toISOString().slice(0, 10), source: '© contributeurs OpenStreetMap (ODbL)', points };
    store.set(cle, { t: Date.now(), d });
    return d;
  }

  /* Direction écrite en toutes lettres, lisible sur papier : « vers le nord-est » */
  function direction(a, b) {
    const r = Math.PI / 180;
    const y = Math.sin((b.lon - a.lon) * r) * Math.cos(b.lat * r);
    const x = Math.cos(a.lat * r) * Math.sin(b.lat * r) - Math.sin(a.lat * r) * Math.cos(b.lat * r) * Math.cos((b.lon - a.lon) * r);
    const deg = (Math.atan2(y, x) / r + 360) % 360;
    return ['vers le nord', 'vers le nord-est', 'vers l\'est', 'vers le sud-est', 'vers le sud', 'vers le sud-ouest', 'vers l\'ouest', 'vers le nord-ouest'][Math.round(deg / 45) % 8];
  }

  const domaine = u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return u; } };

  /* Fiche poussette d'un lieu : note du guide + terrain OpenStreetMap + station la plus proche */
  const FAUTEUIL = { yes: 'accès sans marche signalé', limited: 'accès partiel signalé', no: 'pas d\'accès sans marche', inconnu: 'accessibilité non renseignée' };
  function fichePoussette(a, acces) {
    const note = { facile: 'Facile en poussette', moyen: 'Poussette possible, à anticiper', difficile: 'Porte-bébé conseillé' }[a.poussette];
    const l = [];
    const f = acces?.lieux?.[a.id];
    if (f) {
      l.push(f.paves >= 8 ? 'beaucoup de rues pavées autour' : f.paves >= 3 ? 'quelques rues pavées autour' : 'peu ou pas de pavés signalés autour');
      if (f.marches >= 5) l.push('nombreux escaliers dans le quartier');
      else if (f.marches >= 1) l.push(`${f.marches} escalier${f.marches > 1 ? 's' : ''} signalé${f.marches > 1 ? 's' : ''} à proximité`);
      if (f.station) l.push(`station la plus proche : ${f.station.nom}, à ${fmtDist(f.station.d)}, ${FAUTEUIL[f.station.fauteuil] || FAUTEUIL.inconnu}`);
      if (f.ascenseurs) l.push(`${f.ascenseurs} ascenseur${f.ascenseurs > 1 ? 's' : ''} public${f.ascenseurs > 1 ? 's' : ''} signalé${f.ascenseurs > 1 ? 's' : ''} à moins de 400 m`);
    }
    return { note, details: l, classe: a.poussette };
  }

  /* Liste « Autour de moi » : le service le plus proche de chaque type, distance et direction en clair */
  function autour(osmData, pos) {
    const types = [['toilettes', 'Toilettes'], ['eau', 'Eau potable'], ['aire_jeux', 'Aire de jeux'], ['table_langer', 'Table à langer'], ['pharmacie', 'Pharmacie'], ['station', 'Station'], ['resto_enfants', 'Restaurant équipé']];
    const li = [];
    for (const [c, nom] of types) {
      const pr = proches(osmData.points, pos, c, 1, 1500)[0];
      if (!pr) continue;
      const det = detailPoint(pr);
      li.push(`<li>${ico(CATS[c].ico)}<span><strong>${nom}</strong> à ${fmtDist(pr.d)} ${direction(pos, pr)}, environ ${minutesMarche(pr.d)} min à pied${pr.t?.name ? ` : ${esc(pr.t.name)}` : ''}${det ? ` <span class="muted">(${esc(det)})</span>` : ''}<br><a href="${lienItineraire({ lat: pr.lat, lon: pr.lon })}" target="_blank" rel="noopener">Itinéraire</a></span></li>`);
    }
    return li.length ? `<ul class="autour-liste">${li.join('')}</ul><p class="muted" style="font-size:.85rem">Données OpenStreetMap, non vérifiées sur place. La liste fonctionne sans réseau une fois la page ouverte ; l'itinéraire demande une connexion.</p>` : '<p class="muted">Aucun service signalé à moins de 1,5 km.</p>';
  }

  function distance(a, b) {
    const R = 6371e3, r = Math.PI / 180;
    const dLat = (b.lat - a.lat) * r, dLon = (b.lon - a.lon) * r;
    const x = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  /* Marche avec enfants : ~3 km/h, majoré de 30 % pour les détours réels */
  const minutesMarche = m => Math.max(1, Math.round((m * 1.3) / 50));
  const fmtDist = m => m < 1000 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toFixed(1).replace('.', ',')} km`;

  function proches(points, lieu, cat, n = 2, max = 900) {
    return points.filter(p => p.c === cat)
      .map(p => ({ ...p, d: distance(lieu, p) }))
      .filter(p => p.d <= max)
      .sort((a, b) => a.d - b.d)
      .slice(0, n);
  }

  const lienMaps = l => `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(l.adresse ? `${l.nom}, ${l.adresse}` : `${l.lat},${l.lon}`)}`;
  const lienItineraire = l => `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(l.adresse ? `${l.nom}, ${l.adresse}` : `${l.lat},${l.lon}`)}&travelmode=walking`;
  const lienOSM = p => `https://www.openstreetmap.org/${p.osm}`;

  function nomPoint(p) {
    if (p.t?.name) return p.t.name;
    return { toilettes: 'Toilettes publiques', aire_jeux: 'Aire de jeux', table_langer: 'Toilettes avec table à langer', pharmacie: 'Pharmacie', resto_enfants: 'Restaurant', eau: 'Fontaine d\'eau potable', station: 'Station', ascenseur: 'Ascenseur public' }[p.c] || 'Lieu';
  }

  function detailPoint(p) {
    const t = p.t || {}, d = [];
    if (t.fee === 'no') d.push('gratuit'); else if (t.fee === 'yes') d.push('payant');
    if (t.changing_table === 'yes') d.push('table à langer signalée');
    if (t.wheelchair === 'yes' && p.c !== 'station') d.push('accès fauteuil');
    if (t.highchair === 'yes') d.push('chaise haute');
    if (t.kids_area === 'yes') d.push('coin enfants');
    if (p.c === 'station' && t.wheelchair) d.push(FAUTEUIL[t.wheelchair] || '');
    if (t.opening_hours) d.push(t.opening_hours);
    return d.join(' · ');
  }

  const ico = (n, cls = 'i') => `<svg class="${cls}" aria-hidden="true"><use href="${base}assets/sprite.svg#i-${n}"/></svg>`;
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  /* Export carte — KML importable dans Google My Maps (un calque par dossier) */
  function kml(titre, dossiers) {
    const xml = s => esc(s);
    const styles = Object.entries(CATS).map(([k, c]) => {
      const hex = c.couleur.slice(1);
      const abgr = 'ff' + hex.slice(4, 6) + hex.slice(2, 4) + hex.slice(0, 2);
      return `<Style id="${k}"><IconStyle><color>${abgr}</color><Icon><href>https://maps.google.com/mapfiles/kml/paddle/wht-blank.png</href></Icon></IconStyle></Style>`;
    }).join('');
    const corps = dossiers.map(f => `<Folder><name>${xml(f.nom)}</name>${f.lieux.map(l => `<Placemark><name>${xml(l.nom)}</name><description>${xml(l.desc || '')}</description><styleUrl>#${l.c || 'activite'}</styleUrl><Point><coordinates>${l.lon},${l.lat},0</coordinates></Point></Placemark>`).join('')}</Folder>`).join('');
    return `<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>${xml(titre)}</name>${styles}${corps}</Document></kml>`;
  }

  function csv(lignes) {
    const c = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const tete = ['Nom', 'Catégorie', 'Jour', 'Adresse', 'Latitude', 'Longitude', 'Description'];
    return '﻿' + [tete.map(c).join(','), ...lignes.map(l => [l.nom, l.cat, l.jour, l.adresse, l.lat, l.lon, l.desc].map(c).join(','))].join('\r\n');
  }

  function telecharger(nom, contenu, type) {
    const blob = new Blob([contenu], { type });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = nom;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  }

  function marqueur(L, lat, lon, cat, taille = 14) {
    const couleur = CATS[cat]?.couleur || '#FF6B4A';
    return L.circleMarker([lat, lon], { radius: taille / 2, color: '#1B2A4A', weight: 2, fillColor: couleur, fillOpacity: 1 });
  }

  function fondCarte(L, el, centre, zoom = 13) {
    const m = L.map(el, { scrollWheelZoom: false, tap: true }).setView(centre, zoom);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 19, subdomains: 'abcd',
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · © <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(m);
    return m;
  }

  return { base, acces, autour, ico, direction, domaine, fichePoussette, FAUTEUIL, CATS, INTERETS, store, ville, osm, distance, minutesMarche, fmtDist, proches, lienMaps, lienItineraire, lienOSM, nomPoint, detailPoint, esc, kml, csv, telecharger, marqueur, fondCarte };
})();
