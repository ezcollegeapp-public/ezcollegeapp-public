"use client"
import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { Trash2, Download, FileText, Upload, FolderOpen } from 'lucide-react'

interface UploadedFile {
  filename: string
  size: number
  url?: string
  last_modified?: string
  section?: string
  s3_key?: string
}

interface FilesBySection {
  [key: string]: UploadedFile[]
}

const SECTION_LABELS: { [key: string]: string } = {
  profile: 'Profile Documents',
  education: 'Education Documents',
  activity: 'Activity Documents',
  testing: 'Testing Documents'
}

export function AllFilesReview({ userIdOverride }: { userIdOverride?: string }) {
  const { data: session, status } = useSession({ required: false })
  const [filesBySection, setFilesBySection] = useState<FilesBySection>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const userId = userIdOverride ?? ((session?.user as any)?.id as string | undefined)

  const fetchAllFiles = useCallback(async () => {
    if (!userId) {
      setError('Missing user id in session')
      setLoading(false)
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
      const res = await fetch(`${base}/api/upload/user/${userId}`)
      
      if (!res.ok) {
        throw new Error('Failed to fetch files')
      }
      
      const data = await res.json()
      const files = data.files || []
      
      // Group files by section
      const grouped: FilesBySection = {}
      files.forEach((file: UploadedFile) => {
        const section = file.section || 'other'
        if (!grouped[section]) {
          grouped[section] = []
        }
        grouped[section].push(file)
      })
      
      setFilesBySection(grouped)
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
    fetchAllFiles()
  }, [status, userId, fetchAllFiles])

  const handleDelete = async (s3Key: string, filename: string) => {
    if (!userId) return
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return
    
    setDeleting(s3Key)
    setError(null)
    
    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
      const res = await fetch(`${base}/api/upload/file?s3_key=${encodeURIComponent(s3Key)}&user_id=${userId}`, {
        method: 'DELETE',
      })
      
      if (!res.ok) {
        throw new Error('Failed to delete file')
      }
      
      await fetchAllFiles()
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

  const totalFiles = Object.values(filesBySection).reduce((sum, files) => sum + files.length, 0)

  if (status === 'loading' || loading) {
    return (
      <div className="space-y-4">
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight">All Uploaded Files</h2>
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
        <h2 className="text-2xl font-semibold tracking-tight">All Uploaded Files</h2>
        <p className="text-sm text-muted-foreground">
          Review and manage all your uploaded documents ({totalFiles} file{totalFiles !== 1 ? 's' : ''})
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {!error && totalFiles === 0 && (
        <div className="rounded-lg border border-dashed border-muted-foreground/40 p-12 text-center">
          <FolderOpen className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-medium mb-2">No files uploaded yet</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Start uploading your documents to get started
          </p>
          {!userIdOverride && (
            <Link href="/starter/profile/upload">
              <Button>
                <Upload className="mr-2 h-4 w-4" />
                Start Uploading
              </Button>
            </Link>
          )}
        </div>
      )}

      {totalFiles > 0 && (
        <div className="space-y-6">
          {Object.entries(filesBySection).map(([section, files]) => (
            <div key={section} className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">
                  {SECTION_LABELS[section] || section.charAt(0).toUpperCase() + section.slice(1)}
                </h3>
                <span className="text-sm text-muted-foreground">
                  {files.length} file{files.length !== 1 ? 's' : ''}
                </span>
              </div>
              
              <div className="rounded-lg border">
                <div className="divide-y">
                  {files.map((file, index) => (
                    <div key={index} className="p-4 flex items-center justify-between hover:bg-accent/50 transition-colors">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <FileText className="h-8 w-8 text-muted-foreground flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{file.filename}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatFileSize(file.size)} • {formatDate(file.last_modified)}
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
                          onClick={() => handleDelete(file.s3_key || '', file.filename)}
                          disabled={deleting === file.s3_key}
                          className="text-destructive hover:text-destructive"
                        >
                          {deleting === file.s3_key ? (
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
            </div>
          ))}

          <div className="flex gap-3 pt-4">
            <Link href="/starter/profile/upload" className="flex-1">
              <Button variant="outline" className="w-full">
                <Upload className="mr-2 h-4 w-4" />
                Upload More Files
              </Button>
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

