# MVP Surface — runbook de smoke test físico

Status: **HARNESS IMPLEMENTADO; PROVA FÍSICA AINDA NÃO DECLARADA**

Este runbook valida, no notebook real, a saúde integrada da **Surface compartilhada** e das capacidades Native necessárias para o recorte funcional do MVP. Ele não muda produto, não grava mídia, não arma update e não substitui os gates de trust/Creator/Stable.

O harness é deliberadamente somente leitura. Ele complementa — não substitui — a prova específica de Internet em `docs/evidence/internet-native-physical-proof-runbook.md`. O mesmo coletor pode ser usado em Owner/Development e Stable/MVP, mas cada relatório grava o perfil/runtime observado e comparações entre escopos diferentes falham fechado. Somente `evidence_scope=canonical-stable-mvp` sobre `verified-erofs-overlay` pode compor a evidência canônica Stable/MVP.

## O que o harness verifica automaticamente

`system/surface/bin/ordax-mvp-smoke` executa dentro do runtime WebKit Native já ativo e:

- confirma a presença e registra somente tamanho + SHA-256 das fontes compartilhadas de Arquivos, Notas, Internet, Ajustes, Sistema, composição Native e Surface;
- confirma que o documento Native da Surface responde pelo loopback esperado;
- lê e valida os contratos observacionais de métricas, rede, energia, layout do teclado físico e raiz de Arquivos; o layout configurado precisa estar realmente aplicado, sem restart pendente;
- lê e valida por `GET` o estado vivo do atualizador e o histórico de atualização, sem confirmar health nem disparar qualquer ação;
- registra apenas resumos limitados dos dados observados;
- verifica o tail do log do host por marcadores `traceback`, `segmentation fault` e `fatal`, armazenando apenas hash e contagem;
- grava um relatório JSON com `PASS/WARN/FAIL` sem executar `POST`, `PUT`, `PATCH` ou `DELETE`;
- compara baseline e pós-tour de forma fail-closed para confirmar que pertencem ao mesmo boot, às mesmas fontes e à mesma identidade técnica sanitizada do updater.

### Privacidade da evidência

O relatório não inclui:

- nomes de arquivos;
- nomes de interfaces de rede;
- conteúdo de arquivos;
- conteúdo bruto de logs;
- conteúdo de notas;
- URLs/histórico de navegação;
- token de health ou texto bruto de diagnóstico do atualizador;
- SHAs operacionais brutos de source/target/rejeição do atualizador;
- cookies, tokens ou credenciais.

A listagem de Arquivos é reduzida a contagens. Rede é reduzida a contagem por tipo/estado. O estado do atualizador é reduzido a fase/modo/Entrega, flags de presença e uma impressão SHA-256 da identidade de source, sem preservar o SHA bruto nem o token de health. A Surface e as fontes são representadas por tamanho/hash quando aplicável.

O relatório de comparação não copia `boot_id`, hashes de fontes ou a impressão do updater para a saída. Ele registra apenas o resultado de igualdade/consistência entre as duas coletas.

## Pré-condições

1. para evidência canônica, notebook inicializado pelo **USB Stable/MVP** e Surface em `verified-erofs-overlay`; Owner/Development continua válido apenas como diagnóstico de desenvolvimento;
2. Surface gráfica saudável e em execução;
3. release Stable/MVP contém este harness em `/system` — não depende de checkout Git;
4. runtime Native/WebKit ativo e o contexto de runtime publicado pela própria Surface em `/run/ordax-surface/runtime-proof-context`;
5. nenhum reflash, rebuild de kernel ou escrita física é realizado pelo smoke test.

## Coleta automática inicial

No shell local do Stable/MVP, execute:

```sh
/system/surface/bin/ordax-mvp-smoke collect \
  --label mvp-surface-baseline \
  --output /var/lib/ordax/mvp-smoke/baseline.json
```

`collect` continua sendo o comando padrão, portanto a forma antiga sem a palavra `collect` também permanece válida.

