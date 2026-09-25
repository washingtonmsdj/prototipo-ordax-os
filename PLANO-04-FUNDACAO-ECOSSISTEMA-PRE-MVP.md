# OrdaX — parte 4: fundação de ecossistema pré-MVP

**Estado:** fundação source/backend implementada; runtime público/comercial ainda desativado.  
**Objetivo:** preparar o primeiro MVP para evoluir para produto gratuito + serviços pagos sem reescrever identidade, Intelligence, apps ou projetos depois do lançamento.

Este plano não adiciona cobrança ao MVP e não reabre instalação Native. Ele adiciona fronteiras que são caras de corrigir depois que contas e dados reais existirem.

## 1. Decisões

### 1.1 Conta e perfis não são a mesma coisa

Uma conta OrdaX representa uma pessoa/identidade. Sobre a conta existem **Spaces**.

```text
Account
  +-- personal space
  +-- work/professional spaces
        +-- projects
        +-- profile packs
        +-- memory
        +-- members
```

O perfil pessoal não é produto premium.

Um perfil profissional passa a ser um **Profile Pack versionado** aplicado a um Space. Um pack pode compor apps, templates, fontes de conhecimento, instruções da Intelligence e capacidades opcionais. Ele não cria outro OS e não concede privilégios por conta própria.

### 1.2 Monetização por valor/capacidade

Templates como Developer, Creator, Business ou Legal não são bloqueados apenas pelo nome da categoria.

A arquitetura de entitlement poderá limitar valor mensurável:

- quantidade de Spaces ativos;
- criação de Spaces compartilhados e número de membros;
- memória/sync/backup cloud;
- retenção/histórico;
- compute de modelos externos;
- conectores e automações;
- suporte e serviços.

O MVP mantém preços, cobrança e nomes comerciais de planos fora de escopo. A política provisória preparada permite até **2 Spaces privados ativos** para a experiência gratuita, mas esse número ainda não é contrato comercial congelado.

### 1.3 Perfil profissional de Advocacia

O futuro pack Legal/Advocacia deve tratar conhecimento como conteúdo versionado e rastreável, nunca como "conhecimento do modelo".

Cada fonte precisa de:

- jurisdição;
- origem/proveniência;
- data/versão;
- classe da fonte;
- política de atualização;
- estado de validade/frescura.

Legislação, atos oficiais, reguladores e tribunais devem preferir fontes oficiais. Documentos do escritório entram apenas por autorização do Space. Resposta de modelo não se torna fonte jurídica.

Isso permite atualizações periódicas do conhecimento sem trocar o runtime do OS nem o modelo.

## 2. Memória da Intelligence

A memória pertence ao OrdaX, não a llama.cpp, OpenAI, xAI ou outro provedor.

```text
Files / Notes / System / Assistant
        |
        v
ordax.intelligence/1
        |
        +-- ordax.memory/1
        +-- context selection
        +-- ordax.model-router/1
              +-- local
              +-- OpenAI
              +-- xAI
              +-- future adapters
```

Escopos iniciais:

- device;
- account;
- space;
- project;
- session.

Memória local funciona sem conta. Cloud memory exige conta, política de sync e entitlement. O usuário deve poder ver, editar e apagar memória persistente. Segredos, tokens, chaves privadas e material de recovery não podem virar memória.

Embeddings são índice derivado e reconstruível. Trocar o modelo de embedding não troca a identidade da memória.

## 3. Model Router

O Local AI continua presente no Stable/MVP.

O novo `ordax.model-router/1` prepara provedores externos sem vazar SDK ou marca para Surface. OpenAI/xAI são adapters futuros; a UI fala com Intelligence.

Um Profile Pack pode recomendar política de modelo, mas não pode:

- enviar dados para cloud silenciosamente;
- acessar outro Space;
- usar credenciais escondidas em prompt;
- conceder tools;
- substituir autorização.

