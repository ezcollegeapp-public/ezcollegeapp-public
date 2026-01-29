"use client"
import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'

const MONTHS = [
  'January','February','March','April','May','June','July','August','September','October','November','December'
] as const

const ReviewSchema = z.object({
  schoolName: z.string().min(1, 'School name is required'),
  country: z.string().min(1, 'Country is required'),
  city: z.string().min(1, 'City is required'),
  state: z.string().optional(),
  startMonth: z.enum(MONTHS),
  startYear: z.string().regex(/^\d{4}$/, 'Enter a 4-digit year'),
  endMonth: z.enum(MONTHS).optional(),
  endYear: z.string().regex(/^\d{4}$/, 'Enter a 4-digit year').optional(),
  currentlyAttending: z.boolean().optional().default(false),
  gpa: z.coerce.number().min(0).max(5, 'GPA must be 0.00–5.00'),
  classRank: z.string().optional(),
  counselorName: z.string().optional(),
  counselorEmail: z.string().email('Enter a valid email').optional().or(z.literal('')),
}).refine((data) => {
  if (data.currentlyAttending) return true
  return Boolean(data.endMonth && data.endYear)
}, { message: 'End month and year are required unless currently attending', path: ['endYear'] })

type ReviewValues = z.infer<typeof ReviewSchema>

const SCHOOL_SUGGESTIONS = [
  'Springfield High School',
  'Riverdale High School',
  'Roosevelt High School',
  'Lincoln High School',
  'Jefferson High School',
]

export function EducationReviewForm() {
  const [loading, setLoading] = useState(false)
  const defaults = useMemo<Partial<ReviewValues>>(() => {
    let draft: Partial<ReviewValues> = {}
    try {
      const raw = localStorage.getItem('onboarding_education')
      if (raw) draft = JSON.parse(raw)
    } catch {}
    return {
      schoolName: draft.schoolName ?? '',
      country: draft.country ?? '',
      city: draft.city ?? '',
      state: draft.state ?? '',
      startMonth: (draft.startMonth as ReviewValues['startMonth']) ?? 'August',
      startYear: draft.startYear ?? '',
      endMonth: (draft.endMonth as ReviewValues['endMonth']) ?? undefined,
      endYear: draft.endYear ?? '',
      currentlyAttending: Boolean(draft.currentlyAttending),
      gpa: draft.gpa ?? 4.00,
      classRank: draft.classRank ?? '',
      counselorName: draft.counselorName ?? '',
      counselorEmail: draft.counselorEmail ?? '',
    }
  }, [])

  const form = useForm<ReviewValues>({
    resolver: zodResolver(ReviewSchema),
    defaultValues: defaults as ReviewValues,
  })

  useEffect(() => {
    const sub = form.watch((v) => {
      try { localStorage.setItem('onboarding_education', JSON.stringify(v)) } catch {}
    })
    return () => sub.unsubscribe()
  }, [form])

  const currently = form.watch('currentlyAttending')

  const onSubmit = async (values: ReviewValues) => {
    setLoading(true)
    try {
      // TODO: Persist to backend then navigate to next onboarding step (e.g., activities)
      console.log('Onboarding education saved', values)
      window.location.href = '/'
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Start your journey</h1>
        <p className="text-sm text-muted-foreground">Review your education information from the transcript. Edit anything that needs correction.</p>
      </div>

      <form className="space-y-5" onSubmit={form.handleSubmit(onSubmit)}>
        <div className="space-y-2">
          <Label htmlFor="schoolName">School Name</Label>
          <input list="schoolList" id="schoolName" className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" {...form.register('schoolName')} />
          <datalist id="schoolList">
            {SCHOOL_SUGGESTIONS.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
          {form.formState.errors.schoolName && <p className="text-sm text-destructive">{form.formState.errors.schoolName.message}</p>}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="country">Country</Label>
            <Input id="country" {...form.register('country')} />
            {form.formState.errors.country && <p className="text-sm text-destructive">{form.formState.errors.country.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="city">City</Label>
            <Input id="city" {...form.register('city')} />
            {form.formState.errors.city && <p className="text-sm text-destructive">{form.formState.errors.city.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="state">State</Label>
            <Input id="state" placeholder="State/Province" {...form.register('state')} />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Start Month / Year</Label>
            <div className="grid grid-cols-2 gap-3">
              <select className="h-10 rounded-md border border-input bg-background px-3 text-sm" {...form.register('startMonth')}>
                {MONTHS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
              <Input placeholder="YYYY" {...form.register('startYear')} />
            </div>
            {(form.formState.errors.startMonth || form.formState.errors.startYear) && (
              <p className="text-sm text-destructive">{form.formState.errors.startMonth?.message || form.formState.errors.startYear?.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>End Month / Year</Label>
              <label className="flex items-center gap-2 text-sm">
                <Checkbox checked={currently} onCheckedChange={(v) => form.setValue('currentlyAttending', Boolean(v), { shouldValidate: true })} />
                I currently attend here
              </label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <select className="h-10 rounded-md border border-input bg-background px-3 text-sm disabled:opacity-60" disabled={currently} {...form.register('endMonth')}>
                <option value="">Month</option>
                {MONTHS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
              <Input placeholder="YYYY" disabled={currently} {...form.register('endYear')} />
            </div>
            {(form.formState.errors.endMonth || form.formState.errors.endYear) && !currently && (
              <p className="text-sm text-destructive">{form.formState.errors.endMonth?.message || form.formState.errors.endYear?.message}</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="gpa">GPA</Label>
            <Input id="gpa" type="number" step="0.01" min="0" max="5" {...form.register('gpa', { valueAsNumber: true })} />
            {form.formState.errors.gpa && <p className="text-sm text-destructive">{form.formState.errors.gpa.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="classRank">Class Rank (optional)</Label>
            <Input id="classRank" placeholder="e.g., Top 10% or 15/400" {...form.register('classRank')} />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="counselorName">Counselor Name (optional)</Label>
            <Input id="counselorName" {...form.register('counselorName')} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="counselorEmail">Counselor Email (optional)</Label>
            <Input id="counselorEmail" type="email" {...form.register('counselorEmail')} />
            {form.formState.errors.counselorEmail && <p className="text-sm text-destructive">{form.formState.errors.counselorEmail.message}</p>}
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <Button type="submit" disabled={loading} className="w-full">{loading ? 'Saving...' : 'Save and continue'}</Button>
          <a href="/" className="text-center text-sm text-muted-foreground hover:underline">Skip, I&apos;ll do it later</a>
        </div>
      </form>
    </div>
  )
}

