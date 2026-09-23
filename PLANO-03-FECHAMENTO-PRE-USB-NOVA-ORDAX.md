# OrdaX — parte 3: fechamento funcional pré-USB da visão Nova OrdaX

**Status:** plano canônico de auditoria pré-USB.  
**Data:** 22/09/2026.  
**Protótipo auditado:** `main@8405feedb05421ea321cc277c0b7b912b6da7117`.  
**Referência Nova OrdaX:** `washingtonmsdj/novo-ordax-os@49fe41fa67d9032f2e349e86592304e64d6c2d88`.

**Continua, sem substituir:**

- `MVP.md`;
- `PLANO-FUNCIONAL-SURFACE-E-APPS.md`;
- `PLANO-02-EVOLUCAO-E-REAPROVEITAMENTO-DO-LEGADO.md`;
- contratos e estado canônicos em `docs/`.

Este documento existe para evitar que uma capacidade estrutural da Nova OrdaX seja
descoberta somente depois da primeira mídia Stable/MVP. A existência de uma
especificação no legado não a torna requisito do MVP; da mesma forma, a existência
de um backend no protótipo não prova que a experiência de sistema correspondente
está integrada.

Nenhuma seção deste plano autoriza escrita física.

---

## 0.1 Progresso após a auditoria

A primeira lacuna P0 já foi atacada na mesma linha arquitetural deste plano:

- composição Native: `ordax.local-ai/1 -> ordax.intelligence/1`;
- descoberta do modelo ativo fica dentro do owner local-AI, não na Surface;
- Notas possui consumidor consultivo de resumo, com contexto bounded + provenance;
- Sistema possui consumidor consultivo de explicação de estado, limitado ao snapshot local permitido;
- nenhum dos consumidores ganha autoridade de mutação ou importa provider/modelo diretamente;
- ausência do backend continua degradável e não crítica para o boot.

Isso fecha `INTELLIGENCE_REAL_SYSTEM_CONSUMER` e o handoff v4 em **source**:
Portable v2 verifica o manifest v4, monta `local-ai-runtime.erofs` read-only e
Stable Base inicia o backend loopback quando o runtime verificado está disponível.
Falha da IA continua degradável e não bloqueia o boot. Permanecem pendentes a
materialização/assinatura Stable v4 real e as provas descartáveis/físicas correspondentes.

### 0.2 Sessão local/lock Native — fechamento em source

O segundo fundamento P0 também foi implementado no recorte pré-USB:

- contrato independente `ordax.local-session/1`;
- capability `session.local-lock` exclusiva do Native;
- conta online/identity continua separada;
- credencial local é opcional no MVP;
- sem credencial, o sistema funciona local/offline e não finge oferecer bloqueio autenticado;
- com credencial, um novo start da Surface inicia bloqueado;
- segredo não entra em `first-run.json`, telemetria ou persistência JS;
- host persiste somente salt + verificador scrypt em arquivo `0600`, com troca atômica;
- tentativas incorretas recebem backoff limitado;
- arquivo de credencial presente ou inválido falha fechado;
- lock preserva Workspace/estado montado e torna a Surface inerte até unlock;
- o escopo é explicitamente sessão, **não criptografia dos arquivos do USB**;
- First Run possui etapa Segurança separada de Conta e Ajustes permite configurar/remover/bloquear depois.

```text
LOCAL_SESSION_LOCK_POLICY=PASS_SOURCE
LOCAL_SESSION_LOCK_IMPLEMENTATION=PASS_SOURCE
LOCAL_SESSION_LOCK_PHYSICAL_PROOF=PENDING
```

### 0.3 Arquivos — remoção segura fechada em source

A jornada cotidiana de Arquivos agora possui remoção recuperável no mesmo owner de
`ordax.file-space/11`:

- `trashEntry()`, `listTrash()` e `restoreTrashEntry()`;
- namespace interno reservado e não navegável pela API pública;
- metadata bounded com caminho lógico original e ID interno aleatório;
- arquivo/pasta no mesmo filesystem vai para a Lixeira por rename no-clobber;
- restauração também é no-clobber e nunca substitui um item criado depois no caminho original;
- symlinks e payloads inválidos falham fechados;
- tentativa cross-device para a Lixeira é rejeitada e preserva a origem;
- Recentes deixa de apontar para o item movido;
- continuidade de Projeto afetada é limpa somente depois de trash confirmado;
- não há exclusão permanente nem “esvaziar Lixeira” no fluxo cotidiano do MVP.

