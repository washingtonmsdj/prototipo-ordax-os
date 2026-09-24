import { createNativeComponentSlotSource } from "../../adapters/native/component-slot-source.mjs";
import { runSystemPendingComponentProbation } from "../../services/components/probation-orchestrator.mjs";

export const NATIVE_COMPONENT_PROBATION_SCHEMA =
  "ordax.native-component-probation/1";

export async function runNativePendingComponentProbation({
  componentId,
  windowRef = globalThis.window,
  fetchImpl = globalThis.fetch?.bind(globalThis),
  importModule = (url) => import(url),
  timeoutMs = 5_000,
} = {}) {
  const source = createNativeComponentSlotSource(windowRef);
  return runSystemPendingComponentProbation({
    componentId,
    source,
    fetchImpl,
    importModule,
    timeoutMs,
  });
}
