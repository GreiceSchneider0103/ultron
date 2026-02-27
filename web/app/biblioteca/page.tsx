import { withProtectedShell } from '@/components/layout/protected-app-page'
import { LibraryPage } from '@/components/pages/library-page'

export default async function BibliotecaPage() {
  return withProtectedShell((ctx) => <LibraryPage workspaceId={ctx.workspaceId} />)
}