```text
FILES_DAILY_OPERATIONS=PASS_SOURCE
FILES_SAFE_REMOVAL=PASS_SOURCE
FILES_PERMANENT_DELETE_MVP=NO
FILES_TRASH_PHYSICAL_PROOF=PENDING
```

### 0.4 Diagnóstico/Recovery e hardware — fechamento em source

O owner diagnóstico já existente agora é composto na Surface Native, em vez de
permanecer apenas como serviço/teste. Sistema passa a oferecer revisão local explícita
e sanitizada, com cópia/exportação quando os adapters reais estão disponíveis.

Recovery ganhou um observer read-only `ordax.recovery-status/1`, limitado ao
`portable-v2`. Ele lê somente:

- slot/release em execução;
- `current`;
- `known-good`;
- candidato e transação pendente;
- a entrada `ordax-portable-recovery.conf` no ESP, validando os marcadores mínimos.

O observer não possui rollback, reboot, repair, rede automática ou mutação automática.
A matriz conservadora `hardware-support-matrix/1` já fecha a política de suporte em
source, sem promover um único notebook de desenvolvimento a claim amplo de hardware.

```text
DIAGNOSTICS_RECOVERY_PRESENTATION=PASS_SOURCE
RECOVERY_STATUS_AUTHORITY=READ_ONLY
RECOVERY_STATUS_PHYSICAL_PROOF=PENDING_PHYSICAL
SUPPORTED_HARDWARE_MATRIX=PASS_SOURCE
CANONICAL_STABLE_TARGET_HARDWARE_PROOF=PENDING_PHYSICAL
```

## 1. Decisão principal

**Não gerar ainda o primeiro USB Stable/MVP físico.**

Antes, fechar o conjunto **A — obrigatório pré-USB** abaixo ou registrar uma decisão
canônica explícita retirando o item do MVP. O objetivo não é transportar o
`novo-ordax-os` inteiro; é preservar os invariantes de produto que ainda fazem
sentido na arquitetura clean-room atual.

A auditoria já fechou em source três omissões estruturais que estavam abertas quando
este plano foi criado: consumidores reais de Ordax Intelligence, sessão/lock local Native
e remoção recuperável em Arquivos. O HOLD do primeiro USB Stable/MVP continua porque
ainda restam itens A independentes: cobertura de idioma coerente, diagnóstico/recovery
de produto, inventário/matriz mínima de hardware e lifecycle Stable v4 assinado com a
IA local materializável.

Portanto **“boot/release avançado” continua não equivalendo a “produto pré-USB fechado”**.

---

## 2. Três classes de fechamento

### A — obrigatório antes de gerar o primeiro Stable USB

Precisa estar implementado e provado em source/CI antes da escrita física.

1. **Ordax Intelligence realmente composta no produto.**
   - inicializar `ordax.local-ai/1` + `ordax.intelligence/1` na composição Native;
   - expor estado degraded/ready sem bloquear boot;
   - pelo menos dois consumidores first-party reais e somente-leitura, por exemplo:
     - Notas: resumir/explicar conteúdo selecionado com provenance;
     - Sistema/Diagnóstico: explicar um relatório sanitizado;
   - nenhum acesso implícito a arquivo, shell, rede externa, pacote ou disco;
   - contexto sempre bounded e com provenance;
   - engine/modelo continuam substituíveis.

2. **Sessão local/offline e bloqueio do dispositivo.**
   - separar conta online de usuário/sessão local;
   - definir e implementar política Native de lock/unlock;
   - preservar Workspace/janelas/estado suportado ao bloquear;
   - não depender de Supabase, Web ou internet;
   - segredo local não pode entrar em telemetria, first-run state ou Git;
   - decidir e documentar se o MVP permite sessão sem PIN/senha e qual é o comportamento
     de bloqueio nesse caso.

3. **Idiomas oferecidos pelo OOBE coerentes com a Surface.**
   - PT-BR permanece fonte;
   - en-US, es-ES, de-DE e fr-FR já são oferecidos no primeiro uso;
   - antes do USB público, a seleção não pode levar a uma Surface principal
     significativamente misturada com português;
   - ou se completa a cobertura essencial dos cinco idiomas, ou se reduz
     explicitamente a lista oferecida. Não anunciar cobertura falsa.

4. **Arquivos: fechar jornada cotidiana mínima. — PASS_SOURCE**
   - `ordax.file-space/11` mantém list/create/read/rename/copy/move/import/export e preview;
   - remoção segura foi implementada por Lixeira recuperável;
   - restore é no-clobber e não substitui arquivos existentes;
   - namespace interno da Lixeira não é navegável pelo file-space público;
   - delete irreversível/esvaziar não faz parte do fluxo cotidiano do MVP;
   - confinamento à raiz do usuário, limites, colisões e erros tipados permanecem.

