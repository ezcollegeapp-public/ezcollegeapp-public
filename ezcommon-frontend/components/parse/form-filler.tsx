"use client"

import { useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Download, FileText, CheckCircle2, AlertCircle } from 'lucide-react'

interface S3File {
  filename: string
  section: string
  size: number
  last_modified: string
}

interface ExtractedChunk {
  category: string
  information: string
  source_file: string
  section: string
}

interface ParseResult {
  status: string
  total_chunks: number
  chunks: ExtractedChunk[]
  source_file: string
}

export default function DocumentProcessor({ userIdOverride }: { userIdOverride?: string }) {
  const { data: session } = useSession()
  const sessionUserId = (session?.user as any)?.id as string | undefined
  const userId = userIdOverride ?? sessionUserId

  const [selectedSection, setSelectedSection] = useState<string>('all')
  const [files, setFiles] = useState<S3File[]>([])
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [parseResult, setParseResult] = useState<ParseResult | null>(null)
  const [isLoadingFiles, setIsLoadingFiles] = useState(false)
  const [isParsing, setIsParsing] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string>('')

  // Load files from S3
  const loadFiles = useCallback(async () => {
    if (!userId) {
      setError('Please log in to load files')
      return
    }

    setIsLoadingFiles(true)
    setError('')

    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'
      const section = selectedSection === 'all' ? '' : `&section=${selectedSection}`

      const response = await fetch(`${base}/api/intelligent/files?user_id=${userId}${section}`)

      if (!response.ok) {
        throw new Error('Failed to load files')
      }

      const data = await response.json()
      setFiles(data.files || [])
      setSelectedFiles([])
      setParseResult(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files')
    } finally {
      setIsLoadingFiles(false)
    }
  }, [userId, selectedSection])

  // Toggle file selection
  const toggleFileSelection = useCallback((filename: string) => {
    setSelectedFiles(prev => {
      if (prev.includes(filename)) {
        return prev.filter(f => f !== filename)
      } else {
        return [...prev, filename]
      }
    })
  }, [])

  // Parse files with GPT to extract structured information
  const parseFiles = useCallback(async () => {
    if (!userId) {
      setError('Please log in to parse files')
      return
    }

    if (selectedFiles.length === 0) {
      setError('Please select at least one file to parse')
      return
    }

    setIsParsing(true)
    setError('')
    setParseResult(null)

    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'

      const response = await fetch(`${base}/api/intelligent/extract?user_id=${userId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          files: selectedFiles.map(filename => {
            const file = files.find(f => f.filename === filename)
            return {
              filename,
              section: file?.section || selectedSection
            }
          })
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to parse files')
      }

      const data = await response.json()
      setParseResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse files')
    } finally {
      setIsParsing(false)
    }
  }, [userId, selectedFiles, files, selectedSection])

  // Process CSV to OpenSearch
  const processToOpenSearch = useCallback(async () => {
    if (!userId) {
      setError('Please log in to process data')
      return
    }

    if (!parseResult || parseResult.chunks.length === 0) {
      setError('Please parse files first')
      return
    }

    setIsProcessing(true)
    setError('')

    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '/api/backend'

      const response = await fetch(`${base}/api/intelligent/store?user_id=${userId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          chunks: parseResult.chunks,
          source_file: parseResult.source_file
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to store data')
      }

      const data = await response.json()
      alert(`✅ Successfully stored ${data.stored_chunks} chunks to OpenSearch!`)

      // Clear results after successful storage
      setParseResult(null)
      setSelectedFiles([])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to store data')
    } finally {
      setIsProcessing(false)
    }
  }, [userId, parseResult])

  // Download CSV
  const downloadCSV = useCallback(() => {
    if (!parseResult || parseResult.chunks.length === 0) return

    // Create CSV content
    const headers = ['Category', 'Information', 'Source File', 'Section']
    const rows = parseResult.chunks.map(chunk => [
      chunk.category,
      chunk.information,
      chunk.source_file,
      chunk.section
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(','))
    ].join('\n')

    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    const filename = `extracted_${parseResult.source_file.replace(/\.[^/.]+$/, '')}_${new Date().toISOString().split('T')[0]}.csv`
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }, [parseResult])

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            智能文档提取器
          </CardTitle>
          <CardDescription>
            使用 GPT 智能提取文档中的结构化信息（成绩、论文、获奖等）
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Section Filter */}
          <div className="flex items-center gap-4">
            <Label htmlFor="section-filter" className="min-w-[120px]">
              文档分区:
            </Label>
            <Select value={selectedSection} onValueChange={setSelectedSection}>
              <SelectTrigger id="section-filter" className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">所有分区</SelectItem>
                <SelectItem value="education">Education</SelectItem>
                <SelectItem value="activity">Activity</SelectItem>
                <SelectItem value="testing">Testing</SelectItem>
                <SelectItem value="profile">Profile</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={loadFiles}
              disabled={isLoadingFiles || !userId}
              variant="outline"
            >
              {isLoadingFiles ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  加载中...
                </>
              ) : (
                '加载文件'
              )}
            </Button>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="space-y-2">
              <Label>选择要提取的文件 ({selectedFiles.length}/{files.length})</Label>
              <div className="max-h-[300px] overflow-y-auto border rounded-lg p-3 bg-muted/30">
                <div className="space-y-2">
                  {files.map((file) => (
                    <div
                      key={file.filename}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedFiles.includes(file.filename)
                          ? 'bg-blue-50 dark:bg-blue-950 border-blue-300 dark:border-blue-700'
                          : 'hover:bg-muted'
                      }`}
                      onClick={() => toggleFileSelection(file.filename)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={selectedFiles.includes(file.filename)}
                            onChange={() => {}}
                            className="h-4 w-4"
                          />
                          <FileText className="h-4 w-4" />
                          <span className="text-sm font-medium">{file.filename}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {file.section}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {(file.size / 1024).toFixed(1)} KB
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Parse Button */}
          {selectedFiles.length > 0 && (
            <div className="flex gap-2">
              <Button
                onClick={parseFiles}
                disabled={isParsing || !userId}
                className="flex-1"
                size="lg"
              >
                {isParsing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    使用 GPT 提取中...
                  </>
                ) : (
                  <>
                    <FileText className="mr-2 h-4 w-4" />
                    Parse - 提取文件内容
                  </>
                )}
              </Button>
            </div>
          )}

          {/* Error */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Parse Results - CSV Preview */}
      {parseResult && parseResult.chunks.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>提取结果预览</CardTitle>
                <CardDescription>
                  从 {parseResult.source_file} 中提取了 {parseResult.total_chunks} 条结构化信息
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button onClick={downloadCSV} variant="outline" size="sm">
                  <Download className="h-4 w-4 mr-2" />
                  下载 CSV
                </Button>
                <Button
                  onClick={processToOpenSearch}
                  disabled={isProcessing}
                  size="sm"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      存储中...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                      Process - 存储到 OpenSearch
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="border rounded-lg overflow-hidden">
              <div className="max-h-[500px] overflow-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted sticky top-0">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium">#</th>
                      <th className="px-4 py-2 text-left font-medium">类别</th>
                      <th className="px-4 py-2 text-left font-medium">信息内容</th>
                      <th className="px-4 py-2 text-left font-medium">来源文件</th>
                      <th className="px-4 py-2 text-left font-medium">分区</th>
                    </tr>
                  </thead>
                  <tbody>
                    {parseResult.chunks.map((chunk, index) => (
                      <tr key={index} className="border-t hover:bg-muted/50">
                        <td className="px-4 py-2 text-muted-foreground">{index + 1}</td>
                        <td className="px-4 py-2">
                          <Badge variant="secondary" className="text-xs">
                            {chunk.category}
                          </Badge>
                        </td>
                        <td className="px-4 py-2 max-w-md">
                          <div className="line-clamp-2" title={chunk.information}>
                            {chunk.information}
                          </div>
                        </td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">
                          {chunk.source_file}
                        </td>
                        <td className="px-4 py-2">
                          <Badge variant="outline" className="text-xs">
                            {chunk.section}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

