"use client"
import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { User, Mail, Calendar, Loader2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface UserInfo {
  id: string
  email: string
  first_name: string
  last_name: string
  created_at?: string
  updated_at?: string
}

export function UserProfileInfo() {
  const { data: session, status } = useSession({ required: false })
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const userId = (session?.user as any)?.id as string | undefined

  const fetchUserInfo = useCallback(async () => {
    if (!userId) {
      setError('Missing user id in session')
      setLoading(false)
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
      const res = await fetch(`${base}/api/user/${userId}`)
      
      if (!res.ok) {
        throw new Error('Failed to fetch user information')
      }
      
      const data = await res.json()
      setUserInfo(data.user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load user information')
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    if (status === 'loading') return
    if (!userId) {
      setError('Please log in to view your profile')
      setLoading(false)
      return
    }
    fetchUserInfo()
  }, [status, userId, fetchUserInfo])

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Unknown'
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    } catch {
      return 'Unknown'
    }
  }

  if (status === 'loading' || loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
          <CardDescription>Your account details</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
          <CardDescription>Your account details</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!userInfo) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
          <CardDescription>Your account details</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No user information available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile Information</CardTitle>
        <CardDescription>Your account details</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center gap-4">
          <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
            <User className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h3 className="text-xl font-semibold">
              {userInfo.first_name} {userInfo.last_name}
            </h3>
            <p className="text-sm text-muted-foreground">User ID: {userInfo.id}</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <Mail className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div>
              <p className="text-sm font-medium">Email</p>
              <p className="text-sm text-muted-foreground">{userInfo.email}</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <User className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div>
              <p className="text-sm font-medium">Full Name</p>
              <p className="text-sm text-muted-foreground">
                {userInfo.first_name} {userInfo.last_name}
              </p>
            </div>
          </div>

          {userInfo.created_at && (
            <div className="flex items-start gap-3">
              <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm font-medium">Member Since</p>
                <p className="text-sm text-muted-foreground">
                  {formatDate(userInfo.created_at)}
                </p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

