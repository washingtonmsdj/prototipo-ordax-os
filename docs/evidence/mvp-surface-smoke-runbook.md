# MVP Surface — runbook de smoke test físico

Status: **HARNESS IMPLEMENTADO; PROVA FÍSICA AINDA NÃO DECLARADA**

Este runbook valida, no notebook real, a saúde integrada da **Surface compartilhada** e das capacidades Native necessárias para o recorte funcional do MVP. Ele não muda produto, não grava mídia, não arma update e não substitui os gates de trust/Creator/Stable.

O harness é deliberadamente somente leitura. Ele complementa — não substitui — a prova específica de Internet em `docs/evidence/internet-native-physical-proof-runbook.md`.

## O que o harness verifica automaticamente

`system/surface/bin/ordax-mvp-smoke` executa dentro do runtime WebKit Native já ativo e:

- confirma a presença e registra somente tamanho + SHA-256 das fontes compartilhadas de Arquivos, Notas, Internet, Ajustes, Sistema, composição Native e Surface;
- confirma que o documento Native da Surface responde pelo loopback esperado;
- lê e valida os contratos observacionais de métricas, rede, energia, raiz de Arquivos e histórico de atualização;
- registra apenas resumos limitados dos dados observados;
- verifica o tail do log do host por marcadores `traceback`, `segmentation fault` e `fatal`, armazenando apenas hash e contagem;
- grava um relatório JSON com `PASS/WARN/FAIL` sem executar `POST`, `PUT`, `PATCH` ou `DELETE`.

### Privacidade da evidência

O relatório não inclui:

- nomes de arquivos;
- nomes de interfaces de rede;
- conteúdo de arquivos;
- conteúdo bruto de logs;
- conteúdo de notas;
- URLs/histórico de navegação;
- cookies, tokens ou credenciais.

A listagem de Arquivos é reduzida a contagens. Rede é reduzida a contagem por tipo/estado. A Surface e as fontes são representadas por tamanho/hash quando aplicável.

## Pré-condições

1. notebook inicializado pelo **Owner / Development USB**;
2. Surface gráfica saudável e em execução;
3. checkout sincronizado para a entrega contendo este harness;
4. runtime Native/WebKit já materializado;
5. nenhum reflash, rebuild de kernel ou escrita física é necessário para executar o smoke test.

## Coleta automática inicial

No shell de manutenção Owner/Development, execute:

```sh
/workspace/ordax/system/surface/bin/ordax-mvp-smoke \
  --label mvp-surface-baseline \
  --output /var/lib/ordax/mvp-smoke/baseline.json
```

A saída deve terminar com:

```text
FAIL=0
```

Qualquer `FAIL` precisa ser tratado como evidência de que o recorte integrado ainda não está saudável naquele runtime. Não converter falha em `WARN` apenas para fechar a prova.

## Tour manual obrigatório da Surface

Depois da coleta inicial, registrar PASS/FAIL separadamente para cada item:

1. **Surface:** desktop chega ao estado utilizável; launcher, rail, janelas e troca de apps continuam responsivos.
2. **Arquivos:** abre sem derrubar a Surface, lista a raiz real, navega por ao menos uma pasta e retorna pelo breadcrumb. Se uma mutação de teste for feita, use somente conteúdo descartável do espaço do usuário e remova-o ao final.
3. **Notas:** abre, permite criar/editar uma nota de teste e preserva o conteúdo após uma recarga/reabertura normal da Surface conforme o armazenamento local disponível.
4. **Internet:** abre uma página HTTPS pública e mantém chrome/rail/painel do OrdaX utilizáveis. Para isolamento, persistência de abas e limites de rede, executar também o harness específico `ordax-internet-proof`.
5. **Ajustes:** tema e ao menos uma preferência de acessibilidade suportada mudam a Surface e permanecem coerentes após reabrir a janela.
6. **Sistema:** Visão geral, Atualizações, Armazenamento, Diagnóstico e Sobre abrem sem dados fictícios; métricas/armazenamento exibidos devem ser compatíveis com a coleta automática.
7. **Rede e energia:** estados aparecem somente quando a capacidade correspondente existe. Não executar desligamento/reinício como parte deste smoke test; ações de energia possuem prova própria.
8. **Isolamento de falha:** alternar entre os cinco apps principais não deve encerrar a Surface nem corromper o estado dos demais apps.
9. **Continuidade:** fechar/reabrir janelas e trocar áreas não deve criar duplicação inesperada de estado nem perder o target interno já persistido pelo workspace.
10. **Pós-tour:** nenhum erro fatal visível ou loop de reinício da Surface ocorreu durante o uso.

## Coleta automática após o tour

Sem reiniciar o notebook, execute novamente:

```sh
/workspace/ordax/system/surface/bin/ordax-mvp-smoke \
  --label mvp-surface-after-tour \
  --output /var/lib/ordax/mvp-smoke/after-tour.json
```

A segunda coleta também deve terminar com `FAIL=0`.

A existência de dois relatórios sem falha mostra que os endpoints essenciais e o host continuaram saudáveis antes/depois do uso manual. Ela não prova, sozinha, o comportamento visual de cada app; por isso o checklist manual é obrigatório.

## Evidência mínima para declarar esta prova física

Antes de atualizar qualquer snapshot canônico para PASS, devem existir juntos:

- `baseline.json` revisado com `FAIL=0`;
- checklist manual com resultado explícito por item;
- `after-tour.json` revisado com `FAIL=0`;
- referência ao SHA exato do checkout testado;
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
