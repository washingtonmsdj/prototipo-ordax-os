/* Public marketing simulation only. No product imports, persistence, network or identity. */
(() => {
  "use strict";
  const root = document.querySelector(".playground");
  if (!root) return;
  const screens = [...root.querySelectorAll("[data-device]")];
  const initial = () => ({theme: "light", title: "Uma ideia começa aqui", body: "Um espaço para pensar com calma.\n\nEscreva algo aqui e veja sua ideia aparecer na outra tela.", done: false});
  let state = initial();
  const views = new Map(screens.map(screen => [screen, {app: "notes", folder: "", file: ""}]));
  let noticeTimer;
  const announce = message => {
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => { root.querySelector(".demo-status").textContent = message; }, 250);
  };
  const icons = {notes: "✎", files: "▱", settings: "◐"};
  const names = {notes: "Notas", files: "Arquivos", settings: "Ajustes"};
  const fixtures = {
    "Boas-vindas.txt": "Seu espaço começa com uma ideia.\n\nEsta é uma demonstração interativa do OrdaX. Explore as pastas, escreva uma nota e escolha seu tema. Nada aqui acessa os arquivos do seu dispositivo.",
    "Meu projeto.txt": "Um projeto, muitas possibilidades.\n\n1. Guardar referências\n2. Escrever a primeira ideia\n3. Escolher o próximo passo",
    "Referências.txt": "Referências de exemplo\n\nLuz natural. Materiais simples. Espaço para criar.\n\nNo OrdaX, a visão é aproximar conteúdo e contexto de trabalho."
  };
  function button(label, action, value, className = "") {
    const node = document.createElement("button");
    node.type = "button"; node.textContent = label; node.dataset.action = action;
    if (value !== undefined) node.dataset.value = value;
    node.className = className;
    return node;
  }
  function render(screen) {
    const view = views.get(screen);
    const device = screen.dataset.device;
    screen.dataset.theme = state.theme;
    // This template contains constants only; user text is assigned through value/textContent below.
    screen.innerHTML = `<div class="demo-topbar"><b>OrdaX</b><span>DEMONSTRAÇÃO</span><span aria-hidden="true">◌</span></div><div class="demo-workspace"><nav class="demo-dock" aria-label="Apps no ${device === "phone" ? "telefone" : "notebook"}"></nav><div class="demo-window"><div class="demo-windowbar"><strong></strong><span>Dados de exemplo</span></div><div class="demo-content"></div></div></div>`;
    const dock = screen.querySelector(".demo-dock");
    for (const app of Object.keys(names)) {
      const tab = button(`${icons[app]} ${names[app]}`, "app", app);
      tab.setAttribute("aria-pressed", String(view.app === app));
      dock.append(tab);
    }
    screen.querySelector(".demo-windowbar strong").textContent = names[view.app];
    const content = screen.querySelector(".demo-content");
    if (view.app === "notes") {
      content.innerHTML = `<p class="demo-eyebrow">MEU ESPAÇO / NOTA PESSOAL</p><label class="sr-only" for="${device}-title">Título da nota no ${device === "phone" ? "telefone" : "notebook"}</label><input id="${device}-title" class="demo-title" data-field="title" maxlength="70"><div class="demo-note-meta">Uma ideia, nas duas telas <span aria-hidden="true">↔</span></div><label class="sr-only" for="${device}-body">Texto da nota no ${device === "phone" ? "telefone" : "notebook"}</label><textarea id="${device}-body" data-field="body" maxlength="1800" spellcheck="true"></textarea><label class="demo-check"><input type="checkbox" data-field="done">Experimentar algo novo hoje</label><p class="demo-local">↔ Compartilhado nesta demonstração</p>`;
    } else if (view.app === "settings") {
      content.innerHTML = `<p class="demo-eyebrow">APARÊNCIA</p><h3>Do seu jeito.</h3><p class="demo-description">Uma pequena mudança faz diferença. Escolha a luz do seu espaço.</p><div class="theme-options"></div><p class="demo-local">O tema muda nas duas telas.</p>`;
      for (const [value,label] of [["light","☀ Claro"],["dark","☾ Escuro"]]) {
        const option = button(label,"theme",value,`theme-choice theme-${value}`);
        option.setAttribute("aria-pressed",String(state.theme === value));
        content.querySelector(".theme-options").append(option);
      }
    } else {
      const trail = document.createElement("div"); trail.className = "demo-breadcrumb";
      trail.append(button("Meu espaço", "folder", ""));
      if (view.folder) trail.append(document.createTextNode(` / ${view.folder}`));
      content.append(trail);
      if (view.file) {
        content.append(button("← Voltar aos arquivos", "back"));
        const title = document.createElement("h3"); title.textContent = view.file;
        const text = document.createElement("p"); text.className = "demo-file-text"; text.textContent = fixtures[view.file];
        content.append(title,text);
      } else {
        const heading = document.createElement("h3"); heading.textContent = view.folder || "Tudo tem seu lugar."; content.append(heading);
        const grid = document.createElement("div"); grid.className = "demo-file-grid";
        if (!view.folder) for (const folder of ["Documentos","Projetos"]) grid.append(button(`▰\n${folder}`,"folder",folder,"demo-file folder"));
        const files = view.folder === "Projetos" ? ["Meu projeto.txt","Referências.txt"] : ["Boas-vindas.txt"];
        for (const file of files) grid.append(button(`▤\n${file}`,"file",file,"demo-file"));
        content.append(grid);
      }
    }
    sync();
  }
  function sync(source) {
    for (const screen of screens) {
      screen.dataset.theme = state.theme;
      for (const input of screen.querySelectorAll("[data-field]")) {
        if (input === source) continue;
        if (input.type === "checkbox") input.checked = state.done;
        else input.value = state[input.dataset.field];
      }
      for (const option of screen.querySelectorAll('[data-action="theme"]')) option.setAttribute("aria-pressed",String(option.dataset.value === state.theme));
    }
  }
  for (const screen of screens) {
    render(screen);
    screen.addEventListener("input", event => {
      const field = event.target.dataset.field;
      if (!["title","body","done"].includes(field)) return;
      state[field] = field === "done" ? event.target.checked : event.target.value;
      sync(event.target);
      announce(`Alteração no ${screen.dataset.device === "phone" ? "telefone" : "notebook"} refletida nas duas telas. Simulação local.`);
    });
    screen.addEventListener("click",event => {
      const control = event.target.closest("[data-action]");
      if (!control) return;
      const {action,value} = control.dataset;
      const view = views.get(screen);
      if (action === "theme") { state.theme = value; sync(); announce("Tema alterado nas duas telas."); return; }
      if (action === "app" && names[value]) view.app = value;
      if (action === "folder") { view.folder = value; view.file = ""; }
      if (action === "file" && Object.hasOwn(fixtures,value)) view.file = value;
      if (action === "back") view.file = "";
      render(screen);
      const focusTarget = action === "app" ? screen.querySelector(`[data-action="app"][data-value="${view.app}"]`) : screen.querySelector(".demo-content button");
      focusTarget?.focus({preventScroll:true});
    });
  }
  root.querySelectorAll("[data-layout]").forEach(control => {
    if (control.tagName !== "BUTTON") return;
    control.addEventListener("click",() => {
      root.querySelector(".device-stage").dataset.layout = control.dataset.layout;
      root.querySelector(".phone-device").hidden = control.dataset.layout === "laptop";
      root.querySelector(".sync-bridge").hidden = control.dataset.layout === "laptop";
      root.querySelectorAll("button[data-layout]").forEach(button => button.setAttribute("aria-pressed",String(button === control)));
    });
  });
  root.querySelector("[data-reset]").addEventListener("click",() => {
    state = initial();
    screens.forEach(screen => { views.set(screen,{app:"notes",folder:"",file:""}); render(screen); });
    announce("Demonstração reiniciada. Os dados de exemplo foram restaurados.");
  });
  root.querySelectorAll("[data-recipe]").forEach(control => control.addEventListener("click",() => {
    const app = control.dataset.recipe === "theme" ? "settings" : control.dataset.recipe;
    screens.forEach(screen => { views.get(screen).app = app; render(screen); });
    screens[0].querySelector(".demo-content input, .demo-content button")?.focus({preventScroll:true});
    screens[0].scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",block:"center"});
    announce(app === "notes" ? "Edite a nota em qualquer tela. A outra acompanha." : app === "files" ? "Abra uma pasta e leia os arquivos de exemplo." : "Escolha um tema. As duas telas acompanham.");
  }));
})();
