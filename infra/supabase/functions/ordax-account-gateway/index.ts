import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const SESSION_SCHEMA = "prototype-ordax.public-identity-session/1";
const SYNC_BATCH_SCHEMA = "prototype-ordax.sync-batch/1";
const SYNC_SNAPSHOT_SCHEMA = "prototype-ordax.sync-snapshot/1";
const SYNC_CHANGES_SCHEMA = "prototype-ordax.sync-changes/1";
const SYNC_ACK_SCHEMA = "prototype-ordax.sync-ack/1";
const ERROR_SCHEMA = "prototype-ordax.public-identity-error/1";
const ACCESS_COOKIE = "ordax_access";
const REFRESH_COOKIE = "ordax_refresh";
const RECOVERY_COOKIE = "ordax_recovery";
const RECOVERY_SESSION_MAX_AGE = 10 * 60;
const MAX_BODY = 64 * 1024;
const MIN_REGISTRATION_PASSWORD_CHARS = 12;
const MAX_REGISTRATION_PASSWORD_CHARS = 256;
const PWNED_PASSWORDS_ORIGIN = "https://api.pwnedpasswords.com";
const PWNED_PASSWORDS_MAX_RESPONSE = 256 * 1024;
const PWNED_PASSWORDS_USER_AGENT = "OrdaX-Account-Gateway/1";
const PUBLIC_SITE_ACCOUNT_ENABLED = false;
const ACCOUNT_RECOVERY_REQUEST_ENABLED = false;
const ACCOUNT_RECOVERY_COMPLETION_ENABLED = false;
const DATA_CLASSES = new Set([
  "appearance",
  "preferences",
  "workspace-metadata",
  "app-state-metadata",
  "user-selected-cloud-content",
]);

function json(status: number, value: unknown, cookies: string[] = []) {
  const headers = new Headers({
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store, max-age=0",
    "pragma": "no-cache",
    "x-content-type-options": "nosniff",
  });
  for (const cookie of cookies) headers.append("set-cookie", cookie);
  return new Response(JSON.stringify(value) + "\n", { status, headers });
}

function error(status: number, code: string, message: string) {
  return json(status, { $schema: ERROR_SCHEMA, error: code, message });
}

function redirectResponse(location: string, cookies: string[] = []) {
  const headers = new Headers({
    location,
    "cache-control": "no-store, max-age=0",
    pragma: "no-cache",
    "x-content-type-options": "nosniff",
  });
  for (const cookie of cookies) headers.append("set-cookie", cookie);
  return new Response(null, { status: 303, headers });
}

function wantsJson(req: Request) {
  const accept = (req.headers.get("accept") ?? "").toLowerCase();
  return accept.includes("application/json") && !accept.includes("text/html");
}

function parseCookies(req: Request) {
  const result = new Map<string, string>();
  for (const part of (req.headers.get("cookie") ?? "").split(";")) {
    const index = part.indexOf("=");
    if (index < 1) continue;
    const name = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();
    if (name) result.set(name, value);
  }
  return result;
}

