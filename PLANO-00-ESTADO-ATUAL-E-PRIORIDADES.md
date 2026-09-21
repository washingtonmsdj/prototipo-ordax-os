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
PORTABLE_V3_UPDATE_ACTIVATION=PASS_SOURCE_ONE_SHOT_PENDING_CI_PROOF
PORTABLE_V3_UPDATE_ROLLBACK=PASS_SOURCE_REJECTED_SHA_PENDING_CI_PROOF
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

A consolidação USB-only da antiga PR #357 já foi integrada à `main`. Depois dela, o source avançou: o Portable v2 possui PID1 candidato conectado, verificação offline, Stable Base e runtime gráfico separado por conteúdo; o Creator também possui writer Portable v2 interno/tagged para o layout final `ORDAX-ESP + ORDAX-DATA`. A ativação Portable v3 agora também está conectada em source sobre o **mesmo estado ext4 existente**, sem duplicar A/B nem criar symlink no exFAT: `prepare -> candidate one-shot -> cold-health -> commit/rollback`, com `rejected` persistente para não repetir um SHA ruim. Há provas descartáveis baseline do handoff runtime-v3 anterior; a **nova transação de update desta frente ainda precisa da prova CI do head correspondente** antes de virar PASS de boot/update. O estado das provas deve ser lido nos contratos de evidência, sem transformar prova histórica em afirmação sobre um head novo.

A falha histórica `ORDAX-ESP partition not found` de um head antigo foi superada e não é uma pendência atual. Não voltar a habilitar flags BusyBox, aumentar timeouts ou criar rotas alternativas por causa daquele log sem primeiro reproduzir a falha no source e CI atuais.

O que permanece aberto é de outra classe: trust canônico, autorização pública de escrita, boot físico Stable/MVP no USB final, Secure Boot e validação gráfica integrada em hardware. Se um contrato de evidência ficar atrás do source, reconciliar a evidência com o último commit realmente provado; não reconstruir o handoff que já existe.

### P0 — trust canônico de release

A infraestrutura para cerimônia, promoção do trust público, verificação e recuperação já existe no repositório. O bloqueio não deve ser “resolvido” gerando uma chave privada dentro do Git, CI ou USB.

O próximo marco é uma cerimônia real de operador conforme `docs/RELEASE-TRUST-CEREMONY.md`, com chave privada externa, backup/recovery fora do repositório e promoção **somente do material público/evidência permitida**. Enquanto isso, `CANONICAL_RELEASE_TRUST=PENDING_CANONICAL_KEY` continua correto.

### P0 — prova Stable/MVP integrada

Com o handoff Portable v2 implementado e a transação de update Portable v3 agora conectada em source, o próximo fechamento técnico é provar esse ciclo em mídia descartável: canal assinado -> materialização v3 -> arm one-shot -> reboot -> cold-health -> commit e também candidato falho -> rejected -> rollback offline. Depois disso, o fechamento canônico continua sendo trust real + publicação autorizada + prova física do USB final. Não reaproveitar evidência Owner/Development como se fosse prova de produto.

As provas baseline de QEMU direto e UEFI/OVMF reduzem o risco do boot candidato, mas continuam sendo prova descartável. A prova runtime-v3 do head corrente só é PASS quando os contratos de evidência desse head forem promovidos a partir do workflow correspondente. CI, Web candidate e USB de desenvolvimento não substituem `CANONICAL_NOTEBOOK_UEFI_BOOT`, `CANONICAL_STABLE_GRAPHICAL_MODE`, Secure Boot nem outras provas físicas canônicas pendentes.

### P0 — smoke físico da Surface

Executar o runbook source-controlled no notebook em uma única sessão técnica: gerar `tour.json` via `tour-template`, coletar baseline, realizar o tour funcional, coletar pós-tour, gerar `comparison.json` e encerrar com `finalize`. A sessão só pode ser promovida quando `final.json` tiver `FAIL=0`; não preencher manualmente PASS fora do checklist estruturado nem reutilizar comparação stale/editada.

### P1 — lacunas locais reais, sem expandir produto prematuramente

Depois dos P0, priorizar somente lacunas suportadas por necessidade concreta: comandos manuais do atualizador quando houver autoridade real; inventário/armazenamento além das métricas atuais quando houver contrato; recuperação local por perfil; lixeira/associações de arquivo; e melhorias de acessibilidade/continuidade ainda comprovadamente ausentes.

Identidade/cloud, colaboração, planos, app store e expansões semelhantes não devem deslocar os gates de sistema do MVP.

### Recorte do legado `novo-ordax-os` para o MVP USB-only

Os planos longos registram capacidades herdadas como referência de produto, mas a decisão posterior do MVP mudou a prioridade. Para o MVP público atual, interpretar a matriz C01–C27 assim:

