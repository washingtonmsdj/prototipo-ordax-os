begin;

-- Engineering-only Device Agent extension. Product authority is untouched.
-- Reference semantics reviewed from:
-- washingtonmsdj/novo-ordax-os@49fe41fa67d9032f2e349e86592304e64d6c2d88
-- This migration is the clean-room prototype source owner for the extension.

alter table public.ordax_capability_grants
  drop constraint if exists ordax_capability_grants_check2;

alter table public.ordax_capability_grants
  add constraint ordax_capability_grants_check2 check (
    (authority='OBSERVE' and capability in (
      'ordax.dev.status','ordax.dev.health','ordax.dev.logs.read','ordax.dev.file.read',
      'ordax.dev.git.status','ordax.dev.git.diff','ordax.surface.screenshot','ordax.dev.lab.status'
    )) or
    (authority='DEVELOP' and capability in (
      'ordax.dev.status','ordax.dev.health','ordax.dev.logs.read','ordax.dev.file.read',
      'ordax.dev.git.status','ordax.dev.git.diff','ordax.dev.file.patch',
      'ordax.dev.command.run','ordax.dev.test.run','ordax.dev.service.restart',
      'ordax.dev.device.enroll','ordax.dev.lab.status','ordax.dev.adapter.invoke'
    )) or
    (authority='SYSTEM' and capability in (
      'ordax.dev.status','ordax.dev.health','ordax.dev.logs.read','ordax.dev.file.read',
      'ordax.dev.git.status','ordax.dev.git.diff','ordax.dev.file.patch',
      'ordax.dev.command.run','ordax.dev.test.run','ordax.dev.service.restart',
      'ordax.dev.system.exec','ordax.dev.boot-capsule.preflight','ordax.dev.boot-capsule.stage',
      'ordax.dev.system.reboot','ordax.dev.system.deploy','ordax.dev.device.enroll',
      'ordax.dev.adapter.invoke'
    ))
  );

alter table public.ordax_develop_jobs
  drop constraint if exists ordax_develop_jobs_capability_check;

alter table public.ordax_develop_jobs
  add constraint ordax_develop_jobs_capability_check check (
    capability in (
      'ordax.dev.file.patch','ordax.dev.command.run','ordax.dev.test.run',
      'ordax.dev.service.restart','ordax.dev.adapter.invoke','ordax.dev.system.exec',
      'ordax.dev.boot-capsule.preflight','ordax.dev.boot-capsule.stage'
    )
  );

create or replace function public.ordax_develop_resource_scope_v2(
  p_device_id uuid,
  p_capability text,
  p_payload jsonb
) returns text
language plpgsql
immutable
set search_path to ''
as $function$
declare
  v_path text;
  v_id text;
  v_adapter text;
  v_action text;
  v_project text;
begin
  if p_device_id is null or p_payload is null or jsonb_typeof(p_payload)<>'object' then
    raise exception 'resource_scope_context_invalid' using errcode='22023';
  end if;
  if p_capability='ordax.dev.file.patch' then
    v_path:=p_payload->>'path';
    if v_path is null or char_length(v_path)<1 or char_length(v_path)>256
       or v_path ~ '(^/|(^|/)\.\.(/|$)|//|[[:cntrl:]])'
       or v_path !~ '^[A-Za-z0-9._/@+-]+$' then
      raise exception 'resource_scope_path_invalid' using errcode='22023';
    end if;
    return 'workspace:'||p_device_id::text||':path:'||v_path;
  elsif p_capability='ordax.dev.service.restart' then
    v_id:=p_payload->>'service_id';
    if v_id is null or char_length(v_id)<1 or char_length(v_id)>96
       or v_id !~ '^[A-Za-z0-9._-]+$' then
      raise exception 'resource_scope_service_invalid' using errcode='22023';
    end if;
    return 'device:'||p_device_id::text||':service:'||v_id;
  elsif p_capability in ('ordax.dev.command.run','ordax.dev.test.run') then
    return 'workspace:'||p_device_id::text||':exclusive';
  elsif p_capability='ordax.dev.adapter.invoke' then
    v_adapter:=p_payload->>'adapter';
    v_action:=p_payload->>'action';
    v_project:=p_payload->>'project';
    if v_adapter<>'blender'
       or v_action is null or v_action !~ '^blender\.[a-z][a-z0-9_.]{1,95}$'
       or v_project is null or v_project !~ '^[A-Za-z0-9._-]{1,96}$' then
      raise exception 'resource_scope_adapter_invalid' using errcode='22023';
    end if;
    return 'workspace:'||p_device_id::text||':adapter:'||v_adapter||':project:'||v_project;
  elsif p_capability in ('ordax.dev.system.exec','ordax.dev.boot-capsule.preflight','ordax.dev.boot-capsule.stage') then
    return 'device:'||p_device_id::text||':system:exclusive';
  end if;
  raise exception 'resource_scope_capability_invalid' using errcode='22023';
