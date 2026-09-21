# OrdaX — estado atual e prioridades de execução

**Status:** overlay factual de execução. **Revisão:** 21/09/2026. **Base:** `main`, sempre revalidada contra contratos e source estruturado; este documento não fixa um SHA como autoridade.

Este arquivo existe para impedir que inventários históricos dos planos longos sejam usados como se fossem o estado atual do repositório. Ele **não substitui a especificação de produto** de `PLANO-FUNCIONAL-SURFACE-E-APPS.md` nem a análise de legado de `PLANO-02-EVOLUCAO-E-REAPROVEITAMENTO-DO-LEGADO.md`. Quando houver divergência sobre **o que já existe, o que já foi provado ou qual é a próxima prioridade**, prevalecem, nesta ordem:

1. contratos e código estruturado do commit atual;
2. `docs/CURRENT-STATE.md` e `docs/PROMOTION-GATES.md`;
3. este overlay de execução;
4. inventários e prioridades históricas dos planos longos.

Antes de implementar qualquer item marcado como ausente em plano anterior, revalidar o source atual. Drift documental não autoriza duplicar serviço, tela, contrato ou fluxo já existente.

## 1. Estado factual que não deve regredir

### Sistema

`Sistema` já possui navegação canônica por **Visão geral**, **Atualizações**, **Armazenamento**, **Diagnóstico** e **Sobre**, com targets internos validados e lifecycle compartilhado. O rodapé e os atalhos devem abrir esses destinos canônicos, não criar telas paralelas.

A apresentação de atualização já separa versão do produto, Entrega, SHA e versões/modos dos componentes. Aplicativos e sistema não devem voltar a compartilhar uma identidade de versão fictícia.

O histórico de atualização já possui porta e apresentação consumível pela UI. A lacuna restante não é “criar histórico do zero”, mas ampliar comandos e informações somente quando houver contrato/autoridade reais.

### Diagnóstico

Diagnóstico já possui fluxo local de **preparar revisão**, indicar fontes incluídas/indisponíveis/falhas, avaliar atualidade da observação, mostrar estado de persistência do journal, **copiar resumo sanitizado** e **salvar/exportar a revisão preparada**. Falha ou cancelamento preserva a revisão para nova tentativa.

Portanto, os planos antigos que dizem que ainda faltam “tela local completa”, “estado de atualidade” ou “exportação revisável” estão obsoletos nesse ponto. O trabalho futuro de diagnóstico deve ser guiado por lacunas concretas de fonte, retenção, política ou prova — não por recriação desse fluxo.

### Arquivos

`ordax.file-space/10` já cobre navegação/listagem, criação de pasta, leitura textual limitada, renomeação, cópia/duplicação, movimento com regras explícitas, importação/exportação, metadados reais, busca/ordenação, Recentes locais, retomada da última pasta validada e catálogo local de Projetos.

Continuam lacunas reais como lixeira/exclusão recuperável, múltiplos itens/diretórios em operações que ainda não suportam isso, associações de “Abrir com”, miniaturas/visualizadores ampliados e outros recursos que exigem contrato próprio. A composição Web não deve fingir um filesystem real quando não houver adapter.

### Ajustes

Tema, contraste, redução de movimento e escala de texto já são preferências reais, validadas e persistidas. **Ajustes → Rede** já é o destino canônico para gerenciamento Wi‑Fi quando o adapter Native está disponível. Notificações também possuem política/store real para as fontes integradas.

Papel de parede arbitrário, idioma completo, periféricos/áudio avançados e outras preferências só entram quando houver capacidade real. Não criar controles cosméticos que não persistem nem alteram o dono correto.

### Conta e sincronização

A UI de Conta já distingue estado de identidade indisponível de capacidades locais e possui visão de sincronização local. O núcleo/fila de sync existente **não prova** conta real, nuvem nem continuidade entre dois dispositivos.

Provedor real de identidade, transporte autenticado, isolamento por conta, perfil, segurança e sessões continuam pendentes e não podem ser simulados.

### Surface e prova física

O harness read-only do smoke integrado existe no source com coleta baseline/pós-tour, checklist machine-readable gerado por `tour-template` e `finalize` fail-closed que recalcula a comparação e exige os 10 itens do tour em PASS. Isso melhora a qualidade da evidência, mas não converte execução pendente em PASS físico.

Estados canônicos que permanecem explícitos em `docs/PROMOTION-GATES.md`:

```text
PORTABLE_V2_PID1_INTEGRATION=PASS_SOURCE
PORTABLE_QEMU_DIRECT_KERNEL_BOOT_BASELINE=PASS_CI_DISPOSABLE
PORTABLE_QEMU_UEFI_BOOT_BASELINE=PASS_CI_DISPOSABLE_OVMF_NON_SECURE_BOOT
PORTABLE_RUNTIME_V3_CURRENT_HEAD_PROOF=SEE_PROOF_CONTRACTS
PORTABLE_PHYSICAL_WRITER=PASS_TAGGED_INTERNAL
PORTABLE_PHYSICAL_USB_BOOT=NO
MVP_SURFACE_SMOKE_HARNESS=PASS_SOURCE
MVP_SURFACE_SMOKE_PHYSICAL=PENDING
CANONICAL_STABLE_GRAPHICAL_MODE=PENDING
CANONICAL_RELEASE_TRUST=PENDING_CANONICAL_KEY
PUBLIC_PHYSICAL_APPLY=NO
```

O USB Owner/Development possui provas físicas próprias; elas não equivalem à promoção Stable/MVP canônica.

## 2. Prioridades atuais do sistema

### P0 — consolidar o Stable/MVP portátil a partir do estado já implementado

