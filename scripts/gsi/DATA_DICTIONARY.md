# Dicionário dos dados extraídos

Campos comuns: `run_id` distingue execuções; `cycle` é a data/hora de análise no formato YYYYMMDDHH (UTC); `experiment` é fornecido pelo operador; `source` e `line` apontam para o log original. `line_end`, quando presente, delimita o bloco. Nomes de códigos e sensores são preservados, inclusive zeros à esquerda em `type_code` e `subtype`.

| Tabela | Conteúdo e principais colunas | Uso sugerido |
|---|---|---|
| minimization | `outer`, `inner`, `cost`, `gradient`, `step`, `beta`, `step_status` | Convergência, passo e reinicializações do método |
| cost_terms | `outer`, `inner`, `Jb`, `Jo`, `Jc`, `Jl`; aceita `Je` quando impresso | Evolução e composição da função custo |
| reductions | razões de custo e gradiente por ciclo externo e em relação ao início | Comparar convergência entre datas |
| line_search | `diagnostic`, `values`, `raw`, índices interno/externo | Passos candidatos, penalidades, normas e índice de não linearidade |
| solver_vectors | vetor `J`, `b`, `c` ou `EJ`; componente posicional começando em 1 | Depuração detalhada; não atribuir nomes físicos sem mapear a compilação |
| humidity | avaliação, NEG/SUPERSAT, Q/RH, `count`, `rms` | Contagem e intensidade dos diagnósticos de umidade |
| mass | avaliação, `mean_ps`, `mean_pw`, `pdryini` | Derivas entre avaliações e ciclos, em unidade nativa |
| conventional_fit | avaliação, variável, `asm/rej/mon`, tipo, subtipo, faixa, métrica, valor | Perfis de ajuste e estatísticas de observações |
| observation_counts | avaliação, família, `nread`, `nkeep`, `num` | Fluxo de dados por família, respeitando unidades de contagem |
| observation_penalties | família, avaliação, `pen`, `qcpen`, `r`, `qcr` | Penalidades e razões impressas pelo GSI |
| level_penalties | variável, avaliação, nível de modelo, contagem, termos nomeados | Penalidade por nível; não converter nível em hPa sem coordenada vertical |
| qc_events | descrição original de teste/rejeição/extrapolação e valores | Contadores de QC por contexto; não somar categorias possivelmente sobrepostas |
| radiance_config | índice, sensor, `chan`, `var`, `varch_cld`, `use`, `ermax`, `b_rad`, `pg_rad`, flags | Auditoria de satinfo e mudanças de configuração |
| ozone_config | índice, sensor, `lev`, `use`, `pob`, `gross`, `error`, `b_oz`, `pg_oz` | Configuração de ozônio; não significa que houve assimilação |
| bias_coefficients | índice do canal, sensor, posição do coeficiente, valor inicial | Evolução dos coeficientes de correção de viés entre datas |
| radiance_channels | avaliação, sensor, canal, `count`, `qc_rejected`, `signed_error`, vieses, RMS, desvio padrão e penalidade média | Mapas de calor por canal e efeito da correção de viés |
| radiance_summary | avaliação, satélite, instrumento, `nread`, `nkeep`, `nassim`, penalidades e razões | Monitoramento por plataforma/instrumento |
| radiance_qc | avaliação, plataforma, `nobs`, `iland`, `isnoice`, `icoast`, `ireduce`, `ivarl`, `nlgross`, `qc1`…`qc7` | Diagnósticos de seleção/QC; códigos preservados sem inventar causas |
| radiance_totals | avaliação, penalidade total, penalidade com QC e falhas não lineares | Evolução global de radiâncias |
| ozone_totals | avaliação, penalidade total e penalidade com QC | Diagnóstico de ozônio, inclusive zeros explícitos |
| j_table | ciclo externo/interno, nome explícito do termo, valor | Contribuição por família e custo global; “J Global” inclui os termos impressos |
| field_statistics | etapa `guess/analysis/sval/rval`, variável, média/mínimo/máximo e flag de consistência | Inspeção de campos e vetores; não assumir que todos têm unidades físicas diretas |
| configuration | grupo, chave e valor textual impresso | Auditoria de namelist; preserva notação como `48*0` sem expansão |
| resources | métrica, valor, unidade | Tempo de parede, CPU, RSS, I/O e trocas de contexto |
| input_availability | resultado das mensagens `read_obs_check`, texto original | Arquivos previstos mas indisponíveis; não equivale a falha fatal |
| messages | categoria, mensagem e linha seguinte | Alertas MPI, radiâncias e execução, com contexto |
| unparsed | seção e linha original não reconhecida em `fort.*` | Identificar novos formatos antes de generalizar o parser |
| inventory | bytes, SHA-256, linhas, registros | Rastreabilidade e detecção de alterações |
| runs | data, experimento, identificação, marcador de término e recursos | Resumo operacional por execução |

## Semântica essencial

- `evaluation` segue `jiter` das estatísticas: 1, 2 e 3 na amostra. `outer` é o ciclo externo da minimização: 1 e 2. O terceiro diagnóstico não é um terceiro ciclo de minimização.
- `gradient` é a raiz de `gnorm(1)` impressa em `cost,grad`. Na linha de reduções, a última razão é de norma **ao quadrado** em relação ao início; não a confundir com a razão simples do gradiente.
- `cost_terms` pode ter um registro final sem linha correspondente em `minimization`. Não preencher o gradiente final por propagação ou zero.
- `conventional_fit.metric`: count, bias, rms, cpen, qcpen. Nas linhas de ajuste, cpen/qcpen são penalidades normalizadas por contagem, não totais. Os totais `type ... pen=` ficam em tabela separada.
- `type_code=all` é agregado dos tipos/subtipos. `is_total=true` identifica a faixa completa; na amostra 0–2000 hPa. Ela não é uma camada adicional a somar às outras.
- Unidades declaradas: pressão em mb, temperatura em K, vento em m/s, SST em °C. Para GPS, o cabeçalho diz “fractional difference”; a escala específica do diagnóstico não foi convertida nem rotulada como porcentagem.
- Para uv, `num` do resumo vale duas vezes a contagem de vetores usada na tabela de ajuste. `nread`, `nkeep` e `num` podem ter escopos diferentes conforme a família. Não gerar uma taxa universal de assimilação como num/nread.
- Configuração de canal (`use`) e presença de estatística são coisas distintas. O código de referência torna `signed_error` negativo quando `iuse_rad < 1`; a tabela de canais pode incluir monitoramento.
- `bias_uncorrected` corresponde a O–modelo sem correção de viés; `bias_corrected`, RMS e desvio padrão usam O–modelo com correção. `mean_penalty` é a contribuição média impressa. As unidades nativas foram preservadas.
- Contadores de QC não são necessariamente mutuamente exclusivos; `qc1`…`qc7` ficam como códigos até confirmar seus significados na revisão SMNA.
- O RSS é o valor reportado pelo programa em KB; não é a memória total de todos os processos MPI. Os horários textuais de início/fim do programa não informam fuso; o parser não inventa um.

Interpretação baseada nos cabeçalhos dos arquivos e nas rotinas oficiais `dtast`, `statsconv`, `statsrad` e `pcgsoi`, revisão `124138df09f11f892442e2f073085f0d7af0f7a8` do NOAA-EMC/GSI. A identificação dessa revisão documenta a referência consultada, não afirma que ela corresponde ao executável que gerou os logs.
