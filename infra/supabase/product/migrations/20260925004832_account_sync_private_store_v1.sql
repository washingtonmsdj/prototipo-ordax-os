-- Applied to ordax-control-plane after 20260925004439_account_sync_objects_v1.
-- Internal sync rows live in the unexposed private schema. Public API functions
-- run as SECURITY INVOKER so RLS remains authoritative for each signed-in user.

alter table public.ordax_sync_objects set schema private;
alter table public.ordax_sync_mutations set schema private;

revoke all on table private.ordax_sync_objects from public, anon, authenticated;
revoke all on table private.ordax_sync_mutations from public, anon, authenticated;
grant usage on schema private to authenticated;
grant select, insert, update on table private.ordax_sync_objects to authenticated;
grant select, insert on table private.ordax_sync_mutations to authenticated;

drop policy if exists ordax_sync_objects_select_own on private.ordax_sync_objects;
create policy ordax_sync_objects_select_own
on private.ordax_sync_objects for select to authenticated
using ((select auth.uid()) = owner_user_id);

create policy ordax_sync_objects_insert_own
on private.ordax_sync_objects for insert to authenticated
with check ((select auth.uid()) = owner_user_id);

create policy ordax_sync_objects_update_own
on private.ordax_sync_objects for update to authenticated
using ((select auth.uid()) = owner_user_id)
with check ((select auth.uid()) = owner_user_id);

drop policy if exists ordax_sync_mutations_select_own on private.ordax_sync_mutations;
create policy ordax_sync_mutations_select_own
on private.ordax_sync_mutations for select to authenticated
using ((select auth.uid()) = owner_user_id);

create policy ordax_sync_mutations_insert_own
on private.ordax_sync_mutations for insert to authenticated
with check ((select auth.uid()) = owner_user_id);

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
returns table (
  sync_object_id uuid,
  server_revision bigint,
  tombstone boolean,
  applied boolean,
  conflict boolean
)
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_user_id uuid := (select auth.uid());
  v_existing private.ordax_sync_objects%rowtype;
  v_mutation private.ordax_sync_mutations%rowtype;
  v_revision bigint;
begin
  if v_user_id is null then
    raise exception 'authentication-required' using errcode = '42501';
  end if;
  if p_idempotency_key is null or char_length(p_idempotency_key) < 8 or char_length(p_idempotency_key) > 200 then
    raise exception 'invalid-idempotency-key' using errcode = '22023';
  end if;
  if p_data_class not in ('appearance','preferences','workspace-metadata','app-state-metadata','user-selected-cloud-content') then
    raise exception 'invalid-data-class' using errcode = '22023';
  end if;
  if p_stable_object_id is null or char_length(p_stable_object_id) < 1 or char_length(p_stable_object_id) > 240 then
    raise exception 'invalid-stable-object-id' using errcode = '22023';
  end if;
  if p_object_schema_version is null or p_object_schema_version <= 0 or p_resolver_version is null or p_resolver_version <= 0 then
    raise exception 'invalid-schema-version' using errcode = '22023';
  end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    raise exception 'payload-must-be-object' using errcode = '22023';
  end if;

  select * into v_mutation
  from private.ordax_sync_mutations
  where owner_user_id = v_user_id and idempotency_key = p_idempotency_key;

  if found then
    select * into v_existing
    from private.ordax_sync_objects
    where owner_user_id = v_user_id
      and data_class = v_mutation.data_class
      and stable_object_id = v_mutation.stable_object_id;
    return query select v_existing.sync_object_id, v_mutation.resulting_server_revision,
      coalesce(v_existing.tombstone, false), false, false;
    return;
  end if;

  select * into v_existing
  from private.ordax_sync_objects
  where owner_user_id = v_user_id
    and data_class = p_data_class
    and stable_object_id = p_stable_object_id
  for update;

  if found then
    if p_base_server_revision is null or p_base_server_revision <> v_existing.server_revision then
      return query select v_existing.sync_object_id, v_existing.server_revision,
        v_existing.tombstone, false, true;
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
      where sync_object_id = v_existing.sync_object_id;
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
    base_server_revision, resulting_server_revision, mutation_kind
  ) values (
    v_user_id, p_idempotency_key, p_data_class, p_stable_object_id,
    p_base_server_revision, v_revision, case when p_tombstone then 'delete' else 'upsert' end
  );

  return query select v_existing.sync_object_id, v_revision, p_tombstone, true, false;
end;
$$;

create or replace function public.ordax_list_sync_objects_v1(
  p_after_revision bigint default 0,
  p_limit integer default 200
)
returns table (
  sync_object_id uuid,
  data_class text,
  stable_object_id text,
  object_schema_version integer,
  resolver_version integer,
  server_revision bigint,
  tombstone boolean,
  payload jsonb,
  updated_at timestamptz
)
language sql
stable
security invoker
set search_path = ''
as $$
  select
    s.sync_object_id,
    s.data_class,
    s.stable_object_id,
    s.object_schema_version,
    s.resolver_version,
    s.server_revision,
    s.tombstone,
    s.payload,
    s.updated_at
  from private.ordax_sync_objects s
  where s.owner_user_id = (select auth.uid())
    and s.server_revision > greatest(coalesce(p_after_revision, 0), 0)
  order by s.server_revision, s.sync_object_id
  limit least(greatest(coalesce(p_limit, 200), 1), 500)
$$;

revoke all on function public.ordax_apply_sync_mutation_v1(text,text,text,integer,integer,bigint,boolean,jsonb) from public, anon;
revoke all on function public.ordax_list_sync_objects_v1(bigint,integer) from public, anon;
grant execute on function public.ordax_apply_sync_mutation_v1(text,text,text,integer,integer,bigint,boolean,jsonb) to authenticated;
grant execute on function public.ordax_list_sync_objects_v1(bigint,integer) to authenticated;
