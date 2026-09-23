/* Source release; export_site.py replaces this with the exact exported commit. */
window.SMNA_VERSION = {commit: null};
document.addEventListener('DOMContentLoaded', () => {
  const target = document.getElementById('site-version');
  if (!target) return;
  const version = window.SMNA_VERSION;
  target.textContent = 'Versão local · desenvolvimento';
  if (/^[0-9a-f]{40,64}$/.test(version.commit || '')) {
    const link = document.createElement('a');
    link.href = 'https://github.com/GAD-DIMNT-CPTEC/SMNAMonitorStatic/commit/' + version.commit;
    link.textContent = version.commit.slice(0, 12);
    link.title = version.commit;
    link.target = '_blank'; link.rel = 'noopener';
    target.replaceChildren('Revisão ', link);
  }
});
