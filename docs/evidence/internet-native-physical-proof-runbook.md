# Internet Native — runbook de prova física

Status: **HARNESS IMPLEMENTADO; PROVA FÍSICA AINDA NÃO DECLARADA**

Este runbook fecha a diferença entre os testes de source/CI do app **Internet** e a validação no notebook real. Ele não altera o navegador, não arma update, não grava mídia e não transforma CI em prova física.

## O que o harness prova automaticamente

`system/surface/bin/ordax-internet-proof` executa, dentro do runtime WebKit já ativo, um coletor somente leitura que:

- confirma que há exatamente um `ordax_browser_host.py` ativo com o `--profile-root` canônico;
- confirma o layout persistente do perfil WebKit;
- valida `session.json` como arquivo regular, limitado, schema v1 e modo `0600`;
- registra apenas **quantidade de abas, índice ativo e hashes** — nunca URLs visitadas ou conteúdo de páginas;
- faz probes HTTP **GET-only** no host loopback para confirmar Host exato e rejeição de alias/DNS-rebinding, request-target absoluto, `Origin` estrangeira e `Sec-Fetch-Site: cross-site` nas rotas privilegiadas;
- permite comparar duas coletas no mesmo boot para provar que o browser host reiniciou e que a sessão de abas permaneceu semanticamente idêntica.

A coleta não testa por automação comportamento visual, foco, scroll, touchpad, permissões WebKit ou downloads. Esses itens continuam manuais abaixo.

## Pré-condições

1. para evidência canônica, notebook inicializado pelo **USB Stable/MVP verificado**; Owner/Development permanece somente como escopo de desenvolvimento;
2. Surface gráfica saudável e em execução;
3. no Stable/MVP, o release montado em `/system` contém este harness; no Owner/Development, o checkout correspondente está sincronizado;
4. o wrapper resolve automaticamente o runtime WebKit verificado em `/run/ordax/runtime/native-surface/rootfs` ou o runtime dinâmico de desenvolvimento;
5. nenhuma alteração de kernel, reflash ou escrita física é necessária para o harness.

## Coleta inicial

Abra o **Internet**, carregue pelo menos duas páginas HTTPS públicas, altere a aba ativa e então, no **Stable/MVP canônico**, execute:

```sh
/system/surface/bin/ordax-internet-proof collect \
  --label before-surface-restart \
  --output /var/lib/ordax/internet-proof/before.json
```

Em Owner/Development, o mesmo harness pode ser chamado por `/workspace/ordax/system/surface/bin/ordax-internet-proof`, mas essa prova não deve ser promovida como evidência canônica Stable/MVP.

A saída deve terminar com `FAIL=0`. Um `WARN` sobre `data/cache` só é aceitável antes de o WebKit ter materializado ambos os diretórios; para a prova final, use o Internet primeiro e repita até o perfil existir.

## Prova de persistência após restart da Surface

Reinicie **somente a Surface**, sem reiniciar o notebook. Não altere as abas antes da segunda coleta. Depois execute:

```sh
/system/surface/bin/ordax-internet-proof collect \
  --label after-surface-restart \
  --output /var/lib/ordax/internet-proof/after.json

/system/surface/bin/ordax-internet-proof compare \
  /var/lib/ordax/internet-proof/before.json \
  /var/lib/ordax/internet-proof/after.json \
  --output /var/lib/ordax/internet-proof/compare.json
```

A comparação só passa quando:

- as duas coletas têm o mesmo `boot_id`;
- o PID/start-time do browser host mudou;
- o hash semântico de `session.json` é idêntico;
- a quantidade de abas e o índice ativo são idênticos e há pelo menos uma aba persistida.

Isso comprova persistência da sessão através de **restart da Surface**, não através de reboot completo do sistema.

## Checklist manual obrigatório no notebook

Registrar PASS/FAIL separadamente para os itens que exigem olho/mão humana:

1. Internet abre sem fechar ou alterar Arquivos/Notas/Ajustes/Sistema.
2. Campo de endereço mantém foco de teclado com página já visível.
3. Página HTTPS externa carrega e rola apenas no viewport central.
4. Chrome superior, rail esquerdo e painel de projeto continuam interativos.
5. Nova aba, ativar, fechar, voltar, avançar e recarregar funcionam.
6. Navegação explícita para `127.0.0.1`, `localhost`, IP privado/link-local, nome single-label, `.local` e `.home.arpa` é rejeitada no plano externo.
7. Pedido de permissão de site falha fechado.
8. Tentativa de download não grava arquivo enquanto o contrato de download não existir.
9. Arquivos, Notas, Ajustes, Conta, Sistema, rede, energia e atualização continuam saudáveis depois do uso do Internet.
10. Um restart normal da Surface retorna ao desktop e preserva as abas conforme o `compare` automático.

Subresource/redirect para alvo local não deve ser marcado PASS apenas por inspeção visual. Para a prova final dessa linha, usar uma página remota de teste controlada que tente carregar/redirecionar para um literal não público e registrar a ausência de dispatch conforme o método de evidência definido para o notebook.

## Evidência e privacidade

Os JSONs produzidos podem ser anexados a `docs/evidence/` depois da execução real, desde que revisados antes do commit. Eles não contêm URLs, cookies, HTML, histórico do site ou conteúdo de página. Os hashes servem apenas para comparar a mesma sessão e o mesmo log tail sem divulgar o conteúdo.

Não alterar `docs/CURRENT-STATE.md` para `PASS` até existirem, juntos:

- `collect` antes com `FAIL=0`;
- `collect` depois com `FAIL=0`;
- `compare` com `FAIL=0`;
- checklist manual registrado;
- evidência explícita para a tentativa de subresource/redirect local;
- verificação de que os demais apps e o rollback/health continuam saudáveis.
