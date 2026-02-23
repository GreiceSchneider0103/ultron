import { createClient } from '@/utils/supabase/server';

export default async function Home() {
  const supabase = await createClient();

  // 1. Testamos a conexão com o banco
  // Substitua 'profiles' pelo nome de uma tabela que você criou no SQL
  const { data: testeBanco, error: erroBanco } = await supabase
    .from('profiles') 
    .select('*')
    .limit(1);

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>🚀 Ultron System Check</h1>
      <hr />
      
      <div style={{ marginTop: '20px' }}>
        <h3>Status da Conexão:</h3>
        {erroBanco ? (
          <p style={{ color: 'red' }}>❌ Erro ao acessar tabela: {erroBanco.message}</p>
        ) : (
          <p style={{ color: 'green' }}>✅ Banco de dados conectado e acessível!</p>
        )}
      </div>

      <div style={{ background: '#f4f4f4', padding: '15px', borderRadius: '8px' }}>
        <p><strong>Dica:</strong> Se aparecer erro de "PGRST116" ou "Relation not found", é porque o nome da tabela no código está diferente do nome que você criou no SQL.</p>
      </div>
    </div>
  );
}