end
$function$;

create or replace function public.ordax_enqueue_develop_job_v2(
  p_session_id uuid,
  p_capability text,
  p_payload jsonb default '{}'::jsonb,
  p_requested_by text default 'devop:agent',
  p_ttl_seconds integer default 3600,
  p_priority smallint default 0,
  p_correlation_id uuid default gen_random_uuid(),
  p_idempotency_key text default null,
  p_workspace_id text default 'default'
) returns table(
  job_id uuid,effect_id uuid,status text,correlation_id uuid,
  payload_sha256 text,resource_scope text,created boolean
)
language plpgsql
security definer
set search_path to ''
as $function$
declare
  v_auth jsonb;
  v_device_id uuid;
  v_actor_id uuid;
  v_device_mode text;
  v_authority text;
  v_existing public.ordax_develop_jobs%rowtype;
  v_inserted public.ordax_develop_jobs%rowtype;
  v_scope text;
  v_payload_sha text;
  v_now timestamptz := statement_timestamp();
  v_device_active bigint;
  v_session_active bigint;
  v_device_recent bigint;
  v_device_total bigint;
  v_session_total bigint;
  v_device_payload_bytes bigint;
  v_new_payload_bytes bigint;
begin
  if p_session_id is null or p_capability is null then
    raise exception 'enqueue_context_required' using errcode='22023';
  end if;
  if p_capability not in (
    'ordax.dev.file.patch','ordax.dev.command.run','ordax.dev.test.run',
    'ordax.dev.service.restart','ordax.dev.adapter.invoke','ordax.dev.system.exec','ordax.dev.boot-capsule.preflight','ordax.dev.boot-capsule.stage'
  ) then
    raise exception 'develop_capability_not_routable' using errcode='22023';
  end if;
  if p_payload is null or jsonb_typeof(p_payload)<>'object'
     or octet_length(p_payload::text)>400000 then
    raise exception 'payload_invalid' using errcode='22023';
  end if;
  if p_workspace_id is null or p_workspace_id !~ '^[A-Za-z0-9._-]{1,96}$' then
    raise exception 'workspace_id_invalid' using errcode='22023';
  end if;
  if p_requested_by is null or char_length(p_requested_by) not between 1 and 128
     or p_requested_by !~ '^[A-Za-z0-9._:@/-]+$' then
    raise exception 'requested_by_invalid' using errcode='22023';
  end if;
  if p_ttl_seconds is null or p_ttl_seconds<60 or p_ttl_seconds>86400 then
    raise exception 'job_ttl_out_of_bounds' using errcode='22023';
  end if;
  if p_priority is null or p_priority<-100 or p_priority>100 then
    raise exception 'priority_out_of_bounds' using errcode='22023';
  end if;
  if p_correlation_id is null then
    raise exception 'correlation_id_required' using errcode='22023';
  end if;
  if p_idempotency_key is not null and (
    char_length(p_idempotency_key) not between 1 and 160
    or p_idempotency_key !~ '^[A-Za-z0-9._:@/-]+$'
  ) then
    raise exception 'idempotency_key_invalid' using errcode='22023';
  end if;

  v_auth:=public.ordax_authorize_development_capability(p_session_id,p_capability,v_now);
  if coalesce((v_auth->>'ok')::boolean,false) is not true
     or v_auth->>'authority' not in ('DEVELOP','SYSTEM') then
    raise exception 'develop_capability_denied' using errcode='42501';
  end if;
  v_authority:=v_auth->>'authority';
  if p_capability in ('ordax.dev.system.exec','ordax.dev.boot-capsule.preflight','ordax.dev.boot-capsule.stage') and v_authority<>'SYSTEM' then
    raise exception 'system_authority_required' using errcode='42501';
  end if;
  v_device_id:=(v_auth->>'device_id')::uuid;
  select s.actor_id into v_actor_id
    from public.ordax_actor_sessions s
   where s.session_id=p_session_id and s.state='active' and s.expires_at>v_now;
  if v_actor_id is null then
    raise exception 'active_actor_session_required' using errcode='42501';
  end if;
  select d.mode into v_device_mode from public.ordax_devices d where d.device_id=v_device_id;
  if v_device_mode is distinct from 'developer' then
    raise exception 'device_not_development' using errcode='42501';
  end if;

  if p_capability='ordax.dev.file.patch' then
    if not (p_payload ?& array['path','expected_sha256','content_b64'])
       or (p_payload-'path'-'expected_sha256'-'content_b64')<>'{}'::jsonb
       or coalesce(p_payload->>'expected_sha256','') !~ '^[0-9A-Fa-f]{64}$'
       or coalesce(p_payload->>'content_b64','') !~ '^[A-Za-z0-9+/]*={0,2}$'
       or char_length(coalesce(p_payload->>'content_b64',''))>350000 then
      raise exception 'file_patch_payload_invalid' using errcode='22023';
    end if;
  elsif p_capability='ordax.dev.command.run' then
    if not (p_payload ? 'command_id') or (p_payload-'command_id')<>'{}'::jsonb
       or coalesce(p_payload->>'command_id','') !~ '^[A-Za-z0-9._-]{1,96}$' then
      raise exception 'command_payload_invalid' using errcode='22023';
    end if;
  elsif p_capability='ordax.dev.test.run' then
    if not (p_payload ? 'test_id') or (p_payload-'test_id')<>'{}'::jsonb
       or coalesce(p_payload->>'test_id','') !~ '^[A-Za-z0-9._-]{1,96}$' then
      raise exception 'test_payload_invalid' using errcode='22023';
    end if;
  elsif p_capability='ordax.dev.service.restart' then
    if not (p_payload ? 'service_id') or (p_payload-'service_id')<>'{}'::jsonb
       or coalesce(p_payload->>'service_id','') !~ '^[A-Za-z0-9._-]{1,96}$' then
      raise exception 'service_payload_invalid' using errcode='22023';
    end if;
  elsif p_capability='ordax.dev.adapter.invoke' then
    if not (p_payload ?& array['adapter','action','project','payload'])
       or (p_payload-'adapter'-'action'-'project'-'payload')<>'{}'::jsonb
       or coalesce(p_payload->>'adapter','')<>'blender'
       or coalesce(p_payload->>'action','') !~ '^blender\.[a-z][a-z0-9_.]{1,95}$'
       or coalesce(p_payload->>'project','') !~ '^[A-Za-z0-9._-]{1,96}$'
       or jsonb_typeof(p_payload->'payload')<>'object'
       or octet_length((p_payload->'payload')::text)>131072 then
      raise exception 'adapter_invoke_payload_invalid' using errcode='22023';
    end if;
  elsif p_capability='ordax.dev.boot-capsule.preflight' then
    if p_payload<>'{}'::jsonb then
      raise exception 'boot_capsule_preflight_payload_invalid' using errcode='22023';
    end if;
  elsif p_capability='ordax.dev.boot-capsule.stage' then
    if not (p_payload ?& array['artifact_url','artifact_sha256','capsule_digest'])
       or (p_payload-'artifact_url'-'artifact_sha256'-'capsule_digest')<>'{}'::jsonb
       or char_length(coalesce(p_payload->>'artifact_url','')) not between 9 and 2048
       or coalesce(p_payload->>'artifact_url','') !~ '^https://[^[:space:][:cntrl:]]+$'
       or coalesce(p_payload->>'artifact_sha256','') !~ '^[0-9A-Fa-f]{64}$'
       or coalesce(p_payload->>'capsule_digest','') !~ '^[0-9A-Fa-f]{64}$' then
      raise exception 'boot_capsule_stage_payload_invalid' using errcode='22023';
    end if;
  else
    if not (p_payload ? 'script_b64')
       or (p_payload-'script_b64'-'timeout_seconds')<>'{}'::jsonb
       or coalesce(p_payload->>'script_b64','')=''
       or coalesce(p_payload->>'script_b64','') !~ '^[A-Za-z0-9+/]*={0,2}$'
       or char_length(p_payload->>'script_b64')>350000
       or char_length(p_payload->>'script_b64') % 4 <> 0
       or (
         p_payload ? 'timeout_seconds' and (
           jsonb_typeof(p_payload->'timeout_seconds')<>'number'
           or (p_payload->>'timeout_seconds')::integer not between 1 and 1800
         )
       ) then
      raise exception 'system_exec_payload_invalid' using errcode='22023';
    end if;
  end if;

  v_scope:=public.ordax_develop_resource_scope_v2(v_device_id,p_capability,p_payload);
  v_payload_sha:=encode(extensions.digest(convert_to(p_payload::text,'UTF8'),'sha256'),'hex');

  perform pg_advisory_xact_lock(hashtextextended('ordax-develop-queue:'||v_device_id::text,0));

  if p_idempotency_key is not null then
    select * into v_existing
      from public.ordax_develop_jobs j
     where j.session_id=p_session_id and j.idempotency_key=p_idempotency_key;
    if found then
      if v_existing.capability<>p_capability or v_existing.payload<>p_payload
         or v_existing.device_id<>v_device_id or v_existing.workspace_id<>p_workspace_id
         or v_existing.resource_scope<>v_scope or v_existing.payload_sha256<>v_payload_sha then
        raise exception 'idempotency_conflict' using errcode='23505';
      end if;
      return query select v_existing.job_id,v_existing.effect_id,v_existing.status,
        v_existing.correlation_id,v_existing.payload_sha256,v_existing.resource_scope,false;
      return;
    end if;
  end if;

  v_new_payload_bytes:=octet_length(p_payload::text);
  select
    count(*) filter(where j.status in ('queued','claimed','running','waiting')),
    count(*) filter(where j.requested_at>=v_now-interval '1 hour'),
    count(*),coalesce(sum(octet_length(j.payload::text)),0::bigint)
    into v_device_active,v_device_recent,v_device_total,v_device_payload_bytes
    from public.ordax_develop_jobs j where j.device_id=v_device_id;
  select count(*) filter(where j.status in ('queued','claimed','running','waiting')),count(*)
    into v_session_active,v_session_total
    from public.ordax_develop_jobs j where j.session_id=p_session_id;

  if v_session_active>=32 then
    raise exception 'development_queue_session_active_limit' using errcode='54000';
  elsif v_device_active>=128 then
    raise exception 'development_queue_device_active_limit' using errcode='54000';
  elsif v_device_recent>=512 then
    raise exception 'development_queue_device_rate_limit' using errcode='54000';
  elsif v_session_total>=256 then
    raise exception 'development_queue_session_storage_limit' using errcode='54000';
  elsif v_device_total>=4096 then
    raise exception 'development_queue_device_storage_limit' using errcode='54000';
  elsif v_device_payload_bytes+v_new_payload_bytes>67108864 then
    raise exception 'development_queue_payload_storage_limit' using errcode='54000';
  end if;

  insert into public.ordax_develop_jobs(
    device_id,session_id,actor_id,workspace_id,capability,operation,payload,
    payload_sha256,resource_scope,effect_id,status,priority,requested_by,
    requested_at,expires_at,correlation_id,idempotency_key
  ) values(
    v_device_id,p_session_id,v_actor_id,p_workspace_id,p_capability,p_capability,p_payload,
    v_payload_sha,v_scope,gen_random_uuid(),'queued',p_priority,p_requested_by,
    now(),now()+make_interval(secs=>p_ttl_seconds),p_correlation_id,p_idempotency_key
  ) returning * into v_inserted;

  insert into public.ordax_develop_events(device_id,job_id,event_type,payload)
  values(v_device_id,v_inserted.job_id,'job.queued.v2',jsonb_build_object(
    'actor_id',v_actor_id,'session_id',p_session_id,'effect_id',v_inserted.effect_id,
    'resource_scope',v_scope,'payload_sha256',v_payload_sha,'authority',v_authority
  ));

  return query select v_inserted.job_id,v_inserted.effect_id,v_inserted.status,
    v_inserted.correlation_id,v_inserted.payload_sha256,v_inserted.resource_scope,true;
