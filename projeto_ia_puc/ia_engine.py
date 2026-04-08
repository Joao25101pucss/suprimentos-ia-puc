import os
import requests
from dotenv import load_dotenv

# 1. Carrega as variáveis de ambiente (a chave secreta) do ficheiro invisível .env
load_dotenv()

# 2. Puxa a chave com segurança para a memória do Python
CHAVE_API = os.getenv("OPENROUTER_API_KEY")

def chamar_modelo(modelo, prompt):
    """
    Função que comunica com a API do OpenRouter para processar os prompts.
    """
    
    # Prevenção de erro caso o ficheiro .env não exista ou esteja vazio
    if not CHAVE_API:
        raise ValueError("ERRO: Chave da API não encontrada! Verifique se o ficheiro .env foi criado corretamente.")

    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Cabeçalhos de autorização com a chave oculta
    headers = {
        "Authorization": f"Bearer {CHAVE_API}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://meusistemaerp.com", # Opcional: OpenRouter pede um referer
        "X-Title": "ERP Logistico IA" # Opcional: Título do teu projeto
    }
    
    # Corpo do pedido a ser enviado para a IA
    data = {
        "model": modelo,
        "messages": [
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.1 # Temperatura baixa (0.1) para garantir que a IA é exata e não "inventa" dados na extração do JSON
    }
    
    try:
        # Envia o pedido para o servidor da IA
        response = requests.post(url, headers=headers, json=data)
        
        # Verifica se ocorreu algum erro de comunicação (ex: chave inválida, sem internet)
        response.raise_for_status() 
        
        # Converte a resposta em formato utilizável pelo Python e extrai o texto final
        resposta_json = response.json()
        texto_gerado = resposta_json['choices'][0]['message']['content']
        
        return texto_gerado
        
    except Exception as e:
        # Devolve o erro de forma clara para o Streamlit mostrar no ecrã caso algo falhe
        raise Exception(f"Erro na comunicação com a API da Inteligência Artificial: {str(e)}")