5. **OOBE/primeiro uso como fluxo real do produto.**
   - persistência Native/USB do estado;
   - idioma/fuso;
   - rede opcional;
   - continuar sem conta;
   - privacidade;
   - chegada à Surface;
   - teclado com comportamento honesto: o seletor não promete troca imediata se Cage
     exige reinício da Surface;
   - reentrada/reboot não pode refazer indevidamente etapas concluídas.

6. **Diagnóstico e recuperação visíveis e coerentes.**
   - Sistema deve mostrar saúde/update/recovery usando owners existentes;
   - exportação diagnóstica deve permanecer sanitizada;
   - recovery não pode depender da IA;
   - não criar segundo owner de update/recovery.

7. **Inventário mínimo de hardware e matriz de suporte.**
   - declarar hardware oficialmente suportado no MVP;
   - mostrar no Sistema o que o host realmente conhece, sem simular sensores;
   - separar “detectado”, “suportado” e “fisicamente provado”;
   - usar isso como entrada do tour físico do Stable USB.

8. **Release Stable v4 completa.**
   - `system.erofs`;
   - `native-surface-runtime.erofs`;
   - `local-ai-runtime.erofs`;
   - manifest v4 assinado;
   - aquisição/materialização offline exata;
   - handoff de boot preservando o v3 conhecido-bom;
   - IA continua não crítica para o boot.

### B — source deve estar pronto antes; prova final acontece no USB

Esses itens não podem ser “provados fisicamente antes do pendrive”, mas a
implementação e os testes descartáveis devem estar fechados antes da escrita.

- boot UEFI Stable/MVP;
- Wi-Fi real no hardware-alvo, incluindo os tipos de rede que forem oficialmente
  declarados como suportados;
- teclado/mouse;
- relógio/fuso após reboot;
- browser WebKit real;
- áudio, suspend/resume e aceleração gráfica se forem declarados como suportados
  no lançamento;
- Surface smoke completa;
- cold-health e commit do known-good;
- rollback após candidato defeituoso;
- boot offline;
- local AI carregando no hardware real sem impedir o OS se falhar.

### C — pós-MVP consciente

Ficam fora do primeiro USB **por decisão**, não por esquecimento:

- instalação Native em SSD/NVMe/HD;
- dual boot e resize;
- OrdaX Mobile completo;
- OrdaX Desktop como produto instalado (o Creator desktop é outra responsabilidade);
- sync cloud e continuidade entre dispositivos;
- backup cloud;
- Store;
- package manager geral para terceiros;
- SDK público completo;
- perfis profissionais;
- Object System universal/grafo de objetos;
- ferramentas mutáveis de IA;
- Agent Manager;
- memória persistente de IA;
- automações gerais;
- multi-agent coordination;
- Federation / Research Lab / Mission Control;
- controle remoto geral.

Esses itens podem conservar contratos de extensão, mas não devem aumentar o bootstrap
nem criar owners duplicados no MVP.

---

## 3. Reclassificação atual das capacidades C01–C27 do PLANO-02

