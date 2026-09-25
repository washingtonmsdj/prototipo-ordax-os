import assert from "node:assert/strict";
import test from "node:test";

import {
  DEVICE_AGENT_CAPABILITIES_SCHEMA,
  DEVICE_AGENT_PORT_SCHEMA,
  validateDeviceAgentCapabilitiesSnapshot,
} from "../system/contracts/device-agent.mjs";
import { createDeviceAgentCapabilityReader } from "../system/services/device-agent/capability-reader.mjs";
import {
  probeProjectsDeviceAgent,
} from "../system/apps/projects/device-agent-status.mjs";
import {
  projectsDeviceAgentMessageId,
} from "../system/apps/projects/ui/device-agent-status.mjs";

function fakeAgent(capabilitiesImpl) {
  let executeCalls = 0;
  const port = Object.freeze({
    schema: DEVICE_AGENT_PORT_SCHEMA,
    capabilities: capabilitiesImpl,
    execute() {
      executeCalls += 1;
      throw new Error("Projects status must never execute Device Agent actions");
    },
  });
  return {
    port,
    reader: createDeviceAgentCapabilityReader(port),
    executeCalls: () => executeCalls,
  };
}

test("Projects reads typed Device Agent capabilities through a capability-only reader", async () => {
  const agent = fakeAgent(async ({ client }) => {
    assert.equal(client, "ordax-local");
    return {
      schema: DEVICE_AGENT_CAPABILITIES_SCHEMA,
      state: "ready",
      capabilities: [
        { id: "files.project-read", modes: ["read"] },
        { id: "git.status", modes: ["read", "write"] },
      ],
    };
  });

  assert.equal("execute" in agent.reader, false);
  const status = await probeProjectsDeviceAgent(agent.reader);
  assert.deepEqual(status, {
    schema: "ordax.projects-device-agent-status/1",
    state: "ready",
    capabilityCount: 2,
    readCount: 2,
    writeCount: 1,
    mutationAuthority: "none",
  });
  assert.equal(projectsDeviceAgentMessageId(status), "projects.deviceAgent.ready");
  assert.equal(agent.executeCalls(), 0);
});

test("missing Device Agent capability reader remains invisible to Projects", async () => {
  assert.equal(await probeProjectsDeviceAgent(null), null);
});

test("full mutable Device Agent port is not accepted as the Projects capability boundary", async () => {
  const agent = fakeAgent(async () => ({
    schema: DEVICE_AGENT_CAPABILITIES_SCHEMA,
    state: "ready",
    capabilities: [],
  }));
  const status = await probeProjectsDeviceAgent(agent.port);
  assert.equal(status.state, "degraded");
  assert.equal(status.mutationAuthority, "none");
  assert.equal(agent.executeCalls(), 0);
});

test("capability failure degrades only the optional Projects integration", async () => {
  const agent = fakeAgent(async () => {
    throw new Error("agent offline");
  });
  const status = await probeProjectsDeviceAgent(agent.reader, { timeoutMs: 20 });
  assert.equal(status.state, "degraded");
  assert.equal(status.capabilityCount, 0);
  assert.equal(status.mutationAuthority, "none");
  assert.equal(projectsDeviceAgentMessageId(status), "projects.deviceAgent.degraded");
  assert.equal(agent.executeCalls(), 0);
});

test("hung capability discovery is bounded and degrades instead of blocking Projects", async () => {
  const agent = fakeAgent(() => new Promise(() => {}));
  const started = Date.now();
  const status = await probeProjectsDeviceAgent(agent.reader, { timeoutMs: 10 });
  const elapsed = Date.now() - started;
  assert.equal(status.state, "degraded");
  assert.ok(elapsed < 1000, `bounded probe took ${elapsed}ms`);
  assert.equal(agent.executeCalls(), 0);
});

test("forbidden or malformed capability discovery fails closed into degraded presentation", async () => {
  const forbidden = fakeAgent(async () => ({
    schema: DEVICE_AGENT_CAPABILITIES_SCHEMA,
    state: "ready",
    capabilities: [{ id: "shell.generic", modes: ["read"] }],
  }));
  assert.equal((await probeProjectsDeviceAgent(forbidden.reader)).state, "degraded");

  assert.throws(
    () => validateDeviceAgentCapabilitiesSnapshot({
      schema: DEVICE_AGENT_CAPABILITIES_SCHEMA,
      state: "ready",
      capabilities: [{ id: "git.status", modes: ["read", "read"] }],
    }),
    /modes must be unique/,
  );
});
