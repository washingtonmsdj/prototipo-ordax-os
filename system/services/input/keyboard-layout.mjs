import { KEYBOARD_LAYOUT_IDS } from "../../contracts/keyboard-layout.mjs";

export const DEFAULT_KEYBOARD_LAYOUT_ID = "br-abnt2";

const OPTIONS = Object.freeze({
  "br-abnt2": Object.freeze({
    id: "br-abnt2",
    label: "Português (Brasil) · ABNT2",
    description: "Layout brasileiro ABNT2 para teclados físicos com Ç e tecla AltGr.",
  }),
  us: Object.freeze({
    id: "us",
    label: "English (US)",
    description: "Layout US padrão para teclados físicos sem teclas ABNT2.",
  }),
});

if (!KEYBOARD_LAYOUT_IDS.includes(DEFAULT_KEYBOARD_LAYOUT_ID)) {
  throw new TypeError("Default keyboard layout must be part of the contract");
}
for (const layoutId of KEYBOARD_LAYOUT_IDS) {
  if (!OPTIONS[layoutId]) {
    throw new TypeError(`Missing keyboard layout presentation: ${layoutId}`);
  }
}

export const KEYBOARD_LAYOUT_OPTIONS = Object.freeze(
  KEYBOARD_LAYOUT_IDS.map((layoutId) => OPTIONS[layoutId]),
);

export function keyboardLayoutOption(layoutId) {
  return OPTIONS[layoutId] ?? null;
}
