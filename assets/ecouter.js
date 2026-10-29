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
