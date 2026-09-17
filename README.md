# SMNAMonitorStatic

Dashboard estática de monitoramento da assimilação de dados do CPTEC/INPE. Uma única página apresenta **SMNA-FNCEP** e **SMNA-FINPE**, com dados separados e uma única cópia dos scripts de processamento.

## Organização

- `static/`: interface HTML, CSS e JavaScript; não há build nem backend.
- `static/config.js`: ambientes, caminhos dos diagnósticos e aliases das fontes remotas.
- `scripts/gsi/`: parser, exportação operacional, geração de figuras e suporte à abertura local.
- `scripts/export_site.py`: exporta a interface de um commit para uma pasta de entrega e registra sua versão.
- `docs/`: operação, migração e versionamento.

Os produtos de `static/data/smna-fn/` e `static/data/smna-fc/` são gerados pelo cron e **não fazem parte do Git**, assim como logs, auditorias e ambientes Python. O repositório não contém dados de exemplo ou resultados sintéticos. Por HTTP(S), os diagnósticos são carregados diretamente da origem operacional no CPTEC, configurada em `static/config.js`. O clone não precisa conter esses produtos para consultar a origem remota.

## Abrir localmente

```bash
git clone https://github.com/GAD-DIMNT-CPTEC/SMNAMonitorStatic.git
cd SMNAMonitorStatic
python3 -m http.server 8000 --directory static
```

Acesse http://localhost:8000/; por padrão, os diagnósticos consultam o CPTEC e precisam de internet. Para abertura direta por file://, coloque os conjuntos existentes em `static/data/smna-fn/` e `static/data/smna-fc/`. Cada pasta contém `index.json`, CSVs, `cycles/`, `plots/` e, opcionalmente, `local/`.

Para abertura direta, execute `prepare_local.py` para cada ambiente e abra `ABRIR_SITE.html`. As demais abas consultam o servidor CPTEC e precisam de internet.

## Processamento

Python 3.10 ou superior; o parser usa a biblioteca padrão e as figuras requerem as dependências:

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/gsi/requirements.txt
.venv/bin/python scripts/gsi/operational.py --help
```

O exportador exige `--environment SMNA-FNCEP` ou `--environment SMNA-FINPE`, com entrada, saída e cache separados. O gerador obtém o nome do ambiente no índice. Veja [operação](scripts/gsi/OPERACIONAL.md) e o [dicionário de dados](scripts/gsi/DATA_DICTIONARY.md).

## Manter a versão local e a instalada alinhadas

Trabalhe neste repositório, registre as mudanças em commits e exporte sempre um commit conhecido. Evite editar diretamente a cópia servida. A exportação inclui `version.json` com o commit completo e os hashes dos arquivos; não inclui nem apaga os dados operacionais.

```bash
git pull --ff-only
python3 scripts/export_site.py --output /CAMINHO/DA/ENTREGA
```

Use uma pasta de entrega separada do clone e do servidor. A instalação dessa entrega é manual; veja [versionamento e atualização](docs/VERSIONAMENTO.md). Não há workflow de deploy nem agendamento instalado pelo repositório.

A documentação da interpretação científica também está na aba **Sobre**. O [guia de migração](docs/MIGRACAO.md) registra a consolidação das duas cópias anteriores, suas limitações e a cobertura do pacote local que originou este código.

## Nomes e identificação da página

A interface usa SMNA-FNCEP e SMNA-FINPE. Os IDs/pastas `smna-fn` e `smna-fc` permanecem estáveis para preservar as instalações e o cron. Os nomes anteriores são aceitos como aliases de entrada pelos parsers e para leitura dos índices, mas novas exportações e figuras usam os nomes atuais. Imagens históricas não são regeneradas automaticamente: texto gravado nelas pode manter a nomenclatura anterior.

O rodapé mostra a versão `2026.09.16.2`. Em uma cópia direta do código, essa é a identificação da release; não é uma declaração de que a cópia está sem modificações. Ao executar `scripts/export_site.py`, a entrega passa a mostrar também a hash exata do commit exportado, com link para o GitHub, tanto por HTTP quanto por file://. O arquivo version.json continua oferecendo os hashes para detectar alterações posteriores.

## Origem operacional dos diagnósticos

A página pode ser instalada em `SMNAMonitorStatic/static/`, enquanto os dados continuam em:

```text
https://dataserver.cptec.inpe.br/dataserver_dimnt/das/carlos.bastarz/sandbox/SMNAMonitoringApp/online/static/data/
```

Em HTTP(S), `GSI_BASE` em config.js usa esse endereço absoluto. Os dois ambientes apontam para suas subpastas smna-fn/ e smna-fc/; índices, dados de ciclos, imagens e downloads seguem a mesma origem. O cron existente pode continuar publicando lá. Não é necessário copiar dados para a nova página nem regenerar figuras. Para consultar produtos locais por HTTP, altere explicitamente GSI_BASE para `data/` na configuração de teste. Por file://, essa seleção local já é automática.

Após atualizar o código no host, recarregue a página ignorando o cache. O index.html desta release renova os identificadores de cache dos recursos. O servidor de dados precisa manter acesso público e CORS para leitura dos JSONs a partir de outros domínios. A configuração MIME de WebP é independente: o Apache deve enviar Content-Type: image/webp para que “Abrir imagem original” funcione corretamente.
