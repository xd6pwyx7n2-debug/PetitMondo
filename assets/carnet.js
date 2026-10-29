/* PetitMondo — générateur de carnet familial */
(() => {
  const $ = s => document.querySelector(s);
  const form = $('#form-carnet');
  const zoneEnfants = $('#enfants');
  const sortie = $('#carnet');
  const COULEURS_JOURS = ['#FF6B4A', '#2FB59A', '#6EC6F0', '#A88BEB', '#FFC93C'];
  const FONDS_JOURS = ['#FFE1D9', '#D5F2EA', '#DDF1FB', '#EEE7FC', '#FFF1C9'];
  let carte = null, dernier = null;

  /* ---------- Enfants ---------- */
  function ajouterEnfant(age = 5) {
    const n = zoneEnfants.querySelectorAll('.enfant').length;
    if (n >= 6) return;
    const d = document.createElement('div');
    d.className = 'enfant';
    d.innerHTML = `<label class="sr" for="age${n}">Âge de l'enfant ${n + 1}</label><input id="age${n}" type="number" min="0" max="17" value="${age}" inputmode="numeric"><span>ans</span><button type="button" aria-label="Retirer cet enfant">×</button>`;
    d.querySelector('button').onclick = () => { if (zoneEnfants.querySelectorAll('.enfant').length > 1) d.remove(); };
    zoneEnfants.insertBefore(d, $('#ajout-enfant'));
  }
  $('#ajout-enfant').onclick = () => ajouterEnfant(5);

  /* ---------- Paramètres <-> URL (carnet partageable) ---------- */
  function lireForm() {
    const fd = new FormData(form);
    return {
      ville: fd.get('ville'),
      jours: Math.min(5, Math.max(1, +fd.get('jours') || 3)),
      ages: [...zoneEnfants.querySelectorAll('input')].map(i => Math.min(17, Math.max(0, parseInt(i.value, 10) || 0))),
      rythme: fd.get('rythme') || 'equilibre',
      poussette: fd.get('poussette') === 'oui',
      budget: fd.get('budget') || 'tous',
      depart: fd.get('depart') || '',
      interets: fd.getAll('interets'),
    };
  }
  function versURL(p) {
    const q = new URLSearchParams({ v: p.ville, j: p.jours, a: p.ages.join('-'), r: p.rythme, p: p.poussette ? 1 : 0, b: p.budget, i: p.interets.join('-') });
    if (p.depart) q.set('d', p.depart);
    history.replaceState(null, '', '#' + q.toString());
  }
  function depuisURL() {
    const h = new URLSearchParams(location.hash.slice(1) || location.search.slice(1));
    if (!h.get('v')) return false;
    form.ville.value = h.get('v');
    form.jours.value = h.get('j') || 3;
    zoneEnfants.querySelectorAll('.enfant').forEach(e => e.remove());
    (h.get('a') || '5').split('-').filter(Boolean).forEach(a => ajouterEnfant(+a));
    const coche = (nom, val) => { const el = form.querySelector(`input[name="${nom}"][value="${val}"]`); if (el) el.checked = true; };
    coche('rythme', h.get('r') || 'equilibre');
    coche('poussette', h.get('p') === '1' ? 'oui' : 'non');
    coche('budget', h.get('b') || 'tous');
    if (h.get('d')) form.depart.value = h.get('d');
    const ints = (h.get('i') || '').split('-');
    form.querySelectorAll('input[name="interets"]').forEach(c => { c.checked = ints.includes(c.value); });
    return true;
  }

  /* ---------- Sélection et planification ---------- */
  function score(a, p) {
    let s = 1;
    for (const age of p.ages) {
      if (age >= a.ages[0] && age <= a.ages[1]) s += 2;
      else if (age < a.ages[0] - 2 || age > a.ages[1] + 2) s -= 3;
      else s -= 1;
    }
    if (a.ages[0] >= 10 && Math.min(...p.ages) < a.ages[0]) return -99; // lieux réellement inadaptés aux petits
    for (const i of a.interets) if (p.interets.includes(i)) s += 3;
    if (p.poussette && a.poussette === 'difficile') s -= 2;
    if (p.budget === 'serre') s += a.gratuit === true ? 3 : a.gratuit === 'partiel' ? 1 : -1;
    return s;
  }

  function planifier(v, p) {
    const elig = v.activites.map(a => ({ ...a, s: score(a, p) })).filter(a => a.s > -2 && !a.soir);
    const soirs = v.activites.filter(a => a.soir).map(a => ({ ...a, s: score(a, p) }));
    const parJour = { calme: 2, equilibre: 3, intense: 4 }[p.rythme];
    const petit = Math.min(...p.ages);
    const utilises = new Set();
    const zonesOrd = Object.keys(v.zones)
      .map(z => ({ z, s: elig.filter(a => a.zone === z).sort((a, b) => b.s - a.s).slice(0, parJour).reduce((t, a) => t + Math.max(0, a.s), 0) }))
      .filter(x => x.s > 0).sort((a, b) => b.s - a.s).map(x => x.z);
    const jours = [];

    for (let d = 0; d < p.jours; d++) {
      const zone = zonesOrd[d % zonesOrd.length];
      const zc = v.zones[zone].centre;
      const cz = { lat: zc[0], lon: zc[1] };
      let choix = elig.filter(a => a.zone === zone && !utilises.has(a.id)).sort((a, b) => b.s - a.s).slice(0, parJour);
      if (choix.length < parJour) {
        const compl = elig.filter(a => !utilises.has(a.id) && !choix.includes(a))
          .map(a => ({ a, k: a.s * 400 - PM.distance(cz, a) }))
          .sort((x, y) => y.k - x.k).slice(0, parJour - choix.length).map(x => x.a);
        choix = choix.concat(compl);
      }
      if (!choix.length) break;
      choix.forEach(a => utilises.add(a.id));

      // Ordre : la plus longue activité le matin, puis plus proche voisin
      choix.sort((a, b) => b.duree - a.duree);
      const ordre = [choix.shift()];
      while (choix.length) {
        const der = ordre[ordre.length - 1];
        choix.sort((a, b) => PM.distance(der, a) - PM.distance(der, b));
        ordre.push(choix.shift());
      }

      // Chronologie
      let t = p.rythme === 'calme' ? 600 : 570; // minutes depuis minuit
      const fin = p.rythme === 'intense' ? 1140 : 1095;
      const etapes = [];
      let dejeuner = false;
      const pause = () => {
        t = Math.max(720, Math.ceil(t / 15) * 15);
        etapes.push({ type: 'repas', h: t, titre: 'Déjeuner', texte: 'Pique-nique ou restaurant à l\'ouverture (13 h) pour éviter l\'attente. Voir les restaurants équipés signalés à proximité.' });
        t += 60;
        if (petit < 4) {
          etapes.push({ type: 'pause', h: t, titre: 'Sieste ou temps calme', texte: 'Retour à l\'hébergement, ou sieste en poussette à l\'ombre d\'un parc.' });
          t += 75;
        }
        dejeuner = true;
      };
      const arrondi = m => Math.ceil(m / 15) * 15;
      let place = null;
      ordre.forEach((a, i) => {
        if (place === false) { a.reporte = true; return; }
        let trajet = null, duTrajet = 0;
        if (i > 0) {
          const prec = etapes.filter(e => e.type === 'activite').pop()?.a || ordre[i - 1];
          const m = PM.distance(prec, a);
          const min = PM.minutesMarche(m);
          duTrajet = min > 25 ? 30 : min;
          trajet = { type: 'trajet', texte: min > 25 ? `Trajet en métro ou bus (${PM.fmtDist(m)} à vol d'oiseau)` : `${min} min à pied environ (${PM.fmtDist(m)})` };
        }
        if (!dejeuner && t + duTrajet >= 735) pause();
        if (i > 0 && t + duTrajet + a.duree > fin + 30) { a.reporte = true; place = false; return; }
        if (trajet) { etapes.push({ ...trajet, h: t }); t += duTrajet; }
        t = arrondi(t);
        etapes.push({ type: 'activite', h: t, a });
        t += a.duree;
        if (i === 0 && ordre.length > 2 && !dejeuner && t <= 660) {
          etapes.push({ type: 'pause', h: t, titre: 'Goûter et récréation', texte: 'Pause sur l\'aire de jeux la plus proche (voir ci-dessous).' });
          t += 20;
        }
      });
      if (!dejeuner) pause();
      const lesActs = etapes.filter(e => e.type === 'activite').map(e => e.a);
      ordre.filter(a => a.reporte).forEach(a => { utilises.delete(a.id); delete a.reporte; });

      const centre = lesActs.reduce((c, a) => ({ lat: c.lat + a.lat / lesActs.length, lon: c.lon + a.lon / lesActs.length }), { lat: 0, lon: 0 });
      const soir = soirs.filter(s => PM.distance(centre, s) < 3500 && s.s > -2)[0];
      if (soir && d === p.jours - 1 - (p.jours > 2 ? 1 : 0)) etapes.push({ type: 'soir', h: 1230, a: soir });

      jours.push({ n: d + 1, zone: v.zones[zone].nom, etapes, acts: lesActs, centre });
    }

    // Plan B (pluie, fatigue, fermeture) : lieu couvert non utilisé, le plus proche
    const couverts = elig.filter(a => a.interieur);
    const pris = new Set();
    jours.forEach(j => {
      const libre = couverts.filter(a => !j.acts.some(x => x.id === a.id))
        .sort((a, b) => (PM.distance(j.centre, a) - a.s * 300 + (pris.has(a.id) ? 2000 : 0)) - (PM.distance(j.centre, b) - b.s * 300 + (pris.has(b.id) ? 2000 : 0)));
      j.planB = libre[0] || null;
      if (j.planB) pris.add(j.planB.id);
    });
    return jours;
  }

  /* ---------- Rendu ---------- */
  const hh = m => `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')}`.replace(' 00', '');
  const esc = PM.esc;

  function badgesAct(a, p) {
    const b = [];
    b.push(a.interieur ? '<span class="badge b">Couvert</span>' : '<span class="badge">Plein air</span>');
    if (a.gratuit === true) b.push('<span class="badge o">Gratuit</span>');
    else if (a.gratuit === 'partiel') b.push('<span class="badge o">En partie gratuit</span>');
    if (a.reservation) b.push('<span class="badge t">Réserver à l\'avance</span>');
    if (p.poussette) b.push(a.poussette === 'facile' ? '<span class="badge">Poussette OK</span>' : a.poussette === 'moyen' ? '<span class="badge g">Poussette possible</span>' : '<span class="badge t">Plutôt porte-bébé</span>');
    b.push(`<span class="badge g">${a.ages[0]}–${a.ages[1]} ans</span>`);
    return `<div class="badges">${b.join('')}</div>`;
  }

  function services(a, osm, p) {
    if (!osm) return '';
    const cats = [['toilettes', 'Toilettes'], ['aire_jeux', 'Aire de jeux']];
    if (Math.min(...p.ages) < 3) cats.push(['table_langer', 'Table à langer']);
    cats.push(['resto_enfants', 'Resto équipé']);
    const li = [];
    for (const [c, nom] of cats) {
      const pr = PM.proches(osm.points, a, c, 1, c === 'table_langer' ? 1500 : 900)[0];
      if (pr) li.push(`<li>${PM.ico(PM.CATS[c].ico)}<span><strong>${nom}</strong> à ${PM.fmtDist(pr.d)} : <a href="${PM.lienItineraire({ lat: pr.lat, lon: pr.lon })}" target="_blank" rel="noopener">${pr.t?.name ? esc(pr.t.name) : 'y aller'}</a>${PM.detailPoint(pr) ? ` <span class="muted">(${esc(PM.detailPoint(pr))})</span>` : ''}</span></li>`);
    }
    return li.length ? `<div class="proches"><strong>À proximité</strong> <span class="muted">(signalé dans OpenStreetMap, non vérifié)</span><ul>${li.join('')}</ul></div>` : '';
  }

  function checklist(v, p, jours) {
    const l = ['Carte européenne d\'assurance maladie (CEAM) pour chaque membre de la famille', 'Pièces d\'identité des enfants', 'Gourde et en-cas pour chaque journée', 'Petite trousse : pansements, antipyrétique adapté au poids de l\'enfant, sérum physiologique', 'Batterie externe pour le téléphone'];
    if (Math.min(...p.ages) < 3) l.push('Couches, lingettes et tapis à langer de voyage', 'Porte-bébé pour les lieux difficiles en poussette');
    if (p.poussette) l.push('Poussette pliable et légère (métro, escaliers)');
    const mois = p.depart ? new Date(p.depart).getMonth() + 1 : 0;
    if (!mois || (mois >= 5 && mois <= 9)) l.push('Chapeaux, crème solaire, maillots de bain');
    if (!mois || mois >= 10 || mois <= 4) l.push('Coupe-vent et vêtement de pluie léger');
    const resa = jours.flatMap(j => j.acts).filter(a => a.reservation);
    resa.forEach(a => l.push(`Réserver : ${a.nom}`));
    l.push('Vérifier horaires et tarifs de chaque lieu la veille');
    return l;
  }

  function rendu(v, p, jours, osm) {
    const ages = p.ages.map(a => a === 0 ? 'bébé' : `${a} an${a > 1 ? 's' : ''}`).join(', ');
    const dateTxt = p.depart ? new Date(p.depart + 'T12:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }) : '';
    const dateJour = i => p.depart ? new Date(new Date(p.depart + 'T12:00').getTime() + i * 864e5).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }) : '';
    let h = `
      <div class="couv">
        <div class="txt">
          <span class="etiquette"><i></i>Carnet PetitMondo</span>
          <h2>${esc(v.nom)} <span class="hl">en famille</span></h2>
          <p>${p.jours} jour${p.jours > 1 ? 's' : ''}${dateTxt ? ` · à partir du ${dateTxt}` : ''}</p>
          <p>Enfants : ${esc(ages)}</p>
          <p>Rythme ${{ calme: 'tranquille', equilibre: 'équilibré', intense: 'soutenu' }[p.rythme]}${p.poussette ? ' · avec poussette' : ''}</p>
        </div>
        <div class="illu"><img class="v" src="${PM.base}assets/villes/${v.id}.svg" alt=""><img class="m" src="${PM.base}assets/mondo.svg" alt=""></div>
      </div>
      <div class="actions no-print">
        <button class="btn" id="b-pdf" type="button">${PM.ico('pdf', '')}Imprimer ou enregistrer en PDF</button>
        <button class="btn menthe" id="b-kml" type="button">${PM.ico('carte', '')}Carte Google My Maps</button>
        <button class="btn sec" id="b-csv" type="button">Liste des lieux (CSV)</button>
        <button class="btn sec" id="b-lien" type="button">Copier le lien du carnet</button>
      </div>
      <p class="note no-print">Sur iPhone : « Imprimer » puis « Partager › Enregistrer dans Fichiers » pour garder le PDF hors connexion. Pour My Maps : mymaps.google.com › Créer une carte › Importer › choisir le fichier KML.</p>
      <div id="map" class="no-print" style="margin:18px 0" aria-label="Carte du séjour"></div>
      <div class="filtres no-print">${jours.map((j, i) => `<span class="chip"><i class="pt" style="background:${COULEURS_JOURS[i]}"></i>Jour ${j.n}</span>`).join('')}<span class="chip"><i class="pt" style="background:${PM.CATS.toilettes.couleur}"></i>Toilettes</span><span class="chip"><i class="pt" style="background:${PM.CATS.aire_jeux.couleur}"></i>Aires de jeux</span><span class="chip"><i class="pt" style="background:${PM.CATS.table_langer.couleur}"></i>Tables à langer</span></div>`;

    jours.forEach((j, i) => {
      h += `<article class="jour"><div class="jour-tete" style="--c:${FONDS_JOURS[i]}"><h3>Jour ${j.n}${dateJour(i) ? ` <span style="font-weight:600;font-size:.7em">· ${dateJour(i)}</span>` : ''}</h3><span class="badge tampon">${esc(j.zone)}</span></div><div class="jour-corps">`;
      for (const e of j.etapes) {
        if (e.type === 'trajet') { h += `<div class="etape trajet"><span></span><p>${esc(e.texte)}</p></div>`; continue; }
        if (e.type === 'repas' || e.type === 'pause') { h += `<div class="etape pause"><span class="h">${hh(e.h)}</span><div><h4>${esc(e.titre)}</h4><p>${esc(e.texte)}</p></div></div>`; continue; }
        const a = e.a;
        h += `<div class="etape"><span class="h">${e.type === 'soir' ? 'Soirée' : hh(e.h)}</span><div>
          <h4>${esc(a.nom)}</h4>
          <p>${esc(a.conseil)}</p>
          ${badgesAct(a, p)}
          <p style="font-size:.85rem">${esc(a.adresse)} · environ ${a.duree >= 60 ? hh(a.duree).replace(' h', ' h ').trim() : a.duree + ' min'}</p>
          <p style="font-size:.88rem"><a href="${PM.lienItineraire(a)}" target="_blank" rel="noopener"><strong>Itinéraire</strong></a>${a.site ? ` · <a href="${esc(a.site)}" target="_blank" rel="noopener"><strong>Site officiel</strong> (horaires, tarifs)</a>` : ''}</p>
          ${services(a, osm, p)}
        </div><div class="qr" data-url="${esc(PM.lienMaps(a))}"></div></div>`;
      }
      if (j.planB) {
        const jeux = osm ? PM.proches(osm.points, j.centre, 'aire_jeux', 1, 1500)[0] : null;
        h += `<div class="planb">${PM.ico('pluie')}<div><strong>Sauver la journée</strong> (pluie, fatigue, fermeture) : <a href="${PM.lienItineraire(j.planB)}" target="_blank" rel="noopener">${esc(j.planB.nom)}</a>, lieu couvert à ${PM.fmtDist(PM.distance(j.centre, j.planB))} du quartier. ${esc(j.planB.conseil)}${jeux ? ` Besoin de se défouler ? Aire de jeux à ${PM.fmtDist(jeux.d)} du centre de la journée.` : ''}</div></div>`;
      }
      h += `</div></article>`;
    });

    h += `<article class="jour"><div class="jour-tete" style="--c:#FFF1C9"><h3>Avant de partir</h3>${PM.ico('valise')}</div><div class="jour-corps" style="padding-top:16px"><ul class="check">${checklist(v, p, jours).map(x => `<li>${esc(x)}</li>`).join('')}</ul><p style="margin-top:14px"><a href="${PM.base}valise/"><strong>La liste complète de la valise des enfants</strong></a> · <a href="${PM.base}${v.id}/jeux/"><strong>Les jeux à imprimer pour les enfants</strong></a></p></div></article>`;
    h += `<article class="jour"><div class="jour-tete" style="--c:#DDF1FB"><h3>Bon à savoir à ${esc(v.nom)}</h3>${PM.ico('loupe')}</div><div class="jour-corps" style="padding-top:12px">${v.conseils.map(c => `<p><strong>${esc(c.titre)}.</strong> ${esc(c.texte)}</p>`).join('')}<h4 style="margin-top:18px">Urgences</h4>${v.urgences.map(u => `<p><strong>${esc(u.nom)}</strong> : ${esc(u.detail)}</p>`).join('')}</div></article>`;
    h += `<p class="note">Programme indicatif établi le ${new Date().toLocaleDateString('fr-FR')}. Lieux sélectionnés par PetitMondo (fiches vérifiées le ${new Date(v.verification).toLocaleDateString('fr-FR')}). Toilettes, aires de jeux, tables à langer et restaurants équipés : données © contributeurs OpenStreetMap${osm?.maj ? `, mises à jour le ${new Date(osm.maj).toLocaleDateString('fr-FR')}` : ''}, non vérifiées sur place. ${esc(v.avertissement)}</p>`;
    sortie.innerHTML = h;
    sortie.hidden = false;

    // QR codes (visibles à l'impression)
    if (window.QRCode) sortie.querySelectorAll('.qr').forEach(el => { try { new QRCode(el, { text: el.dataset.url, width: 64, height: 64, correctLevel: QRCode.CorrectLevel.L }); } catch { /* sans QR */ } });

    // Carte
    if (window.L) {
      if (carte) carte.remove();
      carte = PM.fondCarte(L, 'map', v.centre, 13);
      const groupe = [];
      jours.forEach((j, i) => j.acts.forEach((a, k) => {
        const m = L.circleMarker([a.lat, a.lon], { radius: 10, color: '#1B2A4A', weight: 2.5, fillColor: COULEURS_JOURS[i], fillOpacity: 1 })
          .bindPopup(`<strong>J${j.n}.${k + 1} ${esc(a.nom)}</strong><br><a href="${PM.lienItineraire(a)}" target="_blank" rel="noopener">Itinéraire</a>`).addTo(carte);
        groupe.push(m.getLatLng());
      }));
      if (osm) {
        const ids = new Set();
        jours.forEach(j => j.acts.forEach(a => ['toilettes', 'aire_jeux', 'table_langer'].forEach(c => PM.proches(osm.points, a, c, 2).forEach(pr => {
          if (ids.has(pr.osm)) return; ids.add(pr.osm);
          PM.marqueur(L, pr.lat, pr.lon, c, 11).bindPopup(`<strong>${esc(PM.nomPoint(pr))}</strong><br>${esc(PM.detailPoint(pr))}<br><a href="${PM.lienMaps({ lat: pr.lat, lon: pr.lon })}" target="_blank" rel="noopener">Ouvrir dans Maps</a>`).addTo(carte);
        }))));
      }
      if (groupe.length) carte.fitBounds(groupe, { padding: [30, 30] });
    }

    // Exports
    $('#b-pdf').onclick = () => window.print();
    $('#b-lien').onclick = async () => { try { await navigator.clipboard.writeText(location.href); $('#b-lien').textContent = 'Lien copié'; } catch { prompt('Copiez ce lien :', location.href); } };
    const lieuxExport = () => {
      const dossiers = jours.map(j => ({ nom: `Jour ${j.n} — ${j.zone}`, lieux: j.acts.map(a => ({ nom: a.nom, lat: a.lat, lon: a.lon, c: 'activite', adresse: a.adresse, desc: `${a.adresse}. ${a.conseil}${a.site ? ' ' + a.site : ''}` })) }));
      if (osm) {
        const vus = new Set();
        for (const [c, nom] of [['toilettes', 'Toilettes'], ['aire_jeux', 'Aires de jeux'], ['table_langer', 'Tables à langer'], ['resto_enfants', 'Restaurants équipés']]) {
          const l = [];
          jours.forEach(j => j.acts.forEach(a => PM.proches(osm.points, a, c, 3, 1000).forEach(pr => { if (!vus.has(pr.osm)) { vus.add(pr.osm); l.push({ nom: PM.nomPoint(pr), lat: pr.lat, lon: pr.lon, c, desc: `${PM.detailPoint(pr)} — source OpenStreetMap, non vérifié` }); } })));
          if (l.length) dossiers.push({ nom, lieux: l });
        }
      }
      return dossiers;
    };
    $('#b-kml').onclick = () => PM.telecharger(`petitmondo-${v.id}.kml`, PM.kml(`PetitMondo — ${v.nom} en famille`, lieuxExport()), 'application/vnd.google-earth.kml+xml');
    $('#b-csv').onclick = () => PM.telecharger(`petitmondo-${v.id}.csv`, PM.csv(lieuxExport().flatMap(d => d.lieux.map(l => ({ ...l, cat: PM.CATS[l.c]?.nom || '', jour: d.nom.startsWith('Jour') ? d.nom : '' })))), 'text/csv;charset=utf-8');
    sortie.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function generer(e) {
    e?.preventDefault();
    const p = lireForm();
    if (!p.ages.length) return;
    versURL(p);
    const btn = $('#b-generer');
    btn.disabled = true; btn.textContent = 'Préparation du carnet…';
    try {
      const v = await PM.ville(p.ville);
      let osm = null;
      try { osm = await PM.osm(v); } catch { /* le carnet reste utilisable sans services OSM */ }
      const jours = planifier(v, p);
      dernier = { v, p, jours, osm };
      rendu(v, p, jours, osm);
    } catch (err) {
      sortie.hidden = false;
      sortie.innerHTML = `<p class="note">Impossible de préparer le carnet : ${esc(err.message)}. Réessayez dans un instant.</p>`;
    } finally {
      btn.disabled = false; btn.textContent = 'Créer mon carnet';
    }
  }

  form.addEventListener('submit', generer);
  if (depuisURL()) generer(); else ajouterEnfant(5);
})();
