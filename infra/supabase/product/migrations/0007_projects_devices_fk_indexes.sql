begin;

-- Cover every foreign-key lookup introduced by the product Projects/Devices
-- foundation. These indexes are structural, not speculative query tuning.
create index ordax_project_connections_project_space_idx
  on public.ordax_project_connections(project_id, space_id);

create index ordax_remote_grants_project_space_idx
  on public.ordax_remote_capability_grants(project_id, space_id);

create index ordax_remote_grants_device_idx
  on public.ordax_remote_capability_grants(device_id);

create index ordax_remote_grants_approved_by_idx
  on public.ordax_remote_capability_grants(approved_by_user_id);

create index ordax_space_devices_granted_by_idx
  on public.ordax_space_devices(granted_by_user_id);

commit;
