import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.55.0";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "pragma": "no-cache",
  "x-content-type-options": "nosniff",
};

function respond(status: number, body: Record<string, unknown>) {
  return new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") {
    return respond(405, { ok: false, error: "method_not_allowed" });
  }
  if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
    return respond(503, { ok: false, error: "backend_not_configured" });
  }

  const rawToken = req.headers.get("X-Ordax-Device-Token") ?? "";
  if (rawToken.length < 32 || rawToken.length > 512) {
    return respond(401, { ok: false, error: "device_auth_required" });
  }

  try {
    const tokenSha256 = await sha256Hex(rawToken);
    const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
      auth: { persistSession: false },
    });

    const { data: credentials, error: credentialError } = await supabase
      .from("ordax_device_credentials")
      .select("credential_id,device_id")
      .eq("token_sha256", tokenSha256)
      .is("revoked_at", null)
      .limit(2);

    if (credentialError) {
      console.error("development_device_identify_lookup_failed", credentialError.code);
      return respond(500, { ok: false, error: "identity_lookup_failed" });
    }
    if (!Array.isArray(credentials) || credentials.length !== 1) {
      return respond(401, { ok: false, error: "invalid_device_token" });
    }

    const credential = credentials[0] as { credential_id: string; device_id: string };
    const { data: device, error: deviceError } = await supabase
      .from("ordax_devices")
      .select("device_id,mode")
      .eq("device_id", credential.device_id)
      .maybeSingle();

    if (deviceError) {
      console.error("development_device_identify_device_failed", deviceError.code);
      return respond(500, { ok: false, error: "identity_lookup_failed" });
    }
    if (!device || device.mode !== "developer") {
      return respond(403, { ok: false, error: "device_not_development" });
    }

    const { error: touchError } = await supabase
      .from("ordax_device_credentials")
      .update({ last_used_at: new Date().toISOString() })
      .eq("credential_id", credential.credential_id);

    if (touchError) {
      console.error("development_device_identify_touch_failed", touchError.code);
      return respond(500, { ok: false, error: "identity_update_failed" });
    }

    return respond(200, {
      ok: true,
      protocol: "development-v2",
      control_plane: "ordax-control-plane",
      device_id: device.device_id,
    });
  } catch (error) {
    console.error(
      "ordax-development-device-identify",
      error instanceof Error ? error.name : "unknown",
    );
    return respond(500, { ok: false, error: "identify_internal_error" });
  }
});
