import { AppLayout } from '@/components/layout/app-layout'
import { ActivityUpload } from '@/components/starter/activity-upload'
import { OnboardingSteps } from '@/components/starter/onboarding-steps'

export const dynamic = 'force-dynamic'

export default function ActivityUploadPage() {
  return (
    <AppLayout>
      <div className="p-6 flex items-center justify-center">
        <div className="w-full max-w-2xl space-y-4">
          <OnboardingSteps current="activity" />
          <div className="border rounded-lg p-6 shadow-sm bg-card">
            <ActivityUpload />
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