function cookie(name: string, value: string, maxAge: number) {
  return `${name}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;
}

function sessionCookies(access: string, refresh: string, expiresIn: number) {
  return [
    cookie(ACCESS_COOKIE, access, Math.max(60, expiresIn)),
    cookie(REFRESH_COOKIE, refresh, 60 * 60 * 24 * 30),
  ];
}

function clearCookies() {
  return [cookie(ACCESS_COOKIE, "", 0), cookie(REFRESH_COOKIE, "", 0)];
}

function recoveryCookie() {
  return cookie(RECOVERY_COOKIE, "1", RECOVERY_SESSION_MAX_AGE);
}

function clearRecoveryCookie() {
  return cookie(RECOVERY_COOKIE, "", 0);
}

function config() {
  const url = Deno.env.get("SUPABASE_URL") ?? "";
  const key = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  if (!url || !key) throw new Error("provider-unconfigured");
  return { url, key };
}

function recoveryRedirect() {
  const value = (Deno.env.get("ORDAX_ACCOUNT_RECOVERY_REDIRECT_URL") ?? "").trim();
  if (!value) return null;
  try {
    const split = new URL(value);
    if (
      split.protocol !== "https:" ||
      !split.host ||
      split.username ||
      split.password ||
      split.search ||
      split.hash
    ) return null;
    return split.toString();
  } catch {
    return null;
  }
}

async function compromisedPasswordCount(password: string) {
  const digestBuffer = await crypto.subtle.digest(
    "SHA-1",
    new TextEncoder().encode(password),
  );
  const digest = Array.from(new Uint8Array(digestBuffer))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("")
    .toUpperCase();
  const prefix = digest.slice(0, 5);
  const suffix = digest.slice(5);

  const response = await fetch(`${PWNED_PASSWORDS_ORIGIN}/range/${prefix}`, {
    method: "GET",
    headers: {
      Accept: "text/plain",
      "Add-Padding": "true",
      "User-Agent": PWNED_PASSWORDS_USER_AGENT,
    },
  });
  if (!response.ok) throw new Error("pwned-passwords-unavailable");
  const body = await response.text();
  if (body.length > PWNED_PASSWORDS_MAX_RESPONSE) {
    throw new Error("pwned-passwords-response-too-large");
  }
  for (const line of body.split(/\r?\n/)) {
    const separator = line.indexOf(":");
    if (separator < 1) continue;
    if (line.slice(0, separator).trim().toUpperCase() !== suffix) continue;
    const count = Number(line.slice(separator + 1).trim());
    if (!Number.isSafeInteger(count) || count < 0) {
      throw new Error("pwned-passwords-invalid-response");
    }
    return count;
  }
  return 0;
}

async function screenNewPassword(password: string) {
  try {
    return (await compromisedPasswordCount(password)) > 0
      ? "compromised"
      : "safe";
  } catch {
    return "unavailable";
  }
}

function client(accessToken?: string) {
  const { url, key } = config();
  return createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
    global: accessToken ? { headers: { Authorization: `Bearer ${accessToken}` } } : undefined,
  });
}

function crossSiteStateChange(req: Request) {
  if (!["POST", "PUT", "PATCH", "DELETE"].includes(req.method)) return false;
  const fetchSite = (req.headers.get("sec-fetch-site") ?? "").toLowerCase();
  if (fetchSite === "cross-site") return true;

  const forwardedHost = (req.headers.get("x-forwarded-host") ?? "").trim().toLowerCase();
  const origin = (req.headers.get("origin") ?? "").trim();
  if (!forwardedHost || !origin) return false;
  try {
    return new URL(origin).host.toLowerCase() !== forwardedHost;
  } catch {
    return true;
  }
}

function publicSiteRequest(req: Request) {
  return (req.headers.get("x-ordax-public-site") ?? "") === "1";
}

function routePath(url: URL) {
  const marker = "/ordax-account-gateway";
  const index = url.pathname.indexOf(marker);
  if (index >= 0) {
    const rest = url.pathname.slice(index + marker.length);
    return rest || "/";
  }
  return url.pathname;
}

async function boundedBody(req: Request) {
  const length = Number(req.headers.get("content-length") ?? "0");
  if (Number.isFinite(length) && length > MAX_BODY) throw new Error("request-too-large");
  const raw = new Uint8Array(await req.arrayBuffer());
  if (raw.byteLength > MAX_BODY) throw new Error("request-too-large");
  return new TextDecoder().decode(raw);
}

function syncObject(item: Record<string, unknown>) {
  return {
    objectId: item.stable_object_id,
    dataClass: item.data_class,
    objectSchemaVersion: item.object_schema_version,
    resolverVersion: item.resolver_version,
    serverRevision: item.server_revision,
    tombstone: item.tombstone,
    payload: item.payload,
    updatedAt: item.updated_at ?? item.changed_at,
  };
}

async function authenticated(req: Request) {
  const cookies = parseCookies(req);
  const access = cookies.get(ACCESS_COOKIE) ?? "";
  const refresh = cookies.get(REFRESH_COOKIE) ?? "";
  if (access) {
    const supabase = client();
    const { data, error } = await supabase.auth.getUser(access);
    if (!error && data.user) return { access, user: data.user, cookies: [] as string[] };
  }
  if (refresh) {
    const supabase = client();
    const { data, error } = await supabase.auth.refreshSession({ refresh_token: refresh });
    if (!error && data.session && data.user) {
      return {
        access: data.session.access_token,
        user: data.user,
        cookies: sessionCookies(data.session.access_token, data.session.refresh_token, data.session.expires_in),
      };
    }
  }
  return { access: "", user: null, cookies: clearCookies() };
}

async function recovery(req: Request) {
  if (!ACCOUNT_RECOVERY_REQUEST_ENABLED) {
    return error(503, "account-recovery-disabled", "A recuperação da Conta OrdaX ainda não foi ativada.");
  }
  const redirectTo = recoveryRedirect();
  if (!redirectTo) {
    return error(503, "account-recovery-unavailable", "A recuperação da Conta OrdaX ainda não está configurada.");
  }
  let raw = "";
  try { raw = await boundedBody(req); } catch {
    return error(413, "request-too-large", "A solicitação excede o limite permitido.");
  }
  const type = req.headers.get("content-type") ?? "";
  if (!type.toLowerCase().startsWith("application/x-www-form-urlencoded")) {
    return wantsJson(req)
      ? error(400, "invalid-recovery-form", "Revise o e-mail informado.")
      : redirectResponse("/login/?erro=recuperacao-formulario");
  }
  const form = new URLSearchParams(raw);
  const email = (form.get("email") ?? "").trim();
  if (
    email.length < 3 ||
    email.length > 320 ||
    !email.includes("@") ||
    email.includes("\n") ||
    email.includes("\r")
  ) {
    return wantsJson(req)
      ? error(400, "invalid-recovery-form", "Revise o e-mail informado.")
      : redirectResponse("/login/?erro=recuperacao-formulario");
  }

  try {
    const supabase = client();
    const { error: recoveryError } = await supabase.auth.resetPasswordForEmail(email, { redirectTo });
    if (recoveryError) {
      const status = Number(recoveryError.status ?? 0);
      if (status === 429) {
        return wantsJson(req)
          ? error(429, "account-recovery-rate-limited", "Tente novamente mais tarde.")
          : redirectResponse("/login/?erro=recuperacao-limite");
      }
      if (!status || status >= 500) {
        return wantsJson(req)
          ? error(503, "account-recovery-unavailable", "A recuperação da Conta OrdaX está temporariamente indisponível.")
          : redirectResponse("/login/?erro=recuperacao-indisponivel");
      }
      // Provider-level 4xx is intentionally normalized to avoid account enumeration.
    }
  } catch {
    return wantsJson(req)
      ? error(503, "account-recovery-unavailable", "A recuperação da Conta OrdaX está temporariamente indisponível.")
      : redirectResponse("/login/?erro=recuperacao-indisponivel");
  }

  return wantsJson(req)
    ? json(202, {
        recoveryRequested: true,
        message: "Se a conta puder ser recuperada, as instruções serão enviadas por e-mail.",
      })
    : redirectResponse("/login/?recuperacao=verifique-email");
}

async function verifyRecoveryLink(req: Request, url: URL) {
  if (!ACCOUNT_RECOVERY_COMPLETION_ENABLED) {
    return error(503, "account-recovery-completion-disabled", "A conclusão da recuperação da Conta OrdaX ainda não foi ativada.");
  }
  const tokenHash = url.searchParams.get("token_hash") ?? "";
  const recoveryType = url.searchParams.get("type") ?? "";
  if (
    recoveryType !== "recovery" ||
    tokenHash.length < 16 ||
    tokenHash.length > 2048 ||
    /\s/.test(tokenHash)
  ) {
    return error(400, "invalid-recovery-link", "O link de recuperação é inválido ou expirou.");
  }

  try {
    const supabase = client();
    const { data, error: verifyError } = await supabase.auth.verifyOtp({
      token_hash: tokenHash,
      type: "recovery",
    });
    if (verifyError || !data.session) {
      return error(400, "invalid-recovery-link", "O link de recuperação é inválido ou expirou.");
    }
    const expiresIn = Math.min(
      Number(data.session.expires_in ?? RECOVERY_SESSION_MAX_AGE),
      RECOVERY_SESSION_MAX_AGE,
    );
    return redirectResponse(
      "/recuperar/nova-senha/",
      [
        ...sessionCookies(
          data.session.access_token,
          data.session.refresh_token,
          expiresIn,
        ),
        recoveryCookie(),
      ],
    );
  } catch {
    return error(400, "invalid-recovery-link", "O link de recuperação é inválido ou expirou.");
  }
}

async function updateRecoveryPassword(req: Request) {
  if (!ACCOUNT_RECOVERY_COMPLETION_ENABLED) {
    return error(503, "account-recovery-completion-disabled", "A conclusão da recuperação da Conta OrdaX ainda não foi ativada.");
  }
  const cookies = parseCookies(req);
  if (cookies.get(RECOVERY_COOKIE) !== "1") {
    return error(401, "recovery-session-required", "Inicie novamente a recuperação da Conta OrdaX.");
  }

  const session = await authenticated(req);
  if (!session.user || !session.access) {
    return json(
      401,
      {
        $schema: ERROR_SCHEMA,
        error: "recovery-session-required",
        message: "Inicie novamente a recuperação da Conta OrdaX.",
      },
      [...session.cookies, clearRecoveryCookie()],
    );
  }

  let raw = "";
  try { raw = await boundedBody(req); } catch {
    return error(413, "request-too-large", "A solicitação excede o limite permitido.");
  }
  const type = req.headers.get("content-type") ?? "";
  if (!type.toLowerCase().startsWith("application/x-www-form-urlencoded")) {
    return error(400, "recovery-password-policy", "Use uma senha válida e confirme exatamente o mesmo valor.");
  }
  const form = new URLSearchParams(raw);
  const password = form.get("password") ?? "";
  const confirmation = form.get("password_confirmation") ?? "";
  if (
    password !== confirmation ||
    password.length < MIN_REGISTRATION_PASSWORD_CHARS ||
    password.length > MAX_REGISTRATION_PASSWORD_CHARS ||
    password.includes("\0")
  ) {
    return error(400, "recovery-password-policy", "Use uma senha válida e confirme exatamente o mesmo valor.");
  }

  const screening = await screenNewPassword(password);
  if (screening === "compromised") {
    return error(400, "compromised-password", "Escolha outra senha; esta senha aparece em bases públicas de credenciais comprometidas.");
  }
  if (screening === "unavailable") {
    return error(503, "password-screening-unavailable", "A validação de segurança da senha está temporariamente indisponível.");
  }

  try {
    const { url, key } = config();
    const response = await fetch(`${url}/auth/v1/user`, {
      method: "PUT",
      headers: {
        apikey: key,
        Authorization: `Bearer ${session.access}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ password }),
    });
    if (!response.ok) {
      if (response.status === 429) {
        return error(429, "account-recovery-rate-limited", "Tente novamente mais tarde.");
      }
      return error(503, "account-recovery-unavailable", "Não foi possível concluir a recuperação da Conta OrdaX.");
    }
    try {
      await client(session.access).auth.signOut({ scope: "local" });
    } catch {
      // Password was already changed; local cookie clearing still wins.
    }
  } catch {
    return error(503, "account-recovery-unavailable", "Não foi possível concluir a recuperação da Conta OrdaX.");
  }

  return wantsJson(req)
    ? json(
        200,
        { recoveryCompleted: true },
        [...clearCookies(), clearRecoveryCookie()],
      )
    : redirectResponse(
        "/login/?recuperacao=concluida",
        [...clearCookies(), clearRecoveryCookie()],
      );
}

