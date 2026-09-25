alter table private.ordax_sync_mutations
  add column if not exists change_seq bigint generated always as identity,
  add column if not exists object_schema_version integer,
  add column if not exists resolver_version integer,
  add column if not exists tombstone boolean,
  add column if not exists payload jsonb;

alter table private.ordax_sync_mutations
  alter column object_schema_version set default 1,
  alter column resolver_version set default 1,
  alter column tombstone set default false,
  alter column payload set default '{}'::jsonb;

update private.ordax_sync_mutations
set object_schema_version = coalesce(object_schema_version, 1),
    resolver_version = coalesce(resolver_version, 1),
    tombstone = coalesce(tombstone, mutation_kind = 'delete'),
    payload = coalesce(payload, '{}'::jsonb)
where object_schema_version is null
   or resolver_version is null
   or tombstone is null
   or payload is null;

alter table private.ordax_sync_mutations
  alter column object_schema_version set not null,
  alter column resolver_version set not null,
  alter column tombstone set not null,
  alter column payload set not null;

create unique index if not exists ordax_sync_mutations_change_seq_uidx
  on private.ordax_sync_mutations(change_seq);

create index if not exists ordax_sync_mutations_owner_change_seq_idx
  on private.ordax_sync_mutations(owner_user_id, change_seq);

create or replace function public.ordax_apply_sync_mutation_v1(
  p_idempotency_key text,
  p_data_class text,
  p_stable_object_id text,
  p_object_schema_version integer,
  p_resolver_version integer,
  p_base_server_revision bigint,
  p_tombstone boolean,
  p_payload jsonb
)
returns table(
  sync_object_id uuid,
  server_revision bigint,
  tombstone boolean,
  applied boolean,
  conflict boolean
)
language plpgsql
security invoker
set search_path = ''
as $function$
declare
  v_user_id uuid := (select auth.uid());
  v_existing private.ordax_sync_objects%rowtype;
  v_mutation private.ordax_sync_mutations%rowtype;
  v_revision bigint;
begin
  if v_user_id is null then raise exception 'authentication-required' using errcode = '42501'; end if;
  if p_idempotency_key is null or char_length(p_idempotency_key) < 8 or char_length(p_idempotency_key) > 200 then raise exception 'invalid-idempotency-key' using errcode = '22023'; end if;
  if p_data_class not in ('appearance','preferences','workspace-metadata','app-state-metadata','user-selected-cloud-content') then raise exception 'invalid-data-class' using errcode = '22023'; end if;
  if p_stable_object_id is null or char_length(p_stable_object_id) < 1 or char_length(p_stable_object_id) > 240 then raise exception 'invalid-stable-object-id' using errcode = '22023'; end if;
  if p_object_schema_version is null or p_object_schema_version <= 0 or p_resolver_version is null or p_resolver_version <= 0 then raise exception 'invalid-schema-version' using errcode = '22023'; end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then raise exception 'payload-must-be-object' using errcode = '22023'; end if;

  select * into v_mutation from private.ordax_sync_mutations
  where owner_user_id = v_user_id and idempotency_key = p_idempotency_key;

  if found then
    select * into v_existing from private.ordax_sync_objects
    where owner_user_id = v_user_id and data_class = v_mutation.data_class and stable_object_id = v_mutation.stable_object_id;
    return query select v_existing.sync_object_id, v_mutation.resulting_server_revision, v_mutation.tombstone, false, false;
    return;
  end if;

  select * into v_existing from private.ordax_sync_objects
  where owner_user_id = v_user_id and data_class = p_data_class and stable_object_id = p_stable_object_id
  for update;

  if found then
    if p_base_server_revision is null or p_base_server_revision <> v_existing.server_revision then
      return query select v_existing.sync_object_id, v_existing.server_revision, v_existing.tombstone, false, true;
      return;
    end if;
    v_revision := v_existing.server_revision + 1;
    update private.ordax_sync_objects
      set object_schema_version = p_object_schema_version,
          resolver_version = p_resolver_version,
          server_revision = v_revision,
          tombstone = p_tombstone,
          payload = p_payload,
          updated_at = timezone('utc', now())
      where sync_object_id = v_existing.sync_object_id
      returning * into v_existing;
  else
    if coalesce(p_base_server_revision, 0) <> 0 then
      return query select null::uuid, 0::bigint, false, false, true;
      return;
    end if;
    v_revision := 1;
    insert into private.ordax_sync_objects(
      owner_user_id, data_class, stable_object_id, object_schema_version,
      resolver_version, server_revision, tombstone, payload
    ) values (
      v_user_id, p_data_class, p_stable_object_id, p_object_schema_version,
      p_resolver_version, v_revision, p_tombstone, p_payload
    )
    returning * into v_existing;
  end if;

  insert into private.ordax_sync_mutations(
    owner_user_id, idempotency_key, data_class, stable_object_id,
    base_server_revision, resulting_server_revision, mutation_kind,
    object_schema_version, resolver_version, tombstone, payload
  ) values (
    v_user_id, p_idempotency_key, p_data_class, p_stable_object_id,
    p_base_server_revision, v_revision, case when p_tombstone then 'delete' else 'upsert' end,
    p_object_schema_version, p_resolver_version, p_tombstone, p_payload
  );

  return query select v_existing.sync_object_id, v_revision, p_tombstone, true, false;
