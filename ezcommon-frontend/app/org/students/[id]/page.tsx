import { redirect } from 'next/navigation'
import Link from 'next/link'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { AllFilesReview } from '@/components/starter/all-files-review'

export const dynamic = 'force-dynamic'

interface StudentDetail {
  id: string
  email?: string
  first_name?: string
  last_name?: string
  role?: string
}

async function fetchStudent(userId: string): Promise<StudentDetail | null> {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
  try {
    const res = await fetch(`${base}/api/auth/user/${encodeURIComponent(userId)}`, {
      cache: 'no-store',
    })
    if (!res.ok) {
      console.error('Failed to fetch student detail', await res.text())
      return null
    }
    const data = await res.json()
    return data as StudentDetail
  } catch (e) {
    console.error('Error fetching student detail', e)
    return null
  }
}

export default async function OrgStudentDetailPage({
  params,
}: {
  params: any
}) {
  const session = await getServerSession(authOptions)
  const user: any = session?.user || {}
  const role: string = user.role ?? 'student'

  // Only organization users can view this page; others are redirected
  if (!session) {
    redirect('/auth/login')
  }
  if (role !== 'org_admin' && role !== 'org_staff') {
    redirect('/')
  }

  const resolvedParams = await (params as any)
  const studentIdRaw = resolvedParams?.id as string | undefined

  console.log('[OrgStudentDetail] resolvedParams:', resolvedParams, 'studentIdRaw:', studentIdRaw)

  // Guard against invalid route param (e.g. /org/students/undefined)
  if (!studentIdRaw || studentIdRaw === 'undefined') {
    console.warn('[OrgStudentDetail] Invalid studentIdRaw, redirecting to list')
    redirect('/org/students')
  }

  const studentId = decodeURIComponent(studentIdRaw)
  const student = await fetchStudent(studentId)

  if (!student) {
    return (
      <div className="p-6">
        <p className="text-sm text-destructive">Student not found.</p>
      </div>
    )
  }

  const fullName = `${student.first_name ?? ''} ${student.last_name ?? ''}`.trim()

  return (
    <div className="p-6 space-y-4 max-w-xl">
      <div>
        <h1 className="text-2xl font-semibold">Student details</h1>
        <p className="text-muted-foreground mt-1">
          Basic information for this student account.
        </p>
      </div>

      <div className="border rounded-lg bg-card p-4 space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Name</span>
          <span className="font-medium">{fullName || 'N/A'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Email</span>
          <span className="font-medium">{student.email || 'N/A'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">User ID</span>
          <span className="font-mono text-xs">{student.id}</span>
        </div>
      </div>

      <div className="border rounded-lg bg-card p-4 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold">Application files</h2>
            <p className="text-xs text-muted-foreground">
              View and manage all documents this student has uploaded.
            </p>
          </div>
          <Button asChild size="sm" variant="outline">
            <Link href={`/parse?user_id=${encodeURIComponent(student.id)}`}>
              使用 AI 帮助申请
            </Link>
          </Button>
        </div>

        <div className="mt-2">
          <AllFilesReview userIdOverride={student.id} />
        </div>
      </div>
    </div>
  )
}

