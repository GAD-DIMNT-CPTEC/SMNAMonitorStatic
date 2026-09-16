# SMNAMonitorStatic

Dashboard estática de monitoramento da assimilação de dados do CPTEC/INPE. Uma única página apresenta **SMNA-FN** e **SMNA-FC**, com dados separados e uma única cópia dos scripts de processamento.

## Organização

- `static/`: interface HTML, CSS e JavaScript; não há build nem backend.
- `static/config.js`: ambientes, caminhos dos diagnósticos e aliases das fontes remotas.
- `scripts/gsi/`: parser, exportação operacional, geração de figuras e suporte à abertura local.
- `scripts/export_site.py`: exporta a interface de um commit para uma pasta de entrega e registra sua versão.
- `docs/`: operação, migração e versionamento.

Os produtos de `static/data/smna-fn/` e `static/data/smna-fc/` são gerados pelo cron e **não fazem parte do Git**, assim como logs, auditorias e ambientes Python. O repositório não contém dados de exemplo ou resultados sintéticos. Após clonar, os diagnósticos ficam indisponíveis até copiar ou gerar esses produtos.

## Abrir localmente

```bash
git clone https://github.com/GAD-DIMNT-CPTEC/SMNAMonitorStatic.git
cd SMNAMonitorStatic
python3 -m http.server 8000 --directory static
```

Acesse http://localhost:8000/. Para os diagnósticos, coloque os conjuntos existentes em `static/data/smna-fn/` e `static/data/smna-fc/`. Cada pasta contém `index.json`, CSVs, `cycles/`, `plots/` e, opcionalmente, `local/`.

Para abertura direta, execute `prepare_local.py` para cada ambiente e abra `ABRIR_SITE.html`. As demais abas consultam o servidor CPTEC e precisam de internet.

## Processamento

Python 3.10 ou superior; o parser usa a biblioteca padrão e as figuras requerem as dependências:

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/gsi/requirements.txt
.venv/bin/python scripts/gsi/operational.py --help
```

O exportador exige `--environment SMNA-FN` ou `--environment SMNA-FC`, com entrada, saída e cache separados. O gerador obtém o nome do ambiente no índice. Veja [operação](scripts/gsi/OPERACIONAL.md) e o [dicionário de dados](scripts/gsi/DATA_DICTIONARY.md).

## Manter a versão local e a instalada alinhadas

Trabalhe neste repositório, registre as mudanças em commits e exporte sempre um commit conhecido. Evite editar diretamente a cópia servida. A exportação inclui `version.json` com o commit completo e os hashes dos arquivos; não inclui nem apaga os dados operacionais.

```bash
git pull --ff-only
python3 scripts/export_site.py --output /CAMINHO/DA/ENTREGA
```

Use uma pasta de entrega separada do clone e do servidor. A instalação dessa entrega é manual; veja [versionamento e atualização](docs/VERSIONAMENTO.md). Não há workflow de deploy nem agendamento instalado pelo repositório.

A documentação da interpretação científica também está na aba **Sobre**. O [guia de migração](docs/MIGRACAO.md) registra a consolidação das duas cópias anteriores, suas limitações e a cobertura do pacote local que originou este código.
