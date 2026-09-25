begin;

create table if not exists public.ordax_development_oidc_enrollments (
  oidc_jti_sha256 text primary key
    check (oidc_jti_sha256 ~ '^[0-9a-f]{64}$'),
  device_id uuid not null
    references public.ordax_devices(device_id) on delete cascade,
  repository text not null
    check (char_length(repository) between 3 and 160),
  workflow_ref text not null
    check (char_length(workflow_ref) between 3 and 300),
  run_id bigint not null check (run_id > 0),
  created_at timestamptz not null default now()
);

comment on table public.ordax_development_oidc_enrollments is
  'Engineering-only one-time GitHub Actions OIDC enrollment receipts. No raw OIDC token or device token is stored.';

revoke all on table public.ordax_development_oidc_enrollments
  from public, anon, authenticated;

create or replace function public.ordax_enroll_github_runner_device_v1(
  p_stable_identity text,
  p_device_name text,
  p_token_sha256 text,
  p_token_hint text,
  p_oidc_jti_sha256 text,
  p_repository text,
  p_workflow_ref text,
  p_run_id bigint
) returns jsonb
language plpgsql
security definer
set search_path to ''
as $function$
declare
  v_device_id uuid;
  v_credential_id uuid;
begin
  if p_stable_identity is null
     or p_stable_identity !~ '^github-oidc:[0-9a-f]{64}$' then
    raise exception 'stable_identity_invalid' using errcode='22023';
  end if;
  if p_device_name is null
     or char_length(p_device_name) not between 1 and 120
     or p_device_name ~ '[[:cntrl:]]' then
    raise exception 'device_name_invalid' using errcode='22023';
  end if;
  if p_token_sha256 is null or p_token_sha256 !~ '^[0-9a-f]{64}$' then
    raise exception 'token_sha256_invalid' using errcode='22023';
  end if;
  if p_token_hint is not null and (
    char_length(p_token_hint) not between 1 and 16
    or p_token_hint !~ '^[A-Za-z0-9._-]+$'
  ) then
    raise exception 'token_hint_invalid' using errcode='22023';
  end if;
  if p_oidc_jti_sha256 is null or p_oidc_jti_sha256 !~ '^[0-9a-f]{64}$' then
    raise exception 'oidc_jti_invalid' using errcode='22023';
  end if;
  if p_repository is null or char_length(p_repository) not between 3 and 160
     or p_repository !~ '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$' then
    raise exception 'repository_invalid' using errcode='22023';
  end if;
  if p_workflow_ref is null or char_length(p_workflow_ref) not between 3 and 300
     or p_workflow_ref ~ '[[:cntrl:]]' then
    raise exception 'workflow_ref_invalid' using errcode='22023';
  end if;
  if p_run_id is null or p_run_id <= 0 then
    raise exception 'run_id_invalid' using errcode='22023';
  end if;

  insert into public.ordax_devices(
    device_name, stable_identity, mode, status, capabilities, metadata
  ) values (
    p_device_name,
    p_stable_identity,
    'developer',
    'offline',
    '{"development_v2":true,"blender":true}'::jsonb,
    jsonb_build_object(
      'enrollment_source','github-actions-oidc',
      'repository',p_repository,
      'workflow_ref',p_workflow_ref
    )
  )
  on conflict (stable_identity) do update
    set device_name=excluded.device_name,
        mode='developer',
        capabilities=public.ordax_devices.capabilities || excluded.capabilities,
        metadata=public.ordax_devices.metadata || excluded.metadata,
        updated_at=now()
  returning device_id into v_device_id;

  insert into public.ordax_development_oidc_enrollments(
    oidc_jti_sha256, device_id, repository, workflow_ref, run_id
  ) values (
    p_oidc_jti_sha256, v_device_id, p_repository, p_workflow_ref, p_run_id
  );

  update public.ordax_device_credentials
     set revoked_at=now()
   where device_id=v_device_id
     and revoked_at is null;

  insert into public.ordax_device_credentials(
    device_id, token_sha256, token_hint, scopes
  ) values (
    v_device_id,
    p_token_sha256,
    p_token_hint,
    array[
      'develop_heartbeat','develop_poll','develop_report',
      'heartbeat','poll','report'
    ]::text[]
  )
  returning credential_id into v_credential_id;

  return jsonb_build_object(
    'ok',true,
    'device_id',v_device_id,
    'credential_id',v_credential_id
  );
exception
  when unique_violation then
    raise exception 'oidc_enrollment_replay' using errcode='23505';
end
$function$;

revoke all on function public.ordax_enroll_github_runner_device_v1(
  text,text,text,text,text,text,text,bigint
) from public, anon, authenticated;
grant execute on function public.ordax_enroll_github_runner_device_v1(
  text,text,text,text,text,text,text,bigint
) to service_role;

commit;
