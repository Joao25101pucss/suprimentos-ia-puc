import json
import os
import requests
import base64
import PyPDF2
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (onde está sua chave API)
load_dotenv()

# Pegando a chave do OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def conversar_com_agente(historico_mensagens, contexto_banco_dados):
    """
    Conecta com a IA via OpenRouter para analisar o banco de dados SQL.
    """
    if not OPENROUTER_API_KEY:
        return "⚠️ Erro: A chave 'OPENROUTER_API_KEY' não foi encontrada no arquivo .env. Verifique suas configurações."

    # Prepara as mensagens. A primeira é a instrução de sistema (O cérebro + Dados)
    mensagens_api = [
        {"role": "system", "content": contexto_banco_dados}
    ]
    
    # Adiciona o histórico da conversa que veio do Streamlit
    for msg in historico_mensagens:
        mensagens_api.append({"role": msg["role"], "content": msg["content"]})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemini-2.0-flash-exp:free", # Você pode mudar o modelo padrão de chat aqui
        "messages": mensagens_api
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status() # Verifica se deu erro 400 ou 500
        dados = response.json()
        return dados['choices'][0]['message']['content']
    except Exception as e:
        return f"Desculpe, tive um erro de conexão ao consultar a base de dados: {str(e)}"

def extrair_texto_pdf(arquivo):
    """
    Lê um arquivo PDF carregado pelo Streamlit e extrai todo o texto.
    """
    try:
        pdf_reader = PyPDF2.PdfReader(arquivo)
        texto_completo = ""
        for pagina in pdf_reader.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido
        return texto_completo
    except Exception as e:
        print(f"Erro ao extrair PDF: {e}")
        return ""

def processar_nota(arquivo, modelo="google/gemini-2.0-flash-exp:free"):
    """
    Lê o PDF ou Imagem, envia para a IA e força o retorno em formato JSON estruturado.
    """
    if not OPENROUTER_API_KEY:
        st.error("Chave de API não configurada.")
        return None

    # O prompt que obriga a IA a formatar os dados exatamente como nosso banco SQL precisa
    prompt_extracao = """
    Você é um extrator de dados de Notas Fiscais.
    Analise os dados fornecidos e retorne APENAS um arquivo JSON válido, sem textos adicionais, com esta estrutura exata:
    {
        "CNPJ": "00.000.000/0000-00",
        "valor_total": 0.0,
        "itens": [
            {
                "produto": "Nome do Produto",
                "quantidade": 0,
                "preco_unitario": 0.0,
                "subtotal": 0.0
            }
        ]
    }
    """

    messages = []

    # Se for PDF, extraímos o texto via PyPDF2
    if arquivo.name.lower().endswith('.pdf'):
        texto_nf = extrair_texto_pdf(arquivo)
        messages = [
            {"role": "system", "content": prompt_extracao},
            {"role": "user", "content": f"Extraia os dados desta NF:\n\n{texto_nf}"}
        ]
    
    # Se for Imagem, codificamos em Base64 e usamos Visão Computacional
    elif arquivo.name.lower().endswith(('.png', '.jpg', '.jpeg')):
        base64_image = base64.b64encode(arquivo.read()).decode('utf-8')
        messages = [
            {"role": "system", "content": prompt_extracao},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extraia os dados desta imagem de Nota Fiscal:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
    else:
        return None

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": modelo,
        "messages": messages
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        
        resposta_texto = response.json()['choices'][0]['message']['content']

        # Limpeza para garantir que o Python consiga ler o JSON mesmo se a IA mandar markdown (```json ... ```)
        resposta_texto = resposta_texto.replace('```json', '').replace('```', '').strip()
        
        # Converte a string JSON para um Dicionário Python
        dados_json = json.loads(resposta_texto)
        return dados_json
        
    except json.JSONDecodeError:
        print("A IA não retornou um JSON válido.")
        return None
    except Exception as e:
        print(f"Erro na API de extração: {e}")
        return None