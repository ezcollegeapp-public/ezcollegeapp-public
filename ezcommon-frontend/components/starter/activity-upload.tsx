"use client"
import { useCallback, useEffect, useMemo, useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { Mic, Square, Loader2 } from 'lucide-react'

export function ActivityUpload() {
  const router = useRouter()
  const { data: session, status } = useSession({ required: false })
  const [files, setFiles] = useState<File[]>([])
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [existing, setExisting] = useState<{ filename: string; size: number; url?: string }[]>([])
  const [progress, setProgress] = useState<number>(0)

  // Voice recording state
  const [recording, setRecording] = useState(false)
  const [processingVoice, setProcessingVoice] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)

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

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      const chunks: BlobPart[] = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data)
      }

      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        await handleVoiceUpload(blob)
        stream.getTracks().forEach((t) => t.stop())
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setRecording(true)
      setError(null)
    } catch (err) {
      console.error(err)
      setError('Microphone access denied or not available')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop()
      setRecording(false)
    }
  }

  const handleVoiceUpload = async (blob: Blob) => {
    setProcessingVoice(true)
    const userId = (session?.user as any)?.id as string | undefined
    if (!userId) return

    const formData = new FormData()
    formData.append('user_id', userId)
    formData.append('file', blob, 'voice_input.webm')
    formData.append('section', 'activity')

    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
      const res = await fetch(`${base}/api/voice/transcribe`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const errText = await res.text()
        throw new Error(`Transcription failed: ${errText}`)
      }

      // Refresh list
      const listRes = await fetch(`${base}/api/upload/activity?user_id=${encodeURIComponent(userId)}`)
      const listData = await listRes.json()
      setExisting(listData.files || [])
    } catch (err: any) {
      setError(err.message || 'Voice processing failed')
    } finally {
      setProcessingVoice(false)
    }
  }

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
        xhr.open('POST', `${base}/api/upload/activity`)
        xhr.upload.onprogress = (e) => { if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100)) }
        xhr.onload = () => { if (xhr.status >= 200 && xhr.status < 300) resolve(); else reject(new Error('Upload failed')) }
        xhr.onerror = () => reject(new Error('Network error'))
        xhr.send(form)
      })
      router.push('/starter/testing/upload')
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
    fetch(`${base}/api/upload/activity?user_id=${encodeURIComponent(userId)}`)
      .then((r) => r.json())
      .then((data) => setExisting(data.files || []))
      .catch(() => {})
  }, [session])

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Start your journey</h1>
        <p className="text-sm text-muted-foreground">Upload any documents for your activities (resumes, certificates). You can also skip and fill later.</p>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center justify-center rounded-lg border ${outline} p-10 text-center transition-colors`}
      >
        <p className="mb-4 text-sm text-muted-foreground">Drag and drop files here, or click to select. Multiple files supported.</p>
        <input
          aria-label="Upload activities files"
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

      {uploading && (
        <div className="w-full bg-muted h-2 rounded">
          <div className="h-2 bg-primary rounded" style={{ width: `${progress}%` }} />
        </div>
      )}

      <div className="rounded-lg border p-4 bg-card/50">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium">Or record voice input</h3>
          {processingVoice && (
            <span className="text-xs text-muted-foreground flex items-center">
              <Loader2 className="h-3 w-3 animate-spin mr-1" /> Processing...
            </span>
          )}
        </div>
        <Button
          variant={recording ? 'destructive' : 'secondary'}
          onClick={recording ? stopRecording : startRecording}
          disabled={processingVoice || uploading}
          className="w-full"
        >
          {recording ? (
            <>
              <Square className="mr-2 h-4 w-4" /> Stop Recording
            </>
          ) : (
            <>
              <Mic className="mr-2 h-4 w-4" /> Voice Input (Transcribe + Check)
            </>
          )}
        </Button>
      </div>

      <div className="flex flex-col gap-3">
        <Button onClick={handleSubmit} className="w-full" disabled={uploading || status === 'loading'}>
          {uploading ? 'Uploading...' : 'Submit'}
        </Button>
        <Link href="/starter/testing/upload" className="text-center text-sm text-muted-foreground hover:underline">Skip, I will manually input</Link>
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
