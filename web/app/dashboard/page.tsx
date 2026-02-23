import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export default async function DashboardPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) redirect('/login')

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-black">Dashboard</h1>
      <p className="mt-4 text-gray-600">Bem-vindo, {user.email}</p>
    </div>
  )
}