| Capacidade do plano legado | Decisão para o MVP | Estado/ação atual |
|---|---|---|
| C01 Arquivos | **ENTRA no núcleo do MVP** | Operações locais principais já existem. Fechar somente falhas reais de uso/smoke; lixeira, miniaturas e associações avançadas não bloqueiam lançamento. |
| C02 Rede/Wi-Fi | **ENTRA e é requisito do MVP** | Ajustes → Rede e painel rápido existem; falta prova Stable/MVP no hardware-alvo e correção somente de gaps reproduzidos. |
| C03 Sessão local / lock | **ENTRA apenas no recorte local de segurança** | Não introduzir conta cloud para resolver lock. Se lock/unlock for exposto no MVP, precisa de autoridade local real; não deve deslocar os P0 de USB/trust. |
| C04 Workspace/projetos | **JÁ HÁ recorte suficiente; não é gate** | Áreas, janelas, Recentes e catálogo local de Projetos existem. Continuidade avançada fica posterior. |
| C05 Checkpoints de sessão | **PÓS-MVP** | Não bloquear o lançamento por restauração completa de rota/documento/posição/rascunho. |
| C06 Home contextual | **NÃO BLOQUEIA** | Melhorias de “continuar trabalho” são P1/P2; não criar outro shell. |
| C07 Hardware/compatibilidade | **ENTRA no recorte de suporte** | MVP precisa hardware suportado documentado e diagnóstico suficiente; inventário sofisticado de periféricos é posterior. |
| C08 Conta de produto | **CONDICIONAL ao portal público** | Login/cadastro só pode ser ativado com identidade/sessão reais. Dispositivos vinculados, planos e continuidade não bloqueiam o USB. |
| C09 Sync cloud | **PÓS-MVP** | Core local pode permanecer; não implementar transporte cloud para fechar o lançamento. |
| C10 Mobile | **PÓS-MVP** | Em breve; depende de conta/sync reais. |
| C11 Desktop instalado / Creator | **Creator ENTRA; Desktop instalado NÃO** | Creator USB é P0. Instalação permanente/desktop Native continua pós-MVP. |
| C12 Apps instaláveis/SDK | **PÓS-MVP** | Apps first-party atuais bastam para o MVP; package manager geral não é gate. |
| C13 Store | **PÓS-MVP** | Não deslocar P0/P1. |
| C14 Perfis profissionais | **PÓS-MVP** | Fora do lançamento básico. |
| C15 Objetos/proveniência de produto | **PÓS-MVP** | Fora do lançamento básico. |
| C16 IA nativa | **PÓS-MVP** | Não criar dependência de IA para o sistema funcionar. |
| C17 Conectores/automações | **PÓS-MVP** | Fora do lançamento básico. |
| C18 Diagnóstico/exportação | **ENTRA no recorte local útil** | Revisão/exportação sanitizada já existe; evoluir somente lacunas concretas de fonte/retenção/prova. |
| C19 Controle remoto | **PÓS-MVP** | Rescue/observação existentes não viram controle remoto genérico. |
| C20 Update/health/rollback | **ENTRA e é gate do MVP** | Canal oficial sem Git e transação Portable one-shot já estão conectados em source; falta fechar prova CI do ciclo novo e depois known-good/rollback no USB Stable/MVP físico. |
| C21 Instalação/storage/recovery | **USB/recovery ENTRA; Native NÃO** | Layout Portable, persistência e recovery do USB são MVP; instalação em SSD/NVMe/HD permanece desativada. |
| C22 Build/cache/retenção | **ENGENHARIA, não feature do MVP** | Otimizar CI quando medido; não recompilar kernel por mudança administrativa sem dependência real. |
| C23/C24 Intelligence/Lab/federação | **PÓS-MVP** | Fora da trilha de lançamento. |
| C25 Navegador/produtividade | **Internet básico ENTRA; office/editor amplo NÃO** | O app Internet é parte dos apps principais do MVP; suíte de produtividade completa não é gate. |
| C26 Onboarding/notificações/acessibilidade | **ENTRA no básico de produto** | Acessibilidade real já avançou; primeiro uso e notificações só entram quando sustentados por contratos reais. |
| C27 Backup/histórico pessoal | **PÓS-MVP** | Não confundir backup de dados com rollback/known-good do sistema, que é P0. |

Portanto, do legado, os itens que ainda merecem atenção **antes do MVP** são principalmente: C02 no hardware real, C07 no recorte de compatibilidade suportada, C18 somente onde houver gap real, C20, C21 no caminho USB/recovery e o recorte básico de C26. C01/C04 já possuem implementação suficiente para não serem reconstruídos. C08 só sobe de prioridade quando identidade real for habilitada no portal. O restante não deve atrasar o primeiro Stable/MVP USB.

## 3. Regra para trabalho paralelo

A `main` é a linha de integração e a fonte de verdade do desenvolvimento. Nesta fase, evitar proliferação de branches e PRs:

1. manter **no máximo uma branch ativa por frente** e, preferencialmente, **uma PR aberta por vez**;
2. não abrir nova branch para cada correção pequena do mesmo incremento;
3. agrupar mudanças relacionadas antes de disparar CI, evitando uma nova rodada pesada para cada microajuste;
4. mudanças somente documentais ou claramente isoladas/não destrutivas podem ir direto para `main` quando não houver colisão e a política do repositório permitir;
5. mudanças de trust, boot, storage, updater, contratos canônicos, writer físico ou outros limites de segurança continuam usando uma branch curta + revisão/gates proporcionais;
6. CI deve ser acionado por **dependência real**: mudança em script administrativo não deve recompilar kernel/QEMU se esse script não participa do artefato;
7. após merge, a branch deixa de ser linha de trabalho; não criar uma branch substituta sem necessidade concreta;
8. antes de editar, ler a `main` atual e as PRs abertas, cruzar plano com contrato/source e distinguir `PASS_SOURCE`, `PASS_IN_AGENT_TESTS`, `PASS_PHYSICAL_DEVELOPMENT_USB` e prova física Stable/MVP;
9. após CI/merge, atualizar a afirmação factual correspondente — nunca antecipar resultado.

Se uma frente externa estiver mexendo no mesmo arquivo/owner, prefira outro gap real ou diagnóstico independente em vez de produzir uma segunda implementação.

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