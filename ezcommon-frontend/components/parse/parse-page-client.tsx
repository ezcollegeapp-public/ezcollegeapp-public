"use client"

import { useState } from 'react'
import { DocumentParser } from '@/components/parse/document-parser'
import FormFiller from '@/components/parse/form-filler'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { FileText, FormInput } from 'lucide-react'

interface ParsePageClientProps {
  userIdOverride?: string
}

export function ParsePageClient({ userIdOverride }: ParsePageClientProps) {
  const [activeTab, setActiveTab] = useState('parse')

  return (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold tracking-tight">Document Processing</h1>
          <p className="text-muted-foreground mt-2">
            Parse documents and automatically fill form fields
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="parse" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Document Parser
            </TabsTrigger>
            <TabsTrigger value="fill" className="flex items-center gap-2">
              <FormInput className="h-4 w-4" />
              Form Auto-Fill
            </TabsTrigger>
          </TabsList>

          <TabsContent value="parse">
            <DocumentParser userIdOverride={userIdOverride} />
          </TabsContent>

          <TabsContent value="fill">
            <FormFiller userIdOverride={userIdOverride} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

