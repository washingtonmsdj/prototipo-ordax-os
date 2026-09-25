-- Applied to ordax-control-plane as Supabase migration 20260925004439.
-- Provider-neutral account sync store. Clients see OrdaX object/revision semantics,
-- never provider row identity. Device-private material is not allowed here.

create table if not exists public.ordax_sync_objects (
  sync_object_id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  data_class text not null check (data_class in ('appearance','preferences','workspace-metadata','app-state-metadata','user-selected-cloud-content')),
  stable_object_id text not null check (char_length(stable_object_id) between 1 and 240),
  object_schema_version integer not null check (object_schema_version > 0),
  resolver_version integer not null default 1 check (resolver_version > 0),
  server_revision bigint not null default 1 check (server_revision > 0),
  tombstone boolean not null default false,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (owner_user_id, data_class, stable_object_id)
);

create table if not exists public.ordax_sync_mutations (
  mutation_id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  idempotency_key text not null check (char_length(idempotency_key) between 8 and 200),
  data_class text not null check (data_class in ('appearance','preferences','workspace-metadata','app-state-metadata','user-selected-cloud-content')),
  stable_object_id text not null check (char_length(stable_object_id) between 1 and 240),
  base_server_revision bigint,
  resulting_server_revision bigint not null check (resulting_server_revision > 0),
  mutation_kind text not null check (mutation_kind in ('upsert','delete')),
  applied_at timestamptz not null default timezone('utc', now()),
  unique (owner_user_id, idempotency_key)
);

create index if not exists ordax_sync_objects_owner_revision_idx
  on public.ordax_sync_objects(owner_user_id, server_revision);
create index if not exists ordax_sync_mutations_owner_applied_idx
  on public.ordax_sync_mutations(owner_user_id, applied_at desc);

alter table public.ordax_sync_objects enable row level security;
alter table public.ordax_sync_mutations enable row level security;

revoke all on table public.ordax_sync_objects from public, anon, authenticated;
revoke all on table public.ordax_sync_mutations from public, anon, authenticated;
grant select on table public.ordax_sync_objects to authenticated;
grant select on table public.ordax_sync_mutations to authenticated;

create policy ordax_sync_objects_select_own
on public.ordax_sync_objects for select to authenticated
using ((select auth.uid()) = owner_user_id);

create policy ordax_sync_mutations_select_own
on public.ordax_sync_mutations for select to authenticated
using ((select auth.uid()) = owner_user_id);

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
security definer
set search_path = ''
as $$
declare
  v_user_id uuid := (select auth.uid());
  v_existing public.ordax_sync_objects%rowtype;
  v_mutation public.ordax_sync_mutations%rowtype;
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
  from public.ordax_sync_mutations
  where owner_user_id = v_user_id and idempotency_key = p_idempotency_key;

  if found then
    select * into v_existing
    from public.ordax_sync_objects
    where owner_user_id = v_user_id
      and data_class = v_mutation.data_class
      and stable_object_id = v_mutation.stable_object_id;
    return query select v_existing.sync_object_id, v_mutation.resulting_server_revision,
      coalesce(v_existing.tombstone, false), false, false;
    return;
  end if;

  select * into v_existing
  from public.ordax_sync_objects
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
    update public.ordax_sync_objects
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
    insert into public.ordax_sync_objects(
      owner_user_id, data_class, stable_object_id, object_schema_version,
      resolver_version, server_revision, tombstone, payload
    ) values (
      v_user_id, p_data_class, p_stable_object_id, p_object_schema_version,
      p_resolver_version, v_revision, p_tombstone, p_payload
    )
    returning * into v_existing;
  end if;

  insert into public.ordax_sync_mutations(
    owner_user_id, idempotency_key, data_class, stable_object_id,
    base_server_revision, resulting_server_revision, mutation_kind
  ) values (
    v_user_id, p_idempotency_key, p_data_class, p_stable_object_id,
    p_base_server_revision, v_revision, case when p_tombstone then 'delete' else 'upsert' end
  );

  return query select v_existing.sync_object_id, v_revision, p_tombstone, true, false;
end;
$$;

revoke all on function public.ordax_apply_sync_mutation_v1(text,text,text,integer,integer,bigint,boolean,jsonb) from public, anon;
grant execute on function public.ordax_apply_sync_mutation_v1(text,text,text,integer,integer,bigint,boolean,jsonb) to authenticated;
