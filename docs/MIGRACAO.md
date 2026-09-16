# Monitoramento SMNA — interface única

**Registro da entrega local que originou este repositório.** Os dados e figuras descritos abaixo pertencem àquele pacote; não acompanham o clone Git.

Entrega local de 16/09/2026. Não houve deploy. O pacote foi montado a partir das duas cópias locais informadas pelo usuário; as originais não foram alteradas.

## Estrutura

```
SMNAMonitorStatic-unificado/
  ABRIR_SITE.html
  README.md
  scripts/gsi/              # uma única cópia dos scripts
  static/
    index.html             # única página para todos os ambientes
    app.js
    gsi.js
    config.js
    styles.css
    cptec.png
    data/
      smna-fn/             # índice, CSVs, cycles/, plots/, local/
      smna-fc/             # índice, CSVs, cycles/, plots/, local/
```

Abra ABRIR_SITE.html para visualizar os diagnósticos locais. Extraia todo o ZIP. As outras abas precisam de acesso ao servidor CPTEC. A alternativa HTTP é `python3 -m http.server 8000 --directory static` e acesso a http://localhost:8000/#gsi.

O seletor Ambiente troca índices, ciclos, tabelas, galeria e downloads sem navegar para outra página. Os carregamentos locais são identificados por ambiente e ciclo; respostas antigas de uma troca rápida são descartadas. O botão Atualizar disponibilidade relê o índice GSI do ambiente selecionado. Campos Meteorológicos continua mostrando somente SMNA-FN.

## Migração local e hospedagem futura

Esta entrega completa substitui a organização com duas cópias do código. Extraia em uma pasta nova e confira antes de substituir sua organização atual. Na raiz do seu repositório, mantenha apenas uma pasta static/ e uma scripts/ como acima; preserve as cópias anteriores fora da área pública como backup. Não mescle este pacote por cima das duas interfaces antigas, pois isso manteria a duplicação.

Quando decidir publicar, o conteúdo de static/ corresponde diretamente ao diretório online/static/ do servidor. A entrada passa a ser online/static/index.html; os dados ficam em online/static/data/smna-fn/ e online/static/data/smna-fc/. Os endereços antigos não são redirecionados automaticamente. Não há necessidade de manter uma interface por ambiente. Publique recursivamente e preserve as permissões: diretórios 755, arquivos 644, umask 022 na rotina de atualização. Não altere o cron remoto antes de revisar os novos caminhos.

## Configuração e compatibilidade das fontes

config.js contém os IDs smna-fn e smna-fc, os rótulos SMNA-FN e SMNA-FC e os caminhos gsiRoot para cada conjunto. Os nomes antigos foram retirados dos seletores e textos correntes da interface.

O campo sourceKey é um alias técnico dos diretórios já existentes no servidor de origem para Status, Logs, Inventário e imagens meteorológicas. Ele não aparece como nome de ambiente na interface. Esses aliases foram mantidos em um único ponto para não quebrar URLs externas; trocar o nome da interface não renomeia as fontes remotas. Se os diretórios de origem forem reorganizados, altere somente sourceKey em config.js.

## Revisão dos scripts modificados manualmente

As duas versões anteriores diferiam nos nomes fixos do ambiente e nos identificadores das execuções. Agora operational.py exige --environment SMNA-FN ou --environment SMNA-FC. O nome é usado no índice, nos identificadores e na impressão digital do cache. Isso evita reutilizar silenciosamente a extração de outro ambiente. Use diretórios de auditoria e saída diferentes para os dois conjuntos.

plot_operational.py lê o ambiente do index.json e rejeita índices sem um dos dois nomes válidos. O mesmo nome é passado aos títulos do histórico, resumo e galeria. Não existem versões separadas dos scripts por ambiente. prepare_local.py gera carregadores separados por ambiente, permitindo abrir o mesmo ciclo de dois conjuntos sem colisão.

## Atualização pelo cron

Uma única instalação Python atende aos dois conjuntos:

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/gsi/requirements.txt
```

Exemplo para SMNA-FN, a partir da raiz do projeto (no cron, use caminhos absolutos):

```bash
umask 022
.venv/bin/python scripts/gsi/operational.py \
  --environment SMNA-FN \
  --input /CAMINHO/DOS/LOGS/FN \
  --output static/data/smna-fn \
  --audit work/estado/smna-fn/gsi-audit --workers 4

# Somente após avaliar o retorno do exportador; substituir pelas datas necessárias:
.venv/bin/python scripts/gsi/plot_operational.py \
  --data static/data/smna-fn --cycles AAAAMMDDHH
.venv/bin/python scripts/gsi/prepare_local.py --data static/data/smna-fn
```

Para SMNA-FC, use --environment SMNA-FC, a entrada de logs correspondente e saída/auditoria em smna-fc. AAAAMMDDHH é um marcador a substituir, não uma data literal. Se não houver ciclos novos ou alterados, pule a geração. Sem --cycles, o gerador considera todo o índice; o histórico é atualizado mesmo com --cycles. A mudança dos scripts pode invalidar o cache de imagens por horário: escolha os ciclos explicitamente se quiser preservar as figuras históricas.

O novo identificador de versão e o ambiente no fingerprint invalidam o cache antigo na primeira execução. Isso pode reler os logs uma vez, mas não gera figuras automaticamente. Não use --refresh rotineiramente. --limit restringe o índice produzido e não deve ser usado como atualização incremental. O código 2 do exportador informa ciclos com erro; não publique automaticamente uma extração não revisada. O parser ainda não exige marcador de término: o cron deve controlar ciclos em execução. Evite execuções simultâneas e gere os produtos em trabalho antes de publicar uma versão concluída.

## Cobertura e integridade desta entrega

SMNA-FN tem 478 ciclos interpretados, com último ciclo válido 2026091600. SMNA-FC tem 336, com último ciclo válido 2026081112. Os erros presentes nos índices foram preservados; reorganizar a interface não recupera logs ausentes.

Os 336 ciclos válidos comuns possuem tabelas numéricas idênticas nas duas cópias fornecidas. Isso foi conferido após descompressão dos JSONs e não é uma conclusão sobre a procedência científica: revise as entradas e os caches utilizados pelo cron antes de tratar os conjuntos como execuções distintas. Os dados não foram inventados nem corrigidos para criar diferenças.

Os índices e manifestos receberam os novos rótulos. Os carregadores file:// foram refeitos a partir dos índices atuais (478 e 336 ciclos), pois os anteriores estavam desatualizados. Figuras órfãs sem ciclo válido no índice não foram incluídas. Os bytes das imagens referenciadas foram preservados; títulos desenhados dentro das imagens históricas ainda podem trazer a nomenclatura antiga. Remover esse texto interno exige regenerar essas figuras. O código de geração já produz os títulos novos.

A aba Sobre contém a documentação dos arquivos lidos, interpretação numérica, reexecuções, unidades, figuras, cache e limites científicos. Consulte também VALIDACAO.md.