async function credentials(req: Request, register: boolean) {
  let raw = "";
  try { raw = await boundedBody(req); } catch { return error(413, "request-too-large", "A solicitação excede o limite permitido."); }
  const type = req.headers.get("content-type") ?? "";
  if (!type.toLowerCase().startsWith("application/x-www-form-urlencoded")) {
    return wantsJson(req)
      ? error(400, "invalid-credentials-form", "Revise o e-mail e a senha informados.")
      : redirectResponse(register ? "/cadastro/?erro=formulario" : "/login/?erro=formulario");
  }
  const form = new URLSearchParams(raw);
  const email = (form.get("email") ?? "").trim();
  const password = form.get("password") ?? "";
  if (!email || !password) {
    return wantsJson(req)
      ? error(400, "invalid-credentials-form", "Revise o e-mail e a senha informados.")
      : redirectResponse(register ? "/cadastro/?erro=formulario" : "/login/?erro=formulario");
  }
  if (
    register &&
    (password.length < MIN_REGISTRATION_PASSWORD_CHARS ||
      password.length > MAX_REGISTRATION_PASSWORD_CHARS)
  ) {
    return wantsJson(req)
      ? error(400, "registration-password-policy", "Use uma senha com pelo menos 12 caracteres.")
      : redirectResponse("/cadastro/?erro=senha");
  }

  if (register) {
    const screening = await screenNewPassword(password);
    if (screening === "compromised") {
      return wantsJson(req)
        ? error(400, "compromised-password", "Escolha outra senha; esta senha aparece em bases públicas de credenciais comprometidas.")
        : redirectResponse("/cadastro/?erro=senha-comprometida");
    }
    if (screening === "unavailable") {
      return wantsJson(req)
        ? error(503, "password-screening-unavailable", "A validação de segurança da senha está temporariamente indisponível.")
        : redirectResponse("/cadastro/?erro=seguranca-indisponivel");
    }
  }

  const supabase = client();
  const result = register
    ? await supabase.auth.signUp({ email, password })
    : await supabase.auth.signInWithPassword({ email, password });

  if (result.error) {
    if (!wantsJson(req)) {
      return redirectResponse(register ? "/cadastro/?erro=cadastro" : "/login/?erro=credenciais");
    }
    return error(register ? 400 : 401, register ? "registration-failed" : "authentication-failed", "Não foi possível concluir esta operação de conta.");
  }
  if (!result.data.session) {
    return wantsJson(req)
      ? json(202, { authenticated: false, confirmationRequired: true })
      : redirectResponse("/login/?cadastro=verifique-email");
  }
  const cookies = sessionCookies(
    result.data.session.access_token,
    result.data.session.refresh_token,
    result.data.session.expires_in,
  );
  return wantsJson(req)
    ? json(200, { authenticated: true, confirmationRequired: false }, cookies)
    : redirectResponse("/conta/", cookies);
}

