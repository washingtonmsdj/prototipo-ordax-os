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

## 3.1 Custodia de assinatura e evolucao

O primeiro proof fisico Stable/MVP pode usar a chave Ed25519 local criada pela ceremonia canonica, desde que a recuperacao criptografada seja verificada e a chave privada continue fora de Git, USB, Actions artifacts e clientes. Isso e uma solucao de bootstrap/prototipo, nao a custodia definitiva do produto.

A arquitetura de assinatura deve permanecer provider-neutral. O backend local (`local-pem`) e permitido para o prototipo e desenvolvimento; um backend gerenciado com chave nao exportavel em KMS/HSM pode ser adotado depois sem alterar o protocolo de verificacao do dispositivo. GitHub e executor/orquestrador e nao custodiante da chave privada.

```text
MANAGED_KMS_HSM_REQUIRED_FOR_FIRST_PHYSICAL_PROOF=NO
LOCAL_PEM_ALLOWED_FOR_CONTROLLED_PROTOTYPE=YES
PRIVATE_KEY_IN_GIT=NO
GITHUB_IS_KEY_CUSTODIAN=NO
SIGNING_BACKEND_PROVIDER_NEUTRAL=YES
SIGNED_TRUST_ROTATION_REQUIRED_BEFORE_BROAD_PUBLIC_DISTRIBUTION=YES
SINGLE_LOST_FILE_OR_HOST_MUST_NOT_PERMANENTLY_BLOCK_UPDATES=YES
```

Antes de distribuicao publica ampla, o OrdaX deve possuir transicao/rotacao de trust assinada e recuperacao redundante suficiente para que a perda de um computador, arquivo ou uma unica chave operacional nao obrigue reprovisionamento em massa. KMS/HSM e uma evolucao de custodia, nao uma dependencia paga obrigatoria para fechar o primeiro proof fisico.

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

A tabela acima é **somente um exemplo de independência de versionamento**, não um snapshot das versões atuais. Valores correntes devem ser lidos dos manifests/owners e de `docs/CURRENT-STATE.md`; exemplos de planejamento nunca devem ser tratados como estado implementado.

A versão geral do produto pode existir, mas deve ser distinguida da versão dos componentes. Ter uma versão própria também não significa, por si só, possuir atualização independente de produção: esse comportamento depende do `releaseMode` e dos gates correspondentes.

## 5. Definição prática do MVP

Um usuário deve conseguir:

1. chegar à landing pública em `/`;
2. obter o Creator/release pública autorizada;
3. preparar o USB sem terminal, ISO manual, Git ou particionamento;
4. inicializar hardware oficialmente suportado pelo pendrive;
5. concluir o primeiro uso Native no próprio USB, escolhendo idioma/fuso, com rede opcional e **conta opcional**;
6. chegar à Surface e **usar o sistema diretamente pelo USB**, inclusive sem conta online;
7. conectar à rede durante o primeiro uso ou posteriormente;
8. usar Arquivos, Notas, Internet, Ajustes e Sistema;
9. ter **Ordax Intelligence** como capacidade do sistema, com inferência local incluída na distribuição Stable/MVP e degradação segura se o backend falhar;
10. atualizar por canal oficial;
11. recuperar automaticamente de atualização defeituosa;
12. acessar login/cadastro somente quando identidade real estiver habilitada;
13. usar `/conta/` como área autenticada separada da landing quando uma sessão real existir.

## 5.1 Fechamento funcional antes do primeiro USB Stable

Antes de materializar/gravar o primeiro USB Stable/MVP físico, executar a auditoria de
`PLANO-03-FECHAMENTO-PRE-USB-NOVA-ORDAX.md`.

O boot/release estar pronto não é suficiente para iniciar a missão física. O gate
pré-USB exige, no mínimo:

- Ordax Intelligence realmente composta no runtime Native e consumida por fluxos
  first-party consultivos, em vez de existir apenas como backend/modelo e teste;
- política e implementação de sessão/bloqueio local/offline separadas da conta cloud;
- OOBE persistente e coerente com idiomas/fuso/rede/modo sem conta;
- jornada cotidiana de Arquivos fechada, com Lixeira recuperável e restauração no-clobber; exclusão permanente não faz parte do fluxo cotidiano do MVP;
- diagnóstico/recovery de produto e inventário mínimo de hardware/suporte;
- release-manifest/4 real com `local-ai-runtime.erofs` assinada/materializável.

