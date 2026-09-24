begin;

create index if not exists ordax_project_connections_owner_idx
  on public.ordax_project_connections(owner_user_id);

create index if not exists ordax_space_profile_packs_enabled_by_idx
  on public.ordax_space_profile_packs(enabled_by);

create index if not exists ordax_space_profile_packs_pack_idx
  on public.ordax_space_profile_packs(pack_slug, pack_version);

commit;