| ID | Capacidade | Estado no fechamento corrente | Classe pré-USB |
|---|---|---|---|
| C01 | Arquivos | **Fechado para a jornada cotidiana pré-USB em source.** `ordax.file-space/11` acrescenta Lixeira recuperável e restore no-clobber ao fluxo existente. Delete permanente continua deliberadamente fora do MVP. | **PASS_SOURCE; prova física=B** |
| C02 | Wi-Fi cotidiano | **Implementado em source.** scan/connect/disconnect/forget/reconnect e quick panel existem. Cobertura física por tipo de rede continua limitada. | **B** |
| C03 | Sessão local, login, lock/unlock | **Sessão/lock local fechado em source.** `session.local-lock` é Native/offline, independente de conta cloud, usa verificador scrypt e falha fechado. Conta online continua opcional e separada. | **PASS_SOURCE; prova física=B** |
| C04 | Workspace/projeto | **Parcial avançado.** workspace-store v2, áreas/janelas/targets, projetos e recent files existem. | A somente no que sustenta continuidade local |
| C05 | Checkpoint de sessão | **Parcial.** janelas/targets persistem, mas não existe checkpoint genérico de estado interno por app/documento/posição/rascunho. | A mínimo; riqueza pós-MVP |
| C06 | Home contextual/continuar trabalho | **Implementado em recorte útil.** Projetos, Recentes e Pendências existem. | Fechado para MVP |
| C07 | Inventário/suporte de hardware | **Política mínima fechada em source.** `hardware-support-matrix/1` separa driver presente, evidência física e claim de suporte; não generaliza o notebook de desenvolvimento para outras famílias. | **PASS_SOURCE; prova física=B** |
| C08 | Conta/identidade entre modos | **Arquitetura pronta, backend real ainda não ativo.** Conta online é opcional no MVP. | C |
| C09 | Sync/continuidade cloud | **Core offline existe; identity/transport remoto não.** | C |
| C10 | Mobile Companion | **Futuro.** | C |
| C11 | Desktop instalado e Creator | Creator é trilha MVP; Desktop como produto é futuro. | Creator=A/B; Desktop=C |
| C12 | Apps instaláveis/SDK | **Não é requisito do primeiro USB.** | C |
| C13 | Store | **Não implementado e não requerido.** | C |
| C14 | Perfis profissionais | **Visão futura.** | C |
| C15 | Objetos com provenance | **Não existe Object System universal.** Usar metadata/provenance pequenos onde necessários, inclusive IA. | C; provenance mínimo=A |
| C16 | IA nativa/contexto/tools | **IA consultiva fechada em source.** Native compõe `local-ai -> intelligence`; Notas e Sistema possuem consumidores first-party bounded/read-only com provenance. Handoff Stable v4 do backend está `PASS_SOURCE`; materialização assinada e prova física continuam gate de release. Tools mutáveis permanecem deferidas. | **PASS_SOURCE para consumidores; A/P2 para lifecycle v4; C para tools/agents** |
| C17 | Conhecimento/integrações/automações | **Deferido.** | C |
| C18 | Diagnóstico/receipts/captura | **Fechado em source para o MVP.** Controller diagnóstico sanitizado é composto no Native; Sistema prepara/copia/exporta revisão explícita e apresenta recovery Portable v2 read-only sem autoridade de rollback/reboot. | **PASS_SOURCE; prova física=B** |
| C19 | Controle remoto/Companion | Não é requisito do bootstrap/MVP. | C |
| C20 | Update transacional/rollback | **Muito avançado em CI/source.** Falta Stable físico/cold-health. | **B** |
| C21 | Native/durable storage | Native pós-MVP. USB durável é a trilha atual. | USB=A/B; Native=C |
| C22 | Build Intelligence/cache | Build/reprodutibilidade já resolvidos por mecanismos atuais; não portar framework antigo. | Fechado/continuar medindo |
| C23 | Project Intelligence/Mission Control | Visão futura. | C |
| C24 | Federation/Research Lab/agentes de engenharia | Visão futura. | C |
| C25 | Navegador/produtividade | Internet e Notas existem; WebKit Native ainda exige prova física Stable. | **B** |
| C26 | Notificações/acessibilidade/onboarding | Notification Center e OOBE existem; idiomas completos da Surface e alguns gates físicos seguem abertos. | **A/B** |
| C27 | Backup/histórico de dados pessoais | Serviço completo de backup do usuário não existe; não é requisito atual do MVP. Exportação local e recuperação do sistema não equivalem a backup. | C, com export local segura no MVP |

---

## 4. O que a visão Nova OrdaX exige preservar na arquitetura atual

### 4.1 Runtime único e APIs públicas

Não criar um “runtime da IA”, “runtime do app” ou “runtime do sync” com autoridade
paralela. A camada de Intelligence chama serviços através de contratos do produto.

### 4.2 Workspace e Session são diferentes

- Workspace = contexto de trabalho.
- Session = continuidade/autenticação/bloqueio.
- Conta online = identidade de ecossistema.

A Surface atual já possui Workspace; isso não deve ser usado como substituto de
sessão local.

### 4.3 Intelligence é uma camada, inference é um backend

Continuar preservando:

```text
Files / Notes / System / future Assistant
 -> ordax.intelligence/1
 -> ordax.local-ai/1
 -> llama.cpp + model
```

Não permitir:

```text
Notes -> llama.cpp diretamente
Files -> modelo diretamente
Assistant -> owner da Intelligence
```

### 4.4 Contexto não concede autoridade

O MVP pode enviar contexto local sanitizado e proveniente para explicar/resumir.
Isso não concede permissão para executar ações.

O mínimo pré-USB é **contexto consultivo real**; Tool Manager e Capability Bridge
mutáveis continuam pós-MVP.

### 4.5 Observabilidade e degradação

Cada serviço estrutural deve ser capaz de expor pelo menos estado/health útil.
Falha da IA, conta ou rede não pode derrubar a Surface ou bloquear arquivos locais.

---

## 5. Anti-omission gate

Adicionar esta regra à preparação do primeiro Stable USB:

