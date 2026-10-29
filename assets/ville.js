/* PetitMondo — page guide d'une ville : filtres et carte pratique */
(async () => {
  /* Filtres des activités */
  const cartes = [...document.querySelectorAll('#liste .act')];
  const chips = [...document.querySelectorAll('.filtres [data-f]')];
  const age = document.getElementById('f-age');
  function filtrer() {
    const actifs = chips.filter(c => c.getAttribute('aria-pressed') === 'true').map(c => c.dataset.f);
    const a = age.value === '' ? null : +age.value;
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
    document.getElementById('f-vide').hidden = n > 0;
  }
  chips.forEach(c => c.addEventListener('click', () => { c.setAttribute('aria-pressed', c.getAttribute('aria-pressed') === 'true' ? 'false' : 'true'); filtrer(); }));
  age.addEventListener('change', filtrer);

  /* Carte pratique */
  if (!window.L) return;
  const v = await PM.ville(window.PM_VILLE);
  const carte = PM.fondCarte(L, 'map', v.centre, 13);
  const calques = {};
  const actGroupe = L.layerGroup().addTo(carte);
  v.activites.forEach(a => PM.marqueur(L, a.lat, a.lon, 'activite', 16)
    .bindPopup(`<strong>${PM.esc(a.nom)}</strong><br>${a.ages[0]}–${a.ages[1]} ans<br><a href="${PM.lienItineraire(a)}" target="_blank" rel="noopener">Itinéraire</a>`)
    .addTo(actGroupe));
  calques.activite = actGroupe;

  const zone = document.getElementById('calques');
  const info = document.getElementById('osm-info');
  const bouton = (cle, nom, actif, n) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'chip';
    b.setAttribute('aria-pressed', actif ? 'true' : 'false');
    b.innerHTML = `<i class="pt" style="background:${PM.CATS[cle].couleur};margin-right:6px;vertical-align:-1px"></i>${nom}${n != null ? ` (${n})` : ''}`;
    b.onclick = () => {
      const on = b.getAttribute('aria-pressed') !== 'true';
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      on ? calques[cle].addTo(carte) : carte.removeLayer(calques[cle]);
    };
    zone.appendChild(b);
  };
  bouton('activite', 'Activités', true, v.activites.length);

  try {
    const osm = await PM.osm(v);
    const actifsParDefaut = ['toilettes', 'aire_jeux', 'table_langer'];
    for (const cle of ['toilettes', 'aire_jeux', 'table_langer', 'resto_enfants', 'pharmacie']) {
      const pts = osm.points.filter(p => p.c === cle);
      if (!pts.length) continue;
      const g = L.layerGroup();
      pts.forEach(p => PM.marqueur(L, p.lat, p.lon, cle, 10)
        .bindPopup(`<strong>${PM.esc(PM.nomPoint(p))}</strong>${PM.detailPoint(p) ? `<br>${PM.esc(PM.detailPoint(p))}` : ''}<br><a href="${PM.lienItineraire({ lat: p.lat, lon: p.lon })}" target="_blank" rel="noopener">Itinéraire</a> · <a href="${PM.lienOSM(p)}" target="_blank" rel="noopener">Corriger</a>`)
        .addTo(g));
      calques[cle] = g;
      const on = actifsParDefaut.includes(cle);
      if (on) g.addTo(carte);
      bouton(cle, PM.CATS[cle].nom, on, pts.length);
    }
    info.textContent = `Services : données © contributeurs OpenStreetMap${osm.maj ? `, mises à jour le ${new Date(osm.maj).toLocaleDateString('fr-FR')}` : ''}. Non vérifiées sur place. Une erreur ? Le lien « Corriger » permet de la signaler directement dans OpenStreetMap.`;
  } catch {
    info.textContent = 'Les services OpenStreetMap n\'ont pas pu être chargés. Réessayez dans un instant.';
  }
})();
