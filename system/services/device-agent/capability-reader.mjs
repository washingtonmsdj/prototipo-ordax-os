import {
  DEVICE_AGENT_CAPABILITY_READER_SCHEMA,
  assertDeviceAgentPort,
} from "../../contracts/device-agent.mjs";

export function createDeviceAgentCapabilityReader(deviceAgentValue) {
  const deviceAgent = assertDeviceAgentPort(deviceAgentValue);
  return Object.freeze({
    schema: DEVICE_AGENT_CAPABILITY_READER_SCHEMA,
    capabilities(options) {
      return deviceAgent.capabilities(options);
    },
  });
}