```text
PRE_USB_NOVA_ORDAX_AUDIT=PASS
INTELLIGENCE_REAL_SYSTEM_CONSUMER=PASS
LOCAL_SESSION_LOCK_POLICY=PASS
LOCAL_SESSION_LOCK_IMPLEMENTATION=PASS
OOBE_PERSISTENCE=PASS_SOURCE
OOBE_LOCALE_COVERAGE=PASS_OR_EXPLICITLY_REDUCED
FILES_DAILY_OPERATIONS=PASS_SOURCE
FILES_SAFE_REMOVAL=PASS_SOURCE
DIAGNOSTICS_RECOVERY_PRESENTATION=PASS_SOURCE
SUPPORTED_HARDWARE_MATRIX=PASS
SIGNED_RELEASE_V4_WITH_LOCAL_AI=PASS
PHYSICAL_WRITE=STILL_SEPARATE
```

O gate é de produto/source. Ele **não** substitui:

- trust;
- confirmação destrutiva;
- seleção do USB;
- UAC;
- readback;
- prova física.

---

## 6. Ordem de implementação antes do USB

### P0 — arquitetura esquecida — concluído em source

1. **Intelligence composition + consumidores read-only reais. — PASS_SOURCE**
2. **Sessão local/lock Native. — PASS_SOURCE**
3. **Docs/contratos canônicos reconciliados. — PASS_SOURCE**

### P1 — experiência cotidiana

4. Arquivos: remoção segura/lixeira. — **PASS_SOURCE**
5. Cobertura real de idioma da Surface para os idiomas oferecidos no OOBE. — **IN_PROGRESS**: owner + shell inglês `PASS_SOURCE`; Arquivos cobre jornada primária, formulários comuns, ordenação, exportação e preview em inglês `PASS_SOURCE`; navegação de Ajustes/Sistema, resumo/health, leituras de memória/armazenamento, detalhes/histórico de Atualizações e revisão diagnóstica sanitizada de Sistema, Ajustes → Notificações, Ajustes → Segurança/sessão local, lock screen Native e Conta completa também `PASS_SOURCE`; jornadas primárias de Notas e Internet agora `PASS_SOURCE`; trays + quick panels de rede/bateria e Central de Notificações agora `PASS_SOURCE`; histórico first-party de updates usa apresentação semântica rerenderizável via `ordax.notifications/3`; o painel de rede continua sem persistir credenciais; mensagens operacionais/profundas restantes ainda estão em migração
6. Diagnóstico/recovery em Sistema. — **PASS_SOURCE**: controller diagnóstico Native agora é composto de verdade e Sistema exibe recovery read-only a partir dos marcadores reais de `current`, `known-good`, candidato/transação e entrada local de recovery; prova física continua B
7. Inventário mínimo/suporte de hardware. — **PASS_SOURCE** via `hardware-support-matrix/1`; prova física do hardware-alvo Stable continua B

### P2 — fechar release

8. Handoff v4 com AI real. — **PASS_SOURCE**; materialização/assinatura Stable real ainda pendente.
9. Materialização v4 com bytes reais + assinatura efêmera em CI. — **GATE_IMPLEMENTED_NON_PROMOTIONAL**; assinatura/materialização canônica Stable e regressão QEMU/UEFI v4 continuam pendentes.
10. Somente então voltar ao primeiro USB Stable/MVP físico.

---

## 7. Itens deliberadamente não puxados para o MVP

A análise da Nova OrdaX **não** muda as decisões já tomadas:

- conta online continua opcional;
- cloud/sync não bloqueiam o USB MVP;
- Native em disco continua pós-MVP;
- Store não bloqueia;
- Mobile não bloqueia;
- agentes/tools mutáveis não bloqueiam;
- federação não bloqueia;
- Remote Core/Control Plane não entram por antecipação.

Essa separação é importante: a auditoria serve para encontrar **fundamentos esquecidos**,
não para transformar toda a visão futura em escopo de lançamento.

---

## 8. Critério para voltar ao pendrive

Voltar à missão física somente quando:

1. todos os itens A estiverem PASS em source/CI ou tiverem uma decisão canônica explícita
   retirando-os do MVP;
2. o manifest v4 real estiver assinado/materializável;
3. os testes descartáveis/UEFI relevantes estiverem verdes;
4. documentação canônica e contratos estiverem coerentes;
5. então aplicar novamente os gates físicos já existentes.

Até lá:

```text
FIRST_STABLE_MVP_USB_WRITE=HOLD_FUNCTIONAL_CLOSURE
PHYSICAL_WRITE_AUTHORITY=UNCHANGED
```
