create or replace function public.ordax_sync_snapshot_v1(
  p_limit integer default 200
)
returns jsonb
language sql
security invoker
set search_path = ''
as $function$
  with checkpoint as (
    select coalesce(max(m.change_seq), 0)::bigint as cursor
    from private.ordax_sync_mutations m
    where m.owner_user_id = (select auth.uid())
  ),
  objects as (
    select jsonb_agg(
      jsonb_build_object(
        'sync_object_id', o.sync_object_id,
        'data_class', o.data_class,
        'stable_object_id', o.stable_object_id,
        'object_schema_version', o.object_schema_version,
        'resolver_version', o.resolver_version,
        'server_revision', o.server_revision,
        'tombstone', o.tombstone,
        'payload', o.payload,
        'updated_at', o.updated_at
      )
      order by o.data_class, o.stable_object_id
    ) as value
    from (
      select * from private.ordax_sync_objects
      where owner_user_id = (select auth.uid())
      order by data_class, stable_object_id
      limit least(greatest(coalesce(p_limit, 200), 1), 500)
    ) o
  )
  select jsonb_build_object(
    'cursor', checkpoint.cursor,
    'objects', coalesce(objects.value, '[]'::jsonb)
  )
  from checkpoint cross join objects;
$function$;

revoke all on function public.ordax_sync_snapshot_v1(integer) from public, anon;
grant execute on function public.ordax_sync_snapshot_v1(integer) to authenticated;
