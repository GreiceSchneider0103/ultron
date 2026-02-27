'use client'

import { createClient } from '@/utils/supabase/client'

export async function getWorkspaceMembers(workspaceId: string) {
  const supabase = createClient()
  const { data, error } = await supabase
    .from('workspace_members')
    .select('workspace_id,user_id,role,created_at')
    .eq('workspace_id', workspaceId)
    .order('created_at', { ascending: false })

  if (error) throw new Error(error.message)
  return data ?? []
}

export async function getWorkspaceSettings(workspaceId: string) {
  const supabase = createClient()
  const { data, error } = await supabase
    .from('workspaces')
    .select('id,name,plan,created_at,updated_at')
    .eq('id', workspaceId)
    .maybeSingle()

  if (error) throw new Error(error.message)
  return data
}

export async function updateWorkspaceName(workspaceId: string, name: string) {
  const supabase = createClient()
  const { data, error } = await supabase
    .from('workspaces')
    .update({ name })
    .eq('id', workspaceId)
    .select('id,name,plan,updated_at')
    .single()

  if (error) throw new Error(error.message)
  return data
}
