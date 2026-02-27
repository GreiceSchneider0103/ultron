import { withProtectedShell } from '@/components/layout/protected-app-page'
import { RulesPage } from '@/components/pages/rules-page'

export default async function RegrasPage() {
  return withProtectedShell(() => <RulesPage />)
}
