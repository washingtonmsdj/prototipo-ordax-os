# OrdaX Device Agent, Projetos, GitHub, Web e MCP

Status: fundação source em implementação. Não é claim de disponibilidade pública.

## 1. Produto

O runtime antes incubado no repositório histórico `washingtonmsdj/mcp-blender`
passa a ter identidade de produto **OrdaX Device Agent**.

Blender e Unity são adapters iniciais. Git, arquivos, testes e futuras ferramentas
usam o mesmo modelo de capabilities tipadas.

O objetivo é evitar quatro produtos diferentes para a mesma função.

```text
OrdaX Projetos ------+
OrdaX Web -----------+--> OrdaX Action Gateway --> Device Agent --> projeto/apps
External Product MCP +
```

## 2. GitHub não é substituído

GitHub permanece first-class.

Para um usuário que já paga GPT ou Grok, um repositório bem estruturado pode ser
trabalhado diretamente pelo conector GitHub do provedor sem exigir o MCP OrdaX.
Isso preserva uma rota rápida para leitura de código, documentação, branches,
PRs e colaboração.

Esse caminho não deve ser artificialmente bloqueado para forçar o uso do OrdaX.

```text
GPT/Grok --> GitHub connector --> repository
```

O OrdaX agrega valor onde GitHub sozinho não chega:

```text
GPT/Grok --> OrdaX Product MCP --> Action Gateway --> Device Agent
                                               +--> local files
                                               +--> Blender
                                               +--> Unity
                                               +--> artifacts
                                               +--> private project memory
                                               +--> typed actions
```

Os dois caminhos podem coexistir para o mesmo Projeto.

## 3. Projetos é o app principal

O usuário não precisa entender "MCP" para usar o OrdaX.

O app `Projetos` deve ser o workspace universal. Um projeto pode ser:
- local;
- GitHub-only;
- híbrido local + GitHub;
- orientado a Blender/Unity;
- documentos/notas;
- futuro pack profissional.

No Profile Pack Developer, a evolução pode incluir editor, árvore de arquivos,
Git, testes, problemas, artifacts, Intelligence e tarefas tipadas. A proposta é
aproveitar modelos que o usuário já possui/acessa em vez de tornar uma IDE cara
um requisito do OrdaX.

## 4. Conectar GitHub

A conexão GitHub pertence à Conta/Space, embora o fluxo possa ser iniciado por
`Projetos > Importar do GitHub`.

O modelo alvo para integração própria é GitHub App com seleção explícita de
repositórios. Não criar tokens diferentes para Projetos, Intelligence, Web e MCP.

A integração GitHub direta dentro de GPT/Grok continua separada e opcional.

## 5. Product MCP

Product MCP é uma interface externa do Action Gateway, não um clone do Device
Agent e não um atalho administrativo.

Autorização remota precisa ser ligada a:
- conta;
- Space;
- projeto;
- dispositivo;
- capability;
- modo read/write.

Escrita exige aprovação explícita. Shell genérico, disco bruto, chaves de release,
memória de outro Space e admin implícito permanecem proibidos.

O `stdio` existente do runtime de desenvolvimento continua útil localmente; MCP
remoto de produto precisa de gateway autenticado e não deve publicar diretamente
uma porta local da estação.

## 6. Controle Web

OrdaX Web não terá backend de automação paralelo.

```text
ordax.com
   |
Conta OrdaX
   |
dispositivo + projeto
   |
Action Gateway
   |
Device Agent
```

O Web poderá, por capability, exibir presença, projetos, status Git, artifacts,
capturas, apps e Intelligence e executar somente ações autorizadas.

## 7. Atualizações

A disciplina atual do agente é preservada:
- Git `main` continua origem operacional do desenvolvimento;
- atualização fast-forward;
- bootstrap externo/recovery;
- compile/test gate;
- adapters e protocolos versionados;
- capabilities reportadas separadamente de mera versão instalada.

A migração do nome não deve quebrar os entrypoints históricos até a nova cadeia
estar comprovada.

## 8. Sequência

1. identidade OrdaX Device Agent + aliases compatíveis;
2. contrato genérico de projeto/device/capability no OrdaX;
3. ligar Profile Pack Developer ao conceito de Projetos;
4. conexão GitHub central por Conta/Space;
5. contexto compartilhável de projeto separado da Memory privada;
6. Action Gateway read-only;
7. Product MCP read-only;
8. OrdaX Web read-only sobre o mesmo gateway;
9. mutações tipadas com grants/auditoria;
10. adapters adicionais.

Nada desta sequência altera os gates do primeiro Stable/MVP USB. Device Agent,
Web e MCP devem degradar sem impedir boot ou IA local.
