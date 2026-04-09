import os
import json
import base64
import requests
import streamlit as st
import PyPDF2
from dotenv import load_dotenv

# Carrega as variáveis do ficheiro .env
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions".strip()

def processar_nota(arquivo, modelo="nvidia/nemotron-3-nano-30b-a3b:free"):
    """
    Processa faturas em formato PDF (extração de texto) ou Imagem (visão),
    devolvendo os dados estruturados em JSON para o compliance.
    """
    if not OPENROUTER_API_KEY:
        st.error("⚠️ Chave do OpenRouter não encontrada! Verifique o seu ficheiro .env.")
        return None

    try:
        prompt = """
        Você é um auditor fiscal automatizado. Analise os dados da Nota Fiscal fornecidos e extraia as informações, 
        retornando ESTRITAMENTE um formato JSON com a estrutura abaixo. 
        Não invente dados. Se não achar algo, coloque 0 ou "".
        
        {
            "Fornecedor": "Nome/Razão Social da empresa",
            "CNPJ": "CNPJ",
            "Data": "Data de emissão (Formato YYYY-MM-DD)",
            "itens": [
                {
                    "produto": "Descrição do produto",
                    "quantidade": numero (use ponto para decimais),
                    "preco_unitario": numero,
                    "subtotal": numero
                }
            ],
            "valor_total": numero
        }
        
        ATENÇÃO: Retorne APENAS o JSON puro. Não inclua textos como ```json ou explicações.
        """

        conteudo_mensagem = []

        # ==========================================
        # SE FOR PDF: LER TEXTO COM PYPDF2
        # ==========================================
        if arquivo.type == "application/pdf":
            leitor_pdf = PyPDF2.PdfReader(arquivo)
            texto_extraido = ""
            for pagina in leitor_pdf.pages:
                texto_extraido += pagina.extract_text() + "\n"
            
            texto_final = prompt + "\n\n--- TEXTO EXTRAÍDO DA NOTA FISCAL ---\n" + texto_extraido
            
            conteudo_mensagem = [
                {"type": "text", "text": texto_final}
            ]
            
        # ==========================================
        # SE FOR IMAGEM: ENVIAR PARA MODELO DE VISÃO
        # ==========================================
        else:
            file_bytes = arquivo.getvalue()
            base64_image = base64.b64encode(file_bytes).decode('utf-8')
            
            conteudo_mensagem = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{arquivo.type};base64,{base64_image}"}
                }
            ]

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY.strip()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": modelo,
            "messages": [{"role": "user", "content": conteudo_mensagem}]
        }
        
        response = requests.post(url=API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            st.error(f"Erro de comunicação: {response.text}")
            return None
            
        resposta_texto = response.json()['choices'][0]['message']['content']
        texto_limpo = resposta_texto.strip().removeprefix('```json').removesuffix('```').strip()
        
        return json.loads(texto_limpo)
        
    except Exception as e:
        st.error(f"Erro interno no processamento da nota: {e}")
        return None


def conversar_com_agente(historico_chat, contexto_sistema, modelo="nvidia/nemotron-3-nano-30b-a3b:free"):
    """
    Função que dá vida ao Agente Logístico, permitindo que converse e analise a operação na Home.
    """
    if not OPENROUTER_API_KEY:
        return "⚠️ Chave de API ausente. Verifique o seu ficheiro .env."

    try:
        prompt_sistema = f"""
        Você é o Agente de IA Principal do ERP Logístico da PUC-SP. 
        REGRA MÁXIMA E ABSOLUTA: Baseie-se APENAS e ESTRITAMENTE nos dados reais fornecidos abaixo. 
        NÃO invente estatísticas, porcentagens de erro de OCR, falsas rupturas ou problemas imaginários. 
        Se os dados fornecidos abaixo mostrarem apenas valores e quantidades, limite-se a analisar apenas esses números.
        
        DADOS REAIS DA OPERAÇÃO NESTE EXATO MOMENTO:
        {contexto_sistema}
        """

        mensagens_formatadas = [{"role": "system", "content": prompt_sistema}]
        for msg in historico_chat:
            mensagens_formatadas.append({"role": msg["role"], "content": msg["content"]})

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY.strip()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": modelo,
            "messages": mensagens_formatadas
        }
        
        response = requests.post(url=API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"Erro no agente: {response.text}"
            
    except Exception as e:
        return f"Erro no cérebro do Agente: {e}"