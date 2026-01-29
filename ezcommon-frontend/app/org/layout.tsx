import { ReactNode } from 'react'
import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'
import { OrgLayout } from '@/components/layout/org-layout'

export const dynamic = 'force-dynamic'

export default async function OrgRootLayout({ children }: { children: ReactNode }) {
  const session = await getServerSession(authOptions)
  if (!session) {
    redirect('/auth/login')
  }

  const user: any = session.user || {}
  const role: string = user.role ?? 'student'

  if (role !== 'org_admin' && role !== 'org_staff') {
    redirect('/')
  }

  return <OrgLayout>{children}</OrgLayout>
}

