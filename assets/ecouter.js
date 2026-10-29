/* PetitMondo — « Écouter » : lit les mots des enfants avec la voix du téléphone (fonctionne hors connexion sur la plupart des appareils) */
(() => {
  const ok = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
  document.documentElement.classList.toggle('sans-voix', !ok);
  if (!ok) return;
  document.addEventListener('click', ev => {
    const b = ev.target.closest('.ecouter');
    if (!b) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(b.dataset.txt);
    u.lang = b.dataset.lang;
    u.rate = 0.8;
    const voix = speechSynthesis.getVoices().find(v => v.lang && v.lang.toLowerCase().startsWith(b.dataset.lang.slice(0, 2).toLowerCase()));
    if (voix) u.voice = voix;
    speechSynthesis.speak(u);
  });
})();

/* Quiz des enfants : réponse touchée = bonne ou mauvaise, explication affichée */
document.addEventListener('click', ev => {
  const o = ev.target.closest('.quiz .opt');
  if (!o) return;
  const q = o.closest('.question');
  if (q.classList.contains('fait')) return;
  q.classList.add('fait');
  q.querySelectorAll('.opt').forEach(b => b.classList.add(b.dataset.ok === '1' ? 'juste' : 'grise'));
  if (o.dataset.ok !== '1') o.classList.add('faux');
  const p = q.querySelector('.pourquoi');
  if (p) { p.hidden = false; p.textContent = (o.dataset.ok === '1' ? 'Bravo ! ' : 'Presque ! ') + p.textContent; }
});
