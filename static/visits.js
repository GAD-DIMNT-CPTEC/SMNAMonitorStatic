/* O próprio badge do hits.sh registra e exibe a contagem. */
(() => {
  const badge = document.getElementById('visit-count-badge');
  const note = document.getElementById('visit-count-note');
  if (!badge || !note) return;
  function unavailable() {
    badge.hidden = true;
    note.textContent = 'Contagem de acessos temporariamente indisponível';
  }
  badge.addEventListener('error', unavailable);
  // Também trata falhas ocorridas antes da execução do script defer.
  if (badge.complete && badge.naturalWidth === 0) unavailable();
})();
