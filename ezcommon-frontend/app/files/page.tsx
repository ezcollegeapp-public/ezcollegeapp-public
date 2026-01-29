import { AppLayout } from '@/components/layout/app-layout'
import { AllFilesReview } from '@/components/starter/all-files-review'

export const dynamic = 'force-dynamic'

export default function AllFilesPage() {
  return (
    <AppLayout>
      <div className="p-6">
        <div className="max-w-6xl mx-auto">
          <div className="mb-6">
            <h1 className="text-3xl font-bold tracking-tight">All Files</h1>
            <p className="text-muted-foreground mt-2">
              View and manage all your uploaded documents across all sections
            </p>
          </div>
          <div className="border rounded-lg p-6 shadow-sm bg-card">
            <AllFilesReview />
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

