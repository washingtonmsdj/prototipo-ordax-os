# OrdaX — parte 4: fundação de ecossistema pré-MVP

**Estado:** início de implementação em source.  
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

## 5. GPT, Grok e outros clientes através de MCP

O desenho correto não é dar a cada modelo o token GitHub do usuário.

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
        +-- project capability grants
        |
        +-- local OrdaX project source
        +-- GitHub App installation -> selected repositories
```

O usuário autentica **a conta OrdaX** no conector MCP. GitHub é uma conexão adicional da conta/Space.

Para GitHub, a direção é um GitHub App com permissões mínimas e repositórios selecionados. O token GitHub fica no backend/secret owner do OrdaX e nunca é entregue ao ChatGPT/Grok.

As ferramentas MCP iniciais são somente leitura:

- listar Spaces;
- listar projetos;
- ler contexto autorizado;
- pesquisar memória autorizada;
- listar artefatos.

Mutações futuras exigem capability explícita, aprovação, auditoria e escopo de projeto. Nada de shell genérico.

O Control Plane de desenvolvimento existente não pode reutilizar suas credenciais administrativas para usuários finais. Podemos reaproveitar seus padrões de OAuth/capability/auditoria, mas criamos namespace e autoridade de produto próprios.

## 6. Supabase dedicado

O projeto Supabase `ordax-control-plane` é o candidato atual porque está isolado do banco comercial legado.

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
- `ordax_memory_embeddings`.

Todas as tabelas expostas usam RLS. Tokens de GitHub/OpenAI/xAI não entram nessas tabelas públicas.

## 7. Sequência

### P0 — antes do MVP público

1. contratos de Spaces/Profile Packs/entitlements;
2. memória provider-neutral;
3. model-router provider-neutral;
4. schema dedicado no `ordax-control-plane`;
5. identidade Supabase dedicada conectada ao gateway OrdaX;
6. limites de segurança para MCP de produto;
7. manter o primeiro Stable USB e seus gates físicos independentes.

### P1 — após a fundação, sem bloquear o primeiro USB físico

8. UI mínima de Spaces;
9. memória local real com revisão/apagar;
10. primeiro Profile Pack interno (Developer) como prova;
11. catálogo de packs;
12. primeiro app externo assinado de teste.

### P2 — pós-MVP inicial

13. GitHub App público do OrdaX;
14. Product MCP Gateway para ChatGPT/Grok;
15. sync/cloud memory;
16. compartilhamento de Space;
17. pack Legal/Advocacia com pipeline de fontes oficiais;
18. Store pública;
19. billing/plan bundles.

## 8. Regra de fechamento de escopo

Depois de fechar essas fundações, novas features não entram no primeiro MVP apenas por serem boas ideias. O foco volta para release v4 canônica, primeira mídia Stable física, cold-health, known-good, rollback, recovery, smoke real e publicação.
