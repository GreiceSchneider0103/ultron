'use client'

import { useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { extractProductSpec, parseDocument } from '@/services/documents.service'
import { analyzeImages } from '@/services/images.service'

export function LibraryPage({ workspaceId }: { workspaceId: string }) {
  const [file, setFile] = useState<File | null>(null)
  const [documentId, setDocumentId] = useState('')
  const [imageUrl, setImageUrl] = useState('')

  const upload = useApiAction<Record<string, unknown>>()
  const extract = useApiAction<Record<string, unknown>>()
  const image = useApiAction<Record<string, unknown>>()

  async function onUpload() {
    if (!file) return
    const data = await upload.run(() => parseDocument(workspaceId, file))
    if (data?.document_id) setDocumentId(String(data.document_id))
  }

  async function onExtract() {
    if (!documentId) return
    await extract.run(() => extractProductSpec(workspaceId, documentId))
  }

  async function onImageAnalyze() {
    if (!imageUrl) return
    await image.run(() => analyzeImages(workspaceId, { image_urls: [imageUrl] }))
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Biblioteca (Docs & Imagens)</h1>

      <Card>
        <h2 className="text-xl font-semibold">Documentos</h2>
        <input type="file" accept=".pdf" className="mt-3" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" onClick={onUpload} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Upload PDF
          </button>
          <input
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
            className="rounded-md border border-border px-3 py-2 text-sm"
            placeholder="document_id"
          />
          <button type="button" onClick={onExtract} className="rounded-md border border-border px-3 py-2 text-sm">
            Extrair texto
          </button>
        </div>
        {upload.error ? <div className="mt-3"><ErrorState message={upload.error} /></div> : null}
        {extract.error ? <div className="mt-3"><ErrorState message={extract.error} /></div> : null}
      </Card>

      <Card>
        <h2 className="text-xl font-semibold">Imagens</h2>
        <input
          value={imageUrl}
          onChange={(e) => setImageUrl(e.target.value)}
          className="mt-3 w-full rounded-md border border-border px-3 py-2 text-sm"
          placeholder="URL da imagem"
        />
        <button type="button" onClick={onImageAnalyze} className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
          Analisar imagem
        </button>
        {image.error ? <div className="mt-3"><ErrorState message={image.error} /></div> : null}
      </Card>

      {upload.data ? <Card><h3 className="text-lg font-semibold">Upload</h3><div className="mt-3"><JsonView value={upload.data} /></div></Card> : null}
      {extract.data ? <Card><h3 className="text-lg font-semibold">Extract</h3><div className="mt-3"><JsonView value={extract.data} /></div></Card> : null}
      {image.data ? <Card><h3 className="text-lg font-semibold">Image analyze</h3><div className="mt-3"><JsonView value={image.data} /></div></Card> : null}
    </div>
  )
}
