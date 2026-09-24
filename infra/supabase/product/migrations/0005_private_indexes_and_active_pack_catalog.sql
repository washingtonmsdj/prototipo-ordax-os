begin;

-- Draft/retired product-pack definitions are backend/catalog-authority data.
-- Authenticated users may see only packs explicitly activated for the product.
drop policy if exists ordax_profile_packs_select_authenticated
  on public.ordax_profile_packs;

create policy ordax_profile_packs_select_active
on public.ordax_profile_packs
for select
to authenticated
using (state = 'active');

-- Embeddings are a derived internal search index. User-facing Memory exposes the
-- authorized memory item, never the raw vector representation.
revoke select on table public.ordax_memory_embeddings from authenticated;

commit;
