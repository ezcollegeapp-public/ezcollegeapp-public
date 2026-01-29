import { AppLayout } from '@/components/layout/app-layout'
import { UserProfileInfo } from '@/components/starter/user-profile-info'
import { AllFilesReview } from '@/components/starter/all-files-review'

export const dynamic = 'force-dynamic'

export default function StarterProfileIndex() {
  return (
    <AppLayout>
      <div className="p-6 space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Profile</h1>
          <p className="text-muted-foreground mt-2">
            Manage your account information and uploaded documents
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          <div className="md:col-span-1">
            <UserProfileInfo />
          </div>

          <div className="md:col-span-2">
            <div className="border rounded-lg p-6 shadow-sm bg-card">
              <AllFilesReview />
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
