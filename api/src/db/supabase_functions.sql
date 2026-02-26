-- ====================================================================================
-- ULTRON SAAS - Supabase Functions/Triggers Patch
-- Run after schema.sql if you only need helper functions/policies/trigger refresh.
-- ====================================================================================

create or replace function public.user_belongs_to_workspace(ws_id uuid)
returns boolean
language sql
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.workspace_members
    where workspace_id = ws_id
      and user_id = auth.uid()
  );
$$;

create or replace function public.handle_new_user_workspace()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  ws_id uuid;
  ws_name text;
begin
  ws_name := coalesce(
    new.raw_user_meta_data->>'workspace_name',
    split_part(coalesce(new.email, 'workspace'), '@', 1) || '-workspace'
  );

  insert into public.workspaces(name)
  values (ws_name)
  returning id into ws_id;

  insert into public.workspace_members(workspace_id, user_id, role)
  values (ws_id, new.id, 'admin');

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user_workspace();

