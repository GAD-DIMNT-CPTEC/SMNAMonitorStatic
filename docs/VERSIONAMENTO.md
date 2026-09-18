# Código versionado e atualização da instalação

## Fluxo de trabalho

1. Trabalhe em um clone deste repositório. Para alterações compartilhadas, crie uma branch, faça commit, envie e abra um pull request.
2. Valide a interface com os dados locais ignorados pelo Git. Confira SMNA-FNCEP e SMNA-FINPE, imagens, tabelas e downloads.
3. Atualize o clone usado para preparar entregas com `git pull --ff-only`. Não mantenha modificações avulsas na pasta servida.
4. Exporte o commit aprovado: `python3 scripts/export_site.py --output /CAMINHO/ENTREGA`. O exportador aceita `--ref COMMIT_OU_TAG`; por padrão usa HEAD. Mudanças não commitadas não entram na exportação. Um arquivo já existente em ENTREGA só é substituído com `--overwrite`.
5. Confira `ENTREGA/version.json`. Seu campo `commit` identifica o código e `files` contém SHA-256 dos arquivos. A revisão dos resultados científicos é separada da versão do frontend.
6. Instale manualmente o conteúdo da entrega na pasta pública. Preserve `data/`. O código e os dados não têm de ser publicados ao mesmo tempo quando o formato não muda. Se a mudança alterar o esquema, prepare e valide os produtos compatíveis antes de ativar a nova versão.

Exemplo de cópia manual, depois da validação:

```bash
rsync -av --chmod=D755,F644 --exclude='/data/' /CAMINHO/ENTREGA/ /CAMINHO/PUBLICO/static/
```

Não use `--delete` nessa pasta, pois ela também contém os produtos do cron. Esse exemplo não fornece uma troca atômica da instalação inteira; para essa garantia, prepare uma pasta de release completa com acesso a data/ e troque o link da versão ativa ao final, conforme a hospedagem suportar.

## Como conferir disparidades

O arquivo público version.json identifica o commit esperado. Além de comparar esse identificador com `git rev-parse HEAD`, compare os hashes: uma edição manual posterior pode deixar o identificador intacto, mas os arquivos diferentes.

No diretório instalado:

```bash
python3 - <<'PYCODE'
import hashlib, json
from pathlib import Path
root = Path('.')
manifest = json.loads((root/'version.json').read_text())
bad = [name for name, digest in manifest['files'].items()
       if not (root/name).is_file()
       or hashlib.sha256((root/name).read_bytes()).hexdigest() != digest]
print('Commit:', manifest['commit'])
print('Arquivos divergentes:', bad)
raise SystemExit(bool(bad))
PYCODE
```

O cron deve usar scripts de uma revisão conhecida do mesmo repositório, com saída e auditoria independentes por ambiente. Atualizar o repositório não executa o parser nem instala arquivos no dataserver. Alterações do frontend enviadas para main acionam a publicação no GitHub Pages.

## Dados fora do Git

A configuração HTTP(S) consulta os produtos operacionais no CPTEC, independentemente da pasta onde a interface é instalada. Para uso offline por file://, copie os produtos atuais para static/data/smna-fncep/ e static/data/smna-finpe/ ou gere-os com os parsers. Não use git add -f para versionar logs, imagens ou auditorias. Os hashes da exportação cobrem somente os arquivos da interface, não os produtos operacionais.

## Nomes e identificação da página

A interface usa SMNA-FNCEP e SMNA-FINPE. Os IDs internos do seletor e dos carregadores locais continuam `smna-fn` e `smna-fc`. As pastas dos produtos agora são `smna-fncep/` e `smna-finpe/`; os nomes das pastas não precisam coincidir com esses IDs. Atualize os caminhos de saída do cron conforme a organização dos produtos. Os nomes anteriores são aceitos como aliases de entrada pelos parsers e para leitura dos índices, mas novas exportações e figuras usam os nomes atuais. Imagens históricas não são regeneradas automaticamente: texto gravado nelas pode manter a nomenclatura anterior.

O rodapé mostra a versão `2026.09.18.2`. Em uma cópia direta do código, essa é a identificação da release; não é uma declaração de que a cópia está sem modificações. Ao executar `scripts/export_site.py`, a entrega passa a mostrar também a hash exata do commit exportado, com link para o GitHub, tanto por HTTP quanto por file://. O arquivo version.json continua oferecendo os hashes para detectar alterações posteriores.

## Novas pastas operacionais — versão 2026.09.17.3

A origem HTTP(S) permanece no CPTEC em SMNAMonitoringApp/online/static/data/, mas os diagnósticos passam a usar exclusivamente smna-fncep/ e smna-finpe/. As pastas antigas smna-fn/ e smna-fc/ não são apagadas nem usadas como fallback. Cada índice determina a cobertura apresentada; não há fusão automática do histórico antigo com os novos resultados.

Por file://, copie os novos conjuntos para static/data/smna-fncep/ e static/data/smna-finpe/ e execute prepare_local.py nessas pastas. O script continua produzindo os IDs internos compatíveis com o seletor. Não é necessário alterar nomes de arquivos das figuras ou executar novamente o parser para aplicar a mudança dos caminhos da página.

## Publicação no GitHub Pages

O workflow `.github/workflows/pages.yml` usa o mesmo `scripts/export_site.py` das entregas manuais. Ele publica somente a interface, sem `static/data/`, com o hash do commit e o manifesto de integridade. A configuração do repositório em **Settings → Pages → Source** deve ser **GitHub Actions**.

Pushes em main que alteram a interface, o exportador ou o workflow disparam o deploy; alterações apenas de documentação não disparam. Para republicar, execute **Actions → Publish GitHub Pages → Run workflow** na branch main. Confira o resultado da execução e o `version.json` no endereço publicado. Para uma reversão, reverta o commit da interface na main e aguarde o workflow.

O endereço alternativo é https://gad-dimnt-cptec.github.io/SMNAMonitorStatic/. Para manter o dataserver na mesma revisão, exporte o commit indicado no Pages com `--ref COMMIT` e instale a entrega manualmente pelo procedimento acima. O workflow nunca acessa nem modifica a instalação no dataserver.

Os dados continuam externos, na origem operacional atual. O Pages não oferece cópia de contingência das figuras ou tabelas; a disponibilidade dos produtos e a liberação de CORS no dataserver continuam necessárias. Não foram incluídos resultados históricos locais como substitutos dos dados atuais.

## Campos meteorológicos — versão 2026.09.18.1

A fonte dos campos FNCEP é `cron_scripts/anls_imgs/egeon/SMNA-FNCEP/`. A pasta do produto foi corrigida de `SMNA` para `SMNA-FNCEP`, mantendo `egeon` como diretório da origem. A mesma construção de caminho atende às listagens de datas, variáveis, níveis e prazos, à imagem, ao pop-up e ao link original. Não há fallback para a pasta antiga. Os caminhos dos diagnósticos GSI permanecem inalterados.
