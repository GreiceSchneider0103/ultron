'use client'

import { useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { extractProductSpec, parseDocument } from '@/services/documents.service'
import { analyzeImages } from '@/services/images.service'
import { suggestTitleVariants, validateTitle } from '@/services/seo.service'
import { RetryButton } from '@/components/ui/retry-button'

export function GenerateAdPage({ workspaceId }: { workspaceId: string }) {
  const [step, setStep] = useState(1)
  const [file, setFile] = useState<File | null>(null)
  const [imageUrl, setImageUrl] = useState('')
  const [title, setTitle] = useState('Nike Air Max 270 Masculino')
  const [documentId, setDocumentId] = useState('')
  const [sku, setSku] = useState('NK-AM270-P42')
  const [productName, setProductName] = useState('Nike Air Max 270 Masculino')
  const [category, setCategory] = useState('Tenis Esportivos')
  const [brand, setBrand] = useState('Nike')
  const [color, setColor] = useState('Preto')
  const [material, setMaterial] = useState('Mesh respiravel + EVA')
  const [benefits, setBenefits] = useState('Amortecimento Air Max 270, cabedal respiravel, conforto para corrida e academia')
  const [warranty, setWarranty] = useState('12 meses contra defeitos de fabricacao')
  const [tone, setTone] = useState<'tecnico' | 'persuasivo' | 'neutro'>('tecnico')
  const [marketplaceMode, setMarketplaceMode] = useState<'mercadolivre' | 'magalu'>('mercadolivre')

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
      <p className="text-sm text-slate-500">Criacao completa com IA - do produto ao anuncio publicavel</p>

      <Card>
        <div className="grid gap-2 sm:grid-cols-6">
          {[
            'Dados do produto',
            'Upload de arquivos',
            'Regras do marketplace',
            'Gerar conteudo',
            'Midia',
            'Exportacao',
          ].map((label, idx) => (
            <button
              key={label}
              type="button"
              onClick={() => setStep(idx + 1)}
              className={`rounded-md px-3 py-2 text-sm ${
                step === idx + 1 ? 'bg-primary text-white' : 'border border-border bg-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[2fr_1fr]">
        <div className="space-y-4">
          {step === 1 && (
            <Card>
              <h2 className="text-xl font-semibold">Dados do produto</h2>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <input value={sku} onChange={(e) => setSku(e.target.value)} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="SKU" />
                <input
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  className="rounded-md border border-border px-3 py-2 text-sm"
                  placeholder="Nome do produto"
                />
                <select value={category} onChange={(e) => setCategory(e.target.value)} className="rounded-md border border-border px-3 py-2 text-sm">
                  <option>Tenis Esportivos</option>
                  <option>Eletronicos</option>
                  <option>Casa e Decoracao</option>
                </select>
                <input value={brand} onChange={(e) => setBrand(e.target.value)} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Marca" />
                <input value={color} onChange={(e) => setColor(e.target.value)} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Cor" />
                <input value={material} onChange={(e) => setMaterial(e.target.value)} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Material" />
              </div>
              <textarea value={benefits} onChange={(e) => setBenefits(e.target.value)} className="mt-3 w-full rounded-md border border-border px-3 py-2 text-sm" rows={3} />
              <input value={warranty} onChange={(e) => setWarranty(e.target.value)} className="mt-3 w-full rounded-md border border-border px-3 py-2 text-sm" placeholder="Garantia" />
            </Card>
          )}

          {step === 2 && (
            <Card>
              <h2 className="text-xl font-semibold">Upload de arquivos</h2>
              <input type="file" accept=".pdf" className="mt-3" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              <div className="mt-3 flex gap-2">
                <button type="button" onClick={onUploadDocument} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
                  Enviar PDF
                </button>
                <button type="button" onClick={onExtractSpecs} className="rounded-md border border-border px-3 py-2 text-sm">
                  Extrair ficha
                </button>
              </div>
              {docAction.error ? (
                <div className="mt-3 space-y-2">
                  <ErrorState message={docAction.error} />
                  <RetryButton onRetry={onUploadDocument} loading={docAction.loading} />
                </div>
              ) : null}
              {extractAction.error ? (
                <div className="mt-3 space-y-2">
                  <ErrorState message={extractAction.error} />
                  <RetryButton onRetry={onExtractSpecs} loading={extractAction.loading} />
                </div>
              ) : null}
              {docAction.data ? <div className="mt-3"><JsonView value={docAction.data} /></div> : null}
              {extractAction.data ? <div className="mt-3"><JsonView value={extractAction.data} /></div> : null}
            </Card>
          )}

          {step === 3 && (
            <Card>
              <h2 className="text-xl font-semibold">Regras do marketplace</h2>
              <p className="text-sm text-slate-600">Validacao de titulo, atributos obrigatorios e limite de fotos.</p>
              <button
                type="button"
                onClick={onValidateTitle}
                className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"
              >
                Validar regras
              </button>
              {validateAction.error ? (
                <div className="mt-3 space-y-2">
                  <ErrorState message={validateAction.error} />
                  <RetryButton onRetry={onValidateTitle} loading={validateAction.loading} />
                </div>
              ) : null}
              {validateAction.data ? <div className="mt-3"><JsonView value={validateAction.data} /></div> : null}
            </Card>
          )}

          {step === 4 && (
            <Card>
              <h2 className="text-xl font-semibold">Gerar conteudo</h2>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-3 w-full rounded-md border border-border px-3 py-2 text-sm"
                placeholder="Titulo base"
              />
              <button type="button" onClick={onGenerateTitles} className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
                Sugerir variacoes de titulo
              </button>
              {titlesAction.error ? (
                <div className="mt-3 space-y-2">
                  <ErrorState message={titlesAction.error} />
                  <RetryButton onRetry={onGenerateTitles} loading={titlesAction.loading} />
                </div>
              ) : null}
              {titlesAction.data ? <div className="mt-3"><JsonView value={titlesAction.data} /></div> : null}
            </Card>
          )}

          {step === 5 && (
            <Card>
              <h2 className="text-xl font-semibold">Midia</h2>
              <input
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                className="mt-3 w-full rounded-md border border-border px-3 py-2 text-sm"
                placeholder="URL da imagem"
              />
              <button type="button" onClick={onAnalyzeImage} className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
                Analisar imagem
              </button>
              {imageAction.error ? (
                <div className="mt-3 space-y-2">
                  <ErrorState message={imageAction.error} />
                  <RetryButton onRetry={onAnalyzeImage} loading={imageAction.loading} />
                </div>
              ) : null}
              {imageAction.data ? <div className="mt-3"><JsonView value={imageAction.data} /></div> : null}
            </Card>
          )}

          {step === 6 && (
            <Card>
              <h2 className="text-xl font-semibold">Exportacao</h2>
              <p className="text-sm text-slate-600">Opcoes de saida do anuncio gerado.</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <button type="button" className="rounded-md border border-border px-3 py-2 text-sm">Exportar PDF</button>
                <button type="button" className="rounded-md border border-border px-3 py-2 text-sm">Exportar HTML</button>
                <button type="button" className="rounded-md border border-border px-3 py-2 text-sm">Enviar planilha</button>
              </div>
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <Card>
            <h3 className="text-lg font-semibold">Progresso</h3>
            <ol className="mt-3 space-y-2 text-sm text-slate-600">
              {[
                'Dados do produto',
                'Upload de arquivos',
                'Regras do marketplace',
                'Gerar conteudo',
                'Midia',
                'Exportacao',
              ].map((item, idx) => (
                <li key={item} className={step === idx + 1 ? 'font-semibold text-primary' : ''}>
                  {idx + 1}. {item}
                </li>
              ))}
            </ol>
          </Card>

          <Card>
            <h3 className="text-lg font-semibold">Marketplace</h3>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setMarketplaceMode('mercadolivre')}
                className={`rounded-md border px-3 py-2 text-sm ${marketplaceMode === 'mercadolivre' ? 'border-yellow-400 bg-yellow-100' : 'border-border bg-white'}`}
              >
                ML
              </button>
              <button
                type="button"
                onClick={() => setMarketplaceMode('magalu')}
                className={`rounded-md border px-3 py-2 text-sm ${marketplaceMode === 'magalu' ? 'border-blue-400 bg-blue-100' : 'border-border bg-white'}`}
              >
                Magalu
              </button>
            </div>
          </Card>

          <Card>
            <h3 className="text-lg font-semibold">Tom de voz</h3>
            <div className="mt-3 space-y-2 text-sm">
              {[
                ['tecnico', 'Tecnico'],
                ['persuasivo', 'Persuasivo'],
                ['neutro', 'Neutro'],
              ].map(([value, label]) => (
                <label key={value} className="flex items-center gap-2">
                  <input type="radio" checked={tone === value} onChange={() => setTone(value as 'tecnico' | 'persuasivo' | 'neutro')} />
                  {label}
                </label>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
