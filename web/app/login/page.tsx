import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ message?: string | string[] }>
}) {
  const resolvedSearchParams = await searchParams
  const message = Array.isArray(resolvedSearchParams?.message)
    ? resolvedSearchParams.message[0]
    : resolvedSearchParams?.message

  const supabase = await createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (session) redirect('/home')

  async function signIn(formData: FormData) {
    'use server'
    const email = String(formData.get('email') || '')
    const password = String(formData.get('password') || '')

    const supabase = await createClient()
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) redirect('/login?message=Erro ao fazer login')
    redirect('/home')
  }

  async function signUp(formData: FormData) {
    'use server'
    const email = String(formData.get('email') || '')
    const password = String(formData.get('password') || '')

    const supabase = await createClient()
    const { data, error } = await supabase.auth.signUp({ email, password })
    if (error) redirect('/login?message=Erro ao criar conta')
    if (!data.session) {
      redirect('/login?message=Conta criada. Confirme seu e-mail para entrar')
    }
    redirect('/home')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md space-y-6 rounded-xl bg-white p-8 shadow-md">
        <h1 className="text-center text-2xl font-bold text-gray-900">Ultron SaaS</h1>

        {message && (
          <p className="rounded-md bg-red-100 p-4 text-sm text-red-600">
            {message}
          </p>
        )}

        <form className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              name="email"
              type="email"
              required
              className="mt-1 w-full rounded-md border px-3 py-2 text-black focus:border-blue-500 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Senha</label>
            <input
              name="password"
              type="password"
              required
              className="mt-1 w-full rounded-md border px-3 py-2 text-black focus:border-blue-500 focus:ring-blue-500"
            />
          </div>

          <div className="flex gap-4 pt-4">
            <button
              formAction={signIn}
              className="w-full rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
            >
              Entrar
            </button>
            <button
              formAction={signUp}
              className="w-full rounded-md border border-blue-600 px-4 py-2 text-blue-600 hover:bg-blue-50"
            >
              Criar Conta
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
