# MVP — OrdaX

Status: CANÔNICO PARA PLANEJAMENTO DO MVP

Este arquivo existe para que qualquer próxima conversa, agente ou colaborador entenda rapidamente **qual OrdaX estamos construindo para desenvolvimento** e **qual OrdaX será entregue ao usuário final**.

Leia este arquivo antes de iniciar trabalho relacionado a lançamento, pendrive, Creator, atualizações, site público, conta, releases ou MVP.

## 1. Um produto, dois perfis de distribuição

O OrdaX não deve virar dois sistemas diferentes nem dois códigos divergentes.

Existe **uma única base de produto**, mas com duas políticas de distribuição:

### Owner / Development

Uso: desenvolvimento rápido, manutenção e recuperação pelo owner do projeto.

Características:

- checkout Git local permitido;
- atualização rápida a partir da `main`;
- SHA/commit/entrega disponíveis em diagnóstico;
- Git-first USB permitido;
- canais de recovery e ferramentas de desenvolvimento permitidos;
- apps, Surface e serviços podem receber alterações rapidamente;
- Base/kernel continuam usando mecanismos fail-closed, A/B e health quando aplicável;
- esta edição não representa a experiência pública do usuário.

Objetivo: maximizar velocidade de desenvolvimento sem transformar o ambiente de usuário final em um ambiente de engenharia.

### Stable / MVP

Uso: usuário final e distribuição pública.

Características:

- **não depende de Git operacional**;
- não executa `git pull` como mecanismo de atualização;
- não precisa expor repositório, branch, PR ou commit na UX normal;
- recebe somente releases publicadas por canais oficiais;
- artifacts devem ser vinculados a versão, tamanho, hash e provenance;
- releases públicas devem ser verificadas/assinadas conforme os contratos de trust;
- Base/kernel usam staging A/B, one-shot, health gate e rollback;
- apps e componentes devem evoluir para atualização independente quando isso não exigir mudança da Base;
- Creator é o caminho normal para preparar mídia;
- falha de atualização não pode destruir o conhecido-bom.

**Regra:** não criar forks permanentes do código para Owner e Stable. Diferença deve ficar em profile, build, configuração, canal, autorização e política de atualização.

## 2. Modelo de atualização

### Owner / Development

Fluxo esperado:

```text
main
 -> pull/sync de desenvolvimento
 -> componente afetado
 -> hot apply quando possível
 -> Base candidata A/B quando kernel/rootfs/initramfs mudarem
 -> health
 -> promoção ou fallback
```

O desenvolvimento pode continuar rápido. Apps e serviços não devem obrigar reboot do sistema inteiro.

### Stable / MVP

Fluxo esperado:

```text
canal oficial OrdaX
 -> manifest/release envelope autorizado
 -> verificação criptográfica e de integridade
 -> download do componente/release
 -> staging
 -> ativação controlada
 -> health check
 -> promoção
 -> rollback automático se falhar
```

O Stable/MVP **não usa Git como canal de atualização do usuário**.

## 3. Versões de componentes

Não fingir que todos os componentes receberam a mesma versão quando somente um mudou.

Exemplo permitido:

```text
OrdaX Base       0.9.x
Surface          0.8.x
Internet         0.5.x
Notas            0.4.x
Arquivos         0.3.x
Ajustes          0.3.x
Creator          0.2.x
```

A versão geral do produto pode existir, mas deve ser distinguida da versão dos componentes.

## 4. Definição prática de MVP

O MVP público não precisa ser OrdaX 1.0.

Um usuário deve conseguir:

1. chegar ao site oficial, cuja rota `/` é a landing page pública;
2. obter o Creator/release pública autorizada;
3. preparar o pendrive sem terminal, sem manipular ISO, partições, Git ou SHA;
4. inicializar um hardware oficialmente suportado pelo pendrive;
5. escolher entre **usar o OrdaX diretamente pelo USB** ou **instalar o OrdaX no SSD/NVMe/HD**;
6. no modo USB, chegar à Surface e usar o sistema sem instalação obrigatória no disco interno;
7. no modo Native, concluir a instalação no disco interno e depois iniciar sem depender do pendrive;
8. conectar à rede;
9. usar os apps principais;
10. atualizar por canal oficial;
11. recuperar automaticamente de uma atualização defeituosa;
12. entrar/criar Conta OrdaX quando o serviço real de identidade estiver habilitado;
13. após autenticação, acessar a área do usuário em rota separada da landing pública.