Store, Mobile completo, Native em disco, sync cloud, federação, perfis profissionais e
tools/agentes mutáveis de IA permanecem pós-MVP salvo decisão arquitetural posterior.

```text
PRE_USB_NOVA_ORDAX_AUDIT=REQUIRED
FIRST_STABLE_MVP_USB_WRITE=HOLD_UNTIL_FUNCTIONAL_CLOSURE
```

## 6. Gates do MVP público

Bloqueiam lançamento:

- trust/release signing real;
- Creator físico promovido e autorizado **para criação do USB**;
- payload final verificável;
- known-good/fallback suficientemente provados;
- primeiro USB canônico Stable/MVP;
- boot USB -> OOBE/primeiro uso -> Surface -> apps;
- primeiro uso persistente com rota oficial **Continuar sem conta** e rede opcional;
- teclado físico utilizável no layout documentado para o hardware suportado; no MVP PT-BR, ABNT2 é o padrão Native e US é uma alternativa persistente;
- Ordax Intelligence presente como serviço de sistema e payload local de inferência verificável incluído na mídia/release; falha da IA não pode impedir boot/Surface;
- uso real sem instalação no disco interno;
- update oficial sem Git;
- recovery/rollback;
- catálogo público fail-closed;
- identidade real antes de ativar login/cadastro;
- privacidade/termos;
- hardware suportado documentado.

**Não bloqueiam o MVP:** instalador Native, boot por SSD/NVMe/HD, dual boot, resize ou particionamento interno.

O layout do teclado físico é uma capability do host Native, não uma preferência Web. A alteração feita em Ajustes é gravada no USB e aplicada pelo Cage no próximo início da Surface. O seletor não deve aparecer no primeiro uso enquanto não existir uma troca segura na sessão atual ou um handoff gráfico anterior ao compositor.

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

**IA não é um extra selecionável do Creator.** O Stable/MVP inclui Ordax Intelligence e seu backend local verificado como parte do produto. Depois da instalação, modelo, quantização ou engine podem evoluir por atualização governada; isso não equivale a oferecer um checkbox para instalar o OrdaX sem sua camada de Intelligence.

### Estado técnico atual do USB durável v2

O alvo durável do MVP não deve ser confundido com a mídia transitória de três partições usada nas primeiras provas físicas.

```text
MVP target
 -> ORDAX-ESP   FAT32
 -> ORDAX-DATA  exFAT
    -> .ordax/releases/<commit>/system.erofs
    -> .ordax/state/persistent-state.img   # ext4
    -> arquivos do usuário
```

Estado atual do caminho v2:

- storage `ORDAX-ESP + ORDAX-DATA`: prova descartável verde;
- release `system.erofs`: determinística e byte-reprodutível em CI;
- `release-manifest/2`: compatibilidade preservada;
- `release-manifest/3`: generator + signer + verifier + aquisição não-ativante implementados e verdes em CI, com `system.erofs` + `native-surface-runtime.erofs`;
- runtime gráfico v3: armazenamento content-addressed por SHA-256 e reuso de bytes verificados entre releases implementados;
- `release-manifest/4`: caminho de protocolo implementado para acrescentar `local-ai-runtime.erofs`, com binding assinado ao source-lock do engine/modelo e armazenamento da IA por SHA-256 separado do runtime gráfico; o runtime **real** de `llama-server` + Qwen3.5-0.8B-Q4_0 já foi construído duas vezes com bytes idênticos no mesmo job, montado read-only e validado com inferência real tanto no host de CI quanto em Alpine 3.22.5. O engine está pinado por SHA-256/size; a assinatura/materialização Stable v4 e a prova física no USB continuam pendentes, e v4 ainda não substitui o boot v3 fisicamente provado;
- materialização portátil: implementada sem ativação implícita; v4 também permanece não-ativante;
- revalidação offline exata da release assinada: implementada para v2, v3 e para o caminho de protocolo v4;
- mount EROFS + estado ext4 + runtime system read-only: prova descartável verde;
- helper de mount portátil dentro do initramfs: conectado ao PID1 candidato; continua sem autoridade de assinatura/ativação própria;
- estado de ativação `current/known-good/candidate/rejected`: implementado no ext4 persistente;
- transação Portable one-shot: `prepare -> select-boot -> commit/rollback`, com replace atômico + fsync e sem ponteiro mutável no exFAT;
- `candidate` só ganha autoridade de boot quando existe uma transação armada; recebe **uma tentativa** e nunca substitui `current` antes do cold-health;
- SHA rejeitado fica persistido e não é rearmado enquanto o canal oficial não avançar para outro commit;
- o supervisor Stable já orquestra `inspect -> materialize-portable-v3 -> verify-portable-v3-exact -> arm -> reboot -> cold-health -> commit/rollback` na `main`; o baseline exato QEMU direct-kernel + OVMF/UEFI passou em `c8c8fe526d03ced7630420cd116dd954b08ef03a`, e a prova dedicada no source `837a99733654943f08a400d6cc3fb28bf84605f8` passou o caminho de falha `previous -> candidate one-shot -> previous + rejected`; cold-health commit e USB físico continuam separados;
- bootstrap capsule EROFS: determinística, reprodutível, pinada e verificada pelo PID1 candidato;
- Stable Base EROFS: Alpine e conjunto APK transitivo pinados; handoff QEMU/UEFI v2-base já provado em CI, prova física ainda pendente;
- runtime gráfico offline: lock exato de 253 pacotes e EROFS byte-reprodutível provados em CI; handoff v3, preseed Creator e launcher Stable offline já implementados no candidato atual;
- Stable/MVP não instala nem atualiza o runtime gráfico via `apk add` durante o boot; o runtime assinado usa EROFS read-only + OverlayFS efêmero em `/run`;
- handoff do runtime v3 em QEMU direct-kernel e OVMF/UEFI: **revalidado regressivamente como PASS no commit atual da main** `c8c8fe526d03ced7630420cd116dd954b08ef03a` pelo run `35598937763`, com rede desabilitada e sem tocar mídia física;
- essa prova confirma release v3 + runtime offline + Stable Init, mas **não** declara a Surface gráfica completa em hardware real;
- writer físico Portable: implementado apenas no backend interno/tagged e continua inacessível ao Creator público;
- boot físico Stable/MVP v2/v3: não provado;
- Secure Boot: não provado;
- canonical release trust público: pendente;
- Native continua fora do MVP.

