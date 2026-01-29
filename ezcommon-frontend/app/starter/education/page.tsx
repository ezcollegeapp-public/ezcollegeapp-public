import { AppLayout } from '@/components/layout/app-layout'
import { SectionFilePreview } from '@/components/starter/section-file-preview'

export const dynamic = 'force-dynamic'

export default function StarterEducationIndex() {
  return (
    <AppLayout>
      <SectionFilePreview
        section="education"
        title="Education Documents"
        description="View and manage your education documents, transcripts, and related files."
      />
    </AppLayout>
  )
}
