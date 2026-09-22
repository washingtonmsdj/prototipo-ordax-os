import { LOCALIZATION_SCHEMA, assertLocalizationPort } from "../../contracts/localization.mjs";
import { assertPreferenceRuntimePort } from "../../contracts/preference-runtime.mjs";
import { REGIONAL_LOCALE_PREFERENCE_ID } from "../preferences/regional.mjs";

export const SURFACE_SOURCE_LOCALE = "pt-BR";
export const SURFACE_COMPLETE_LOCALES = Object.freeze(["pt-BR"]);
export const SURFACE_ENGLISH_TARGET_LOCALE = "en-US";

const SOURCE = Object.freeze({
  "shell.rail.aria": "Aplicativos principais",
  "shell.home.loadingDate": "Carregando data…",
  "shell.launcher.command": "Abrir aplicativo…",
  "shell.space.title": "Seu espaço",
  "shell.space.documents": "Documentos",
  "shell.space.images": "Imagens",
  "shell.space.downloads": "Downloads",
  "shell.slogan": "IDEIAS\nORGANIZAM\nREALIDADES",
  "shell.launcher.dialog": "Abrir aplicativo",
  "shell.launcher.search": "Pesquisar aplicativos",
  "shell.statusbar.aria": "Estado e áreas da Surface",
  "shell.areas.aria": "Áreas de trabalho",
  "shell.runningApps.aria": "Aplicações abertas",
  "shell.systemStatus.aria": "Estado do sistema",
  "shell.network.quickOpen": "Abrir acesso rápido de Wi-Fi",
  "shell.battery.quickOpen": "Abrir estado da bateria",
  "shell.datetime.quickOpen": "Abrir data e hora",
  "shell.quick.access": "Acesso rápido",
  "shell.quick.wifiClose": "Fechar acesso rápido de Wi-Fi",
  "shell.quick.wifiReading": "Lendo estado do Wi-Fi…",
  "shell.quick.energy": "Energia",
  "shell.quick.battery": "Bateria",
  "shell.quick.batteryClose": "Fechar estado da bateria",
  "shell.quick.batteryReading": "Lendo estado da bateria…",
  "shell.quick.powerSource": "Fonte de energia",
  "shell.quick.checking": "Verificando…",
  "shell.quick.dateTime": "Data e hora",
  "shell.quick.dateTimeClose": "Fechar data e hora",
  "shell.quick.timeZone": "Fuso horário",
  "shell.clock.timeZone": "Fuso horário: {timeZone}",

  "surface.connectivity.online": "Online",
  "surface.connectivity.offline": "Offline",
  "surface.connectivity.unknown": "Conectividade desconhecida",
  "surface.area.label": "Área {ordinal}",
  "surface.capability.available": "Disponível",
  "surface.capability.unavailable": "Indisponível neste host",
  "surface.capability.none": "Nenhuma capacidade adicional foi declarada.",
  "surface.window.move": "Mover {app}. Use Alt mais setas ou arraste quando houver espaço.",
  "surface.window.minimize": "Minimizar {app}",
  "surface.window.maximize": "Maximizar {app}",
  "surface.window.restore": "Restaurar {app}",
  "surface.window.close": "Fechar {app}",
  "surface.launcher.open": "Abrir {app}",
  "surface.launcher.unavailable": "{app} indisponível",
  "surface.launcher.requirementsUnavailable": "Capacidades necessárias indisponíveis",
  "surface.launcher.empty": "Nenhum aplicativo encontrado.",
  "surface.dock.restore": "Restaurar {app}",
  "surface.dock.focus": "Focar {app}",
  "surface.area.switch": "Mudar para {area}",
  "surface.area.create": "Criar nova área de trabalho",
  "surface.network.label": "Rede: {status}",
  "surface.capability.destinationRequired": "Este destino requer o espaço local do usuário.",

  "app.files.title": "Arquivos",
  "app.files.description": "Organize documentos, imagens, downloads e conteúdo persistente do usuário.",
  "app.files.panel.0.label": "Espaço do usuário",
  "app.files.panel.0.title": "Arquivos",
  "app.files.panel.0.body": "Este host não expõe um espaço local de arquivos para esta Surface.",

  "app.notes.title": "Notas",
  "app.notes.description": "Escrita local, projetos, tarefas e referências disponíveis offline.",
  "app.notes.panel.0.label": "Notas",
  "app.notes.panel.0.title": "Seu espaço de escrita",
  "app.notes.panel.0.body": "O espaço local de Notas não está disponível nesta composição.",

  "app.internet.title": "Internet",
  "app.internet.description": "Navegue, organize referências e conecte pesquisa ao seu trabalho.",
  "app.internet.panel.0.label": "Navegador",
  "app.internet.panel.0.title": "Internet",
  "app.internet.panel.0.body": "A navegação integrada depende de um engine isolado fornecido pelo host.",

  "app.settings.title": "Ajustes",
  "app.settings.description": "Preferências compartilhadas, aparência e rede do OrdaX.",
  "app.settings.panel.0.label": "Ajustes",
  "app.settings.panel.0.title": "Preferências do OrdaX",
  "app.settings.panel.0.body": "As preferências desta Surface não estão disponíveis neste host.",

  "app.account.title": "Conta",
  "app.account.description": "Identidade, acesso e continuidade segura entre os modos do OrdaX.",
  "app.account.panel.0.label": "Conta",
  "app.account.panel.0.title": "Identidade e continuidade",
  "app.account.panel.0.body": "Este host não oferece uma integração de identidade para esta Surface.",

  "app.system.title": "Sistema",
  "app.system.description": "Entrega, atualizações, conectividade e recursos desta execução do OrdaX.",
  "app.system.panel.0.label": "Sistema",
  "app.system.panel.0.title": "Visão geral",
  "app.system.panel.0.body": "O estado detalhado do sistema não está disponível neste host."
});

