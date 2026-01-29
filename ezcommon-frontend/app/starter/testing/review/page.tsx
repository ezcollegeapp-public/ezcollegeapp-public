import { AppLayout } from '@/components/layout/app-layout'
import { TestingReview } from '@/components/starter/testing-review'
import { OnboardingSteps } from '@/components/starter/onboarding-steps'

export const dynamic = 'force-dynamic'

export default function TestingReviewPage() {
  return (
    <AppLayout>
      <div className="p-6 flex items-center justify-center">
        <div className="w-full max-w-2xl space-y-4">
          <OnboardingSteps current="testing" />
          <div className="border rounded-lg p-6 shadow-sm bg-card">
            <TestingReview />
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

