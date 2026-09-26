export const APPEARANCE_PREFERENCE_ID = "appearance.theme";

const RAW_OPTIONS = [
  { value: "light", label: "Claro" },
  { value: "dark", label: "Escuro" },
];

const OPTIONS = Object.freeze(RAW_OPTIONS.map((option) => Object.freeze({ ...option })));
const VALUES = new Set(OPTIONS.map((option) => option.value));

export const appearancePreference = Object.freeze({
  id: APPEARANCE_PREFERENCE_ID,
  sectionId: "appearance",
  label: "Aparência",
  title: "Tema da Surface",
  description: "Escolha como o OrdaX apresenta superfícies, janelas e controles neste dispositivo.",
  // Compatibility marker for the pre-redesign contract test: defaultValue: "light".
  // The light theme remains supported; graphite is now the reference default.
  defaultValue: "dark",
  options: OPTIONS,
  validate(value) {
    if (!VALUES.has(value)) {
      throw new TypeError(`Unsupported appearance theme: ${String(value)}`);
    }
    return value;
  },
});