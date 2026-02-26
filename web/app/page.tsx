import { createClient } from '@/utils/supabase/server'

export default async function Home() {
  const supabase = await createClient()

  const { error: erroBanco } = await supabase
    .from('marketplace_rulesets')
    .select('id')
    .limit(1)

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Ultron System Check</h1>
      <hr />

      <div style={{ marginTop: '20px' }}>
        <h3>Status da Conexao:</h3>
        {erroBanco ? (
          <p style={{ color: 'red' }}>Erro ao acessar tabela: {erroBanco.message}</p>
        ) : (
          <p style={{ color: 'green' }}>Banco de dados conectado e acessivel.</p>
        )}
      </div>

      <div style={{ background: '#f4f4f4', padding: '15px', borderRadius: '8px' }}>
        <p>
          <strong>Dica:</strong> Este check usa a tabela &quot;marketplace_rulesets&quot; do schema V5.
          Se aparecer &quot;relation not found&quot;, aplique o SQL do schema atualizado.
        </p>
      </div>
    </div>
  )
}