A mídia transitória atual continua apenas como caminho de validação de hardware. A prova QEMU/UEFI do runtime v3 já está fechada; não habilitar o writer público antes de **trust canônico, autorização física separada e prova física do USB Stable/MVP**.

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

A conta OrdaX é **opcional para usar o sistema operacional**. O primeiro uso deve oferecer uma rota explícita **Continuar sem conta**, preservando Arquivos, Notas, Internet, Ajustes, atualizações e preferências locais no USB.

O mínimo futuro da conta pública é criar conta, entrar, sair, recuperar acesso, sessão real, perfil básico e `/conta/`. Entrar/Criar conta no OOBE são capability-driven: ficam inativos enquanto nenhum provedor real estiver conectado e nunca bloqueiam a conclusão local do primeiro uso.

`/conta/` permanece fail-closed enquanto identidade/sessão reais não estiverem conectadas. Não simular dados, dispositivos, sync ou assinatura.

Conta online e PIN/senha local do dispositivo são responsabilidades diferentes. Web, Mobile, backup e sincronização aparecem somente como **Em breve** até existirem de verdade; sincronização cloud não é requisito para o MVP USB.

## 11.1 Idiomas do lançamento

O primeiro uso Native oferece **pt-BR, en-US, es-ES, de-DE e fr-FR**. Essa cobertura é do OOBE; não chamar inglês, espanhol, alemão ou francês de “Surface completa” enquanto telas/apps ainda tiverem texto fixo em português. A prioridade de migração do restante do produto é: inglês primeiro, espanhol em seguida, depois alemão e francês. PT-BR permanece idioma-fonte e padrão inicial.

## 12. Ordem recomendada de lançamento

```text
1. fechar boot-counting/provenance
2. fechar trust de release
3. promover Creator físico para USB
4. gerar primeira mídia Stable/MVP
5. validar boot/recovery USB em hardware suportado
6. validar OOBE/primeiro uso, inclusive rede opcional e modo sem conta
7. validar apps principais
8. fechar canal oficial de update sem Git
9. conectar Conta OrdaX real sem torná-la requisito de boot
10. fechar legal/publicação
11. publicar MVP USB-only
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
- não use exemplos de documentação como snapshot atual quando há manifest/contrato estruturado;
- qualquer mudança de versão, `releaseMode`, geometria física ou outro valor canônico deve atualizar o snapshot/contrato correspondente no mesmo change set e manter o guardrail de freshness verde;
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
- `docs/contracts/sync-model.json`;
- `docs/contracts/first-run.json`.

Este documento define o **escopo público do MVP**. Os contratos machine-readable continuam autoridade dos invariantes técnicos.