A consolidação USB-only da antiga PR #357 já foi integrada à `main`. Depois dela, o source avançou: o Portable v2 possui PID1 candidato conectado, seleção `current -> known-good`, verificação offline, Stable Base e runtime gráfico separado por conteúdo; o Creator também possui writer Portable v2 interno/tagged para o layout final `ORDAX-ESP + ORDAX-DATA`. Há provas descartáveis baseline de boot direto e UEFI/OVMF. O estado da prova runtime-v3 do head atual deve ser lido nos contratos `portable-v2-qemu-boot-proof.json` e `portable-v2-uefi-boot-proof.json`, sem transformar uma prova histórica em afirmação sobre um head ainda não promovido.

A falha histórica `ORDAX-ESP partition not found` de um head antigo foi superada e não é uma pendência atual. Não voltar a habilitar flags BusyBox, aumentar timeouts ou criar rotas alternativas por causa daquele log sem primeiro reproduzir a falha no source e CI atuais.

O que permanece aberto é de outra classe: trust canônico, autorização pública de escrita, boot físico Stable/MVP no USB final, Secure Boot e validação gráfica integrada em hardware. Se um contrato de evidência ficar atrás do source, reconciliar a evidência com o último commit realmente provado; não reconstruir o handoff que já existe.

### P0 — trust canônico de release

A infraestrutura para cerimônia, promoção do trust público, verificação e recuperação já existe no repositório. O bloqueio não deve ser “resolvido” gerando uma chave privada dentro do Git, CI ou USB.

O próximo marco é uma cerimônia real de operador conforme `docs/RELEASE-TRUST-CEREMONY.md`, com chave privada externa, backup/recovery fora do repositório e promoção **somente do material público/evidência permitida**. Enquanto isso, `CANONICAL_RELEASE_TRUST=PENDING_CANONICAL_KEY` continua correto.

### P0 — prova Stable/MVP integrada

Com o handoff Portable v2 já implementado e exercitado em mídia descartável, o próximo fechamento canônico é trust real + publicação autorizada + prova física do USB final. A partir daí, fechar no hardware os gates de aquisição/assinatura/health/rollback do perfil Stable sem reaproveitar evidência Owner/Development como se fosse prova de produto.

As provas baseline de QEMU direto e UEFI/OVMF reduzem o risco do boot candidato, mas continuam sendo prova descartável. A prova runtime-v3 do head corrente só é PASS quando os contratos de evidência desse head forem promovidos a partir do workflow correspondente. CI, Web candidate e USB de desenvolvimento não substituem `CANONICAL_NOTEBOOK_UEFI_BOOT`, `CANONICAL_STABLE_GRAPHICAL_MODE`, Secure Boot nem outras provas físicas canônicas pendentes.

### P0 — smoke físico da Surface

Executar o runbook source-controlled no notebook em uma única sessão técnica: gerar `tour.json` via `tour-template`, coletar baseline, realizar o tour funcional, coletar pós-tour, gerar `comparison.json` e encerrar com `finalize`. A sessão só pode ser promovida quando `final.json` tiver `FAIL=0`; não preencher manualmente PASS fora do checklist estruturado nem reutilizar comparação stale/editada.

### P1 — lacunas locais reais, sem expandir produto prematuramente

Depois dos P0, priorizar somente lacunas suportadas por necessidade concreta: comandos manuais do atualizador quando houver autoridade real; inventário/armazenamento além das métricas atuais quando houver contrato; recuperação local por perfil; lixeira/associações de arquivo; e melhorias de acessibilidade/continuidade ainda comprovadamente ausentes.

Identidade/cloud, colaboração, planos, app store e expansões semelhantes não devem deslocar os gates de sistema do MVP.

## 3. Regra para trabalho paralelo

Antes de abrir uma branch:

1. ler a `main` atual e as PRs abertas;
2. listar arquivos alterados pela frente ativa mais próxima;
3. escolher um incremento que não duplique dono nem colida com branch alheia;
4. cruzar plano com contrato/source antes de chamar algo de “ausente”;
5. distinguir `PASS_SOURCE`, `PASS_IN_AGENT_TESTS`, `PASS_PHYSICAL_DEVELOPMENT_USB` e prova física Stable/MVP;
6. após CI/merge, atualizar a afirmação factual correspondente — nunca antecipar resultado.

Se uma frente externa estiver mexendo no mesmo arquivo/owner, prefira diagnóstico reproduzível, teste independente, documentação factual não conflitante ou outro gap real em vez de produzir uma segunda implementação.

## 4. O que não fazer agora

- Não reconstruir Sistema/Diagnóstico porque um inventário de 18/09 ainda os descreve como incompletos.
- Não reabrir a falha histórica `ORDAX-ESP partition not found` nem a antiga reconciliação da PR #357 sem reprodução no source atual.
- Não criar updater/store de produção para app `git-app`; Git é mecanismo de desenvolvimento, não atualização independente Stable.
- Não transformar prova QEMU ou CI em prova física.
- Não habilitar escrita física/destrutiva para “testar mais rápido”.
- Não colocar chave privada canônica em source, artifact público, CI ou pendrive do produto.
- Não criar forks Web/Native da Surface para resolver diferenças de capacidade.
- Não adicionar botões que impliquem login, nuvem, atualização, recuperação ou hardware quando a operação real não existe.

## 5. Critério para encerrar este overlay

Este arquivo pode ser absorvido ou removido quando os planos longos tiverem seus inventários/status integralmente reconciliados com o source e houver uma proteção equivalente contra drift. Até lá, ele serve como ponte de execução; não é um novo contrato de produto.