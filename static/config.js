/* IDs públicos estáveis; sourceKey é somente o caminho legado no servidor de dados. */
window.SMNA_CONFIG = {
  defaultEnvironment: 'smna-fn',
  environments: {
    'smna-fn': {label: 'SMNA-FNCEP', aliases: ['SMNA-FN'], gsiRoot: 'data/smna-fn/', sourceKey: 'egeon'},
    'smna-fc': {label: 'SMNA-FINPE', aliases: ['SMNA-FC'], gsiRoot: 'data/smna-fc/', sourceKey: 'xc50'}
  }
};