### Apps principais do MVP

Prioridade funcional:

- Arquivos;
- Notas;
- Internet;
- Ajustes;
- Sistema.

Eles devem ser apps/componentes do produto, não código acoplado de forma que uma falha simples derrube a Base.

## 5. O que bloqueia o MVP público

Os gates abaixo são de lançamento, não uma lista de recursos de v1.0:

- trust/release signing real;
- Creator físico promovido e autorizado;
- payload final verificável para mídia pública;
- one-shot A/B e fallback suficientemente provados;
- primeiro pendrive canônico Stable/MVP validado;
- boot pelo USB -> escolha **Usar OrdaX** / **Instalar OrdaX**;
- modo USB funcional sem instalação obrigatória no disco interno;
- instalador Native funcional para SSD/NVMe/HD suportado;
- boot Native validado após remover o pendrive;
- boot -> Surface -> rede -> apps principais;
- fluxo de update oficial sem Git;
- recovery/rollback funcional;
- catálogo público de releases fail-closed;
- Conta OrdaX real para login/cadastro antes de habilitar os botões públicos;
- privacidade/termos prontos antes de ativar contas reais;
- conjunto de hardware suportado documentado.

## 6. O que NÃO bloqueia o MVP

Não atrasar o MVP esperando tudo abaixo:

- loja de apps completa;
- sync completo entre vários dispositivos;
- amplo suporte a notebooks diferentes;
- áudio perfeito em todo hardware;
- suspend/resume universal;
- aceleração gráfica refinada em todas as GPUs;
- internacionalização completa;
- bootloader físico autoatualizável para todos os cenários;
- conjunto completo de recursos planejados para 1.0.

Esses itens podem entrar durante o MVP, beta ou depois.

## 7. Pendrive e Creator

Existem dois usos diferentes de USB.

### USB Owner / Development

- Git-first;
- pode conter ferramentas extras de diagnóstico;
- serve para evolução rápida e recovery de desenvolvimento;
- não deve ser apresentado como release pública.

### USB Stable / MVP

- gerado por Creator/release autorizada;
- sem dependência operacional de Git;
- conteúdo vinculado a manifest/hashes/provenance;
- atualização posterior por canais oficiais;
- recovery conhecido-bom preservado;
- usuário não precisa manipular ISO, partição, Git, SHA ou terminal;
- deve inicializar como um modo de produto utilizável, não apenas como mídia descartável de instalação;
- deve oferecer, no fluxo suportado do MVP, as ações **Usar OrdaX** e **Instalar OrdaX**.

### Fluxo público obrigatório do MVP

```text
site oficial
 -> baixar OrdaX Creator
 -> conectar USB
 -> Creator baixa/seleciona release Stable autorizada
 -> verifica assinatura/hash
 -> prepara e verifica o USB
 -> usuário inicializa pelo USB
 -> escolher:
      1. Usar OrdaX diretamente pelo USB
      2. Instalar OrdaX no SSD/NVMe/HD
```

O modo **OrdaX USB** deve funcionar como ambiente real do produto enquanto o computador estiver inicializado pelo pendrive. A instalação no disco interno produz o modo **OrdaX Native**, consumindo o mesmo modelo de release em vez de criar outro sistema.

O `OrdaX Creator` é um único produto/core. Durante o MVP ele pode ser distribuído como aplicativo standalone quando necessário; posteriormente a mesma capacidade deve ser incorporada ao **OrdaX Desktop**, sem criar um segundo gravador ou uma política paralela de mídia.

O backend físico do Creator pode existir antes de sua promoção pública. **Existência de código de gravação não equivale a autorização para release pública.**

## 8. Site público

