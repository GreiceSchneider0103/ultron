import { redirect } from 'next/navigation'

import { createClient } from '@/utils/supabase/server'

type WorkspaceContext = {
  user: { id: string; email: string | null }
  workspaceId: string
  role: string
  workspace: { id: string; name: string; plan: string | null }
}

export async function getWorkspaceContext(): Promise<WorkspaceContext> {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) redirect('/login')

  let { data: membership } = await supabase
    .from('workspace_members')
    .select('workspace_id, role, workspaces(id, name, plan)')
    .eq('user_id', user.id)
    .limit(1)
    .maybeSingle()

  if (!membership?.workspace_id) {
    const workspaceName = `${(user.email ?? 'workspace').split('@')[0]}-workspace`
    const { data: createdWorkspace } = await supabase
      .from('workspaces')
      .insert({ name: workspaceName })
      .select('id, name, plan')
      .single()

    if (createdWorkspace?.id) {
      await supabase.from('workspace_members').insert({
        workspace_id: createdWorkspace.id,
        user_id: user.id,
        role: 'admin',
      })
    }

    const retry = await supabase
      .from('workspace_members')
      .select('workspace_id, role, workspaces(id, name, plan)')
      .eq('user_id', user.id)
      .limit(1)
      .maybeSingle()

    membership = retry.data
  }

  if (!membership?.workspace_id) redirect('/dashboard')
  const workspace = Array.isArray(membership.workspaces) ? membership.workspaces[0] : membership.workspaces
  if (!workspace?.id) redirect('/dashboard')

  return {
    user: { id: user.id, email: user.email ?? null },
    workspaceId: membership.workspace_id,
    role: membership.role,
    workspace: {
      id: workspace.id,
      name: workspace.name,
      plan: workspace.plan ?? 'free',
    },
  }
}
