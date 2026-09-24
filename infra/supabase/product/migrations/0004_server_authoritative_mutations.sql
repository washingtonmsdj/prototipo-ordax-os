begin;

-- Authenticated clients may read authorized product-domain rows, but they must
-- not mutate billable/scoped resources directly through the Data API.
-- Product gateways/services enforce entitlements, quotas, auditing and future
-- approval policy before using server-side authority.

revoke insert, update, delete on table public.ordax_spaces from authenticated;
revoke insert, update, delete on table public.ordax_space_members from authenticated;
revoke insert, update, delete on table public.ordax_memory_items from authenticated;
revoke insert, update, delete on table public.ordax_memory_embeddings from authenticated;
revoke insert, update, delete on table public.ordax_project_connections from authenticated;
revoke insert, update, delete on table public.ordax_space_profile_packs from authenticated;
revoke insert, update, delete on table public.ordax_entitlement_grants from authenticated;
revoke insert, update, delete on table public.ordax_profile_packs from authenticated;

revoke update on table public.ordax_accounts from authenticated;
grant update (display_name) on table public.ordax_accounts to authenticated;

commit;
