import React from 'react'

type StepKey = 'profile' | 'education' | 'activity' | 'testing' | 'review'

const ORDER: { key: StepKey; label: string }[] = [
  { key: 'profile', label: 'Profile' },
  { key: 'education', label: 'Education' },
  { key: 'activity', label: 'Activity' },
  { key: 'testing', label: 'Testing' },
  { key: 'review', label: 'Review' },
]

export function OnboardingSteps({ current }: { current: StepKey }) {
  return (
    <div className="mb-4 text-base sm:text-lg">
      <nav aria-label="Onboarding steps" className="flex flex-wrap items-center gap-3 sm:gap-4">
        {ORDER.map((s, idx) => (
          <React.Fragment key={s.key}>
            <span className={s.key === current ? 'text-primary font-semibold' : 'text-muted-foreground'}>
              {s.label}
            </span>
            {idx < ORDER.length - 1 && <span className="text-muted-foreground">-</span>}
          </React.Fragment>
        ))}
      </nav>
    </div>
  )
}
