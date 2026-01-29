"use client"
import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { Trash2, Download, FileText, Upload } from 'lucide-react'

interface UploadedFile {
  filename: string
  size: number
  url?: string
  uploaded_at?: string
}

export function ActivityReview() {
  const router = useRouter()
  const { data: session, status } = useSession({ required: false })
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const userId = (session?.user as any)?.id as string | undefined

  const fetchFiles = useCallback(async () => {
    if (!userId) {
      setError('Missing user id in session')
      setLoading(false)
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
      const res = await fetch(`${base}/api/upload/activity?user_id=${userId}`)
      
      if (!res.ok) {
        throw new Error('Failed to fetch files')
      }
      
      const data = await res.json()
      setFiles(data.files || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files')
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    if (status === 'loading') return
    if (!userId) {
      setError('Please log in to view your files')
      setLoading(false)
      return
    }
    fetchFiles()
  }, [status, userId, fetchFiles])

  const handleDelete = async (filename: string) => {
    if (!userId) return
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return
    
    setDeleting(filename)
    setError(null)
    
    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
      const res = await fetch(`${base}/api/upload/activity/${encodeURIComponent(filename)}?user_id=${userId}`, {
        method: 'DELETE',
      })
      
      if (!res.ok) {
        throw new Error('Failed to delete file')
      }
      
      await fetchFiles()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete file')
    } finally {
      setDeleting(null)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Unknown'
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return 'Unknown'
    }
  }

  if (status === 'loading' || loading) {
    return (
      <div className="space-y-4">
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight">Activity Documents</h2>
          <p className="text-sm text-muted-foreground">Loading your uploaded files...</p>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold tracking-tight">Activity Documents</h2>
        <p className="text-sm text-muted-foreground">
          Review and manage your uploaded activity documents (certificates, awards, etc.)
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {!error && files.length === 0 && (
        <div className="rounded-lg border border-dashed border-muted-foreground/40 p-12 text-center">
          <FileText className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-medium mb-2">No files uploaded yet</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Upload your activity documents to get started
          </p>
          <Link href="/starter/activity/upload">
            <Button>
              <Upload className="mr-2 h-4 w-4" />
              Upload Files
            </Button>
          </Link>
        </div>
      )}

      {files.length > 0 && (
        <div className="space-y-4">
          <div className="rounded-lg border">
            <div className="divide-y">
              {files.map((file, index) => (
                <div key={index} className="p-4 flex items-center justify-between hover:bg-accent/50 transition-colors">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <FileText className="h-8 w-8 text-muted-foreground flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{file.filename}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatFileSize(file.size)} • {formatDate(file.uploaded_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {file.url && (
                      <a href={file.url} target="_blank" rel="noopener noreferrer">
                        <Button variant="outline" size="sm">
                          <Download className="h-4 w-4 mr-2" />
                          Download
                        </Button>
                      </a>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(file.filename)}
                      disabled={deleting === file.filename}
                      className="text-destructive hover:text-destructive"
                    >
                      {deleting === file.filename ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-destructive"></div>
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <Link href="/starter/activity/upload" className="flex-1">
              <Button variant="outline" className="w-full">
                <Upload className="mr-2 h-4 w-4" />
                Upload More Files
              </Button>
            </Link>
            <Link href="/starter/testing/upload" className="flex-1">
              <Button className="w-full">
                Continue to Testing
              </Button>
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

