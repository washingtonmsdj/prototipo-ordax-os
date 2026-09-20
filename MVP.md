# MVP — OrdaX

Status: CANÔNICO PARA PLANEJAMENTO DO MVP

Este arquivo define o escopo público do MVP. Leia-o antes de trabalhar em lançamento, pendrive, Creator, site, conta, releases, instalação Native ou monetização.

## 1. Decisão definitiva de escopo

**MVP = execução pelo pendrive.**

No MVP público, o OrdaX funciona exclusivamente como **OrdaX USB**:

```text
site oficial
 -> OrdaX Creator
 -> USB Stable/MVP verificado
 -> boot pelo pendrive
 -> OrdaX em execução diretamente pelo USB
```

O MVP **não oferece instalação permanente** em SSD, NVMe ou HD. Também não oferece dual boot, resize, editor de partições nem qualquer escrita destrutiva em disco interno.

A instalação **OrdaX Native** continua sendo uma direção arquitetural válida. Todo o trabalho técnico já realizado deve ser preservado, testado e evoluído como fundação **pós-MVP**. Preservar a fundação não significa expor a capability ao usuário do MVP.

## 2. Um produto, dois perfis de distribuição

O OrdaX não deve virar dois sistemas nem dois códigos divergentes.

### Owner / Development

- checkout Git local permitido;
- atualização rápida a partir da `main`;
- SHA/commit disponíveis em diagnóstico;
- Git-first USB permitido;
- ferramentas de engenharia e provas Native podem existir;
- não representa a experiência pública.

### Stable / MVP

- não depende de Git operacional;
- recebe somente releases oficiais verificadas;
- Creator é o caminho normal para criar o USB;
- **modo de execução público: USB**;
- **instalação Native: desativada e inacessível**;
- **escrita destrutiva em disco interno: proibida**;
- conhecido-bom, health e rollback permanecem obrigatórios.

Diferenças pertencem a profile, build, configuração, canal, capability e política — nunca a forks permanentes.

## 3. Atualização

### Owner / Development

```text
main
 -> pull/sync de desenvolvimento
 -> componente afetado
 -> hot apply quando possível
 -> Base candidata quando necessário
 -> health
 -> promoção ou fallback
```

### Stable / MVP

```text
canal oficial OrdaX
 -> release autorizada
 -> verificação criptográfica/integridade
 -> staging
 -> ativação controlada
 -> health
 -> promoção
 -> rollback automático se falhar
```

Stable/MVP não usa Git como canal de atualização do usuário.

## 4. Versões de componentes

Não fingir que todos os componentes receberam a mesma versão quando somente um mudou.

```text
OrdaX Base       0.9.x
Surface          0.8.x
Internet         0.5.x
Notas            0.4.x
Arquivos         0.3.x
Ajustes          0.3.x
Creator          0.2.x
```

## 5. Definição prática do MVP

Um usuário deve conseguir:

1. chegar à landing pública em `/`;
2. obter o Creator/release pública autorizada;
3. preparar o USB sem terminal, ISO manual, Git ou particionamento;
4. inicializar hardware oficialmente suportado pelo pendrive;
5. chegar à Surface e **usar o sistema diretamente pelo USB**;
6. conectar à rede;
7. usar Arquivos, Notas, Internet, Ajustes e Sistema;
8. atualizar por canal oficial;
9. recuperar automaticamente de atualização defeituosa;
10. acessar login/cadastro quando identidade real estiver habilitada;
11. usar `/conta/` como área autenticada separada da landing.

## 6. Gates do MVP público

Bloqueiam lançamento:

- trust/release signing real;
- Creator físico promovido e autorizado **para criação do USB**;
- payload final verificável;
- known-good/fallback suficientemente provados;
- primeiro USB canônico Stable/MVP;
- boot USB -> Surface -> rede -> apps;
- uso real sem instalação no disco interno;
- update oficial sem Git;
- recovery/rollback;
- catálogo público fail-closed;
- identidade real antes de ativar login/cadastro;
- privacidade/termos;
- hardware suportado documentado.

**Não bloqueiam o MVP:** instalador Native, boot por SSD/NVMe/HD, dual boot, resize ou particionamento interno.

## 7. Fundação Native pós-MVP

Não apagar, duplicar ou degradar a arquitetura já construída para Native.

Permanecem como fundação pós-MVP:

- contratos de storage Native;
- Creator Core e planners;
- identidade/revalidação de target;
- LUKS2 + Btrfs;
- initramfs Native;
- kernel compartilhado com pré-requisitos Native;
- boot entries e ESP Native;
- provas descartáveis de storage/runtime/ESP;
- brokers/adapters de descoberta;
- testes e provenance.

No perfil Stable/MVP:

```text
native-install-capability = disabled
internal-disk-destructive-write = forbidden
native-install-ui = absent
native-install-api-token = absent
```

