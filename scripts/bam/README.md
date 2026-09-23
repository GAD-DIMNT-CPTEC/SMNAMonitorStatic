# Diagnósticos BAM: dois ambientes e múltiplas integrações

A aba BAM apresenta produtos pré-calculados de SMNA-FINPE e SMNA-FNCEP, com seleção de integração na barra lateral. Uma página única atende aos dois ambientes; os produtos ficam separados. Nenhum processamento científico ocorre no navegador.

## Instalação no host

Requer Linux, Bash, Python 3.10+ e Matplotlib. Instale as dependências uma vez, fora do cron:

```bash
python3 -m venv /caminho/venv-bam
/caminho/venv-bam/bin/python -m pip install -r /caminho/SMNAMonitorStatic/scripts/bam/requirements.txt
cp /caminho/SMNAMonitorStatic/scripts/bam/bam.env.example /caminho/SMNAMonitorStatic/scripts/bam/bam.env
```

Edite `bam.env`: `BAM_PYTHON` aponta para o Python do ambiente; `BAM_OUTPUT` aponta para `static/bam` da página efetivamente servida; `BAM_CACHE` fica fora do diretório público. Use caminhos absolutos. Se os logs já existem no host, defina `BAM_FINPE_SOURCE` e `BAM_FNCEP_SOURCE` como os diretórios locais `logs/smna-finpe/model` e `logs/smna-fncep/model`. Caso contrário, as duas URLs do dataserver fornecidas são os padrões. Não é necessário editar o Python para mudar essas origens.

Teste manualmente, com o usuário do cron:

```bash
bash /caminho/SMNAMonitorStatic/scripts/bam/run_bam.sh
```

Para chamada direta:

```bash
/caminho/venv-bam/bin/python /caminho/SMNAMonitorStatic/scripts/bam/operational.py \
  --output /caminho/site/static/bam \
  --cache /caminho/privado/bam-cache \
  --smna-finpe /caminho/cron_scripts/logs/smna-finpe/model \
  --smna-fncep /caminho/cron_scripts/logs/smna-fncep/model
```

## Cron

Preferencialmente acrescente `run_bam.sh` ao final do fluxo que coleta os logs, após a coleta bem-sucedida. Alternativamente, este exemplo consulta a cada hora no minuto 20 (horário do cron do host):

```cron
20 * * * * /bin/bash /caminho/SMNAMonitorStatic/scripts/bam/run_bam.sh >> /caminho/logs/update-bam.log 2>&1
```

Crie o diretório de logs antes. O minuto 20 é um exemplo, não uma inferência sobre o término operacional do modelo. O wrapper define diretório de cache Matplotlib, usa `set -euo pipefail`, propaga o código de saída e funciona independentemente do diretório de trabalho do cron. `BAM_CONFIG` permite escolher outro arquivo de configuração.

Códigos: `0` sucesso; `2` houve falha em pelo menos uma origem/log (demais produtos disponíveis são publicados); `3` outro processo mantém o bloqueio do mesmo diretório de saída; outras falhas não tratadas retornam erro. A execução não envia mensagens nem instala crontab.

## Nomes, seleção e atualização incremental

Somente `model_YYYYMMDDHH.YYYYMMDDHH.log` é aceito. O primeiro timestamp deve coincidir com o início de integração declarado no cabeçalho BAM; o segundo deve coincidir com o fim previsto. Não representa necessariamente horário de execução real, download ou tentativa. As datas são validadas. Duas integrações com mesmo início e fins diferentes permanecem selecionáveis.

Por padrão, todos os logs são revisados em cada execução. SHA-256 do conteúdo e dos scripts determina a necessidade de refazer os produtos. Logs idênticos com nomes iguais em ambientes diferentes continuam separados. A presença de todos os produtos também é conferida; figuras ausentes são regeneradas. A coleta HTTP relê os logs para detectar atualizações mesmo quando o nome não muda. O cache armazena os textos usados na geração, sem servir como autoridade para pular coleta.

`BAM_LIMIT=8` ou `--limit 8` verifica somente os oito nomes mais recentes por ambiente; `0` verifica todos. O limite não apaga o histórico anterior. Para revisar ciclos antigos alterados, mantenha `0`.

## Publicação local e falhas

Um bloqueio `flock` no diretório de saída impede duas publicações simultâneas. Cada log alterado é processado em diretório temporário e movido para um caminho novo identificado pelo conteúdo e gerador. O índice é substituído atomicamente somente após os produtos existirem. O navegador carrega `index.js` e depois os dados da integração selecionada. `index.json` é a cópia para ferramentas externas. Os dois índices são substituídos individualmente; cada um referencia apenas snapshots completos.

Falhas HTTP, logs sem cabeçalho e divergências de datas são relatados e não sobrescrevem a última versão válida. O índice registra falhas e a interface avisa quando os produtos foram preservados. Logs com cabeçalho reconhecido, porém ainda em andamento, podem produzir tabelas parciais; a interface distingue término não confirmado. O marcador literal `MODEL EXECUTION ENDS NORMALY` confirma o término. Não se infere sucesso apenas pelo nome do arquivo.

Arquivos novos são `644`, diretórios novos são `755`, inclusive sob cron com umask restritiva. Os diretórios ancestrais também precisam permitir travessia pelo servidor HTTP. Não há exclusão automática de histórico nem de snapshots antigos: isso preserva links de páginas já abertas. Planeje retenção separadamente após definir o período desejado.

## Integração com o site

Distribua a pasta `static/bam/` completa junto à versão atualizada de `static/index.html`, `static/app.js`, `static/bam.js`, `static/config.js` e `static/styles.css`. Não copie somente o índice. A interface usa `SMNA_CONFIG.bamRoot`, por padrão `bam/` relativo ao site. Para uma página no GitHub Pages lendo os produtos do dataserver, configure `bamRoot` com a URL HTTPS completa da pasta BAM publicada; o cron pode permanecer no host de dados. O carregamento utiliza scripts estáticos, sem precisar de `fetch` ou CORS para os catálogos, e as imagens são PNG. Downloads em outra origem dependem do comportamento do navegador. Teste a origem HTTPS configurada antes de publicar.

Com `bamRoot: 'bam/'`, o conjunto completo também pode ser aberto via `static/index.html#bam` diretamente do disco. As requisições assíncronas possuem controle de seleção para não misturar respostas ao trocar ambientes rapidamente. “Atualizar disponibilidade” relê o índice. Nenhum deploy ou push é executado pelos scripts.

## Produtos e interpretação

Cinco PNGs por integração com dados: temperatura, umidade específica, divergência/vorticidade, precipitação e fluxos. Os passos permanecem na tabela/CSV, sem gerar o gráfico removido. Seções sem registros não geram figuras vazias. Seis CSVs e JSON/JavaScript preservam perfis, `AVE`, `LNP`, campos globais, passos e coordenadas híbridas. Configuração, avisos, arquivos de saída, origem e SHA-256 ficam no JSON.

O parser aceita mensagens intercaladas na coordenada híbrida e junta a continuação da unidade de precipitação. `LYR` é índice, não pressão. Valores são preservados nas unidades nativas; as definições de G.M./Z.S./Z.A. fornecidas pelo usuário constam da página. A fronteira híbrida final, com formato diferente, fica em `hybrid_boundary`. Passos de inicialização/reinícios são preservados e não somados como duração total. Precipitação em taxa não é convertida para acumulado. Término normal não é validação física. O log não fornece tempo de parede, memória nem CFL.

`parse_bam.py` permanece disponível para processar um único arquivo; para produzir o catálogo consumido pela página use `operational.py` ou `run_bam.sh`.
