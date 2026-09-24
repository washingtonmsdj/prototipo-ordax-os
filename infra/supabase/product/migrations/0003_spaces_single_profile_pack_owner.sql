begin;

alter table public.ordax_spaces
  drop column if exists profile_pack_slug;

revoke update on table public.ordax_spaces from authenticated;
grant update (name, state, metadata) on table public.ordax_spaces to authenticated;

commit;