const ENGLISH = Object.freeze({
  "shell.rail.aria": "Main applications",
  "shell.home.loadingDate": "Loading date…",
  "shell.launcher.command": "Open application…",
  "shell.space.title": "Your space",
  "shell.space.documents": "Documents",
  "shell.space.images": "Pictures",
  "shell.space.downloads": "Downloads",
  "shell.slogan": "IDEAS\nORGANIZE\nREALITIES",
  "shell.launcher.dialog": "Open application",
  "shell.launcher.search": "Search applications",
  "shell.statusbar.aria": "Surface status and workspaces",
  "shell.areas.aria": "Workspaces",
  "shell.runningApps.aria": "Open applications",
  "shell.systemStatus.aria": "System status",
  "shell.network.quickOpen": "Open Wi-Fi quick access",
  "shell.battery.quickOpen": "Open battery status",
  "shell.datetime.quickOpen": "Open date and time",
  "shell.quick.access": "Quick access",
  "shell.quick.wifiClose": "Close Wi-Fi quick access",
  "shell.quick.wifiReading": "Reading Wi-Fi status…",
  "shell.quick.energy": "Power",
  "shell.quick.battery": "Battery",
  "shell.quick.batteryClose": "Close battery status",
  "shell.quick.batteryReading": "Reading battery status…",
  "shell.quick.powerSource": "Power source",
  "shell.quick.checking": "Checking…",
  "shell.quick.dateTime": "Date and time",
  "shell.quick.dateTimeClose": "Close date and time",
  "shell.quick.timeZone": "Time zone",
  "shell.clock.timeZone": "Time zone: {timeZone}",

  "surface.connectivity.online": "Online",
  "surface.connectivity.offline": "Offline",
  "surface.connectivity.unknown": "Connectivity unknown",
  "surface.area.label": "Area {ordinal}",
  "surface.capability.available": "Available",
  "surface.capability.unavailable": "Unavailable on this host",
  "surface.capability.none": "No additional capabilities were declared.",
  "surface.window.move": "Move {app}. Use Alt plus arrow keys or drag when there is space.",
  "surface.window.minimize": "Minimize {app}",
  "surface.window.maximize": "Maximize {app}",
  "surface.window.restore": "Restore {app}",
  "surface.window.close": "Close {app}",
  "surface.launcher.open": "Open {app}",
  "surface.launcher.unavailable": "{app} unavailable",
  "surface.launcher.requirementsUnavailable": "Required capabilities unavailable",
  "surface.launcher.empty": "No applications found.",
  "surface.dock.restore": "Restore {app}",
  "surface.dock.focus": "Focus {app}",
  "surface.area.switch": "Switch to {area}",
  "surface.area.create": "Create a new workspace",
  "surface.network.label": "Network: {status}",
  "surface.capability.destinationRequired": "This destination requires local user storage.",

  "app.files.title": "Files",
  "app.files.description": "Organize documents, pictures, downloads, and persistent user content.",
  "app.files.panel.0.label": "User space",
  "app.files.panel.0.title": "Files",
  "app.files.panel.0.body": "This host does not expose local file storage to this Surface.",

  "app.notes.title": "Notes",
  "app.notes.description": "Local writing, projects, tasks, and references available offline.",
  "app.notes.panel.0.label": "Notes",
  "app.notes.panel.0.title": "Your writing space",
  "app.notes.panel.0.body": "The local Notes workspace is unavailable in this composition.",

  "app.internet.title": "Internet",
  "app.internet.description": "Browse, organize references, and connect research to your work.",
  "app.internet.panel.0.label": "Browser",
  "app.internet.panel.0.title": "Internet",
  "app.internet.panel.0.body": "Integrated browsing depends on an isolated engine supplied by the host.",

  "app.settings.title": "Settings",
  "app.settings.description": "Shared preferences, appearance, and OrdaX network settings.",
  "app.settings.panel.0.label": "Settings",
  "app.settings.panel.0.title": "OrdaX preferences",
  "app.settings.panel.0.body": "Surface preferences are unavailable on this host.",

  "app.account.title": "Account",
  "app.account.description": "Identity, access, and secure continuity across OrdaX modes.",
  "app.account.panel.0.label": "Account",
  "app.account.panel.0.title": "Identity and continuity",
  "app.account.panel.0.body": "This host does not provide identity integration for this Surface.",

  "app.system.title": "System",
  "app.system.description": "Delivery, updates, connectivity, and resources for this OrdaX run.",
  "app.system.panel.0.label": "System",
  "app.system.panel.0.title": "Overview",
  "app.system.panel.0.body": "Detailed system status is unavailable on this host."
});

