'use client'

import { useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { extractProductSpec, parseDocument } from '@/services/documents.service'
import { analyzeImages } from '@/services/images.service'
import { suggestTitleVariants, validateTitle } from '@/services/seo.service'

export function GenerateAdPage({ workspaceId }: { workspaceId: string }) {
  const [step, setStep] = useState(1)
  const [file, setFile] = useState<File | null>(null)
  const [imageUrl, setImageUrl] = useState('')
  const [title, setTitle] = useState('Tenis de corrida amortecimento premium')
  const [documentId, setDocumentId] = useState('')

  const docAction = useApiAction<Record<string, unknown>>()
  const extractAction = useApiAction<Record<string, unknown>>()
  const imageAction = useApiAction<Record<string, unknown>>()
  const titlesAction = useApiAction<Record<string, unknown>>()
  const validateAction = useApiAction<Record<string, unknown>>()

  async function onUploadDocument() {
    if (!file) return
    const data = await docAction.run(() => parseDocument(workspaceId, file))
    if (data?.document_id) {
      setDocumentId(String(data.document_id))
    }
  }

  async function onExtractSpecs() {
    if (!documentId) return
    await extractAction.run(() => extractProductSpec(workspaceId, documentId))
  }

  async function onAnalyzeImage() {
    if (!imageUrl) return
    await imageAction.run(() => analyzeImages(workspaceId, { image_urls: [imageUrl] }))
  }

  async function onGenerateTitles() {
    await titlesAction.run(() =>
      suggestTitleVariants(workspaceId, { marketplace: 'mercadolivre', product_title: title, limit: 5 })
    )
  }

  async function onValidateTitle() {
    await validateAction.run(() =>
      validateTitle(workspaceId, { marketplace: 'mercadolivre', product_title: title, limit: 5 })
    )
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Gerar Anuncio do Zero</h1>

      <Card>
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3, 4].map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setStep(s)}
              className={`rounded-md px-3 py-2 text-sm ${step === s ? 'bg-primary text-white' : 'border border-border bg-white'}`}
            >
              Etapa {s}
            </button>
          ))}
        </div>
      </Card>

      {step === 1 && (
        <Card>
          <h2 className="text-xl font-semibold">1. Enviar documento</h2>
          <input
            type="file"
            accept=".pdf"
            className="mt-3"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <div className="mt-3 flex gap-2">
            <button type="button" onClick={onUploadDocument} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
              Enviar PDF
            </button>
            <button type="button" onClick={onExtractSpecs} className="rounded-md border border-border px-3 py-2 text-sm">
              Extrair especificacoes
            </button>
          </div>
          {docAction.error ? <ErrorState message={docAction.error} /> : null}
          {extractAction.error ? <ErrorState message={extractAction.error} /> : null}
          {docAction.data ? <div className="mt-3"><JsonView value={docAction.data} /></div> : null}
          {extractAction.data ? <div className="mt-3"><JsonView value={extractAction.data} /></div> : null}
        </Card>
      )}

      {step === 2 && (
        <Card>
          <h2 className="text-xl font-semibold">2. Analise de imagens</h2>
          <input
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            className="mt-3 w-full rounded-md border border-border px-3 py-2 text-sm"
            placeholder="https://..."
          />
          <button type="button" onClick={onAnalyzeImage} className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Analisar imagem
          </button>
          {imageAction.error ? <ErrorState message={imageAction.error} /> : null}
          {imageAction.data ? <div className="mt-3"><JsonView value={imageAction.data} /></div> : null}
        </Card>
      )}

      {step === 3 && (
        <Card>
          <h2 className="text-xl font-semibold">3. Gerar conteudo</h2>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-3 w-full rounded-md border border-border px-3 py-2 text-sm"
          />
          <button type="button" onClick={onGenerateTitles} className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Sugerir variacoes de titulo
          </button>
          {titlesAction.error ? <ErrorState message={titlesAction.error} /> : null}
          {titlesAction.data ? <div className="mt-3"><JsonView value={titlesAction.data} /></div> : null}
        </Card>
      )}

      {step === 4 && (
        <Card>
          <h2 className="text-xl font-semibold">4. Validar regras</h2>
          <button type="button" onClick={onValidateTitle} className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Validar titulo
          </button>
          {validateAction.error ? <ErrorState message={validateAction.error} /> : null}
          {validateAction.data ? <div className="mt-3"><JsonView value={validateAction.data} /></div> : null}
        </Card>
      )}
    </div>
  )
}
