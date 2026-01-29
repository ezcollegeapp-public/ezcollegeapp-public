import Link from 'next/link'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface OrgStudent {
  id: string
  email?: string
  first_name?: string
  last_name?: string
}

async function fetchOrgStudents(orgId: string): Promise<OrgStudent[]> {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
  try {
    const res = await fetch(
      `${base}/api/org/students?org_id=${encodeURIComponent(orgId)}`,
      { cache: 'no-store' },
    )
    if (!res.ok) {
      console.error('Failed to fetch org students', await res.text())
      return []
    }
    const data = await res.json()
    const students = (data as any)?.students ?? []
    return Array.isArray(students) ? students : []
  } catch (e) {
    console.error('Error fetching org students', e)
    return []
  }
}

export default async function OrgStudentsPage() {
  const session = await getServerSession(authOptions)
  const user: any = session?.user || {}
  const orgId = (user.orgId as string | undefined) ?? undefined

  if (!orgId) {
    return (
      <div className="p-6">
        <p className="text-sm text-destructive">No organization is associated with your account.</p>
      </div>
    )
  }

  const students = await fetchOrgStudents(orgId)

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Students</h1>
        <p className="text-muted-foreground mt-1">
          These students have accepted your organization&apos;s invitation.
        </p>
      </div>

      {students.length === 0 ? (
        <p className="text-sm text-muted-foreground">No students have accepted your invitation yet.</p>
      ) : (
        <div className="border rounded-lg divide-y bg-card">
          {students.map((s) => {
            const fullName = `${s.first_name ?? ''} ${s.last_name ?? ''}`.trim()
            return (
              <div
                key={s.id}
                className="flex items-center justify-between px-4 py-3 text-sm"
              >
                <div>
                  <div className="font-medium">
                    {fullName || s.email || 'Student'}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    <span className="font-mono">{s.id}</span>
                    {s.email && <span className="ml-2">{s.email}</span>}
                  </div>
                </div>
                <Link
                  href={`/org/students/${encodeURIComponent(s.id)}`}
                  className="text-xs text-primary hover:underline"
                >
                  View details
                </Link>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