A reativação futura exige promoção explícita pós-MVP e novos gates de produto/hardware.

## 8. Pendrive e Creator

### USB Owner / Development

- Git-first;
- diagnóstico/recovery de engenharia;
- não é release pública.

### USB Stable / MVP

- gerado por Creator/release autorizada;
- sem Git operacional;
- manifest/hash/provenance;
- conhecido-bom e recovery;
- usuário não manipula partições ou terminal;
- é um **modo de produto utilizável**, não mídia de instalação.

### Fluxo público obrigatório

```text
site oficial
 -> baixar OrdaX Creator
 -> conectar USB
 -> Creator seleciona release Stable autorizada
 -> verifica assinatura/hash
 -> pré-materializa a release verificada e o conhecido-bom no USB
 -> prepara e verifica o USB
 -> usuário inicializa pelo USB sem depender da internet para o primeiro boot
 -> usa o OrdaX diretamente pelo pendrive
```

O Creator do MVP prepara mídia removível. Não oferece gravação/instalação em disco interno.

## 9. Site público e rotas

```text
/            -> landing pública
/download/   -> Creator / releases
/login/      -> autenticação
/cadastro/   -> criação de conta
/conta/      -> área autenticada
```

A Surface/área do usuário nunca substitui `/`. OrdaX Web é experiência autenticada futura e separada do portal público.

Landing e Download comunicam MVP USB-only. Instalação permanente só pode aparecer como **futuro/pós-MVP**. Web, Mobile, sync, backup e continuidade ainda indisponíveis podem aparecer apenas como **Em breve**.

## 10. Conta e monetização

No MVP:

- não implementar cobrança;
- não publicar preços;
- não definir tiers comerciais definitivos;
- não impor limite comercial de dispositivos;
- não cobrar arbitrariamente pelo segundo dispositivo;
- conta, quando ativada, é uma identidade única;
- registro de dispositivos/sessões pode existir por segurança e revogação, não como paywall.

A arquitetura continua preparada para dispositivos, sincronização, backup, continuidade PC/Web/Mobile, armazenamento, assinatura/entitlements e serviços premium.

A direção futura de monetização é vender **valor do ecossistema** — sincronização, backup, continuidade, armazenamento, colaboração, compute e serviços — e não transformar quantidade de dispositivos isoladamente no produto vendido.

Nenhuma política de preço, nome de plano, quota comercial ou limite de dispositivos está definida.

## 11. Conta OrdaX

O mínimo futuro da conta pública é criar conta, entrar, sair, recuperar acesso, sessão real, perfil básico e `/conta/`.

`/conta/` permanece fail-closed enquanto identidade/sessão reais não estiverem conectadas. Não simular dados, dispositivos, sync ou assinatura.

Web, Mobile e sincronização aparecem somente como **Em breve** até existirem de verdade.

## 12. Ordem recomendada de lançamento

```text
1. fechar boot-counting/provenance
2. fechar trust de release
3. promover Creator físico para USB
4. gerar primeira mídia Stable/MVP
5. validar boot/recovery USB em hardware suportado
6. validar apps principais
7. fechar canal oficial de update sem Git
8. conectar Conta OrdaX
9. fechar legal/publicação
10. publicar MVP USB-only
```

Native permanece em trilha técnica pós-MVP, sem bloquear a sequência.

## 13. Regras para próximos chats

- sincronize com `main` e PRs antes de editar;
- não duplique trabalho paralelo;
- Stable/MVP público = USB-only;
- preserve fundações Native, mas não as exponha no MVP;
- não introduza escrita destrutiva em disco interno no MVP;
- não introduza Git operacional no Stable/MVP;
- não anuncie recurso futuro como disponível;
- não invente preços, tiers ou limites comerciais;
- preserve gates fail-closed;
- não declare prova física quando houve apenas CI/prova descartável;
- prefira arquitetura a paliativos.

## 14. Referências técnicas

- `docs/CURRENT-STATE.md`;
- `docs/PUBLIC-SITE.md`;
- `docs/PRODUCT-MODES.md`;
- `docs/ACCOUNT-SYNC-AND-PLANS.md`;
- `docs/NATIVE-INSTALLATION.md`;
- `docs/PHYSICAL-MEDIA.md`;
- `docs/contracts/distribution-profiles.json`;
- `docs/contracts/portable-bootstrap-v2.json`;
- `docs/contracts/portable-usb-v2.json`;
- `docs/contracts/portable-boot-handoff.json`;
- `docs/contracts/native-installation.json`;
- `docs/contracts/public-site.json`;
- `docs/contracts/foundation.json`;
- `docs/contracts/sync-model.json`.

Este documento define o **escopo público do MVP**. Os contratos machine-readable continuam autoridade dos invariantes técnicos.
