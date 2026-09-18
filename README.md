# SMNAMonitorStatic

Dashboard estática de monitoramento da assimilação de dados do CPTEC/INPE. Uma única página apresenta **SMNA-FNCEP** e **SMNA-FINPE**, com dados separados e uma única cópia dos scripts de processamento.

## Organização

- `static/`: interface HTML, CSS e JavaScript; não há build nem backend.
- `static/config.js`: ambientes, caminhos dos diagnósticos e aliases das fontes remotas.
- `scripts/gsi/`: parser, exportação operacional, geração de figuras e suporte à abertura local.
- `scripts/export_site.py`: exporta a interface de um commit para uma pasta de entrega e registra sua versão.
- `docs/`: operação, migração e versionamento.

Os produtos de `static/data/smna-fncep/` e `static/data/smna-finpe/` são gerados pelo cron e **não fazem parte do Git**, assim como logs, auditorias e ambientes Python. O repositório não contém dados de exemplo ou resultados sintéticos. Por HTTP(S), os diagnósticos são carregados diretamente da origem operacional no CPTEC, configurada em `static/config.js`. O clone não precisa conter esses produtos para consultar a origem remota.

## Abrir localmente

```bash
git clone https://github.com/GAD-DIMNT-CPTEC/SMNAMonitorStatic.git
cd SMNAMonitorStatic
python3 -m http.server 8000 --directory static
```

Acesse http://localhost:8000/; por padrão, os diagnósticos consultam o CPTEC e precisam de internet. Para abertura direta por file://, coloque os conjuntos existentes em `static/data/smna-fncep/` e `static/data/smna-finpe/`. Cada pasta contém `index.json`, CSVs, `cycles/`, `plots/` e, opcionalmente, `local/`.

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

Use uma pasta de entrega separada do clone e do servidor. A instalação dessa entrega no dataserver é manual; veja [versionamento e atualização](docs/VERSIONAMENTO.md). O GitHub Pages é atualizado pelo workflow descrito abaixo. O repositório não instala agendamento de processamento.

A documentação da interpretação científica também está na aba **Sobre**. O [guia de migração](docs/MIGRACAO.md) registra a consolidação das duas cópias anteriores, suas limitações e a cobertura do pacote local que originou este código.

## Nomes e identificação da página

A interface usa SMNA-FNCEP e SMNA-FINPE. Os IDs internos do seletor e dos carregadores locais continuam `smna-fn` e `smna-fc`. As pastas dos produtos agora são `smna-fncep/` e `smna-finpe/`; os nomes das pastas não precisam coincidir com esses IDs. Atualize os caminhos de saída do cron conforme a organização dos produtos. Os nomes anteriores são aceitos como aliases de entrada pelos parsers e para leitura dos índices, mas novas exportações e figuras usam os nomes atuais. Imagens históricas não são regeneradas automaticamente: texto gravado nelas pode manter a nomenclatura anterior.

O rodapé mostra a versão `2026.09.18.3`. Em uma cópia direta do código, essa é a identificação da release; não é uma declaração de que a cópia está sem modificações. Ao executar `scripts/export_site.py`, a entrega passa a mostrar também a hash exata do commit exportado, com link para o GitHub, tanto por HTTP quanto por file://. O arquivo version.json continua oferecendo os hashes para detectar alterações posteriores.

## Origem operacional dos diagnósticos

A página pode ser instalada em `SMNAMonitorStatic/static/`, enquanto os dados continuam em:

```text
https://dataserver.cptec.inpe.br/dataserver_dimnt/das/carlos.bastarz/sandbox/SMNAMonitoringApp/online/static/data/
```

Em HTTP(S), `GSI_BASE` em config.js usa esse endereço absoluto. Os dois ambientes apontam para suas subpastas smna-fncep/ e smna-finpe/; índices, dados de ciclos, imagens e downloads seguem a mesma origem. O cron existente pode continuar publicando lá. Não é necessário copiar dados para a nova página nem regenerar figuras. Para consultar produtos locais por HTTP, altere explicitamente GSI_BASE para `data/` na configuração de teste. Por file://, essa seleção local já é automática.

