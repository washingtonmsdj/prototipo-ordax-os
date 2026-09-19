const UPDATE_LABELS = Object.freeze({
  running: "Em execução",
  applied: "Atualização aplicada",
  updating: "Atualizando",
  "network-error": "Sem conexão para atualizar",
  "remote-error": "Fonte de atualização indisponível",
  "pull-error": "Falha ao atualizar",
  "rolled-back": "Atualização revertida",
  rejected: "Entrega bloqueada",
  pinned: "Entrega fixada",
  disabled: "Atualização indisponível",
  unavailable: "Estado indisponível",
});

export function updateStatusLabel(status) {
  return UPDATE_LABELS[status] ?? String(status || "Estado indisponível");
}

export function updateIsAlerting(snapshot) {
  return Boolean(snapshot?.bootRefreshRequired) || [
    "network-error",
    "remote-error",
    "pull-error",
    "rolled-back",
    "rejected",
  ].includes(snapshot?.status);
}

export function shortSha(value) {
  if (typeof value !== "string" || value.length < 8 || value === "unavailable") return "—";
  return value.slice(0, 8);
}

export function deliveryLabel(value) {
  return Number.isSafeInteger(value) && value > 0 ? `Entrega ${value}` : "Entrega sem número";
}

export function formatUpdateTimestamp(value) {
  if (typeof value !== "string" || !value || value === "unknown") return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Bahia",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

export function readableUpdateMode(mode) {
  switch (mode) {
    case "reload": return "Recarga rápida da Surface";
    case "surface-restart": return "Reinício somente da Surface";
    case "supervisor-restart": return "Reinício do supervisor";
    case "initial": return "Inicialização";
    default: return "Sem ação pendente";
  }
}

export function readableBaseUpdatePhase(phase) {
  switch (phase) {
    case "waiting-candidate": return "Aguardando candidata de Base";
    case "candidate-requested": return "Candidata de Base solicitada";
    case "candidate-fetching": return "Baixando candidata de Base";
    case "candidate-ready": return "Candidata de Base pronta";
    case "staged": return "Base gravada no slot inativo";
    case "activation-ready": return "Base pronta para ativação";
    default: return "Sem atualização de Base pendente";
  }
}

export function readableUpdatePhase(phase) {
  switch (phase) {
    case "checking": return "Verificando atualizações";
    case "fetching": return "Baixando entrega";
    case "validating": return "Validando sistema";
    case "activating": return "Ativando entrega";
    case "health-wait": return "Aguardando confirmação de saúde";
    case "rollback": return "Revertendo automaticamente";
    case "blocked": return "Bloqueada";
    case "error": return "Falha";
    default: return "Em repouso";
  }
}

export function updateSummaryLabel(snapshot) {
  if (!snapshot?.bootRefreshRequired) return updateStatusLabel(snapshot?.status);
  switch (snapshot?.baseUpdatePhase) {
    case "candidate-requested": return "Preparando atualização de Base";
    case "candidate-fetching": return "Baixando atualização de Base";
    case "candidate-ready": return "Candidata de Base pronta";
    case "staged": return "Base gravada no slot inativo";
    case "activation-ready": return "Base pronta para ativação";
    default: return "Atualização de base pendente";
  }
}

export function updateSummaryDetail(snapshot) {
  if (!snapshot?.bootRefreshRequired) return "";
  switch (snapshot?.baseUpdatePhase) {
    case "candidate-requested":
      return "A candidata exata foi solicitada ao atualizador de Base. A entrega atual continua em execução.";
    case "candidate-fetching":
      return "Kernel, initramfs e rootfs da candidata estão sendo baixados e verificados sem alterar o boot atual.";
    case "candidate-ready":
      return "A candidata e a rootfs versionada foram verificadas. O staging no slot inativo é a próxima etapa.";
    case "staged":
      return "A candidata foi gravada no slot inativo. O boot atual e a recuperação permanecem preservados.";
    case "activation-ready":
      return "A candidata foi revalidada no slot inativo e está pronta para a etapa de ativação. A ativação automática ainda não está habilitada; reiniciar manualmente não força a aplicação.";
    default:
      return "Reiniciar manualmente agora não conclui esta atualização. O OrdaX preserva o boot atual enquanto prepara e valida a candidata.";
  }
}

export function updateBootLabel(snapshot) {
  if (!snapshot?.bootRefreshRequired) return "Nenhuma atualização de base pendente";
  switch (snapshot?.baseUpdatePhase) {
    case "candidate-requested": return "Base solicitada";
    case "candidate-fetching": return "Base em preparação";
    case "candidate-ready": return "Base pronta para staging";
    case "staged": return "Candidata no slot inativo";
    case "activation-ready": return "Base pendente de ativação";
    default: return "Base pendente de ativação";
  }
}

export function updateAttentionMessage(snapshot) {
  if (snapshot?.bootRefreshRequired) {
    return updateSummaryDetail(snapshot);
  }
  return "A entrega atual permanece preservada enquanto o atualizador tenta recuperar um estado saudável.";
}