Deno.serve(async (req: Request) => {
  const url = new URL(req.url);
  const path = routePath(url);

  if (crossSiteStateChange(req)) {
    return error(403, "cross-site-request-rejected", "Solicitação de outra origem rejeitada.");
  }

  if (publicSiteRequest(req) && !PUBLIC_SITE_ACCOUNT_ENABLED) {
    if (path === "/auth/login" && req.method === "GET") return redirectResponse("/login/");
    if (path === "/auth/register" && req.method === "GET") return redirectResponse("/cadastro/");
    if (path === "/auth/logout" && req.method === "POST") {
      return wantsJson(req)
        ? json(200, { signedOut: true }, clearCookies())
        : redirectResponse("/", clearCookies());
    }
    if (path === "/auth/session" && req.method === "GET") {
      return json(200, {
        $schema: SESSION_SCHEMA,
        authenticated: false,
        provider: "gated",
        status: "anonymous",
      }, clearCookies());
    }
    if (path.startsWith("/auth/") || path.startsWith("/sync/") || path.startsWith("/account/")) {
      return error(503, "public-account-access-disabled", "O acesso público à Conta OrdaX ainda não foi ativado.");
    }
  }

  if (path === "/health" && req.method === "GET") {
    return json(200, { status: "ok", service: "ordax-account-gateway", version: 11 });
  }

  if (path === "/auth/session" && req.method === "GET") {
    try {
      const session = await authenticated(req);
      if (!session.user) {
        return json(200, { $schema: SESSION_SCHEMA, authenticated: false, provider: "supabase", status: "anonymous" }, session.cookies);
      }
      return json(200, {
        $schema: SESSION_SCHEMA,
        authenticated: true,
        provider: "supabase",
        status: "authenticated",
        subject: session.user.id,
        email: session.user.email ?? null,
      }, session.cookies);
    } catch {
      return error(503, "identity-provider-unavailable", "O serviço de identidade OrdaX está indisponível.");
    }
  }

  if (path === "/auth/login" && req.method === "GET") return redirectResponse("/login/");
  if (path === "/auth/register" && req.method === "GET") return redirectResponse("/cadastro/");
  if (path === "/auth/login" && req.method === "POST") return credentials(req, false);
  if (path === "/auth/register" && req.method === "POST") return credentials(req, true);
  if (path === "/auth/recover" && req.method === "POST") return recovery(req);
  if (path === "/auth/recover/verify" && req.method === "GET") return verifyRecoveryLink(req, url);
  if (path === "/auth/recover/complete" && req.method === "POST") return updateRecoveryPassword(req);

  if (path === "/auth/logout" && req.method === "POST") {
    try {
      const access = parseCookies(req).get(ACCESS_COOKIE);
      if (access) await client(access).auth.signOut({ scope: "local" });
    } catch {
      // Idempotent logout: cookie removal still wins.
    }
    return wantsJson(req)
      ? json(200, { signedOut: true }, clearCookies())
      : redirectResponse("/", clearCookies());
  }


  if (path === "/account/export" && req.method === "GET") {
    const session = await authenticated(req);
    if (!session.user || !session.access) {
      return json(401, {
        $schema: ERROR_SCHEMA,
        error: "authentication-required",
        message: "Entre na Conta OrdaX para exportar seus dados.",
      }, session.cookies);
    }
    const supabase = client(session.access);
    const { data, error: rpcError } = await supabase.rpc("ordax_account_export_v1");
    if (
      rpcError ||
      !data ||
      typeof data !== "object" ||
      data.$schema !== "prototype-ordax.account-export/1"
    ) {
      return error(502, "account-export-failed", "Não foi possível gerar a exportação da Conta OrdaX.");
    }
    return json(200, data, session.cookies);
  }

  if (path === "/sync/snapshot" && req.method === "GET") {
    const session = await authenticated(req);
    if (!session.user || !session.access) {
      return json(401, { $schema: ERROR_SCHEMA, error: "authentication-required", message: "Entre na Conta OrdaX para sincronizar." }, session.cookies);
    }
    const limit = Number(url.searchParams.get("limit") ?? "200");
    if (!Number.isInteger(limit) || limit < 1 || limit > 500) {
      return error(400, "invalid-sync-query", "Consulta de sincronização inválida.");
    }
    const supabase = client(session.access);
    const { data, error: rpcError } = await supabase.rpc("ordax_sync_snapshot_v1", {
      p_limit: limit,
    });
    if (
      rpcError ||
      !data ||
      typeof data !== "object" ||
      !Number.isSafeInteger(Number(data.cursor)) ||
      !Array.isArray(data.objects)
    ) return error(502, "sync-snapshot-failed", "Não foi possível ler o snapshot sincronizado.");

    return json(200, {
      $schema: SYNC_SNAPSHOT_SCHEMA,
      cursor: Number(data.cursor),
      objects: data.objects.map((item: Record<string, unknown>) => syncObject(item)),
    }, session.cookies);
  }

  if (path === "/sync/changes" && req.method === "GET") {
    const session = await authenticated(req);
    if (!session.user || !session.access) {
      return json(401, { $schema: ERROR_SCHEMA, error: "authentication-required", message: "Entre na Conta OrdaX para sincronizar." }, session.cookies);
    }
    const afterCursor = Number(url.searchParams.get("afterCursor") ?? "0");
    const limit = Number(url.searchParams.get("limit") ?? "200");
    if (
      !Number.isSafeInteger(afterCursor) || afterCursor < 0 ||
      !Number.isInteger(limit) || limit < 1 || limit > 500
    ) return error(400, "invalid-sync-query", "Consulta de sincronização inválida.");

    const supabase = client(session.access);
    const { data, error: rpcError } = await supabase.rpc("ordax_pull_sync_changes_v1", {
      p_after_cursor: afterCursor,
      p_limit: limit,
    });
    if (rpcError || !Array.isArray(data)) {
      return error(502, "sync-pull-failed", "Não foi possível ler as mudanças sincronizadas.");
    }
    const changes = data.map((item: Record<string, unknown>) => ({
      cursor: Number(item.change_cursor),
      ...syncObject(item),
    }));
    const nextCursor = changes.length ? changes[changes.length - 1].cursor : afterCursor;
    return json(200, {
      $schema: SYNC_CHANGES_SCHEMA,
      afterCursor,
      nextCursor,
      changes,
    }, session.cookies);
  }

  if (path === "/sync/objects" && req.method === "GET") {
    const session = await authenticated(req);
    if (!session.user || !session.access) {
      return json(401, { $schema: ERROR_SCHEMA, error: "authentication-required", message: "Entre na Conta OrdaX para sincronizar." }, session.cookies);
    }
    const after = Number(url.searchParams.get("afterRevision") ?? "0");
    const limit = Number(url.searchParams.get("limit") ?? "200");
    if (!Number.isInteger(after) || after < 0 || !Number.isInteger(limit) || limit < 1 || limit > 500) {
      return error(400, "invalid-sync-query", "Consulta de sincronização inválida.");
    }
    const supabase = client(session.access);
    const { data, error: rpcError } = await supabase.rpc("ordax_list_sync_objects_v1", {
      p_after_revision: after,
      p_limit: limit,
    });
    if (rpcError || !Array.isArray(data)) return error(502, "sync-read-failed", "Não foi possível ler o estado sincronizado.");
    const objects = data.map((item: Record<string, unknown>) => syncObject(item));
    return json(200, { $schema: SYNC_BATCH_SCHEMA, objects }, session.cookies);
  }

  if (path === "/sync/mutate" && req.method === "POST") {
    const session = await authenticated(req);
    if (!session.user || !session.access) {
      return json(401, { $schema: ERROR_SCHEMA, error: "authentication-required", message: "Entre na Conta OrdaX para sincronizar." }, session.cookies);
    }
    let mutation: Record<string, unknown>;
    try {
      mutation = JSON.parse(await boundedBody(req));
    } catch {
      return error(400, "invalid-sync-mutation", "A alteração de sincronização é inválida.");
    }
    if (
      mutation.$schema !== "ordax.sync-mutation/1" ||
      typeof mutation.dataClass !== "string" ||
      !DATA_CLASSES.has(mutation.dataClass)
    ) return error(400, "invalid-sync-mutation", "A alteração de sincronização é inválida.");

    const supabase = client(session.access);
    const { data, error: rpcError } = await supabase.rpc("ordax_apply_sync_mutation_v2", {
      p_idempotency_key: mutation.idempotencyKey,
      p_data_class: mutation.dataClass,
      p_stable_object_id: mutation.objectId,
      p_object_schema_version: mutation.objectSchemaVersion,
      p_resolver_version: mutation.resolverVersion ?? 1,
      p_base_server_revision: mutation.baseServerRevision,
      p_tombstone: mutation.operation === "delete",
      p_payload: mutation.payload ?? {},
    });
    if (rpcError || !Array.isArray(data) || data.length !== 1) return error(502, "sync-write-failed", "Não foi possível gravar o estado sincronizado.");
    const item = data[0] as Record<string, unknown>;
    return json(200, {
      $schema: SYNC_ACK_SCHEMA,
      objectId: mutation.objectId,
      dataClass: mutation.dataClass,
      serverRevision: item.server_revision,
      tombstone: item.tombstone,
      applied: item.applied,
      conflict: item.conflict,
      changeCursor: item.change_cursor === null ? null : Number(item.change_cursor),
    }, session.cookies);
  }

  if (
    (path.startsWith("/auth/") || path.startsWith("/sync/") || path.startsWith("/account/")) &&
    !["GET", "POST"].includes(req.method)
  ) {
    return error(405, "method-not-allowed", "Método não permitido.");
  }
  return error(404, "gateway-route-not-found", "Rota inexistente.");
});
