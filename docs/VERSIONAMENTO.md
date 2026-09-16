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

O cron deve usar scripts de uma revisão conhecida do mesmo repositório, com saída e auditoria independentes por ambiente. Atualizar o repositório não executa o parser e não altera automaticamente a página pública.

## Dados fora do Git

Copie os produtos atuais para static/data/smna-fn/ e static/data/smna-fc/ ou gere-os com os parsers. Não use git add -f para versionar logs, imagens ou auditorias. Os hashes da exportação cobrem somente os arquivos da interface, não os produtos operacionais.

## Nomes e identificação da página

A interface usa SMNA-FNCEP e SMNA-FINPE. Os IDs/pastas `smna-fn` e `smna-fc` permanecem estáveis para preservar as instalações e o cron. Os nomes anteriores são aceitos como aliases de entrada pelos parsers e para leitura dos índices, mas novas exportações e figuras usam os nomes atuais. Imagens históricas não são regeneradas automaticamente: texto gravado nelas pode manter a nomenclatura anterior.

O rodapé mostra a versão `2026.09.16.1`. Em uma cópia direta do código, essa é a identificação da release; não é uma declaração de que a cópia está sem modificações. Ao executar `scripts/export_site.py`, a entrega passa a mostrar também a hash exata do commit exportado, com link para o GitHub, tanto por HTTP quanto por file://. O arquivo version.json continua oferecendo os hashes para detectar alterações posteriores.