A saída deve terminar com:

```text
FAIL=0
```

Qualquer `FAIL` precisa ser tratado como evidência de que o recorte integrado ainda não está saudável naquele runtime. Não converter falha em `WARN` apenas para fechar a prova. Para a prova canônica, confirme também no JSON que `evidence_context.evidence_scope` é `canonical-stable-mvp`, `distribution_profile` é `stable-mvp` e `runtime_mode` é `verified-erofs-overlay`.

Para repetir o mesmo diagnóstico no USB Owner/Development, use `/workspace/ordax/system/surface/bin/ordax-mvp-smoke`. Esses relatórios ficam marcados como `development` e **não** fecham o gate Stable/MVP.

## Tour manual obrigatório da Surface

Antes do tour, gere o checklist machine-readable da mesma sessão:

```sh
/system/surface/bin/ordax-mvp-smoke tour-template \
  --label mvp-surface-tour \
  --output /var/lib/ordax/mvp-smoke/tour.json
```

O template nasce com todos os itens em `pending` e, portanto, **não pode** fechar a prova. Durante o tour, alterar somente o campo `status` de cada item para `pass` ou `fail`. O schema rejeita campos livres/notas para não carregar conteúdo privado acidentalmente para a evidência.

Depois da coleta inicial, registrar PASS/FAIL separadamente para cada item:

1. **Surface:** desktop chega ao estado utilizável; launcher, rail, janelas e troca de apps continuam responsivos.
2. **Arquivos:** abre sem derrubar a Surface, lista a raiz real, navega por ao menos uma pasta e retorna pelo breadcrumb. Se uma mutação de teste for feita, use somente conteúdo descartável do espaço do usuário e remova-o ao final.
3. **Notas:** abre, permite criar/editar uma nota de teste e preserva o conteúdo após uma recarga/reabertura normal da Surface conforme o armazenamento local disponível.
4. **Internet:** abre uma página HTTPS pública e mantém chrome/rail/painel do OrdaX utilizáveis. Para isolamento, persistência de abas e limites de rede, executar também o harness específico `ordax-internet-proof`.
5. **Ajustes:** tema e ao menos uma preferência de acessibilidade suportada mudam a Surface e permanecem coerentes após reabrir a janela. Em **Idioma e região**, confirme que o layout físico aparece como **Em uso** (não “Próximo início”) e digite ao menos uma tecla/caractere que diferencie o layout selecionado, além de pontuação comum, para validar o teclado real.
6. **Sistema:** Visão geral, Atualizações, Armazenamento, Diagnóstico e Sobre abrem sem dados fictícios; métricas/armazenamento e estado de atualização exibidos devem ser compatíveis com a coleta automática.
7. **Rede e energia:** estados aparecem somente quando a capacidade correspondente existe. Não executar desligamento/reinício como parte deste smoke test; ações de energia possuem prova própria.
8. **Isolamento de falha:** alternar entre os cinco apps principais não deve encerrar a Surface nem corromper o estado dos demais apps.
9. **Continuidade:** fechar/reabrir janelas e trocar áreas não deve criar duplicação inesperada de estado nem perder o target interno já persistido pelo workspace.
10. **Pós-tour:** nenhum erro fatal visível ou loop de reinício da Surface ocorreu durante o uso.

## Coleta automática após o tour

Sem reiniciar o notebook, execute novamente:

```sh
/system/surface/bin/ordax-mvp-smoke collect \
  --label mvp-surface-after-tour \
  --output /var/lib/ordax/mvp-smoke/after-tour.json
```

A segunda coleta também deve terminar com `FAIL=0`.

A existência de dois relatórios sem falha mostra que os endpoints essenciais, o estado observacional do atualizador e o host estavam saudáveis nas duas observações. Ela não prova, sozinha, que as observações pertencem ao mesmo estado técnico; por isso a comparação abaixo é obrigatória.

## Comparação automática baseline x pós-tour

