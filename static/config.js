/* IDs públicos estáveis; sourceKey é somente o caminho legado no servidor de dados. */
// Na abertura direta, preserve os produtos locais; HTTP(S) usa a origem operacional.
const GSI_BASE = location.protocol === 'file:'
  ? 'data/'
  : 'https://dataserver.cptec.inpe.br/dataserver_dimnt/das/carlos.bastarz/sandbox/SMNAMonitoringApp/online/static/data/';

window.SMNA_CONFIG = {
  defaultEnvironment: 'smna-fn',
  environments: {
    'smna-fn': {label: 'SMNA-FNCEP', aliases: ['SMNA-FN'], gsiRoot: GSI_BASE + 'smna-fncep/', sourceKey: 'egeon', logsKey: 'smna-fncep', inventoryKey: 'smna-fncep'},
    'smna-fc': {label: 'SMNA-FINPE', aliases: ['SMNA-FC'], gsiRoot: GSI_BASE + 'smna-finpe/', sourceKey: 'xc50', logsKey: 'smna-finpe', inventoryKey: 'smna-finpe'}
  }
};