exception when unique_violation then
  if p_idempotency_key is null then raise; end if;
  select * into v_existing
    from public.ordax_develop_jobs j
   where j.session_id=p_session_id and j.idempotency_key=p_idempotency_key;
  if not found or v_existing.capability<>p_capability or v_existing.payload<>p_payload
     or v_existing.device_id<>v_device_id or v_existing.workspace_id<>p_workspace_id
     or v_existing.resource_scope<>v_scope or v_existing.payload_sha256<>v_payload_sha then
    raise exception 'idempotency_conflict' using errcode='23505';
  end if;
  return query select v_existing.job_id,v_existing.effect_id,v_existing.status,
    v_existing.correlation_id,v_existing.payload_sha256,v_existing.resource_scope,false;
end
$function$;

create or replace function public.ordax_begin_internal_develop_job(
  p_device_id uuid,
  p_capability text,
  p_payload jsonb default '{}'::jsonb,
  p_requested_by text default 'devop:internal'
)
returns table(
  session_id uuid,
  job_id uuid,
  status text,
  correlation_id uuid,
  created boolean
)
language plpgsql
security invoker
set search_path to 'public','pg_temp'
as $function$
declare
  v_actor public.ordax_actors%rowtype;
  v_session_id uuid := gen_random_uuid();
  v_issued_at timestamptz := statement_timestamp();
  v_session jsonb;
  v_count integer;
