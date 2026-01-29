"use client"

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { AppLayout } from '@/components/layout/app-layout'
import { Button } from '@/components/ui/button'

interface Invitation {
  org_id: string
  student_id: string
  status: string
  created_at?: string
  updated_at?: string
  org_name?: string
}

const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'

export default function StudentInvitationsPage() {
  const { data: session } = useSession()
  const studentId = (session?.user as any)?.id as string | undefined

  const [invitations, setInvitations] = useState<Invitation[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadInvites = async () => {
    if (!studentId) return
    try {
      setLoading(true)
      setError(null)
      const res = await fetch(
        `${backendBase}/api/student/invitations?student_id=${encodeURIComponent(studentId)}`,
      )
      if (!res.ok) throw new Error('Failed to load invitations')
      const data = await res.json()
      const items = (data as any)?.items ?? []
      setInvitations(Array.isArray(items) ? items : [])
    } catch (e) {
      console.error(e)
      setError(e instanceof Error ? e.message : 'Failed to load invitations')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadInvites()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId])

  const handleAction = async (inv: Invitation, action: 'accept' | 'reject') => {
    if (!studentId) return
    try {
      setError(null)
      const res = await fetch(`${backendBase}/api/student/invitations/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ org_id: inv.org_id, student_id: studentId }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error((data as any)?.detail || `Failed to ${action} invitation`)
      }
      await loadInvites()
    } catch (e) {
      console.error(e)
      setError(e instanceof Error ? e.message : 'Operation failed')
    }
  }

  return (
    <AppLayout>
      <div className="p-6 space-y-4">
        <div>
          <h1 className="text-2xl font-semibold">Organization invitations</h1>
          <p className="text-muted-foreground mt-1">
            View and respond to invitations from organizations that want to help manage your
            application.
          </p>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading invitations...</p>
        ) : invitations.length === 0 ? (
          <p className="text-sm text-muted-foreground">You don&apos;t have any invitations yet.</p>
        ) : (
          <div className="border rounded-lg divide-y bg-card">
            {invitations.map((inv) => (
              <div
                key={`${inv.org_id}:${inv.student_id}`}
                className="flex items-center justify-between px-4 py-3 text-sm"
              >
                <div>
                  <div className="font-medium">
                    {inv.org_name || 'Organization'}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Status: {inv.status}
                    {inv.created_at && <span className="ml-2">Invited: {inv.created_at}</span>}
                  </div>
                </div>
                <div className="flex gap-2">
                  {inv.status === 'pending' && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleAction(inv, 'reject')}
                      >
                        Reject
                      </Button>
                      <Button size="sm" onClick={() => handleAction(inv, 'accept')}>
                        Accept
                      </Button>
                    </>
                  )}
                  {inv.status === 'accepted' && (
                    <span className="text-xs text-emerald-600 font-medium">Accepted</span>
                  )}
                  {inv.status === 'rejected' && (
                    <span className="text-xs text-muted-foreground">Rejected</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  )
}

