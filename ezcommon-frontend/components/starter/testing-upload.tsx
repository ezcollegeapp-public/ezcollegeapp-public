"use client"
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'

export function TestingUpload() {
  const router = useRouter()
  const { data: session, status } = useSession({ required: false })
  const [files, setFiles] = useState<File[]>([])
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [existing, setExisting] = useState<{ filename: string; size: number; url?: string }[]>([])
  const [progress, setProgress] = useState<number>(0)

  const onDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragOver(false)
    const list = Array.from(e.dataTransfer.files || [])
    if (list.length) setFiles((prev) => [...prev, ...list])
  }, [])

  const onSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const list = Array.from(e.target.files || [])
    if (list.length) setFiles((prev) => [...prev, ...list])
  }, [])

  const outline = useMemo(() => (dragOver ? 'border-primary bg-accent/40' : 'border-dashed border-muted-foreground/40'), [dragOver])

  const handleSubmit = useCallback(async () => {
    setError(null)
    const userId = (session?.user as any)?.id as string | undefined
    if (!userId) { setError('Missing user id in session'); return }
    if (!files.length) { setError('Please select at least one file'); return }
    setUploading(true)
    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
      const form = new FormData()
      form.append('user_id', userId)
      files.forEach((f) => form.append('files', f))
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest()
        xhr.open('POST', `${base}/api/upload/testing`)
        xhr.upload.onprogress = (e) => { if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100)) }
        xhr.onload = () => { if (xhr.status >= 200 && xhr.status < 300) resolve(); else reject(new Error('Upload failed')) }
        xhr.onerror = () => reject(new Error('Network error'))
        xhr.send(form)
      })
      router.push('/')
    } catch (e: any) {
      setError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }, [session, files, router])

  useEffect(() => {
    const userId = (session?.user as any)?.id as string | undefined
    if (!userId) return
    const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
    fetch(`${base}/api/upload/testing?user_id=${encodeURIComponent(userId)}`)
      .then((r) => r.json())
      .then((data) => setExisting(data.files || []))
      .catch(() => {})
  }, [session])

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Start your journey</h1>
        <p className="text-sm text-muted-foreground">Upload any standardized testing documents (SAT, ACT, TOEFL, IELTS). You can also skip and fill later.</p>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center justify-center rounded-lg border ${outline} p-10 text-center transition-colors`}
      >
        <p className="mb-4 text-sm text-muted-foreground">Drag and drop files here, or click to select. Multiple files supported.</p>
        <input
          aria-label="Upload testing files"
          type="file"
          multiple
          onChange={onSelect}
          className="block cursor-pointer text-sm"
        />
        {files.length > 0 && (
          <ul className="mt-3 text-sm text-left w-full max-w-md">
            {files.map((f, i) => (
              <li key={i} className="truncate">• {f.name}</li>
            ))}
          </ul>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {error && <p className="text-sm text-destructive">{error}</p>}
      {uploading && (
        <div className="w-full bg-muted h-2 rounded">
          <div className="h-2 bg-primary rounded" style={{ width: `${progress}%` }} />
        </div>
      )}

      <div className="flex flex-col gap-3">
        <Button onClick={handleSubmit} className="w-full" disabled={uploading || status === 'loading'}>
          {uploading ? 'Uploading...' : 'Submit'}
        </Button>
        <Link href="/" className="text-center text-sm text-muted-foreground hover:underline">Skip, I will manually input</Link>
      </div>

      {existing.length > 0 && (
        <div className="mt-4 text-sm">
          <div className="font-medium mb-2">Uploaded files</div>
          <ul className="list-disc pl-5 space-y-1">
            {existing.map((f, idx) => (
              <li key={idx} className="truncate">
                {f.filename} <span className="text-muted-foreground">({Math.round(f.size / 1024)} KB)</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
