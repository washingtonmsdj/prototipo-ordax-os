begin;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
grant usage on schema private to authenticated;

create extension if not exists vector with schema extensions;

create table public.ordax_accounts (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text check (display_name is null or char_length(display_name) between 1 and 120),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table public.ordax_spaces (
  space_id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 120),
  kind text not null default 'work' check (kind in ('personal','work','professional')),
  state text not null default 'active' check (state in ('active','archived')),
  profile_pack_slug text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table public.ordax_space_members (
  space_id uuid not null references public.ordax_spaces(space_id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner','admin','member','viewer')),
  state text not null default 'active' check (state in ('active','suspended')),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  primary key (space_id, user_id)
);

create table public.ordax_entitlement_grants (
  grant_id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  space_id uuid references public.ordax_spaces(space_id) on delete cascade,
  entitlement_key text not null check (entitlement_key ~ '^[a-z][a-z0-9.-]{2,95}$'),
  entitlement_value jsonb not null,
  source text not null default 'admin' check (source in ('product-default','admin','promotion','billing','migration')),
  valid_from timestamptz not null default timezone('utc', now()),
  valid_until timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  check ((user_id is not null)::integer + (space_id is not null)::integer = 1),
  check (valid_until is null or valid_until > valid_from)
);

create table public.ordax_profile_packs (
  slug text not null check (slug ~ '^[a-z0-9][a-z0-9-]{1,79}$'),
  version integer not null check (version > 0),
  title text not null check (char_length(title) between 1 and 120),
  category text not null check (char_length(category) between 1 and 80),
  state text not null default 'draft' check (state in ('draft','active','retired')),
  manifest jsonb not null default '{}'::jsonb,
  knowledge_policy jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  primary key (slug, version)
);

create table public.ordax_space_profile_packs (
  space_id uuid primary key references public.ordax_spaces(space_id) on delete cascade,
  pack_slug text not null,
  pack_version integer not null,
  config jsonb not null default '{}'::jsonb,
  enabled_at timestamptz not null default timezone('utc', now()),
  enabled_by uuid not null references auth.users(id) on delete restrict,
  foreign key (pack_slug, pack_version)
    references public.ordax_profile_packs(slug, version)
    on delete restrict
);

create table public.ordax_memory_items (
  memory_id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  space_id uuid references public.ordax_spaces(space_id) on delete cascade,
  project_ref text check (project_ref is null or char_length(project_ref) between 1 and 240),
  scope text not null check (scope in ('device','account','space','project','session')),
  kind text not null check (kind in ('preference','fact','instruction','summary','artifact-reference')),
  sensitivity text not null default 'private' check (sensitivity in ('normal','private','restricted')),
  content text not null check (char_length(content) between 1 and 32768),
  provenance text not null check (char_length(provenance) between 1 and 1024),
  source_timestamp timestamptz not null default timezone('utc', now()),
  confidence numeric(4,3) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  state text not null default 'active' check (state in ('active','superseded','deleted')),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  check (scope <> 'space' or space_id is not null),
  check (scope <> 'project' or project_ref is not null)
);

create table public.ordax_memory_embeddings (
  memory_id uuid not null references public.ordax_memory_items(memory_id) on delete cascade,
  embedding_model_id text not null check (char_length(embedding_model_id) between 1 and 160),
  embedding extensions.vector not null,
  created_at timestamptz not null default timezone('utc', now()),
  primary key (memory_id, embedding_model_id)
);

create table public.ordax_project_connections (
  connection_id uuid primary key default gen_random_uuid(),
  space_id uuid not null references public.ordax_spaces(space_id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  provider text not null check (provider in ('github','local-git','other')),
  external_account_id text,
  installation_id bigint,
  repository_id bigint,
  repository_full_name text,
  default_branch text,
  access_mode text not null default 'read' check (access_mode in ('read','read-write')),
  state text not null default 'active' check (state in ('active','revoked','error')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  check (provider <> 'github' or (installation_id is not null and repository_id is not null))
);

create index ordax_spaces_owner_state_idx
  on public.ordax_spaces(owner_user_id, state);
create index ordax_space_members_user_state_idx
  on public.ordax_space_members(user_id, state);
create index ordax_entitlement_grants_user_key_idx
  on public.ordax_entitlement_grants(user_id, entitlement_key)
  where user_id is not null;
create index ordax_entitlement_grants_space_key_idx
  on public.ordax_entitlement_grants(space_id, entitlement_key)
  where space_id is not null;
create index ordax_memory_items_owner_scope_idx
  on public.ordax_memory_items(owner_user_id, scope, state);
create index ordax_memory_items_space_scope_idx
  on public.ordax_memory_items(space_id, scope, state)
  where space_id is not null;
create index ordax_project_connections_space_idx
  on public.ordax_project_connections(space_id, state);

create or replace function private.ordax_touch_updated_at()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.updated_at := timezone('utc', now());
  return new;
end;
$$;

create or replace function private.handle_ordax_account_created()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.ordax_accounts(user_id)
  values (new.id)
  on conflict (user_id) do nothing;
  return new;
end;
$$;

create or replace function private.ordax_can_access_space(target_space_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select (select auth.uid()) is not null and (
    exists (
      select 1
      from public.ordax_spaces s
      where s.space_id = target_space_id
        and s.owner_user_id = (select auth.uid())
    )
    or exists (
      select 1
      from public.ordax_space_members m
      where m.space_id = target_space_id
        and m.user_id = (select auth.uid())
        and m.state = 'active'
    )
  );
$$;

create or replace function private.ordax_can_admin_space(target_space_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select (select auth.uid()) is not null and (
    exists (
      select 1
      from public.ordax_spaces s
      where s.space_id = target_space_id
        and s.owner_user_id = (select auth.uid())
    )
    or exists (
      select 1
      from public.ordax_space_members m
      where m.space_id = target_space_id
        and m.user_id = (select auth.uid())
        and m.state = 'active'
        and m.role in ('owner','admin')
    )
  );
$$;

revoke all on function private.ordax_touch_updated_at() from public, anon, authenticated;
revoke all on function private.handle_ordax_account_created() from public, anon, authenticated;
revoke all on function private.ordax_can_access_space(uuid) from public, anon, authenticated;
revoke all on function private.ordax_can_admin_space(uuid) from public, anon, authenticated;
grant execute on function private.ordax_can_access_space(uuid) to authenticated;
grant execute on function private.ordax_can_admin_space(uuid) to authenticated;

create trigger touch_ordax_accounts_updated_at
before update on public.ordax_accounts
for each row execute function private.ordax_touch_updated_at();

create trigger touch_ordax_spaces_updated_at
before update on public.ordax_spaces
for each row execute function private.ordax_touch_updated_at();

create trigger touch_ordax_space_members_updated_at
before update on public.ordax_space_members
for each row execute function private.ordax_touch_updated_at();

create trigger touch_ordax_profile_packs_updated_at
before update on public.ordax_profile_packs
for each row execute function private.ordax_touch_updated_at();

create trigger touch_ordax_memory_items_updated_at
before update on public.ordax_memory_items
for each row execute function private.ordax_touch_updated_at();

create trigger touch_ordax_project_connections_updated_at
before update on public.ordax_project_connections
for each row execute function private.ordax_touch_updated_at();

create trigger on_auth_user_created_ordax_product
after insert on auth.users
for each row execute function private.handle_ordax_account_created();

insert into public.ordax_accounts(user_id)
select id from auth.users
on conflict (user_id) do nothing;

insert into public.ordax_profile_packs(
  slug, version, title, category, state, manifest, knowledge_policy
) values
(
  'developer',
  1,
  'Developer',
  'development',
  'draft',
  '{"apps":[],"templates":[],"capabilities":[]}'::jsonb,
  '{"source_classes":["project-source","project-docs"],"freshness":"project-owned"}'::jsonb
),
(
  'legal-br',
  1,
  'Advocacia Brasil',
  'legal',
  'draft',
  '{"apps":[],"templates":[],"capabilities":[],"jurisdiction":"BR"}'::jsonb,
  '{"jurisdiction":"BR","authoritative_source_classes":["official-legislation","official-regulator","official-court-or-tribunal","user-authorized-firm-material"],"source_date_required":true,"stale_knowledge_must_be_identified":true}'::jsonb
)
on conflict (slug, version) do nothing;

alter table public.ordax_accounts enable row level security;
alter table public.ordax_spaces enable row level security;
alter table public.ordax_space_members enable row level security;
alter table public.ordax_entitlement_grants enable row level security;
alter table public.ordax_profile_packs enable row level security;
alter table public.ordax_space_profile_packs enable row level security;
alter table public.ordax_memory_items enable row level security;
alter table public.ordax_memory_embeddings enable row level security;
alter table public.ordax_project_connections enable row level security;

revoke all on table public.ordax_accounts from public, anon, authenticated;
revoke all on table public.ordax_spaces from public, anon, authenticated;
revoke all on table public.ordax_space_members from public, anon, authenticated;
revoke all on table public.ordax_entitlement_grants from public, anon, authenticated;
revoke all on table public.ordax_profile_packs from public, anon, authenticated;
revoke all on table public.ordax_space_profile_packs from public, anon, authenticated;
revoke all on table public.ordax_memory_items from public, anon, authenticated;
revoke all on table public.ordax_memory_embeddings from public, anon, authenticated;
revoke all on table public.ordax_project_connections from public, anon, authenticated;

grant select, update on table public.ordax_accounts to authenticated;
grant select, insert, update, delete on table public.ordax_spaces to authenticated;
grant select, insert, update, delete on table public.ordax_space_members to authenticated;
grant select on table public.ordax_entitlement_grants to authenticated;
grant select on table public.ordax_profile_packs to authenticated;
grant select on table public.ordax_space_profile_packs to authenticated;
grant select, insert, update, delete on table public.ordax_memory_items to authenticated;
grant select on table public.ordax_memory_embeddings to authenticated;
grant select on table public.ordax_project_connections to authenticated;

create policy ordax_accounts_select_own
on public.ordax_accounts for select to authenticated
using ((select auth.uid()) = user_id);

create policy ordax_accounts_update_own
on public.ordax_accounts for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy ordax_spaces_select_member
on public.ordax_spaces for select to authenticated
using (private.ordax_can_access_space(space_id));

create policy ordax_spaces_insert_own
on public.ordax_spaces for insert to authenticated
with check ((select auth.uid()) = owner_user_id);

create policy ordax_spaces_update_admin
on public.ordax_spaces for update to authenticated
using (private.ordax_can_admin_space(space_id))
with check (private.ordax_can_admin_space(space_id));

create policy ordax_spaces_delete_owner
on public.ordax_spaces for delete to authenticated
using ((select auth.uid()) = owner_user_id);

create policy ordax_space_members_select_space
on public.ordax_space_members for select to authenticated
using (private.ordax_can_access_space(space_id));

create policy ordax_space_members_insert_admin
on public.ordax_space_members for insert to authenticated
with check (private.ordax_can_admin_space(space_id));

create policy ordax_space_members_update_admin
on public.ordax_space_members for update to authenticated
using (private.ordax_can_admin_space(space_id))
with check (private.ordax_can_admin_space(space_id));

create policy ordax_space_members_delete_admin
on public.ordax_space_members for delete to authenticated
using (private.ordax_can_admin_space(space_id));

create policy ordax_entitlement_grants_select_subject
on public.ordax_entitlement_grants for select to authenticated
using (
  user_id = (select auth.uid())
  or (space_id is not null and private.ordax_can_access_space(space_id))
);

create policy ordax_profile_packs_select_authenticated
on public.ordax_profile_packs for select to authenticated
using (true);

create policy ordax_space_profile_packs_select_member
on public.ordax_space_profile_packs for select to authenticated
using (private.ordax_can_access_space(space_id));

create policy ordax_memory_items_select_authorized
on public.ordax_memory_items for select to authenticated
using (
  owner_user_id = (select auth.uid())
  or (space_id is not null and private.ordax_can_access_space(space_id))
);

create policy ordax_memory_items_insert_own
on public.ordax_memory_items for insert to authenticated
with check (
  owner_user_id = (select auth.uid())
  and (space_id is null or private.ordax_can_access_space(space_id))
);

create policy ordax_memory_items_update_own
on public.ordax_memory_items for update to authenticated
using (owner_user_id = (select auth.uid()))
with check (
  owner_user_id = (select auth.uid())
  and (space_id is null or private.ordax_can_access_space(space_id))
);

create policy ordax_memory_items_delete_own
on public.ordax_memory_items for delete to authenticated
using (owner_user_id = (select auth.uid()));

create policy ordax_memory_embeddings_select_authorized
on public.ordax_memory_embeddings for select to authenticated
using (
  exists (
    select 1
    from public.ordax_memory_items m
    where m.memory_id = ordax_memory_embeddings.memory_id
      and (
        m.owner_user_id = (select auth.uid())
        or (m.space_id is not null and private.ordax_can_access_space(m.space_id))
      )
  )
);

create policy ordax_project_connections_select_space
on public.ordax_project_connections for select to authenticated
using (private.ordax_can_access_space(space_id));

commit;
