import { AppLayout } from '@/components/layout/app-layout'
import { ParsePageClient } from '@/components/parse/parse-page-client'

interface ParsePageProps {
  searchParams?: { [key: string]: string | string[] | undefined }
}

export default function ParsePage({ searchParams }: ParsePageProps) {
  const userIdParam = searchParams?.user_id
  const userIdOverride = Array.isArray(userIdParam) ? userIdParam[0] : userIdParam

  return (
    <AppLayout>
      <ParsePageClient userIdOverride={userIdOverride} />
    </AppLayout>
  )
}

