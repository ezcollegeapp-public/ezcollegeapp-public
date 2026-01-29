"use client"
import { useState, useCallback, useRef, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Upload,
  FileText,
  Image as ImageIcon,
  CheckCircle2,
  XCircle,
  Loader2,
  Download,
  Trash2,
  FolderOpen,
  AlertCircle,
  RefreshCw,
  Eye
} from 'lucide-react'

interface S3FileInfo {
  key: string
  filename: string
  section: string
  file_type: string
  size: number
  last_modified: string
  url: string
}

interface FileItem {
  s3_file?: S3FileInfo
  status: 'pending' | 'processing' | 'success' | 'error'
  progress: number
  progressMessage?: string
  result?: ParseResult
  error?: string
}

interface ParseResult {
  status: string
  document_id: string
  source_file: string
  s3_key: string
  section: string
  file_type: string
  chunks_created: number
  chunks: Array<{
    text: string
    category: string
    chunk_type: string
  }>
  processor_used: string
  opensearch_stored: boolean
}

interface ProcessingReport {
  total_files: number
  successful: number
  failed: number
  total_chunks: number
  processing_time: string
  files: Array<{
    filename: string
    status: 'success' | 'error'
    chunks?: number
    error?: string
  }>
}

export function DocumentParser({ userIdOverride }: { userIdOverride?: string }) {
  const { data: session } = useSession()
  const [s3Files, setS3Files] = useState<S3FileInfo[]>([])
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())
  const [files, setFiles] = useState<FileItem[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [isLoadingFiles, setIsLoadingFiles] = useState(false)
  const [report, setReport] = useState<ProcessingReport | null>(null)
  const [selectedSection, setSelectedSection] = useState<string>('all')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const userIdFromSession = (session?.user as any)?.id as string | undefined
  const userId = userIdOverride ?? userIdFromSession

  // Load user's uploaded files from S3
  const loadS3Files = useCallback(async () => {
    if (!userId) {
      console.log('No userId available, user not logged in')
      alert('Please login first to load files')
      return
    }

    setIsLoadingFiles(true)
    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
      const section = selectedSection === 'all' ? '' : selectedSection

      const url = `${base}/api/parse/files?user_id=${userId}${section ? `&section=${section}` : ''}`
      console.log('Fetching files from:', url)

      const response = await fetch(url)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('API error:', response.status, errorText)
        throw new Error(`Failed to load files: ${response.status} ${errorText}`)
      }

      const data: S3FileInfo[] = await response.json()
      console.log('Loaded files:', data.length)
      setS3Files(data)
    } catch (error: any) {
      console.error('Error loading files:', error)
      alert(`Failed to load files: ${error.message}`)
    } finally {
      setIsLoadingFiles(false)
    }
  }, [userId, selectedSection])

  // Load files on mount and when section changes
  useEffect(() => {
    loadS3Files()
  }, [loadS3Files])



  const toggleFileSelection = useCallback((key: string) => {
    setSelectedFiles(prev => {
      const newSet = new Set(prev)
      if (newSet.has(key)) {
        newSet.delete(key)
      } else {
        newSet.add(key)
      }
      return newSet
    })
  }, [])

  const selectAll = useCallback(() => {
    setSelectedFiles(new Set(s3Files.map(f => f.key)))
  }, [s3Files])

  const deselectAll = useCallback(() => {
    setSelectedFiles(new Set())
  }, [])

  const processSelectedFiles = useCallback(async () => {
    if (!userId) {
      alert('Please login first')
      return
    }

    if (selectedFiles.size === 0) {
      alert('Please select files to process')
      return
    }

    setIsProcessing(true)
    const startTime = Date.now()
    const results: ProcessingReport['files'] = []

    // Convert selected files to FileItem array
    const filesToProcess = s3Files.filter(f => selectedFiles.has(f.key))
    const fileItems: FileItem[] = filesToProcess.map(f => ({
      s3_file: f,
      status: 'pending' as const,
      progress: 0
    }))
    setFiles(fileItems)

    for (let i = 0; i < filesToProcess.length; i++) {
      const s3File = filesToProcess[i]

      // Update status to processing
      setFiles(prev => prev.map((f, idx) =>
        idx === i ? { ...f, status: 'processing' as const, progress: 0 } : f
      ))

      try {
        const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
        const currentUserId = userId

        // Use Server-Sent Events for real-time progress
        const eventSource = new EventSource(
          `${base}/api/parse/file/stream?s3_key=${encodeURIComponent(s3File.key)}&user_id=${currentUserId}`
        )

        let parseResult: ParseResult | null = null

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)

            if (data.error) {
              // Handle error
              eventSource.close()
              setFiles(prev => prev.map((f, idx) =>
                idx === i
                  ? { ...f, status: 'error', error: data.error }
                  : f
              ))
              return
            }

            if (data.result) {
              // Processing complete
              parseResult = data.result
              eventSource.close()
            } else if (data.progress !== undefined) {
              // Update progress
              setFiles(prev => prev.map((f, idx) =>
                idx === i
                  ? {
                      ...f,
                      progress: data.progress,
                      progressMessage: data.message
                    }
                  : f
              ))
            }
          } catch (err) {
            console.error('Error parsing SSE data:', err)
          }
        }

        eventSource.onerror = (error) => {
          console.error('SSE error:', error)
          eventSource.close()

          if (!parseResult) {
            setFiles(prev => prev.map((f, idx) =>
              idx === i
                ? { ...f, status: 'error', error: 'Connection lost during processing' }
                : f
            ))
          }
        }

        // Wait for completion
        await new Promise<void>((resolve) => {
          const checkInterval = setInterval(() => {
            if (eventSource.readyState === EventSource.CLOSED) {
              clearInterval(checkInterval)
              resolve()
            }
          }, 100)
        })

        if (!parseResult) {
          throw new Error('Processing failed - no result received')
        }

        // Update status to success (parseResult is guaranteed to be non-null here)
        const finalResult: ParseResult = parseResult

        setFiles(prev => prev.map((f, idx) =>
          idx === i ? {
            ...f,
            status: 'success' as const,
            progress: 100,
            result: finalResult
          } : f
        ))

        results.push({
          filename: s3File.filename,
          status: 'success',
          chunks: finalResult.chunks_created
        })

      } catch (error: any) {
        // Update status to error
        setFiles(prev => prev.map((f, idx) =>
          idx === i ? {
            ...f,
            status: 'error' as const,
            progress: 0,
            error: error.message
          } : f
        ))

        results.push({
          filename: s3File.filename,
          status: 'error',
          error: error.message
        })
      }
    }

    const endTime = Date.now()
    const processingTime = ((endTime - startTime) / 1000).toFixed(2) + 's'

    // Generate report
    const successful = results.filter(r => r.status === 'success').length
    const failed = results.filter(r => r.status === 'error').length
    const totalChunks = results
      .filter(r => r.status === 'success')
      .reduce((sum, r) => sum + (r.chunks || 0), 0)

    setReport({
      total_files: filesToProcess.length,
      successful,
      failed,
      total_chunks: totalChunks,
      processing_time: processingTime,
      files: results
    })

    setIsProcessing(false)
  }, [selectedFiles, s3Files, userId])

  const downloadReport = useCallback(() => {
    if (!report) return

    const reportText = `
DOCUMENT PARSING REPORT
${'='.repeat(50)}
Generated: ${new Date().toLocaleString()}
Processing Time: ${report.processing_time}

SUMMARY:
  Total Files: ${report.total_files}
  Successfully Processed: ${report.successful}
  Failed: ${report.failed}
  Total Chunks Created: ${report.total_chunks}

SUCCESSFULLY PROCESSED FILES:
${'-'.repeat(40)}
${report.files
  .filter(f => f.status === 'success')
  .map(f => `  ${f.filename}: ${f.chunks} chunks`)
  .join('\n')}

${report.files.filter(f => f.status === 'error').length > 0 ? `
FAILED FILES:
${'-'.repeat(40)}
${report.files
  .filter(f => f.status === 'error')
  .map(f => `  ${f.filename}: ${f.error}`)
  .join('\n')}
` : ''}
${'='.repeat(50)}
    `.trim()

    const blob = new Blob([reportText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `parse_report_${new Date().toISOString().replace(/[:.]/g, '-')}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [report])

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    if (ext === 'pdf') return <FileText className="h-5 w-5 text-red-500" />
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext || '')) {
      return <ImageIcon className="h-5 w-5 text-blue-500" />
    }
    return <FileText className="h-5 w-5 text-gray-500" />
  }

  const getStatusIcon = (status: FileItem['status']) => {
    switch (status) {
      case 'pending':
        return <AlertCircle className="h-5 w-5 text-gray-400" />
      case 'processing':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
      case 'success':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Section Filter and Actions */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FolderOpen className="h-5 w-5" />
                Your Uploaded Files
              </CardTitle>
              <CardDescription>
                Select files from your uploads to parse and extract information
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadS3Files}
              disabled={isLoadingFiles}
            >
              {isLoadingFiles ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Section Filter */}
          <div className="flex gap-2 mb-4">
            {['all', 'education', 'activity', 'testing', 'profile'].map((section) => (
              <Button
                key={section}
                variant={selectedSection === section ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedSection(section)}
              >
                {section.charAt(0).toUpperCase() + section.slice(1)}
              </Button>
            ))}
          </div>

          {/* File List */}
          {isLoadingFiles ? (
            <div className="text-center py-8">
              <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />
              <p className="text-muted-foreground">Loading files...</p>
            </div>
          ) : s3Files.length === 0 ? (
            <div className="text-center py-8 border-2 border-dashed rounded-lg">
              <FolderOpen className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
              <p className="text-muted-foreground">No files found</p>
              <p className="text-sm text-muted-foreground mt-1">
                Upload files in Education, Activity, Testing, or Profile sections first
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm text-muted-foreground">
                  {s3Files.length} file(s) found, {selectedFiles.size} selected
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={selectAll}>
                    Select All
                  </Button>
                  <Button variant="outline" size="sm" onClick={deselectAll}>
                    Deselect All
                  </Button>
                  <Button
                    onClick={processSelectedFiles}
                    disabled={isProcessing || selectedFiles.size === 0}
                    size="sm"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Upload className="h-4 w-4 mr-2" />
                        Parse Selected ({selectedFiles.size})
                      </>
                    )}
                  </Button>
                </div>
              </div>

              <div className="space-y-2 max-h-96 overflow-y-auto">
                {s3Files.map((file) => (
                  <div
                    key={file.key}
                    className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedFiles.has(file.key) ? 'bg-primary/10 border-primary' : 'hover:bg-gray-50'
                    }`}
                    onClick={() => toggleFileSelection(file.key)}
                  >
                    <input
                      type="checkbox"
                      checked={selectedFiles.has(file.key)}
                      onChange={() => {}}
                      className="h-4 w-4"
                    />
                    {getFileIcon(file.filename)}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{file.filename}</p>
                      <p className="text-sm text-muted-foreground">
                        {file.section} • {(file.size / 1024).toFixed(2)} KB
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        window.open(file.url, '_blank')
                      }}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Processing Results */}
      {files.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Processing Results</CardTitle>
            <CardDescription>
              Detailed extraction results for each document
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {files.map((fileItem, index) => (
                <div key={index} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {fileItem.s3_file && getFileIcon(fileItem.s3_file.filename)}
                      <span className="font-medium">
                        {fileItem.s3_file?.filename || 'Unknown file'}
                      </span>
                    </div>
                    {getStatusIcon(fileItem.status)}
                  </div>

                  {fileItem.status === 'processing' && (
                    <div className="mt-2 space-y-2">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-primary h-2 rounded-full transition-all duration-300"
                          style={{ width: `${fileItem.progress}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">
                          {fileItem.progressMessage || 'Processing...'}
                        </span>
                        <span className="font-medium text-primary">
                          {fileItem.progress}%
                        </span>
                      </div>
                    </div>
                  )}

                  {fileItem.status === 'success' && fileItem.result && (
                    <div className="mt-3 space-y-3">
                      {/* Summary */}
                      <div className="p-3 bg-green-50 rounded border border-green-200">
                        <p className="text-sm font-medium text-green-800 mb-2">
                          ✓ Successfully parsed
                        </p>
                        <div className="grid grid-cols-2 gap-2 text-xs text-green-700">
                          <div>
                            <span className="font-medium">Document ID:</span>
                            <p className="truncate">{fileItem.result.document_id}</p>
                          </div>
                          <div>
                            <span className="font-medium">Section:</span>
                            <p>{fileItem.result.section}</p>
                          </div>
                          <div>
                            <span className="font-medium">File Type:</span>
                            <p>{fileItem.result.file_type}</p>
                          </div>
                          <div>
                            <span className="font-medium">Chunks:</span>
                            <p>{fileItem.result.chunks_created}</p>
                          </div>
                          <div>
                            <span className="font-medium">Processor:</span>
                            <p>{fileItem.result.processor_used}</p>
                          </div>
                          <div>
                            <span className="font-medium">Stored:</span>
                            <p>{fileItem.result.opensearch_stored ? 'Yes' : 'No'}</p>
                          </div>
                        </div>
                      </div>

                      {/* Extracted Chunks */}
                      {fileItem.result.chunks && fileItem.result.chunks.length > 0 && (
                        <div className="border rounded-lg p-3 bg-gray-50">
                          <p className="font-medium text-sm mb-3">
                            Extracted Information ({fileItem.result.chunks.length} chunks):
                          </p>
                          <div className="space-y-2 max-h-96 overflow-y-auto">
                            {fileItem.result.chunks.map((chunk, idx) => (
                              <div
                                key={idx}
                                className="p-3 bg-white rounded border-l-4 border-blue-500"
                              >
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-xs font-semibold text-blue-600 bg-blue-100 px-2 py-1 rounded">
                                    {chunk.category}
                                  </span>
                                  <span className="text-xs text-gray-500">
                                    {chunk.chunk_type}
                                  </span>
                                </div>
                                <p className="text-sm text-gray-700 whitespace-pre-wrap">
                                  {chunk.text}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {fileItem.status === 'error' && (
                    <div className="mt-2 p-3 bg-red-50 rounded border border-red-200">
                      <p className="text-sm font-medium text-red-800 mb-1">
                        ✗ Processing Error
                      </p>
                      <p className="text-xs text-red-700">
                        {fileItem.error}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Report */}
      {report && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Processing Report</CardTitle>
              <Button variant="outline" size="sm" onClick={downloadReport}>
                <Download className="h-4 w-4 mr-2" />
                Download Report
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="text-center p-4 border rounded-lg">
                <p className="text-2xl font-bold">{report.total_files}</p>
                <p className="text-sm text-muted-foreground">Total Files</p>
              </div>
              <div className="text-center p-4 border rounded-lg bg-green-50">
                <p className="text-2xl font-bold text-green-600">{report.successful}</p>
                <p className="text-sm text-muted-foreground">Successful</p>
              </div>
              <div className="text-center p-4 border rounded-lg bg-red-50">
                <p className="text-2xl font-bold text-red-600">{report.failed}</p>
                <p className="text-sm text-muted-foreground">Failed</p>
              </div>
              <div className="text-center p-4 border rounded-lg bg-blue-50">
                <p className="text-2xl font-bold text-blue-600">{report.total_chunks}</p>
                <p className="text-sm text-muted-foreground">Total Chunks</p>
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              Processing Time: {report.processing_time}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

