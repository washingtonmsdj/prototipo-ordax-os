export const IDENTITY_CREDENTIALS_SCHEMA = "ordax.identity-credentials/1";

function validEmail(value) {
  return (
    typeof value === "string"
    && value.length >= 3
    && value.length <= 320
    && value.includes("@")
    && !value.includes("\n")
    && !value.includes("\r")
  );
}

export function validateIdentityCredentialInput(value) {
  if (!value || typeof value !== "object") {
    throw new TypeError("Identity credentials are required");
  }
  const email = typeof value.email === "string" ? value.email.trim() : "";
  const password = value.password;
  if (!validEmail(email)) {
    throw new TypeError("Identity email is invalid");
  }
  if (typeof password !== "string" || password.length < 1 || password.length > 1024 || password.includes("\0")) {
    throw new TypeError("Identity password is invalid");
  }
  return Object.freeze({ email, password });
}

export function assertIdentityCredentialsPort(port) {
  if (!port || typeof port !== "object" || port.schema !== IDENTITY_CREDENTIALS_SCHEMA) {
    throw new TypeError("A compatible identity credentials port is required");
  }
  if (typeof port.signIn !== "function" || typeof port.register !== "function") {
    throw new TypeError("Identity credentials port must implement signIn() and register()");
  }
  return port;
}
