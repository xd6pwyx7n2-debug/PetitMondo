/* PetitMondo — générateur de carnet familial (parents + enfants) */
(() => {
  const $ = s => document.querySelector(s);
  const form = $('#form-carnet');
  const zoneEnfants = $('#enfants');
  const sortie = $('#carnet');
  const COULEURS_JOURS = ['#FF6B4A', '#2FB59A', '#6EC6F0', '#A88BEB', '#FFC93C'];
  const FONDS_JOURS = ['#FFE1D9', '#D5F2EA', '#DDF1FB', '#EEE7FC', '#FFF1C9'];
  const esc = PM.esc;
  let carte = null;
  let PHOTOS = null;

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
      enfants: !!fd.get('pe'),
    };
  }
  function versURL(p) {
    const q = new URLSearchParams({ v: p.ville, j: p.jours, a: p.ages.join('-'), r: p.rythme, p: p.poussette ? 1 : 0, b: p.budget, i: p.interets.join('-'), e: p.enfants ? 1 : 0 });
    if (p.depart) q.set('d', p.depart);
    history.replaceState(null, '', '#' + q.toString());
  }
  function depuisURL() {
    const h = new URLSearchParams(location.hash.slice(1) || location.search.slice(1));
    if (!h.get('v')) return false;
    if ([...form.ville.options].some(o => o.value === h.get('v'))) form.ville.value = h.get('v');
    form.jours.value = h.get('j') || 3;
    zoneEnfants.querySelectorAll('.enfant').forEach(e => e.remove());
    (h.get('a') || '5').split('-').filter(Boolean).forEach(a => ajouterEnfant(+a));
    const coche = (nom, val) => { const el = form.querySelector(`input[name="${nom}"][value="${val}"]`); if (el) el.checked = true; };
    coche('rythme', h.get('r') || 'equilibre');
    coche('poussette', h.get('p') === '1' ? 'oui' : 'non');
    coche('budget', h.get('b') || 'tous');
    form.pe.checked = h.get('e') !== '0';
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

  const arrondi = m => Math.ceil(m / 15) * 15;

  /* Construit la chronologie d'une journée à partir d'une liste ordonnée de lieux */
  function journee(ordre, p) {
    const petit = Math.min(...p.ages);
    let t = p.rythme === 'calme' ? 600 : 570; // minutes depuis minuit
    const fin = p.rythme === 'intense' ? 1140 : 1095;
    const etapes = [];
    const reportes = [];
    let dejeuner = false;
    const pause = () => {
      t = Math.max(720, arrondi(t));
      etapes.push({ type: 'repas', h: t, titre: 'Déjeuner', texte: 'Pique-nique ou restaurant dès l\'ouverture du service pour éviter l\'attente. Voir les restaurants équipés signalés à proximité.' });
      t += 60;
      if (petit < 4) {
        etapes.push({ type: 'pause', h: t, titre: 'Sieste ou temps calme', texte: 'Retour à l\'hébergement, ou sieste en poussette à l\'ombre d\'un parc.' });
        t += 75;
      }
      dejeuner = true;
    };
    let plein = false;
    ordre.forEach((a, i) => {
      if (plein) { reportes.push(a); return; }
      let trajet = null, duTrajet = 0;
      if (i > 0) {
        const prec = etapes.filter(e => e.type === 'activite').pop()?.a || ordre[i - 1];
        const m = PM.distance(prec, a);
        const min = PM.minutesMarche(m);
        duTrajet = min > 25 ? 30 : min;
        trajet = { type: 'trajet', texte: min > 25 ? `Trajet en transports (${PM.fmtDist(m)} à vol d'oiseau) : ${a.transport}` : `${min} min à pied environ (${PM.fmtDist(m)})` };
      }
      if (!dejeuner && t + duTrajet >= 735) pause();
      if (i > 0 && t + duTrajet + a.duree > fin + 30) { reportes.push(a); plein = true; return; }
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
    return { etapes, acts: etapes.filter(e => e.type === 'activite').map(e => e.a), reportes };
  }

  function ordonner(choix) {
    choix = [...choix].sort((a, b) => b.duree - a.duree);
    const ordre = [choix.shift()];
    while (choix.length) {
      const der = ordre[ordre.length - 1];
      choix.sort((a, b) => PM.distance(der, a) - PM.distance(der, b));
      ordre.push(choix.shift());
    }
    return ordre;
  }

  function planifier(v, p) {
    const tous = v.activites.map(a => ({ ...a, s: score(a, p) }));
    const elig = tous.filter(a => a.s > -2 && !a.soir && !a.excursion);
    const soirs = tous.filter(a => a.soir && a.s > -2);
    const excursion = p.jours >= 4 ? tous.filter(a => a.excursion && a.s > 0).sort((a, b) => b.s - a.s)[0] : null;
    const joursVille = excursion ? p.jours - 1 : p.jours;
    const parJour = { calme: 2, equilibre: 3, intense: 4 }[p.rythme];
    const utilises = new Set();
    const soirsPris = new Set();
    const zonesOrd = Object.keys(v.zones)
      .map(z => ({ z, s: elig.filter(a => a.zone === z).sort((a, b) => b.s - a.s).slice(0, parJour).reduce((t, a) => t + Math.max(0, a.s), 0) }))
      .filter(x => x.s > 0).sort((a, b) => b.s - a.s).map(x => x.z);
    const jours = [];

    for (let d = 0; d < joursVille && zonesOrd.length; d++) {
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
      const j = journee(ordonner(choix), p);
      j.acts.forEach(a => utilises.add(a.id));
      const centre = j.acts.reduce((c, a) => ({ lat: c.lat + a.lat / j.acts.length, lon: c.lon + a.lon / j.acts.length }), { lat: 0, lon: 0 });
      const soir = soirs.find(s => !soirsPris.has(s.id) && (s.zone === zone || PM.distance(centre, s) < 3500));
      if (soir && (p.rythme !== 'calme' || Math.min(...p.ages) >= 3)) { j.etapes.push({ type: 'soir', h: 1230, a: soir }); soirsPris.add(soir.id); }
      jours.push({ zone: v.zones[zone].nom, ...j, centre });
    }
    if (excursion) {
      const j = journee([excursion], p);
      const pos = Math.max(0, jours.length - 1);
      jours.splice(pos, 0, { zone: v.zones[excursion.zone].nom, ...j, centre: { lat: excursion.lat, lon: excursion.lon }, excursion: true });
    }
    jours.forEach((j, i) => { j.n = i + 1; });

    // Plan B (pluie, fatigue, fermeture) : lieu couvert non prévu, le plus proche
    const couverts = elig.filter(a => a.interieur);
    const pris = new Set();
    jours.forEach(j => {
      if (j.excursion) { j.planB = null; return; }
      const cout = a => PM.distance(j.centre, a) - a.s * 300 + (pris.has(a.id) || utilises.has(a.id) ? 2500 : 0);
      const libre = couverts.filter(a => !j.acts.some(x => x.id === a.id)).sort((a, b) => cout(a) - cout(b));
      j.planB = libre[0] || null;
      if (j.planB) pris.add(j.planB.id);
    });
    return jours;
  }

  /* Version « jour de pluie » : uniquement des lieux couverts, proches du quartier du jour */
  function versionCouverte(v, p, jours, i) {
    const j = jours[i];
    const ailleurs = new Set(jours.filter((x, k) => k !== i).flatMap(x => x.acts.map(a => a.id)));
    const parJour = Math.max(2, Math.min(j.acts.length, { calme: 2, equilibre: 3, intense: 4 }[p.rythme]));
    const choix = v.activites.map(a => ({ ...a, s: score(a, p) }))
      .filter(a => a.interieur && !a.soir && !a.excursion && a.s > -2 && !ailleurs.has(a.id))
      .sort((a, b) => (PM.distance(j.centre, a) - a.s * 300) - (PM.distance(j.centre, b) - b.s * 300))
      .slice(0, parJour);
    if (!choix.length) return j;
    const nv = journee(ordonner(choix), p);
    return { ...nv, n: j.n, zone: 'Version jour de pluie', centre: j.centre, planB: null, pluie: true, original: j };
  }

  /* ---------- Rendu ---------- */
  const hh = m => `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')}`.replace(' 00', '');
  const dureeTxt = m => m < 60 ? `${m} min` : hh(m);
  const photoDe = (vid, id) => PHOTOS?.[`${vid}/${id}`] || null;
  const imgPhoto = (vid, a, cls) => {
    const ph = photoDe(vid, a.id);
    if (ph) return `<figure class="photo ${cls}"><img src="${PM.base}${ph.fichier}" alt="${esc(a.nom)}" loading="lazy"></figure>`;
    return `<figure class="photo ill ${cls}"><img src="${PM.base}assets/villes/${vid}.svg" alt="" loading="lazy"></figure>`;
  };
  const numero = (j, k) => `<span class="num" style="--c:${COULEURS_JOURS[(j.n - 1) % 5]}">${j.n}.${k}</span>`;

  function badgesAct(a, p) {
    const b = [];
    b.push(a.interieur ? '<span class="badge b">Couvert</span>' : '<span class="badge">Plein air</span>');
    if (a.gratuit === true) b.push('<span class="badge s">Gratuit</span>');
    else if (a.gratuit === 'partiel') b.push('<span class="badge s">En partie gratuit</span>');
    if (a.reservation) b.push('<span class="badge c">Réserver à l\'avance</span>');
    if (p.poussette) b.push(a.poussette === 'facile' ? '<span class="badge l">Poussette OK</span>' : a.poussette === 'moyen' ? '<span class="badge g">Poussette possible</span>' : '<span class="badge c">Plutôt porte-bébé</span>');
    b.push(`<span class="badge g">${a.ages[0]}–${a.ages[1]} ans</span>`);
    return `<div class="badges">${b.join('')}</div>`;
  }

  function services(a, osm, p) {
    if (!osm) return '';
    const cats = [['toilettes', 'Toilettes'], ['aire_jeux', 'Aire de jeux'], ['eau', 'Eau potable']];
    if (Math.min(...p.ages) < 3) cats.push(['table_langer', 'Table à langer']);
    cats.push(['resto_enfants', 'Resto équipé']);
    const li = [];
    for (const [c, nom] of cats) {
      const pr = PM.proches(osm.points, a, c, 1, c === 'table_langer' ? 1500 : 900)[0];
      if (pr) {
        const det = PM.detailPoint(pr).split(' · ').filter(x => x && !(c === 'table_langer' && x.startsWith('table à langer'))).join(' · ');
        const nomP = pr.t?.name ? ` : <a href="${PM.lienItineraire({ lat: pr.lat, lon: pr.lon })}" target="_blank" rel="noopener">${esc(pr.t.name)}</a>` : '';
        li.push(`<li>${PM.ico(PM.CATS[c].ico)}<span><strong>${nom}</strong> ${PM.aPied(pr.d)}${nomP}${det ? ` <span class="muted">· ${esc(det)}</span>` : ''}</span></li>`);
      }
    }
    return li.length ? `<div class="proches"><strong>À proximité</strong> <span class="muted">(signalé dans OpenStreetMap, non vérifié)</span><ul>${li.join('')}</ul></div>` : '';
  }

  let ACCES = null;
  function poussette(a, p) {
    if (!p.poussette && Math.min(...p.ages) >= 3) return '';
    const f = PM.fichePoussette(a, ACCES);
    return `<div class="poussette-fiche ${f.classe}">${PM.ico('poussette', 'i s')}<div><strong>${f.note}</strong>${f.details.length ? `<span class="muted"> · ${esc(f.details.join(' · '))}</span>` : ''}</div></div>`;
  }

  function checklist(v, p, jours) {
    const l = [v.papiers, 'Gourde et en-cas pour chaque journée', 'Petite trousse : pansements, antipyrétique adapté au poids de l\'enfant, sérum physiologique', 'Batterie externe pour le téléphone', 'Ce carnet enregistré en PDF sur le téléphone, pour le mode avion'];
    if (Math.min(...p.ages) < 3) l.push('Couches, lingettes et tapis à langer de voyage', 'Porte-bébé pour les lieux difficiles en poussette');
    if (p.poussette) l.push('Poussette pliable et légère (escaliers, transports)');
    if (p.enfants) l.push('Les pages enfants imprimées et une trousse de crayons');
    const mois = p.depart ? new Date(p.depart + 'T12:00').getMonth() + 1 : 0;
    if (!mois || (mois >= 5 && mois <= 9)) l.push('Chapeaux et crème solaire');
    if (!mois || mois >= 10 || mois <= 4) l.push('Coupe-vent et vêtement de pluie léger');
    jours.flatMap(j => j.acts).filter(a => a.reservation).forEach(a => l.push(`Réserver : ${a.nom}`));
    l.push('Vérifier horaires et tarifs de chaque lieu la veille');
    return l;
  }

  async function pagesEnfants(v, jours) {
    let frag = '';
    try {
      const r = await fetch(`${PM.base}data/enfants/${v.id}.html`);
      if (r.ok) frag = (await r.text()).replaceAll('{{BASE}}', PM.base);
      const tmp = document.createElement('div');
      tmp.innerHTML = frag;
      tmp.querySelectorAll('.journal[data-jour]').forEach(el => { if (+el.dataset.jour > jours.length) el.remove(); });
      frag = tmp.innerHTML;
    } catch { /* hors connexion sans cache : on garde la page « Ce que je vais voir » */ }
    const voir = jours.map(j => `<h3 style="margin-top:18px">Jour ${j.n}</h3><div class="voir-grille">${j.acts.map((a, k) => `
      <div class="voir">${numero(j, k + 1)}${imgPhoto(v.id, a, '')}<div class="txt"><b>${esc(a.nom)}</b>${esc(a.enfant || '')}<span class="coche">☐ J'y suis allé !</span></div></div>`).join('')}</div>`).join('');
    return `<section class="page-enfant voir-page">
      <div class="pe-tete"><img src="${PM.base}assets/mondo-coucou.svg" alt="" class="pe-mondo"><div><span class="etiquette"><i></i>Le carnet de l'explorateur</span><h2>Ce que je vais voir à ${esc(v.nom)}</h2></div></div>
      <p class="pe-consigne">Chaque lieu a un numéro, le même que sur la carte des parents. Coche-le quand tu y es allé !</p>${voir}
    </section>${frag}`;
  }

  /* Météo du séjour (Open-Meteo), seulement si le départ est dans les 15 jours */
  const METEO = c => c === 0 ? ['Soleil', 'soleil'] : c <= 3 ? ['Éclaircies', 'nuages'] : c <= 48 ? ['Brouillard', 'nuages'] : c <= 67 || (c >= 80 && c <= 82) ? ['Pluie', 'pluie'] : c <= 77 || c === 85 || c === 86 ? ['Neige', 'pluie'] : ['Orages', 'pluie'];
  async function meteo(v, p, n) {
    if (!p.depart) return { etat: 'sans-date' };
    const debut = new Date(p.depart + 'T12:00'), auj = new Date();
    const ecart = Math.round((debut - auj) / 864e5);
    if (ecart > 14) return { etat: 'trop-tot', ecart };
    if (ecart < -n) return { etat: 'passe' };
    const fin = new Date(debut.getTime() + (n - 1) * 864e5).toISOString().slice(0, 10);
    try {
      const ctrl = new AbortController(); setTimeout(() => ctrl.abort(), 5000);
      const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${v.centre[0]}&longitude=${v.centre[1]}&daily=weather_code,temperature_2m_max,precipitation_probability_max&timezone=auto&start_date=${p.depart}&end_date=${fin}`, { signal: ctrl.signal });
      const j = await r.json();
      if (!j.daily) return { etat: 'indispo' };
      return { etat: 'ok', jours: j.daily.time.map((t, i) => ({ code: j.daily.weather_code[i], tmax: Math.round(j.daily.temperature_2m_max[i]), pluie: j.daily.precipitation_probability_max[i] ?? 0 })) };
    } catch { return { etat: 'indispo' }; }
  }
  function bandeauMeteo(m, i) {
    const d = m.etat === 'ok' ? m.jours[i] : null;
    if (!d) return '';
    const [lib] = METEO(d.code);
    let conseil = '';
    if (d.pluie >= 60) conseil = ' Pluie probable : gardez le plan B sous la main.';
    else if (d.tmax >= 30) conseil = ' Forte chaleur : visites en plein air le matin, lieux couverts l\'après-midi.';
    else if (d.tmax <= 5) conseil = ' Il fera froid : bonnets et gants pour les enfants.';
    return `<p class="meteo ${d.pluie >= 60 ? 'alerte' : ''}">${PM.ico(METEO(d.code)[1] === 'pluie' ? 'pluie' : 'horloge', 'i s')}<span><strong>Météo prévue : ${lib}, ${d.tmax} °C</strong>, risque de pluie ${d.pluie} %.${conseil}</span></p>`;
  }

  /* Vacances scolaires françaises pendant le séjour (calendrier officiel de l'Éducation nationale) */
  async function vacances(p, n) {
    if (!p.depart) return null;
    const debut = p.depart, fin = new Date(new Date(p.depart + 'T12:00').getTime() + (n - 1) * 864e5).toISOString().slice(0, 10);
    try {
      const r = await fetch(`${PM.base}data/vacances.json`);
      if (!r.ok) return null;
      const liste = await r.json();
      const zones = new Map();
      for (const x of liste) {
        if (x.debut > fin || x.fin < debut) continue;
        if (!zones.has(x.nom)) zones.set(x.nom, new Set());
        zones.get(x.nom).add(x.zone);
      }
      return [...zones].map(([nom, z]) => ({ nom, zones: [...z].sort() }));
    } catch { return null; }
  }

  async function rendu(v, p, jours, osm) {
    const [met, vac] = await Promise.all([meteo(v, p, jours.length), vacances(p, jours.length)]);
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
          ${p.enfants ? '<p><span class="badge s">Avec les pages enfants : jeux, découverte et premiers mots</span></p>' : ''}
        </div>
        <div class="illu"><img class="v" src="${PM.base}assets/villes/${v.id}.svg" alt=""><img class="m" src="${PM.base}assets/mondo-coucou.svg" alt=""></div>
      </div>
      <div class="actions no-print">
        <button class="btn" id="b-pdf" type="button">${PM.ico('pdf', '')}Enregistrer en PDF (mode avion)</button>
        <button class="btn menthe" id="b-kml" type="button">${PM.ico('carte', '')}Carte Google My Maps</button>
        <button class="btn sec" id="b-csv" type="button">Liste des lieux (CSV)</button>
        <button class="btn jaune" id="b-autour" type="button">${PM.ico('carte', '')}Autour de moi</button>
        <button class="btn sec" id="b-lien" type="button">Partager le carnet</button>
      </div>
      <div id="autour" class="carte no-print" hidden><h3>Autour de moi</h3><div id="autour-res"><p class="muted">Recherche de votre position…</p></div></div>
      ${vac && vac.length ? `<p class="note vacances">${PM.ico('horloge', 'i s')} <strong>Vacances scolaires françaises pendant votre séjour</strong> : ${vac.map(x => `${esc(x.nom)} (zone${x.zones.length > 1 ? 's' : ''} ${x.zones.join(', ')})`).join(' ; ')}. Attendez-vous à plus de monde sur les grands sites : réservez tôt et arrivez à l'ouverture.</p>` : ''}
      ${met.etat === 'trop-tot' ? `<p class="note no-print">La météo de chaque journée apparaîtra ici dans les 15 jours avant le départ (encore ${met.ecart - 14} jours) : rouvrez simplement le lien du carnet.</p>` : ''}${met.etat === 'sans-date' ? '<p class="note no-print">Indiquez la date d\'arrivée pour voir la météo de chaque journée dans les 15 jours avant le départ.</p>' : ''}
      <div class="avion carte no-print">${PM.ico('avion', 'i l')}<div><h3>À faire avant de partir</h3><p>Enregistrez ce carnet en PDF : il s'ouvrira en mode avion, sans réseau. Tout y est écrit en clair : adresses, transports, services proches avec leur temps de marche. Les QR codes ne servent que si vous avez du réseau. Sur iPhone : « Imprimer », puis « Partager › Enregistrer dans Fichiers ». Sur Android : « Imprimer › Enregistrer au format PDF ». Pour la carte : mymaps.google.com › Créer une carte › Importer le fichier KML.</p></div></div>
      <div id="map" class="no-print" style="margin:22px 0 12px" aria-label="Carte du séjour"></div>
      <div class="filtres no-print">${jours.map((j, i) => `<span class="chip"><i class="pt" style="background:${COULEURS_JOURS[i % 5]}"></i>Jour ${j.n}</span>`).join('')}<span class="chip"><i class="pt" style="background:${PM.CATS.toilettes.couleur}"></i>Toilettes</span><span class="chip"><i class="pt" style="background:${PM.CATS.aire_jeux.couleur}"></i>Aires de jeux</span><span class="chip"><i class="pt" style="background:${PM.CATS.table_langer.couleur}"></i>Tables à langer</span></div>`;

    const jourHTML = (j, i) => {
      let out = '';
      out += `<article id="jour-${i}" class="jour${j.pluie ? ' jour-couvert' : ''}${met.etat === 'ok' && met.jours[i]?.pluie >= 60 ? ' jour-pluie' : ''}"><div class="jour-tete" style="--c:${FONDS_JOURS[i % 5]}"><h3>Jour ${j.n}${dateJour(i) ? ` <span style="font-weight:600;font-size:.7em">· ${dateJour(i)}</span>` : ''}</h3><span class="badge tampon">${esc(j.zone)}</span>${j.excursion ? '' : `<button class="btn petit ${j.pluie ? 'jaune' : 'sec'} no-print b-pluie" type="button" data-i="${i}">${j.pluie ? 'Revenir au programme' : 'Il pleut ? Version couverte'}</button>`}</div><div class="jour-corps">${bandeauMeteo(met, i)}`;
      let k = 0;
      for (const e of j.etapes) {
        if (e.type === 'trajet') { out += `<div class="etape trajet"><span></span><p>${esc(e.texte)}</p></div>`; continue; }
        if (e.type === 'repas' || e.type === 'pause') { out += `<div class="etape pause"><span class="h">${hh(e.h)}</span><div><h4>${esc(e.titre)}</h4><p>${esc(e.texte)}</p></div></div>`; continue; }
        const a = e.a;
        const num = e.type === 'soir' ? `<span class="num" style="--c:#1B2A4A;color:#fff">★</span>` : numero(j, ++k);
        out += `<div class="etape"><span class="h">${e.type === 'soir' ? 'Soirée' : hh(e.h)}</span><div>
          ${imgPhoto(v.id, a, 'vignette')}
          <div class="tete-lieu">${num}<h4>${esc(a.nom)}</h4></div>
          <p>${esc(a.conseil)}</p>
          ${badgesAct(a, p)}
          <p class="acces">${PM.ico('carte', 'i s')}<span><strong>${esc(a.adresse)}</strong><br>${esc(a.transport)} · environ ${dureeTxt(a.duree)}</span></p>
          <p class="ecran" style="font-size:.9rem"><a href="${PM.lienItineraire(a)}" target="_blank" rel="noopener"><strong>Itinéraire</strong></a>${a.site ? ` · <a href="${esc(a.site)}" target="_blank" rel="noopener"><strong>Site officiel</strong> (horaires, tarifs)</a>` : ''}</p>
          ${a.site ? `<p class="papier" style="font-size:.9rem">Horaires et tarifs : <strong>${esc(PM.domaine(a.site))}</strong></p>` : ''}
          ${poussette(a, p)}
          ${services(a, osm, p)}
        </div><div class="qr" data-url="${esc(PM.lienItineraire(a))}"></div></div>`;
      }
      if (j.planB) {
        const jeux = osm ? PM.proches(osm.points, j.centre, 'aire_jeux', 1, 1500)[0] : null;
        out += `<div class="planb">${PM.ico('pluie')}<div><strong>Sauver la journée</strong> (pluie, fatigue, fermeture) : <a href="${PM.lienItineraire(j.planB)}" target="_blank" rel="noopener">${esc(j.planB.nom)}</a>, lieu couvert ${PM.aPied(PM.distance(j.centre, j.planB))}. Adresse : ${esc(j.planB.adresse)}. ${esc(j.planB.transport)}.${jeux ? ` Besoin de se défouler ? Une aire de jeux est signalée ${PM.aPied(jeux.d)}.` : ''}</div></div>`;
      }
      out += `</div></article>`;
      return out;
    };
    jours.forEach((j, i) => { h += jourHTML(j, i); });

    h += `<article class="jour"><div class="jour-tete" style="--c:#FFF1C9"><h3>Avant de partir</h3>${PM.ico('valise')}</div><div class="jour-corps" style="padding-top:16px"><ul class="check">${checklist(v, p, jours).map(x => `<li>${esc(x)}</li>`).join('')}</ul></div></article>`;
    h += `<article class="jour"><div class="jour-tete" style="--c:#DDF1FB"><h3>Bon à savoir · ${esc(v.nom)}</h3>${PM.ico('loupe')}</div><div class="jour-corps" style="padding-top:12px">${v.conseils.map(c => `<p><strong>${esc(c.titre)}.</strong> ${esc(c.texte)}</p>`).join('')}${(p.poussette || Math.min(...p.ages) < 3) && v.poussette ? `<h4 style="margin-top:18px">Avec une poussette</h4>${v.poussette.map(c => `<p><strong>${esc(c.titre)}.</strong> ${esc(c.texte)}</p>`).join('')}` : ''}<h4 style="margin-top:18px">Urgences</h4>${v.urgences.map(u => `<p><strong>${esc(u.nom)}</strong> : ${esc(u.detail)}</p>`).join('')}</div></article>`;
    if (p.enfants) h += await pagesEnfants(v, jours);

    const utilisees = [...new Set(jours.flatMap(j => j.acts.concat(j.planB ? [j.planB] : [])).map(a => a.id))]
      .map(id => ({ a: v.activites.find(x => x.id === id), ph: photoDe(v.id, id) })).filter(x => x.ph);
    const creditsTxt = utilisees.length ? `<p class="credits-pdf"><strong>Photos</strong> (Wikimedia Commons) : ${utilisees.map(x => `${esc(x.a.nom)} : ${esc(x.ph.auteur.replace('This Photo was taken by ', '').split('. ')[0].slice(0, 60))}, ${esc(x.ph.licence)}`).join(' · ')}.</p>` : '';
    h += `<p class="note">Programme indicatif établi le ${new Date().toLocaleDateString('fr-FR')}. Lieux sélectionnés par PetitMondo (fiches vérifiées le ${new Date(v.verification + 'T12:00').toLocaleDateString('fr-FR')}). Toilettes, aires de jeux, tables à langer et restaurants équipés : données © contributeurs OpenStreetMap${osm?.maj ? `, mises à jour le ${new Date(osm.maj + 'T12:00').toLocaleDateString('fr-FR')}` : ''}, non vérifiées sur place. ${esc(v.avertissement)}</p>${creditsTxt}`;
    sortie.innerHTML = h;
    sortie.hidden = false;

    // QR codes vers l'itinéraire (visibles à l'impression)
    if (window.QRCode) sortie.querySelectorAll('.qr').forEach(el => { try { new QRCode(el, { text: el.dataset.url, width: 66, height: 66, correctLevel: QRCode.CorrectLevel.L }); } catch { /* sans QR */ } });

    // Carte avec repères numérotés identiques au carnet
    if (window.L) {
      if (carte) carte.remove();
      carte = PM.fondCarte(L, 'map', v.centre, 13);
      const groupe = [];
      jours.forEach((j, i) => j.acts.forEach((a, k) => {
        const icone = L.divIcon({ className: 'marqueur', html: `<span style="background:${COULEURS_JOURS[i % 5]}">${j.n}.${k + 1}</span>`, iconSize: [30, 30], iconAnchor: [15, 15] });
        const m = L.marker([a.lat, a.lon], { icon: icone }).bindPopup(`<strong>${j.n}.${k + 1} · ${esc(a.nom)}</strong><br>${esc(a.transport)}<br><a href="${PM.lienItineraire(a)}" target="_blank" rel="noopener">Itinéraire</a>`).addTo(carte);
        groupe.push(m.getLatLng());
      }));
      if (osm) {
        const ids = new Set();
        jours.forEach(j => j.acts.forEach(a => ['toilettes', 'aire_jeux', 'table_langer'].forEach(c => PM.proches(osm.points, a, c, 2).forEach(pr => {
          if (ids.has(pr.osm)) return; ids.add(pr.osm);
          PM.marqueur(L, pr.lat, pr.lon, c, 11).bindPopup(`<strong>${esc(PM.nomPoint(pr))}</strong><br>${esc(PM.detailPoint(pr))}<br><a href="${PM.lienItineraire({ lat: pr.lat, lon: pr.lon })}" target="_blank" rel="noopener">Itinéraire</a>`).addTo(carte);
        }))));
      }
      if (groupe.length) carte.fitBounds(groupe, { padding: [30, 30], maxZoom: 16 });
    }

    // Exports
    $('#b-pdf').onclick = () => window.print();
    sortie.onclick = ev => {
      const b = ev.target.closest('.b-pluie');
      if (!b) return;
      const i = +b.dataset.i;
      jours[i] = jours[i].pluie ? jours[i].original : versionCouverte(v, p, jours, i);
      const art = document.getElementById(`jour-${i}`);
      art.outerHTML = jourHTML(jours[i], i);
      const neuf = document.getElementById(`jour-${i}`);
      if (window.QRCode) neuf.querySelectorAll('.qr').forEach(el => { try { new QRCode(el, { text: el.dataset.url, width: 66, height: 66, correctLevel: QRCode.CorrectLevel.L }); } catch { /* sans QR */ } });
      neuf.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    $('#b-autour').onclick = () => {
      const zone = $('#autour'), res = $('#autour-res');
      zone.hidden = false; zone.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (!osm) { res.innerHTML = '<p class="muted">Les services ne sont pas disponibles pour le moment.</p>'; return; }
      if (!navigator.geolocation) { res.innerHTML = '<p class="muted">La position n\'est pas disponible sur cet appareil.</p>'; return; }
      navigator.geolocation.getCurrentPosition(pos => {
        const ici = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        res.innerHTML = PM.distance(ici, { lat: v.centre[0], lon: v.centre[1] }) > 40000
          ? `<p class="muted">Vous semblez loin ${/^[AEIOUYÉ]/i.test(v.nom) ? 'd\'' : 'de '}${esc(v.nom)}. Ce bouton est fait pour le jour J, sur place.</p>`
          : PM.autour(osm, ici);
      }, () => { res.innerHTML = '<p class="muted">Autorisez la localisation pour voir les services les plus proches.</p>'; }, { enableHighAccuracy: true, timeout: 12000 });
    };
    $('#b-lien').onclick = async () => {
      const texte = `Notre carnet de voyage PetitMondo pour ${v.nom} : le programme jour par jour, les adresses et les pages de jeux des enfants.`;
      if (navigator.share) { try { await navigator.share({ title: `PetitMondo · ${v.nom} en famille`, text: texte, url: location.href }); return; } catch { /* partage annulé */ } }
      try { await navigator.clipboard.writeText(location.href); $('#b-lien').textContent = 'Lien copié'; } catch { prompt('Copiez ce lien :', location.href); }
    };
    const lieuxExport = () => {
      const dossiers = jours.map(j => ({ nom: `Jour ${j.n} — ${j.zone}`, lieux: j.acts.map((a, k) => ({ nom: `${j.n}.${k + 1} ${a.nom}`, lat: a.lat, lon: a.lon, c: 'activite', adresse: a.adresse, desc: `${a.adresse}. ${a.transport}. ${a.conseil}${a.site ? ' ' + a.site : ''}` })) }));
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

  async function generer(ev) {
    ev?.preventDefault();
    const p = lireForm();
    if (!p.ages.length) return;
    versURL(p);
    const btn = $('#b-generer');
    btn.disabled = true; btn.textContent = 'Préparation du carnet…';
    try {
      const v = await PM.ville(p.ville);
      if (PHOTOS === null) {
        try { const r = await fetch(`${PM.base}data/photos.json`); PHOTOS = r.ok ? await r.json() : {}; } catch { PHOTOS = {}; }
      }
      let osm = null;
      try { osm = await PM.osm(v); } catch { /* le carnet reste utilisable sans services OSM */ }
      ACCES = await PM.acces(v);
      const jours = planifier(v, p);
      await rendu(v, p, jours, osm);
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