## 4. Store e apps

A Store futura será catálogo/distribuição sobre o runtime de apps, não um segundo updater.

Primeiro contrato:

- manifesto versionado;
- publisher/origem;
- compatibilidade;
- capabilities/permissões solicitadas;
- hash e assinatura;
- atualização transacional;
- rollback de versão funcional;
- remoção de app separada de remoção de dados.

Profile Pack pode depender/recomendar apps, mas nunca contorna assinatura ou concessão de permissões.

Antes de abrir Store pública, provar um app externo pequeno e não privilegiado.

## 5. GPT, Grok, GitHub e OrdaX Device Agent

Não existe um único caminho obrigatório para IA externa.

Para projetos de código, a integração GitHub oferecida diretamente por GPT, Grok
ou outra ferramenta continua sendo uma rota excelente e deve permanecer
first-class:

```text
ChatGPT / Grok
        |
        +-- GitHub connector --> selected repository
```

Ela permite que o usuário aproveite uma assinatura de modelo que já possui sem
tornar uma IDE paga adicional requisito do OrdaX. Esse acesso é independente da
Conta OrdaX e não concede automaticamente Memory privada, arquivos locais ou
controle do dispositivo.

O segundo caminho adiciona capacidades que GitHub sozinho não possui:

```text
ChatGPT / Grok / other MCP client
        |
        | OAuth user authorization
        v
OrdaX Product MCP Gateway
        |
        +-- account/session
        +-- entitlements
        +-- Space membership
        +-- project/device capability grants
        |
        v
OrdaX Action Gateway
        |
        v
OrdaX Device Agent
        |
        +-- local project/files
        +-- Git/GitHub when connected
        +-- Blender adapter
        +-- Unity adapter
        +-- artifacts/evidence
        +-- authorized private project context
```

O runtime incubado historicamente em `washingtonmsdj/mcp-blender` evolui para
**OrdaX Device Agent**. Blender e Unity passam a ser adapters/capabilities, e não
a identidade do produto. A migração deve preservar os entrypoints antigos até
bootstrap/update/recovery estarem comprovadamente migrados.

O usuário autentica **a conta OrdaX** no Product MCP. GitHub é uma conexão
adicional da Conta/Space quando o OrdaX precisa operar repositórios. Para essa
integração própria, a direção é um GitHub App com permissões mínimas e
repositórios selecionados. O token GitHub fica no backend/secret owner do OrdaX e
nunca é entregue ao ChatGPT/Grok.

O usuário pode usar **GitHub direto no GPT/Grok e OrdaX MCP ao mesmo tempo**. Não
devemos forçar um caminho a substituir o outro.

As ferramentas MCP iniciais de produto continuam somente leitura:
- listar Spaces;
- listar projetos;
- ler contexto autorizado;
- pesquisar memória autorizada;
- listar artefatos;
- consultar status/capabilities de dispositivo quando autorizado.

Mutações futuras exigem capability explícita, aprovação, auditoria e escopo de
projeto/dispositivo. Nada de shell genérico.

O **OrdaX Web** não cria um segundo sistema de controle remoto. Ele será outro
cliente do mesmo Action Gateway usado pelo Product MCP e pelo app Projetos.

O Control Plane de desenvolvimento existente não pode reutilizar suas credenciais
administrativas para usuários finais. Podemos reaproveitar padrões de
OAuth/capability/auditoria, mas criamos namespace e autoridade de produto próprios.

## 6. Supabase dedicado

O projeto Supabase `ordax-control-plane` é o alvo dedicado atual. O schema inicial já foi aplicado e validado; login público continua desativado.

A camada de produto precisa permanecer provider-neutral:

```text
Surface
 -> OrdaX account/memory/spaces services
 -> OrdaX gateway
 -> Supabase adapter (current backend)
```

Supabase Auth é provedor, não identidade de domínio.

Schema inicial:

