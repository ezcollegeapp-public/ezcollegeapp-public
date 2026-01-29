import { AppLayout } from '@/components/layout/app-layout'
import { EducationReview } from '@/components/starter/education-review'
import { OnboardingSteps } from '@/components/starter/onboarding-steps'

export const dynamic = 'force-dynamic'

export default function EducationReviewPage() {
  return (
    <AppLayout>
      <div className="p-6 flex items-center justify-center">
        <div className="w-full max-w-2xl space-y-4">
          <OnboardingSteps current="education" />
          <div className="border rounded-lg p-6 shadow-sm bg-card">
            <EducationReview />
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
