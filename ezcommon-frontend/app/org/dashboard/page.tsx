import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

export const dynamic = 'force-dynamic'

export default async function OrgDashboardPage() {
  const session = await getServerSession(authOptions)
  const user: any = session?.user || {}
  const orgId: string | null = user.orgId ?? null

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Organization Dashboard</h1>
        <p className="text-muted-foreground mt-2">
          Manage your students and invitations in EZCommon.
        </p>
      </div>

      {orgId && (
        <p className="text-sm text-muted-foreground">
          Organization ID: <span className="font-mono">{orgId}</span>
        </p>
      )}
    </div>
  )
}

