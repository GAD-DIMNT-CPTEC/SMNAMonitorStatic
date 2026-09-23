/* IDs públicos estáveis; sourceKey identifica o diretório das imagens no servidor. */
// Na abertura direta, preserve os produtos locais; HTTP(S) usa a origem operacional.
const GSI_BASE = location.protocol === 'file:'
  ? 'data/'
  : 'https://dataserver.cptec.inpe.br/dataserver_dimnt/das/carlos.bastarz/sandbox/SMNAMonitoringApp/online/static/data/';

const BAM_BASE = location.protocol === 'file:' || ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)
  ? 'bam/'
  : 'https://dataserver.cptec.inpe.br/dataserver_dimnt/das/carlos.bastarz/sandbox/SMNAMonitorStatic/static/bam/';

window.SMNA_CONFIG = {
  defaultEnvironment: 'smna-fn',
  bamRoot: BAM_BASE,
  environments: {
    'smna-fn': {label: 'SMNA-FNCEP', aliases: ['SMNA-FN'], gsiRoot: GSI_BASE + 'smna-fncep/', sourceKey: 'smna-fncep', logsKey: 'smna-fncep', inventoryKey: 'smna-fncep', updates: [{time: '09:00', cycle: '00Z'}, {time: '13:15', cycle: '06Z'}, {time: '17:00', cycle: '12Z'}, {time: '23:15', cycle: '18Z'}]},
    'smna-fc': {label: 'SMNA-FINPE', aliases: ['SMNA-FC'], gsiRoot: GSI_BASE + 'smna-finpe/', sourceKey: 'xc50', logsKey: 'smna-finpe', inventoryKey: 'smna-finpe', updates: [{time: '07:45', cycle: '00Z'}, {time: '11:15', cycle: '06Z'}, {time: '17:45', cycle: '12Z'}, {time: '22:30', cycle: '18Z'}]}
  }
};
