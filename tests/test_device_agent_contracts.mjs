import test from "node:test";
import assert from "node:assert/strict";

import {
  validateDeviceCapabilityGrant,
  validateDeviceProjectBinding,
} from "../system/contracts/device-agent.mjs";

test("local project does not require GitHub", () => {
  const binding = validateDeviceProjectBinding({
    projectId: "dioramas-biblicos",
    deviceId: "surface-owner",
    sourceType: "local",
    localRegistered: true,
  });

  assert.equal(binding.githubRepositoryId, null);
  assert.equal(binding.sourceType, "local");
});

test("GitHub-only project does not pretend to control a local device", () => {
  const binding = validateDeviceProjectBinding({
    projectId: "web-app",
    sourceType: "github",
    githubRepositoryId: "123456789",
  });

  assert.equal(binding.deviceId, null);
  assert.equal(binding.localRegistered, false);
});

test("hybrid project requires both local registration and selected GitHub repo", () => {
  assert.throws(() => validateDeviceProjectBinding({
    projectId: "ordax",
    deviceId: "surface-owner",
    sourceType: "hybrid",
    localRegistered: true,
  }));
});

test("Web and MCP use scoped grants over the same OrdaX action gateway", () => {
  for (const client of ["ordax-web", "mcp"]) {
    const grant = validateDeviceCapabilityGrant({
      accountId: "account-1",
      spaceId: "space-dev",
      projectId: "ordax",
      deviceId: "surface-owner",
      client,
      capability: "git.diff",
      mode: "read",
    });
    assert.equal(grant.actionGateway, "ordax");
  }
});

test("remote writes require approval and generic shell remains forbidden", () => {
  assert.throws(() => validateDeviceCapabilityGrant({
    accountId: "account-1",
    spaceId: "space-dev",
    projectId: "ordax",
    deviceId: "surface-owner",
    client: "mcp",
    capability: "project.text_write",
    mode: "write",
    approved: false,
  }));

  assert.throws(() => validateDeviceCapabilityGrant({
    accountId: "account-1",
    spaceId: "space-dev",
    projectId: "ordax",
    deviceId: "surface-owner",
    client: "ordax-web",
    capability: "shell.generic",
    mode: "read",
  }));
});