O portal público vive em:

```text
sites/public/
```

Ele é separado do modo de produto OrdaX Web.

Objetivos do portal para o MVP:

- landing page pública em `/`;
- Download/Creator;
- login;
- cadastro;
- área autenticada da conta em `/conta/`;
- entrada para o modo OrdaX Web a partir da experiência autenticada, sem substituir a landing;
- licenças/SBOM/source compliance;
- privacidade;
- termos.

### Regra de rotas públicas e autenticadas

```text
/            -> landing page pública do produto
/download/   -> download / Creator / releases
/login/      -> entrada de autenticação
/cadastro/   -> criação de conta
/conta/      -> área autenticada do usuário
```

A **Surface/área OrdaX do usuário não deve ocupar `/`**. A raiz é sempre a apresentação pública do produto. A área pessoal, dispositivos, sessão, preferências sincronizadas e entrada para experiências autenticadas pertencem à conta. O modo **OrdaX Web** continua sendo produto separado do portal público e deve ser alcançado a partir de uma sessão/entrada apropriada, não renderizado como homepage pública.

### Regra de comunicação pública

A landing deve falar de produto e benefício ao usuário.

Evitar na home pública:

- `main`;
- `git pull`;
- PR;
- branch;
- detalhes do ambiente Owner;
- recursos ainda não reais apresentados como disponíveis.

O Download deve continuar fail-closed: sem release autorizada, sem botão falso de download.

## 9. Conta OrdaX

Para MVP público, o mínimo é:

- criar conta;
- entrar;
- sair;
- recuperar acesso;
- sessão real;
- perfil básico;
- área autenticada em `/conta/`;
- encaminhamento pós-login para a experiência autenticada, nunca para uma falsa dashboard em `/`;
- entrada para o OrdaX Web quando o runtime Web e os contratos de sessão estiverem realmente habilitados.

A rota `/conta/` pode permanecer fail-closed/indisponível enquanto identidade e sessão reais não estiverem conectadas. Ela não deve simular dados, dispositivos ou sincronização.

O site está correto ao não coletar senha enquanto o serviço real de identidade não estiver conectado.

Sync completo pode vir depois.

## 10. Ordem recomendada de lançamento

```text
1. fechar boot-counting/provenance
2. fechar trust de release
3. promover Creator físico
4. gerar primeira mídia Stable/MVP
5. validar boot/recovery em hardware suportado
6. validar apps principais
7. fechar canal oficial de update sem Git
8. conectar Conta OrdaX
9. fechar legal/publicação
10. publicar MVP
```

## 11. Regras para próximos chats

Ao continuar o projeto:

- sincronize com `main` e PRs abertos antes de editar;
- não duplique trabalho paralelo;
- mantenha Owner/Development e Stable/MVP como **profiles/canais**, não como forks;
- não introduza Git operacional no Stable/MVP;
- não exponha no site público capacidades que ainda não tenham serviço real;
- preserve os gates fail-closed;
- não declare prova física quando houve apenas prova descartável/CI;
- mantenha apps/componentes independentes quando possível;
- prefira corrigir arquitetura a adicionar paliativos;
- atualize este arquivo quando uma decisão de MVP mudar materialmente.

## 12. Referências técnicas

Para detalhes atuais, consultar também:

- `docs/CURRENT-STATE.md`;
- `docs/PUBLIC-SITE.md`;
- `docs/CREATOR-INSTALLATION.md`;
- `docs/NATIVE-INSTALLATION.md`;
- `docs/PHYSICAL-MEDIA.md`;
- `docs/PROMOTION-GATES.md`;
- `docs/contracts/base-update.json`;
- `docs/contracts/distribution-profiles.json`;
- `docs/contracts/native-installation.json`;
- `docs/contracts/device-update-coverage.json`;
- `docs/contracts/public-site.json`;
- `docs/contracts/public-release-catalog.json`;
- `docs/contracts/physical-write-authorization.json`.

Este documento define o **alvo de produto**. Os contratos machine-readable continuam sendo a autoridade dos invariantes técnicos.
