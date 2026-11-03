# Contador de acessos — hits.sh

O rodapé usa diretamente o badge do hits.sh. Não há Worker, banco próprio, autenticação, chave ou configuração de conta a manter.

Identificador único compartilhado por todas as cópias da página:
`gad-dimnt-cptec.github.io/SMNAMonitorStatic`

- Badge: https://hits.sh/gad-dimnt-cptec.github.io/SMNAMonitorStatic.svg
- Estatísticas (ao clicar): https://hits.sh/gad-dimnt-cptec.github.io/SMNAMonitorStatic/
- Documentação oficial: https://github.com/silentsoft/hits

O carregamento da imagem é contabilizado conforme as regras do serviço. É uma contagem de acessos, não uma garantia de pessoas únicas ou histórico de visitas anterior à instalação. Cache, bloqueadores e disponibilidade do serviço podem afetar o resultado. Não há contador de localStorage nem valor fictício ou parâmetro extraCount.

A prévia local também carrega o badge verdadeiro; portanto, testes locais podem entrar na contagem. Trocar abas/ambiente não recria o badge. GitHub Pages e dataserver somarão no mesmo identificador, pois a URL é fixa e não deriva do endereço local.

O badge é uma imagem externa com referrerpolicy=no-referrer. Se falhar, aparece uma mensagem de indisponibilidade, sem bloquear os diagnósticos. `visits.js` trata somente essa falha. O serviço externo recebe a requisição normal da imagem.

Esta entrega é apenas local: sem commit, push ou deploy.
