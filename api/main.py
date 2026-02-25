import logging
import os
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from api.src.orchestrator.agent import MarketAgent
from api.src.connectors.mercado_livre import MercadoLivreConnector
from api.src.connectors.magalu import MagaluConnector

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ultron Market Intelligence API", version="1.0.0")

# Modelo de requisição
class AgentRequest(BaseModel):
    instruction: str

# Instância global do agente
agent: Optional[MarketAgent] = None

@app.on_event("startup")
async def startup_event():
    global agent
    
    # Inicializar conectores
    # O token é obtido via variável de ambiente ML_ACCESS_TOKEN dentro do conector
    ml_connector = MercadoLivreConnector()
    magalu_connector = MagaluConnector()
    
    connectors = {
        "mercado_livre": ml_connector,
        "magalu": magalu_connector
    }
    
    # Inicializar agente
    agent = MarketAgent(connectors=connectors)
    logger.info("Agente Ultron inicializado com sucesso.")

@app.post("/agent/run")
async def run_agent(request: AgentRequest) -> Dict[str, Any]:
    """
    Endpoint principal para interagir com o Agente.
    
    Envia uma instrução em linguagem natural (ex: "Analise o mercado de cadeiras gamer")
    e recebe o relatório processado com dados e insights.
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agente não inicializado")
    
    try:
        result = await agent.run(request.instruction)
        
        # Se houver erro crítico na resposta do agente, podemos tratar aqui
        if isinstance(result, dict) and result.get("error"):
            logger.warning(f"Erro reportado pelo agente: {result['error']}")
            
        return result
    except Exception as e:
        logger.error(f"Erro ao executar agente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "active", "agent_ready": agent is not None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)