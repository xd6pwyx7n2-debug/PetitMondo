/* PetitMondo — pages ville : filtres des activités et carte pratique */
(async () => {
  const liste = document.getElementById('liste');
  if (liste) {
    const cartes = [...liste.querySelectorAll('.act')];
    const chips = [...document.querySelectorAll('.filtres [data-f]')];
    const age = document.getElementById('f-age');
    const filtrer = () => {
      const actifs = chips.filter(c => c.getAttribute('aria-pressed') === 'true').map(c => c.dataset.f);
      const a = !age || age.value === '' ? null : +age.value;
      let n = 0;
      for (const c of cartes) {
        let ok = a === null || (a >= +c.dataset.min && a <= +c.dataset.max);
        for (const f of actifs) {
          if (f === 'couvert' && c.dataset.couvert !== '1') ok = false;
          if (f === 'gratuit' && c.dataset.gratuit !== '1') ok = false;
          if (f.startsWith('int:') && !c.dataset.int.split(' ').includes(f.slice(4))) ok = false;
        }
        c.hidden = !ok;
        if (ok) n++;
      }
      const vide = document.getElementById('f-vide');
      if (vide) vide.hidden = n > 0;
    };
    chips.forEach(c => c.addEventListener('click', () => { c.setAttribute('aria-pressed', c.getAttribute('aria-pressed') === 'true' ? 'false' : 'true'); filtrer(); }));
    age?.addEventListener('change', filtrer);
  }

  const el = document.getElementById('map');
  if (!el || !window.L) return;
  const actifs = window.PM_CALQUES || ['activite', 'toilettes', 'aire_jeux', 'table_langer'];
  const v = await PM.ville(window.PM_VILLE);
  const carte = PM.fondCarte(L, el, v.centre, 13);
  const calques = {};
  const zone = document.getElementById('calques');
  const info = document.getElementById('osm-info');

  const bouton = (cle, n) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'chip';
    const on = actifs.includes(cle);
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.innerHTML = `<i class="pt" style="background:${PM.CATS[cle].couleur}"></i>${PM.CATS[cle].nom} <span style="opacity:.7">${n}</span>`;
    b.onclick = () => {
      const actif = b.getAttribute('aria-pressed') !== 'true';
      b.setAttribute('aria-pressed', actif ? 'true' : 'false');
      actif ? calques[cle].addTo(carte) : carte.removeLayer(calques[cle]);
    };
    zone?.appendChild(b);
    if (on) calques[cle].addTo(carte);
  };

  const gAct = L.layerGroup();
  v.activites.forEach(a => PM.marqueur(L, a.lat, a.lon, 'activite', 18)
    .bindPopup(`<strong>${PM.esc(a.nom)}</strong><br>${a.ages[0]}–${a.ages[1]} ans · ${a.interieur ? 'couvert' : 'plein air'}<br><a href="${PM.lienItineraire(a)}" target="_blank" rel="noopener">Itinéraire</a>`)
    .addTo(gAct));
  calques.activite = gAct;
  bouton('activite', v.activites.length);

  try {
    const osm = await PM.osm(v);
    for (const cle of ['toilettes', 'aire_jeux', 'table_langer', 'resto_enfants', 'pharmacie']) {
      const pts = osm.points.filter(p => p.c === cle);
      if (!pts.length) continue;
      const g = L.layerGroup();
      pts.forEach(p => PM.marqueur(L, p.lat, p.lon, cle, 11)
        .bindPopup(`<strong>${PM.esc(PM.nomPoint(p))}</strong>${PM.detailPoint(p) ? `<br>${PM.esc(PM.detailPoint(p))}` : ''}<br><a href="${PM.lienItineraire({ lat: p.lat, lon: p.lon })}" target="_blank" rel="noopener">Itinéraire</a> · <a href="${PM.lienOSM(p)}" target="_blank" rel="noopener">Corriger</a>`)
        .addTo(g));
      calques[cle] = g;
      bouton(cle, pts.length);
    }
    if (info) info.textContent = `Services : données © contributeurs OpenStreetMap${osm.maj ? `, mises à jour le ${new Date(osm.maj).toLocaleDateString('fr-FR')}` : ''}, non vérifiées sur place. Une erreur ? Le lien « Corriger » ouvre la fiche dans OpenStreetMap.`;
  } catch {
    if (info) info.textContent = 'Les services OpenStreetMap n\'ont pas pu être chargés. Réessayez dans un instant.';
  }

  /* Bouton « autour de moi » */
  if (navigator.geolocation && zone) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'chip'; b.style.background = 'var(--soleil)';
    b.textContent = 'Autour de moi';
    b.onclick = () => navigator.geolocation.getCurrentPosition(p => {
      const ll = [p.coords.latitude, p.coords.longitude];
      L.circleMarker(ll, { radius: 9, color: '#1B2A4A', weight: 3, fillColor: '#FFC93C', fillOpacity: 1 }).addTo(carte).bindPopup('Vous êtes ici').openPopup();
      carte.setView(ll, 16);
    }, () => { b.textContent = 'Position indisponible'; }, { enableHighAccuracy: true, timeout: 10000 });
    zone.appendChild(b);
  }
})();