Após atualizar o código no host, recarregue a página ignorando o cache. O index.html desta release renova os identificadores de cache dos recursos. O servidor de dados precisa manter acesso público e CORS para leitura dos JSONs a partir de outros domínios. A configuração MIME de WebP é independente: o Apache deve enviar Content-Type: image/webp para que “Abrir imagem original” funcione corretamente.

## Origem do Status Operacional e Logs Completos

A configuração separa `logsKey` de `sourceKey`: Status e Logs usam `cron_scripts/logs/smna-fncep/` e `cron_scripts/logs/smna-finpe/`; as imagens meteorológicas mantêm sua fonte existente, e o inventário usa a chave independente inventoryKey. Não altere sourceKey para corrigir somente a tabela de status. O botão Abrir CSV aponta para a origem selecionada mesmo quando há erro, e o aviso exibe o código HTTP. Não há fallback para CSVs antigos de outro diretório.

Na verificação desta correção, os dois novos CSVs retornavam HTTP 403. Além de atualizar o código, o operador deve permitir acesso aos diretórios de logs e leitura dos arquivos públicos no servidor (diretórios 755, arquivos 644). A correção da interface não modifica essas permissões.

## Inventário de observações

`inventoryKey` seleciona `cron_scripts/obsm/smna-fncep/mon_rec_obs_final.csv` ou `cron_scripts/obsm/smna-finpe/mon_rec_obs_final.csv`. O botão “Abrir CSV de origem” permite conferir o arquivo realmente consultado; o download filtrado continua disponível separadamente. A normalização dos registros, as unidades e os filtros não mudaram. Não há fallback para os inventários antigos.

Na verificação desta correção, ambos os CSVs novos retornavam HTTP 403. Verifique no host a permissão de travessia dos diretórios (755) e de leitura dos CSVs públicos (644). Atualizar o código não altera as permissões do servidor.

## GitHub Pages — interface alternativa

Endereço: https://gad-dimnt-cptec.github.io/SMNAMonitorStatic/

O workflow `.github/workflows/pages.yml` exporta o frontend do commit e publica no Pages. Ele executa quando há alterações em `static/`, no exportador ou no próprio workflow na branch `main`. Também pode ser executado manualmente em **Actions → Publish GitHub Pages → Run workflow**, escolhendo `main`. O rodapé e `version.json` identificam o commit publicado.

Esta hospedagem mantém a interface disponível em outro provedor, mas **não espelha os dados operacionais**. Imagens, JSONs e CSVs continuam nos endereços atuais do dataserver. Durante uma indisponibilidade desse servidor, as consultas não carregarão. Quando ele retornar, recarregue a página. O servidor precisa permitir CORS para leitura dos dados pelo domínio do Pages.

A publicação não modifica o dataserver, os parsers, o cron ou as figuras. A mesma exportação funciona na pasta atual do dataserver e no subdiretório do GitHub Pages, pois os recursos da interface usam caminhos relativos e as fontes operacionais usam URLs absolutas. Para ter também os resultados disponíveis durante uma queda, será necessário manter um espelho atualizado dos produtos em uma origem independente.

## Campos meteorológicos — versão 2026.09.18.1

A fonte dos campos FNCEP é `cron_scripts/anls_imgs/egeon/SMNA-FNCEP/`. A pasta do produto foi corrigida de `SMNA` para `SMNA-FNCEP`, mantendo `egeon` como diretório da origem. A mesma construção de caminho atende às listagens de datas, variáveis, níveis e prazos, à imagem, ao pop-up e ao link original. Não há fallback para a pasta antiga. Os caminhos dos diagnósticos GSI permanecem inalterados.

As falhas de carregamento em Status, Diagnósticos GSI, Inventário e Logs usam mensagens em português, sem detalhes técnicos do fetch. O alerta GSI compartilha o estilo do Status Operacional.

## Modo noturno

O seletor no cabeçalho alterna os temas claro e escuro em todas as abas. Na primeira visita, segue a preferência do sistema; depois, lembra a escolha neste navegador. Sem acesso ao armazenamento local, a alternância continua funcionando durante a visita. As figuras científicas mantêm suas cores originais. A preferência é independente entre GitHub Pages, dataserver e abertura local.
