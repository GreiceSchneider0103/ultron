import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'

type CookieStoreWritable = {
  set: (name: string, value: string, options?: CookieOptions) => void
}

export async function createClient() {
  const cookieStore = await cookies()

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          // Next (algumas versões) tipa como readonly, mas em runtime funciona
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            const writable = cookieStore as unknown as CookieStoreWritable
            cookiesToSet.forEach(({ name, value, options }) => {
              writable.set(name, value, options as CookieOptions)
            })
          } catch {
            // Em Server Components pode falhar ao setar cookie — ok
          }
        },
      },
    }
  )
}
