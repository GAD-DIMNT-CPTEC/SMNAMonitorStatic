# Extração operacional e atualização do site

A nova entrada `operational.py` usa `gsi_parser.Run` para ler somente `fort.*` e `gsi*.log` nos diretórios de ciclo `YYYYMMDDHH` imediatamente abaixo da raiz. Os diagnósticos binários, arquivos de análise e subdiretórios `diag` não são lidos. O parser 1.1.1 aceita expoentes Fortran sem a letra E (por exemplo, `0.21890-302`) e distingue a decoração `***WARNING***` de um campo numérico com overflow. O parser reconhece também a família `q` de `fort.204` e `spd` de `fort.205`.

## Atualização

Execute com Python 3.10 ou superior. O parser usa apenas a biblioteca padrão; a geração de gráficos precisa de matplotlib e numpy, conforme `requirements.txt`. Use o mesmo ambiente Python nos dois comandos.

Execute a partir da raiz do repositório; no cron, use caminhos absolutos:

```bash
umask 022
python3 scripts/gsi/operational.py \
  --environment SMNA-FNCEP \
  --input /CAMINHO/LOGS/FN \
  --output static/data/smna-fn \
  --audit work/estado/smna-fn/gsi-audit --workers 4

# Substitua AAAAMMDDHH pelos ciclos que precisam de figuras.
python3 scripts/gsi/plot_operational.py --data static/data/smna-fn --cycles AAAAMMDDHH
python3 scripts/gsi/prepare_local.py --data static/data/smna-fn
```

Para SMNA-FINPE, troque o ambiente, a entrada e as pastas de saída/auditoria para smna-fc. Não compartilhe caches entre os ambientes. O índice precisa identificar SMNA-FNCEP ou SMNA-FINPE. O exportador inclui o ambiente e as versões dos scripts no fingerprint; a primeira atualização após migração pode reler logs antigos. Isso não gera figuras automaticamente.

Sem `--cycles`, o gerador considera todos os ciclos; o cache de figuras depende das datas dos dados e scripts, portanto uma atualização de código pode provocar regeneração. O histórico é gerado mesmo com uma seleção de ciclos. `prepare_local.py` apenas empacota dados existentes e não gera figuras.

`--limit 2` só deve ser usado em outra pasta de saída para testes: ele cria um índice restrito, não uma atualização incremental. Não execute os passos seguintes cegamente quando o parser retorna código 2; reveja ciclos com erro. O cron deve controlar ciclos ainda em execução, pois o parser não exige marcador de término.

O processamento usa quatro processos por padrão, cada qual mantém um ciclo por vez em memória. `--workers 1` reduz a simultaneidade; o máximo é oito. JSONs compactos de cada ciclo são gravados individualmente, sem acumular todos os vetores e coeficientes do arquivo operacional na memória. O navegador baixa somente o índice, um JSON por seleção e o gráfico escolhido. Python e matplotlib não rodam no site.

A auditoria local contém tamanho, SHA-256, contagem de linhas e identificação dos arquivos processados. O cache compara nomes, tamanhos, datas de modificação e versões do parser/exportador; `--refresh` força nova leitura. Não execute duas atualizações simultaneamente no mesmo diretório de saída. Os dados devem ser gerados em uma cópia de trabalho e publicados juntos após a geração dos gráficos. Não aponte diretamente para um diretório servido em produção enquanto a atualização estiver em andamento.

## Saídas

- `index.json`: ciclos, horário UTC da extração e indicadores resumidos.
- `cycles/YYYYMMDDHH.json.gz`: minimização, termos de custo, ajustes agregados, perfis por pressão, contagens, radiâncias, canais, umidade, massa, estatísticas de campos, contribuições nomeadas de custo (`j_table`) e avisos.
- `cycles.csv`: resumo de todas as datas encontradas.
- `fits.csv`: contagens, RMS, bias e penalidades por variável, uso e avaliação.
- `plots/history.png`: evolução no tempo, com interrupção nas lacunas maiores que seis horas.
- `plots/YYYYMMDDHH.png`: custo/gradiente com ciclos externos em sequência no eixo de iterações acumuladas (transição tracejada), RMS normalizado pelo inicial e contagens finais.
- Diretório de auditoria: inventários e avisos por ciclo, mantidos fora do site.