const TABLES = Object.freeze({
  [SURFACE_SOURCE_LOCALE]: SOURCE,
  [SURFACE_ENGLISH_TARGET_LOCALE]: ENGLISH,
});

function interpolate(text, values = {}) {
  return text.replace(/\{([A-Za-z][A-Za-z0-9]*)\}/g, (match, key) => {
    const value = values[key];
    return value === undefined || value === null ? match : String(value);
  });
}

export function createSurfaceLocalization(preferenceRuntime) {
  const preferences = assertPreferenceRuntimePort(preferenceRuntime);
  let locale = preferences.getSnapshot()[REGIONAL_LOCALE_PREFERENCE_ID] ?? SURFACE_SOURCE_LOCALE;
  const listeners = new Set();

  const translate = (messageId, values = {}) => {
    if (typeof messageId !== "string" || !messageId) {
      throw new TypeError("Localization message id must be a non-empty string");
    }
    const source = SOURCE[messageId];
    if (typeof source !== "string") {
      throw new TypeError(`Unknown Surface localization message: ${messageId}`);
    }
    const translated = TABLES[locale]?.[messageId] ?? source;
    return interpolate(translated, values);
  };

  const port = {
    schema: LOCALIZATION_SCHEMA,
    getLocale() {
      return locale;
    },
    translate,
    subscribe(listener) {
      if (typeof listener !== "function") {
        throw new TypeError("Localization listener must be a function");
      }
      listeners.add(listener);
      listener(locale);
      return () => listeners.delete(listener);
    },
    dispose() {
      unsubscribePreferences();
      listeners.clear();
    },
  };

  const unsubscribePreferences = preferences.subscribe((snapshot) => {
    const next = snapshot[REGIONAL_LOCALE_PREFERENCE_ID] ?? SURFACE_SOURCE_LOCALE;
    if (next === locale) return;
    locale = next;
    for (const listener of [...listeners]) listener(locale);
  });

  assertLocalizationPort(port);
  return Object.freeze(port);
}

export function surfaceMessageIds() {
  return Object.freeze(Object.keys(SOURCE));
}

export function surfaceLocaleCoverage(locale) {
  const table = TABLES[locale] ?? null;
  const total = Object.keys(SOURCE).length;
  const translated = table ? Object.keys(table).length : 0;
  return Object.freeze({
    locale,
    sourceLocale: SURFACE_SOURCE_LOCALE,
    translated,
    total,
    complete: locale === SURFACE_SOURCE_LOCALE || translated === total,
  });
}
