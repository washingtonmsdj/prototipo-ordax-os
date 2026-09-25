import {
  IDENTITY_CREDENTIALS_SCHEMA,
  validateIdentityCredentialInput,
} from "../../contracts/identity-credentials.mjs";

async function submit(windowRef, path, credentials) {
  const value = validateIdentityCredentialInput(credentials);
  const body = new URLSearchParams();
  body.set("email", value.email);
  body.set("password", value.password);
  const response = await windowRef.fetch(path, {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    redirect: "manual",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    },
    body: body.toString(),
  });
  if (response.status === 202) {
    return Object.freeze({ authenticated: false, confirmationRequired: true });
  }
  if (!(response.ok || response.status === 303 || response.status === 0)) {
    throw new Error(`Identity credential request failed: ${response.status}`);
  }
  return Object.freeze({ authenticated: true, confirmationRequired: false });
}

export function createSameOriginIdentityCredentials(windowRef = globalThis.window) {
  if (!windowRef || typeof windowRef.fetch !== "function") {
    throw new TypeError("Identity credentials adapter requires window.fetch");
  }
  return Object.freeze({
    schema: IDENTITY_CREDENTIALS_SCHEMA,
    signIn(credentials) {
      return submit(windowRef, "/auth/login", credentials);
    },
    register(credentials) {
      return submit(windowRef, "/auth/register", credentials);
    },
  });
}