Para obter todas as tabelas detalhadas de uma data, incluindo vetores e coeficientes de bias, continue usando `gsi_parser.py --input DIRETORIO_DO_CICLO --output DESTINO`. O exportador operacional oferece uma seleção menor para o site, não substitui a exportação científica completa.

## Critérios e limites

Um ciclo interpretado não significa que a execução terminou normalmente: esse indicador depende do marcador explícito do stdout. Um erro de leitura ou data conflitante é registrado como erro daquele ciclo. Quando há reexecuções, o exportador operacional só escolhe um stdout se houver um único candidato com a sequência completa de minimização idêntica à de fort.220 e modificação até 600 segundos após esse arquivo. A seleção e os logs excluídos ficam registrados. Sem correspondência única, o ciclo continua marcado como erro. A entrada científica gsi_parser.py mantém a rejeição de múltiplos stdout por padrão. O comando retorna 2 se algum ciclo não foi interpretado; os demais permanecem disponíveis. Avisos de conteúdo não impedem a extração.

O custo final usa a soma do último `costterms` quando disponível. O último gradiente pode pertencer à iteração anterior. Totais `all` de 0–2000 hPa são usados apenas como agregados e não somados com as faixas de pressão. As avaliações inicial e final podem usar amostras diferentes; sua comparação não mede desempenho contra dados independentes. Valores ausentes são nulos, não zeros.

Linhas não reconhecidas são contabilizadas por arquivo. Nos ciclos recentes, há conteúdo auxiliar em `fort.208`, `fort.217`, `fort.237` e mensagens de QC em `fort.204` que permanecem fora das tabelas estruturadas. Os avisos de média fora do intervalo min/max preservam os valores originais e não significam automaticamente uma falha do modelo.

Esta atualização não instala agendamento nem publica automaticamente novos ciclos. Depois da exportação e geração, publique novamente os arquivos estáticos pelo procedimento habitual do site.

## Galeria completa por ciclo

`plot_operational.py` usa também `plot_diagnostics.py`; mantenha ambos ao lado de `gsi_parser.py`. Além do resumo e histórico, gera `plots/YYYYMMDDHH/figures.json` e até nove imagens WebP sem perdas: minimização detalhada, ajuste RMS nativo, uso/rejeição/monitoramento, perfis verticais, contagens finais, radiâncias por plataforma, canais, massa/umidade e contribuições iniciais de custo. O manifesto contém somente figuras com dados disponíveis. O site oferece essas opções no seletor lateral e abre cada imagem no mesmo pop-up dos campos meteorológicos. Ao trocar de ciclo, preserva o tipo de gráfico quando disponível.

A exportação 1.2.0-op3 invalida o cache anterior para incluir `j_table`. Os mesmos dois comandos de atualização regeneram a galeria, sem etapas manuais adicionais. Imagens e manifesto são regenerados quando mudam os dados ou scripts de gráficos. Não publique antes de ambos os comandos terminarem e conferir os ciclos com erro.

As figuras detalhadas usam WebP sem perdas para manter o pacote de hospedagem abaixo do limite de tamanho. A conversão preserva os pixels; o resumo e o histórico continuam em PNG. A galeria científica independente mantém PNG e SVG.

Os dados por ciclo são publicados em JSON gzip (`.json.gz`), sem perda de conteúdo. O navegador descomprime apenas o ciclo selecionado usando DecompressionStream. O parser e o gerador de gráficos leem/escrevem esse formato automaticamente. Os CSVs continuam disponíveis sem compressão.
