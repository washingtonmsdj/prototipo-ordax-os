import { accountComponent } from "../../../apps/account/component.mjs";
import { filesComponent } from "../../../apps/files/component.mjs";
import { settingsComponent } from "../../../apps/settings/component.mjs";
import { systemComponent } from "../../../apps/system/component.mjs";

export {
  accountComponent,
  filesComponent,
  settingsComponent,
  systemComponent,
};

export const appComponentManifests = Object.freeze([
  filesComponent,
  settingsComponent,
  accountComponent,
  systemComponent,
]);
