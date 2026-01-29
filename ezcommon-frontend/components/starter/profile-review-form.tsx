"use client"
import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

const applyingAsOptions = ['Freshman', 'Transfer', 'International', 'Reapplicant'] as const

const ReviewSchema = z.object({
  firstName: z.string().min(1, 'First name is required'),
  lastName: z.string().min(1, 'Last name is required'),
  preferredName: z.string().optional(),
  email: z.string().email('Enter a valid email'),
  phoneNumber: z.string().min(7, 'Enter a valid phone'),
  dateOfBirth: z.string().min(1, 'Date of birth is required'),
  citizenships: z.string().optional(), // comma separated
  applyingAs: z.enum(applyingAsOptions),
  commonAppId: z.string().optional(),
  intendedMajor: z.string().min(1, 'Please select or enter a major'),
  heardAbout: z.string().min(1, 'Please tell us how you heard about us'),
})

export type ReviewValues = z.infer<typeof ReviewSchema>

const MAJOR_OPTIONS = [
  'Computer Science',
  'Business Administration',
  'Economics',
  'Biology',
  'Psychology',
  'Mathematics',
  'Mechanical Engineering',
]

export function ProfileReviewForm({ email }: { email?: string | null }) {
  const [loading, setLoading] = useState(false)

  const defaults = useMemo<Partial<ReviewValues>>(() => {
    let draft: Partial<ReviewValues> = {}
    try {
      const raw = localStorage.getItem('onboarding_profile')
      if (raw) draft = JSON.parse(raw)
    } catch {}
    if (email && !draft.email) draft.email = email
    return {
      firstName: draft.firstName ?? '',
      lastName: draft.lastName ?? '',
      preferredName: draft.preferredName ?? '',
      email: draft.email ?? '',
      phoneNumber: draft.phoneNumber ?? '',
      dateOfBirth: draft.dateOfBirth ?? '',
      citizenships: draft.citizenships ?? '',
      applyingAs: (draft.applyingAs as ReviewValues['applyingAs']) ?? 'Freshman',
      commonAppId: draft.commonAppId ?? '',
      intendedMajor: draft.intendedMajor ?? '',
      heardAbout: draft.heardAbout ?? '',
    }
  }, [email])

  const form = useForm<ReviewValues>({
    resolver: zodResolver(ReviewSchema),
    defaultValues: defaults as ReviewValues,
  })

  useEffect(() => {
    // Keep local draft up to date
    const sub = form.watch((v) => {
      try { localStorage.setItem('onboarding_profile', JSON.stringify(v)) } catch {}
    })
    return () => sub.unsubscribe()
  }, [form])

  const onSubmit = async (values: ReviewValues) => {
    setLoading(true)
    try {
      // TODO: Persist to backend, then go to next onboarding step
      console.log('Onboarding profile saved', values)
      // Go to next onboarding step: education
      window.location.href = '/starter/education'
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Start your journey</h1>
        <p className="text-sm text-muted-foreground">Review and edit your basic profile information.</p>
      </div>

      <form className="space-y-5" onSubmit={form.handleSubmit(onSubmit)}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="firstName">First Name</Label>
            <Input id="firstName" {...form.register('firstName')} />
            {form.formState.errors.firstName && <p className="text-sm text-destructive">{form.formState.errors.firstName.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="lastName">Last Name</Label>
            <Input id="lastName" {...form.register('lastName')} />
            {form.formState.errors.lastName && <p className="text-sm text-destructive">{form.formState.errors.lastName.message}</p>}
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="preferredName">Preferred Name (optional)</Label>
          <Input id="preferredName" placeholder="If different" {...form.register('preferredName')} />
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" {...form.register('email')} />
          {form.formState.errors.email && <p className="text-sm text-destructive">{form.formState.errors.email.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="phoneNumber">Phone Number</Label>
          <Input id="phoneNumber" placeholder="e.g. +1 555 123 4567" {...form.register('phoneNumber')} />
          {form.formState.errors.phoneNumber && <p className="text-sm text-destructive">{form.formState.errors.phoneNumber.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="dateOfBirth">Date of Birth</Label>
          <Input id="dateOfBirth" type="date" {...form.register('dateOfBirth')} />
          {form.formState.errors.dateOfBirth && <p className="text-sm text-destructive">{form.formState.errors.dateOfBirth.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="citizenships">Citizenship(s)</Label>
          <Input id="citizenships" placeholder="Comma-separated, e.g. United States, Canada" {...form.register('citizenships')} />
        </div>

        <div className="space-y-2">
          <Label htmlFor="applyingAs">Applying as</Label>
          <select id="applyingAs" className="h-10 rounded-md border border-input bg-background px-3 text-sm" {...form.register('applyingAs')}>
            {applyingAsOptions.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="commonAppId">Common App ID (optional)</Label>
          <Input id="commonAppId" {...form.register('commonAppId')} />
        </div>

        <div className="space-y-2">
          <Label>Intended Major</Label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <select className="h-10 rounded-md border border-input bg-background px-3 text-sm" onChange={(e) => {
              const v = e.target.value
              if (v) form.setValue('intendedMajor', v, { shouldValidate: true })
            }}>
              <option value="">Select a major</option>
              {MAJOR_OPTIONS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <Input placeholder="Or type your major" {...form.register('intendedMajor')} />
          </div>
          {form.formState.errors.intendedMajor && <p className="text-sm text-destructive">{form.formState.errors.intendedMajor.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="heardAbout">How did you hear about EZ Common App?</Label>
          <Input id="heardAbout" placeholder="Friend, counselor, social media, search, etc." {...form.register('heardAbout')} />
          {form.formState.errors.heardAbout && <p className="text-sm text-destructive">{form.formState.errors.heardAbout.message}</p>}
        </div>

        <div className="flex flex-col gap-3">
          <Button type="submit" disabled={loading} className="w-full">{loading ? 'Saving...' : 'Save and continue'}</Button>
          <Link href="#" onClick={(e) => { e.preventDefault(); window.location.href = '/starter/education' }} className="text-center text-sm text-muted-foreground hover:underline">Skip, I&apos;ll do it later</Link>
        </div>
      </form>
    </div>
  )
}