Depois das duas coletas, ainda sem reiniciar ou atualizar deliberadamente o notebook, execute:

```sh
/system/surface/bin/ordax-mvp-smoke compare \
  --label mvp-surface-same-session \
  --baseline /var/lib/ordax/mvp-smoke/baseline.json \
  --after /var/lib/ordax/mvp-smoke/after-tour.json \
  --output /var/lib/ordax/mvp-smoke/comparison.json
```

A comparação deve terminar com:

```text
FAIL=0
```

Ela falha se qualquer coleta já contiver `FAIL`, se os `boot_id` forem diferentes/ausentes, se as fontes obrigatórias mudarem, se a identidade sanitizada do source do updater mudar ou se a Surface não estiver alinhada ao source nas duas observações. Isso impede juntar acidentalmente evidências de boots, checkouts ou atualizações diferentes em uma única prova física.

Uma atualização automática que ocorra entre baseline e pós-tour também invalida esta execução do smoke integrado. Nesse caso, iniciar uma nova sequência baseline -> tour -> pós-tour -> comparação sobre o estado já estabilizado, em vez de reinterpretar as duas sessões como equivalentes.

## Finalização fail-closed da sessão

Depois que `comparison.json` estiver em PASS e os 10 itens de `tour.json` tiverem sido revisados, finalize a sessão:

```sh
/system/surface/bin/ordax-mvp-smoke finalize \
  --label mvp-surface-final \
  --baseline /var/lib/ordax/mvp-smoke/baseline.json \
  --after /var/lib/ordax/mvp-smoke/after-tour.json \
  --comparison /var/lib/ordax/mvp-smoke/comparison.json \
  --checklist /var/lib/ordax/mvp-smoke/tour.json \
  --output /var/lib/ordax/mvp-smoke/final.json
```

`finalize` não confia cegamente no arquivo de comparação: ele recalcula baseline x pós-tour e exige equivalência semântica com `comparison.json`. Também exige exatamente os 10 ids de tour, todos em `pass`. Um item pendente/falho, comparação editada/stale ou qualquer FAIL automático produz `FAIL>0`.

O relatório final não copia `boot_id`, hashes das fontes nem a identidade sanitizada do updater. Ele registra explicitamente `physical_write=false` e `reboot_required=false`.

## Evidência mínima para declarar esta prova física

Antes de atualizar qualquer snapshot canônico para PASS, devem existir juntos:

- `baseline.json` revisado com `FAIL=0`;
- checklist manual com resultado explícito por item;
- `after-tour.json` revisado com `FAIL=0`;
- `comparison.json` revisado com `FAIL=0`;
- `tour.json` com exatamente os 10 itens em `pass`;
- `final.json` revisado com `FAIL=0`;
- `evidence_context` dos relatórios/final igual a `stable-mvp + verified-erofs-overlay + canonical-stable-mvp` quando a afirmação for canônica;
- referência ao SHA exato da release Stable/MVP testada;
- confirmação `PHYSICAL_WRITE=NO` e `REBOOT_REQUIRED=NO` para esta operação;
- quando Internet fizer parte da afirmação de isolamento/persistência, evidência do runbook específico de Internet.

Os JSONs podem ser preservados em `docs/evidence/` somente depois de revisão humana de privacidade.

## O que este smoke test NÃO fecha

Mesmo com todos os itens acima em PASS, ele **não** declara:

- canonical release trust resolvido;
- Creator público autorizado;
- escrita física Stable/MVP autorizada;
- boot do primeiro USB Stable canônico;
- rollback/recovery físico canônico concluído;
- instalação Native em disco interno;
- Conta OrdaX real;
- áudio, suspend/resume, aceleração gráfica ou cobertura de hardware ampla;
- promoção do repositório de protótipo para produto oficial.

Esses itens continuam governados por `MVP.md`, `docs/PROMOTION-GATES.md` e pelos contratos machine-readable correspondentes.