- `ordax_accounts`;
- `ordax_spaces`;
- `ordax_space_members`;
- `ordax_entitlement_grants`;
- `ordax_profile_packs`;
- `ordax_space_profile_packs`;
- `ordax_memory_items`;
- `ordax_memory_embeddings`;
- `ordax_project_connections`.

Todas as tabelas expostas usam RLS. Tokens de GitHub/OpenAI/xAI não entram nessas tabelas públicas.

Mutações de recursos sujeitos a quota/entitlement são **server-authoritative**: cliente autenticado não pode criar/alterar diretamente Spaces, memberships, memória cloud, conexões de projeto, packs ou grants pelo Data API. Isso impede bypass futuro de planos. O backend/gateway OrdaX deverá aplicar quota, entitlement, auditoria e aprovação antes da mutação.

## 7. Sequência

### P0 — antes do MVP público

1. contratos de Spaces/Profile Packs/entitlements — **PASS_SOURCE**;
2. memória provider-neutral — **PASS_SOURCE CONTRACT + BACKEND SCHEMA**;
3. model-router provider-neutral — **PASS_SOURCE**;
4. schema dedicado no `ordax-control-plane` — **PASS_APPLIED**;
5. alvo Supabase dedicado selecionado no gateway/contrato de identidade — **PASS_SOURCE**, login público ainda fail-closed;
6. limites de segurança para MCP de produto — **PASS_SOURCE BOUNDARY**;
7. mutações de produto server-authoritative — **PASS_APPLIED**;
8. manter o primeiro Stable USB e seus gates físicos independentes — **PRESERVADO**.

### P1 — após a fundação, sem bloquear o primeiro USB físico

9. UI mínima de Spaces;
10. memória local real com revisão/apagar;
11. primeiro Profile Pack interno (Developer) ativado como prova;
12. integrar o conceito OrdaX Device Agent ao app Projetos sem torná-lo boot-critical;
13. preservar GitHub como conexão first-class e preparar vínculo Conta/Space -> repositórios selecionados;
14. catálogo de packs consumível pela Surface;
15. primeiro app externo assinado de teste.

### P2 — pós-MVP inicial

16. GitHub App público do OrdaX;
17. Action Gateway read-only para device/project capabilities;
18. Product MCP Gateway para ChatGPT/Grok;
19. OrdaX Web sobre o mesmo Action Gateway;
20. sync/cloud memory completo — **P2**; a primeira fatia segura de continuidade (`appearance`, preferências portáveis e metadata do workspace) já está **PASS_SOURCE Web + Native/USB**, ainda sem disponibilidade pública;
21. compartilhamento de Space;
22. pack Legal/Advocacia com pipeline de fontes oficiais;
23. Store pública;
24. billing/plan bundles.

## 8. Regra de fechamento de escopo

Depois de fechar essas fundações, novas features não entram no primeiro MVP apenas por serem boas ideias. O foco volta para release v4 canônica, primeira mídia Stable física, cold-health, known-good, rollback, recovery, smoke real e publicação.


## Estado incremental de identidade e continuidade

A fundação evoluiu sem tornar conta obrigatória:

```text
PUBLIC_IDENTITY_PASSWORD_FLOW=PASS_SOURCE_ACTIVATION_GATED
ACCOUNT_SYNC_SAFE_STATE_BACKEND=PASS_APPLIED
ACCOUNT_SYNC_WEB=PASS_SOURCE
ACCOUNT_SYNC_NATIVE_USB=PASS_SOURCE_GATEWAY_DEPLOYMENT_PENDING
ACCOUNT_SYNC_PUBLIC_AVAILABILITY=NO
```

A sessão Native fica no dispositivo e não é dado sincronizável. Senhas são entradas transitórias e não entram em estado do OOBE, memória, sync ou Git. A disponibilidade pública continua bloqueada pelos gates de Auth/legal/deployment e pelas provas físicas pertinentes.