begin
  if p_device_id is null then
    raise exception 'device_id_required' using errcode='22023';
  end if;

  if not exists (
    select 1 from public.ordax_devices d
    where d.device_id = p_device_id and d.mode = 'developer'
  ) then
    raise exception 'device_not_development' using errcode='42501';
  end if;

  select count(*) into v_count
  from public.ordax_actors a
  where a.actor_type = 'ai'
    and a.provider = 'openai'
    and a.client = 'chatgpt'
    and a.state = 'active';

  if v_count <> 1 then
    raise exception 'internal_develop_actor_not_unique' using errcode='42501';
  end if;

  select * into v_actor
  from public.ordax_actors a
  where a.actor_type = 'ai'
    and a.provider = 'openai'
    and a.client = 'chatgpt'
    and a.state = 'active'
  limit 1;

  v_session := public.ordax_issue_developer_session(
    v_session_id,
    v_actor.actor_id,
    v_actor.actor_type,
    v_actor.provider,
    v_actor.client,
    p_device_id,
    'DEVELOP',
    array[
      'ordax.dev.file.patch',
      'ordax.dev.command.run',
      'ordax.dev.test.run',
      'ordax.dev.service.restart',
      'ordax.dev.adapter.invoke'
    ]::text[],
    v_issued_at,
    v_issued_at + interval '30 minutes'
  );

  if coalesce((v_session->>'ok')::boolean, false) is not true then
    raise exception 'internal_develop_session_failed:%',
      coalesce(v_session->>'error', 'unknown') using errcode='42501';
  end if;

  return query
    select
      v_session_id,
      q.job_id,
      q.status,
      q.correlation_id,
      q.created
    from public.ordax_enqueue_develop_job_v2(
      v_session_id,
      p_capability,
      p_payload,
      p_requested_by,
      600,
      0::smallint,
      gen_random_uuid(),
      null,
      'default'
    ) q;
end
$function$;

revoke all on function public.ordax_develop_resource_scope_v2(uuid,text,jsonb)
  from public, anon, authenticated;
grant execute on function public.ordax_develop_resource_scope_v2(uuid,text,jsonb)
  to service_role;

revoke all on function public.ordax_enqueue_develop_job_v2(uuid,text,jsonb,text,integer,smallint,uuid,text,text)
  from public, anon, authenticated;
grant execute on function public.ordax_enqueue_develop_job_v2(uuid,text,jsonb,text,integer,smallint,uuid,text,text)
  to service_role;

revoke all on function public.ordax_begin_internal_develop_job(uuid,text,jsonb,text)
  from public, anon, authenticated;
grant execute on function public.ordax_begin_internal_develop_job(uuid,text,jsonb,text)
  to service_role;

commit;
