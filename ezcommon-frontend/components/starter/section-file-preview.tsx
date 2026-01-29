"use client"
import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { Trash2, Upload, FileText, Loader2, Eye, Download } from 'lucide-react'

interface UploadedFile {
  filename: string
  size: number
  url?: string
  last_modified?: string
  section?: string
  s3_key?: string
}

interface SectionFilePreviewProps {
  section: 'profile' | 'education' | 'activity' | 'testing'
  title: string
  description: string
}

export function SectionFilePreview({ section, title, description }: SectionFilePreviewProps) {
  const { data: session } = useSession({ required: false })
  const userId = (session?.user as any)?.id

  const [files, setFiles] = useState<UploadedFile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<UploadedFile | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  const fetchFiles = useCallback(async () => {
    if (!userId) return
    
    setLoading(true)
    setError(null)
    
    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
      const res = await fetch(`${base}/api/upload/${section}?user_id=${userId}`)
      
      if (!res.ok) {
        throw new Error(`Failed to fetch files: ${res.statusText}`)
      }
      
      const data = await res.json()
      setFiles(data.files || [])
      
      // Auto-select first file for preview
      if (data.files && data.files.length > 0) {
        setSelectedFile(data.files[0])
        setPreviewUrl(data.files[0].url)
      }
    } catch (err: any) {
      console.error('Error fetching files:', err)
      setError(err.message || 'Failed to load files')
    } finally {
      setLoading(false)
    }
  }, [userId, section])

  useEffect(() => {
    fetchFiles()
  }, [fetchFiles])

  const handleDelete = async (file: UploadedFile) => {
    if (!userId || !file.s3_key) return
    
    if (!confirm(`Are you sure you want to delete "${file.filename}"?`)) {
      return
    }

    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
      const res = await fetch(
        `${base}/api/upload/file?s3_key=${encodeURIComponent(file.s3_key)}&user_id=${userId}`,
        { method: 'DELETE' }
      )

      if (!res.ok) {
        throw new Error('Failed to delete file')
      }

      // If deleted file was selected, clear preview
      if (selectedFile?.s3_key === file.s3_key) {
        setSelectedFile(null)
        setPreviewUrl(null)
      }

      await fetchFiles()
    } catch (err: any) {
      alert(err.message || 'Failed to delete file')
    }
  }

  const handleFileSelect = (file: UploadedFile) => {
    setSelectedFile(file)
    setPreviewUrl(file.url || null)
  }

  const getFileExtension = (filename: string) => {
    return filename.split('.').pop()?.toLowerCase() || ''
  }

  const isPreviewable = (filename: string) => {
    const ext = getFileExtension(filename)
    return ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'txt'].includes(ext)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  if (!userId) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Please log in to view files.</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        <p className="text-muted-foreground mt-2">{description}</p>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {!loading && !error && (
        <div className="grid gap-6 md:grid-cols-3">
          {/* File List */}
          <div className="md:col-span-1 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Files ({files.length})</h2>
              <Link href={`/starter/${section}/upload`}>
                <Button size="sm">
                  <Upload className="mr-2 h-4 w-4" />
                  Upload
                </Button>
              </Link>
            </div>

            {files.length === 0 ? (
              <div className="rounded-lg border border-dashed border-muted-foreground/40 p-6 text-center">
                <FileText className="mx-auto h-8 w-8 text-muted-foreground/50 mb-2" />
                <p className="text-sm text-muted-foreground mb-3">No files uploaded yet</p>
                <Link href={`/starter/${section}/upload`}>
                  <Button size="sm">
                    <Upload className="mr-2 h-4 w-4" />
                    Upload Files
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {files.map((file, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleFileSelect(file)}
                    className={`rounded-lg border p-3 cursor-pointer transition-colors hover:bg-accent ${
                      selectedFile?.s3_key === file.s3_key ? 'bg-accent border-primary' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{file.filename}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatFileSize(file.size)}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(file)
                        }}
                        className="h-8 w-8 p-0"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Preview Area */}
          <div className="md:col-span-2">
            <div className="rounded-lg border bg-card">
              <div className="border-b p-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold">Preview</h2>
                {selectedFile && (
                  <div className="flex gap-2">
                    {previewUrl && (
                      <a href={previewUrl} target="_blank" rel="noopener noreferrer">
                        <Button size="sm" variant="outline">
                          <Download className="mr-2 h-4 w-4" />
                          Download
                        </Button>
                      </a>
                    )}
                  </div>
                )}
              </div>
              
              <div className="p-4">
                {!selectedFile ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <Eye className="h-12 w-12 text-muted-foreground/50 mb-4" />
                    <p className="text-muted-foreground">Select a file to preview</p>
                  </div>
                ) : !isPreviewable(selectedFile.filename) ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
                    <p className="text-muted-foreground mb-2">Preview not available for this file type</p>
                    <p className="text-sm text-muted-foreground mb-4">{selectedFile.filename}</p>
                    {previewUrl && (
                      <a href={previewUrl} target="_blank" rel="noopener noreferrer">
                        <Button>
                          <Download className="mr-2 h-4 w-4" />
                          Download to View
                        </Button>
                      </a>
                    )}
                  </div>
                ) : previewUrl ? (
                  <div className="w-full">
                    {getFileExtension(selectedFile.filename) === 'pdf' ? (
                      <iframe
                        src={previewUrl}
                        className="w-full h-[600px] border-0 rounded"
                        title={selectedFile.filename}
                      />
                    ) : ['jpg', 'jpeg', 'png', 'gif'].includes(getFileExtension(selectedFile.filename)) ? (
                      <img
                        src={previewUrl}
                        alt={selectedFile.filename}
                        className="max-w-full h-auto rounded"
                      />
                    ) : (
                      <iframe
                        src={previewUrl}
                        className="w-full h-[600px] border-0 rounded"
                        title={selectedFile.filename}
                      />
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    <p className="text-sm text-muted-foreground mt-2">Loading preview...</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