end;
$function$;

create or replace function public.ordax_apply_sync_mutation_v2(
  p_idempotency_key text,
  p_data_class text,
  p_stable_object_id text,
  p_object_schema_version integer,
  p_resolver_version integer,
  p_base_server_revision bigint,
  p_tombstone boolean,
  p_payload jsonb
)
returns table(
  sync_object_id uuid,
  server_revision bigint,
  tombstone boolean,
  applied boolean,
  conflict boolean,
  change_cursor bigint
)
language plpgsql
security invoker
set search_path = ''
as $function$
declare
  v_user_id uuid := (select auth.uid());
  v_result record;
  v_cursor bigint;
begin
  if v_user_id is null then raise exception 'authentication-required' using errcode = '42501'; end if;

  select * into v_result
  from public.ordax_apply_sync_mutation_v1(
    p_idempotency_key, p_data_class, p_stable_object_id,
    p_object_schema_version, p_resolver_version,
    p_base_server_revision, p_tombstone, p_payload
  );

  select m.change_seq into v_cursor
  from private.ordax_sync_mutations m
  where m.owner_user_id = v_user_id and m.idempotency_key = p_idempotency_key;

  return query select
    v_result.sync_object_id, v_result.server_revision, v_result.tombstone,
    v_result.applied, v_result.conflict, v_cursor;
end;
$function$;

create or replace function public.ordax_pull_sync_changes_v1(
  p_after_cursor bigint default 0,
  p_limit integer default 200
)
returns table(
  change_cursor bigint,
  data_class text,
  stable_object_id text,
  object_schema_version integer,
  resolver_version integer,
  server_revision bigint,
  tombstone boolean,
  payload jsonb,
  changed_at timestamptz
)
language sql
security invoker
set search_path = ''
as $function$
  select
    m.change_seq, m.data_class, m.stable_object_id,
    m.object_schema_version, m.resolver_version,
    m.resulting_server_revision, m.tombstone, m.payload, m.applied_at
  from private.ordax_sync_mutations m
  where m.owner_user_id = (select auth.uid())
    and m.change_seq > greatest(coalesce(p_after_cursor, 0), 0)
  order by m.change_seq
  limit least(greatest(coalesce(p_limit, 200), 1), 500);
$function$;

revoke all on function public.ordax_apply_sync_mutation_v2(text,text,text,integer,integer,bigint,boolean,jsonb) from public, anon;
grant execute on function public.ordax_apply_sync_mutation_v2(text,text,text,integer,integer,bigint,boolean,jsonb) to authenticated;
revoke all on function public.ordax_pull_sync_changes_v1(bigint,integer) from public, anon;
grant execute on function public.ordax_pull_sync_changes_v1(bigint,integer) to authenticated;
