begin;

-- Product-domain Projects/Devices are deliberately separate from the older
-- engineering Control Plane tables such as public.ordax_devices.  End-user
-- product authority must never inherit development/operator credentials.

create table public.ordax_projects (
  project_id uuid primary key default gen_random_uuid(),
  space_id uuid not null references public.ordax_spaces(space_id) on delete cascade,
  created_by_user_id uuid not null references auth.users(id) on delete restrict,
  name text not null check (char_length(name) between 1 and 120),
  kind text not null default 'general'
    check (kind in ('general','development','creative','legal','business','research')),
  state text not null default 'active'
    check (state in ('active','archived')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (project_id, space_id)
);

comment on table public.ordax_projects is
  'Provider-neutral OrdaX product project identity. Local paths, provider tokens and secrets are not stored here.';

-- Existing product schema had connection records before a first-class project
-- row existed. Public product login is still disabled and this table is empty in
-- the prepared control plane. Fail closed rather than inventing a backfill if
-- that assumption is no longer true.
alter table public.ordax_project_connections
  add column project_id uuid;

do $$
begin
  if exists (select 1 from public.ordax_project_connections) then
    raise exception
      'ordax_project_connections requires an explicit project backfill before migration 0006';
  end if;
end;
$$;

alter table public.ordax_project_connections
  alter column project_id set not null,
  add constraint ordax_project_connections_project_space_fk
    foreign key (project_id, space_id)
    references public.ordax_projects(project_id, space_id)
    on delete cascade;

create table public.ordax_product_devices (
  device_id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  device_public_id text not null unique
    check (
      char_length(device_public_id) between 8 and 160
      and device_public_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]+$'
    ),
  display_name text not null check (char_length(display_name) between 1 and 120),
  device_kind text not null default 'other'
    check (device_kind in ('desktop','laptop','mobile','server','other')),
  channel text not null default 'stable'
    check (channel in ('stable','development')),
  state text not null default 'active'
    check (state in ('active','revoked')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

comment on table public.ordax_product_devices is
  'End-user OrdaX device registry. Separate from engineering public.ordax_devices and contains no device credential secrets.';

create table public.ordax_device_presence (
  device_id uuid primary key
    references public.ordax_product_devices(device_id) on delete cascade,
  online boolean not null default false,
  runtime_kind text
    check (
      runtime_kind is null
      or runtime_kind in ('ordax-os','desktop-agent','mobile-client','other')
    ),
  agent_version text
    check (agent_version is null or char_length(agent_version) between 1 and 80),
  capability_digest text
    check (
      capability_digest is null
      or capability_digest ~ '^[0-9a-f]{64}$'
    ),
  last_seen_at timestamptz,
  observed_at timestamptz not null default timezone('utc', now())
);

comment on table public.ordax_device_presence is
  'Ephemeral-ish product presence metadata. Backend-owned; no local paths, tokens or raw capability secrets.';

create table public.ordax_space_devices (
  space_id uuid not null
    references public.ordax_spaces(space_id) on delete cascade,
  device_id uuid not null
    references public.ordax_product_devices(device_id) on delete cascade,
  access_mode text not null default 'observe'
    check (access_mode in ('observe','execute')),
  state text not null default 'active'
    check (state in ('active','revoked')),
  granted_by_user_id uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  primary key (space_id, device_id)
);

create table public.ordax_device_project_bindings (
  binding_id uuid primary key default gen_random_uuid(),
  project_id uuid not null
    references public.ordax_projects(project_id) on delete cascade,
  device_id uuid not null
    references public.ordax_product_devices(device_id) on delete cascade,
  local_project_ref text not null
    check (
      char_length(local_project_ref) between 1 and 160
      and local_project_ref !~ '[\\/]'
      and local_project_ref !~ '\.\.'
    ),
  state text not null default 'active'
    check (state in ('active','unavailable','revoked')),
  allowed_capabilities text[] not null default '{}'::text[],
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (project_id, device_id, local_project_ref)
);

comment on column public.ordax_device_project_bindings.local_project_ref is
  'Opaque Device Agent project reference. It must not contain or expose an absolute/local filesystem path.';

create table public.ordax_remote_capability_grants (
  grant_id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  space_id uuid not null
    references public.ordax_spaces(space_id) on delete cascade,
  project_id uuid not null,
  device_id uuid not null
    references public.ordax_product_devices(device_id) on delete cascade,
  client_kind text not null
    check (client_kind in ('ordax-web','ordax-mobile','product-mcp')),
  client_id text
    check (client_id is null or char_length(client_id) between 1 and 180),
  capability text not null
    check (
      char_length(capability) between 2 and 120
      and capability ~ '^[a-z][a-z0-9.-]+$'
    ),
  access_mode text not null
    check (access_mode in ('read','write')),
  state text not null default 'active'
    check (state in ('active','revoked','expired')),
  approved_by_user_id uuid not null references auth.users(id) on delete restrict,
  valid_until timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  check (valid_until is null or valid_until > created_at),
  foreign key (project_id, space_id)
    references public.ordax_projects(project_id, space_id)
    on delete cascade
);

comment on table public.ordax_remote_capability_grants is
  'Server-authoritative Product MCP/Web/Mobile capability grants. A grant never contains provider credentials or generic shell authority.';

create index ordax_projects_space_state_idx
  on public.ordax_projects(space_id, state);
create index ordax_projects_creator_idx
  on public.ordax_projects(created_by_user_id);
create index ordax_project_connections_project_idx
  on public.ordax_project_connections(project_id, state);
create index ordax_product_devices_owner_state_idx
  on public.ordax_product_devices(owner_user_id, state);
create index ordax_device_presence_online_seen_idx
  on public.ordax_device_presence(online, last_seen_at);
create index ordax_space_devices_device_state_idx
  on public.ordax_space_devices(device_id, state);
create index ordax_device_project_bindings_project_state_idx
  on public.ordax_device_project_bindings(project_id, state);
create index ordax_device_project_bindings_device_state_idx
  on public.ordax_device_project_bindings(device_id, state);
create index ordax_remote_grants_space_state_idx
  on public.ordax_remote_capability_grants(space_id, state);
create index ordax_remote_grants_project_device_state_idx
  on public.ordax_remote_capability_grants(project_id, device_id, state);
create index ordax_remote_grants_owner_client_state_idx
  on public.ordax_remote_capability_grants(owner_user_id, client_kind, state);

create trigger touch_ordax_projects_updated_at
before update on public.ordax_projects
for each row execute function private.ordax_touch_updated_at();

create trigger touch_ordax_product_devices_updated_at
before update on public.ordax_product_devices
for each row execute function private.ordax_touch_updated_at();

create trigger touch_ordax_space_devices_updated_at
before update on public.ordax_space_devices
for each row execute function private.ordax_touch_updated_at();

create trigger touch_ordax_device_project_bindings_updated_at
before update on public.ordax_device_project_bindings
for each row execute function private.ordax_touch_updated_at();

create trigger touch_ordax_remote_capability_grants_updated_at
before update on public.ordax_remote_capability_grants
for each row execute function private.ordax_touch_updated_at();

create or replace function private.ordax_can_access_project(target_project_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.ordax_projects p
    where p.project_id = target_project_id
      and private.ordax_can_access_space(p.space_id)
  );
$$;

create or replace function private.ordax_can_access_product_device(target_device_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select (select auth.uid()) is not null and (
    exists (
      select 1
      from public.ordax_product_devices d
      where d.device_id = target_device_id
        and d.owner_user_id = (select auth.uid())
        and d.state = 'active'
    )
    or exists (
      select 1
      from public.ordax_space_devices sd
      where sd.device_id = target_device_id
        and sd.state = 'active'
        and private.ordax_can_access_space(sd.space_id)
    )
  );
$$;

revoke all on function private.ordax_can_access_project(uuid)
  from public, anon, authenticated;
revoke all on function private.ordax_can_access_product_device(uuid)
  from public, anon, authenticated;
grant execute on function private.ordax_can_access_project(uuid)
  to authenticated;
grant execute on function private.ordax_can_access_product_device(uuid)
  to authenticated;

alter table public.ordax_projects enable row level security;
alter table public.ordax_product_devices enable row level security;
alter table public.ordax_device_presence enable row level security;
alter table public.ordax_space_devices enable row level security;
alter table public.ordax_device_project_bindings enable row level security;
alter table public.ordax_remote_capability_grants enable row level security;

revoke all on table public.ordax_projects
  from public, anon, authenticated;
revoke all on table public.ordax_product_devices
  from public, anon, authenticated;
revoke all on table public.ordax_device_presence
  from public, anon, authenticated;
revoke all on table public.ordax_space_devices
  from public, anon, authenticated;
revoke all on table public.ordax_device_project_bindings
  from public, anon, authenticated;
revoke all on table public.ordax_remote_capability_grants
  from public, anon, authenticated;

-- Product resources remain server-authoritative. Signed-in clients can inspect
-- only rows authorized by RLS; creation/mutation flows must pass through OrdaX
-- gateways where entitlements, approval and audit are enforced.
grant select on table public.ordax_projects to authenticated;
grant select on table public.ordax_product_devices to authenticated;
grant select on table public.ordax_device_presence to authenticated;
grant select on table public.ordax_space_devices to authenticated;
grant select on table public.ordax_device_project_bindings to authenticated;
grant select on table public.ordax_remote_capability_grants to authenticated;

create policy ordax_projects_select_space
on public.ordax_projects
for select
to authenticated
using (private.ordax_can_access_space(space_id));

create policy ordax_product_devices_select_authorized
on public.ordax_product_devices
for select
to authenticated
using (private.ordax_can_access_product_device(device_id));

create policy ordax_device_presence_select_authorized
on public.ordax_device_presence
for select
to authenticated
using (private.ordax_can_access_product_device(device_id));

create policy ordax_space_devices_select_space
on public.ordax_space_devices
for select
to authenticated
using (private.ordax_can_access_space(space_id));

create policy ordax_device_project_bindings_select_project
on public.ordax_device_project_bindings
for select
to authenticated
using (private.ordax_can_access_project(project_id));

create policy ordax_remote_capability_grants_select_admin
on public.ordax_remote_capability_grants
for select
to authenticated
using (
  owner_user_id = (select auth.uid())
  or private.ordax_can_admin_space(space_id)
);

commit;
