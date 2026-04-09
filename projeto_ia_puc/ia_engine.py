"""
ia_engine.py — Motor de IA do ERP Logística
Conecta ao OpenRouter (NVIDIA Nemotron 120B) e blinda a extração de NFs.
"""

import json
import os
import base64
import requests
import pdfplumber
import re
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Modelos de IA
MODEL_CHAT     = "nvidia/nemotron-3-super-120b-a12b:free"
MODEL_VISAO    = "meta-llama/llama-3.2-11b-vision-instruct:free"   
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# ─────────────────────────────────────────────
#  HELPERS INTERNOS
# ─────────────────────────────────────────────

def _headers() -> dict:
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }


def _chamar_api(messages: list, model: str, max_tokens: int = 2048) -> str:
    """Chama a API do OpenRouter e retorna o texto da resposta."""
    if not OPENROUTER_API_KEY:
        print("[DEBUG] ⚠️ OPENROUTER_API_KEY não encontrada.")
        return "⚠️ Chave `OPENROUTER_API_KEY` não encontrada no arquivo `.env`."
    
    payload = {
        "model": model, 
        "messages": messages, 
        "max_tokens": max_tokens
    }
    
    try:
        resp = requests.post(OPENROUTER_URL, headers=_headers(), json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        print("[DEBUG] ⏱️ Timeout na requisição da API.")
        return "⏱️ A IA demorou muito para responder. Tente novamente."
    except Exception as e:
        print(f"[DEBUG] ❌ Erro de requisição: {str(e)}")
        return f"❌ Erro de conexão com a IA: {str(e)}"


# ─────────────────────────────────────────────
#  CHAT — TORRE DE COMANDO
# ─────────────────────────────────────────────

SYSTEM_PROMPT_TORRE = """
Você é ARIA (Autonomous Routing & Intelligence Analyst), o agente de IA central
do ERP Logística Visionary. Você tem acesso em tempo real ao banco de dados SQL
do sistema.

## Sua Personalidade
- Tom profissional, direto e analítico — como um gestor sênior de supply chain.
- Use dados reais do banco para embasar CADA resposta. Nunca invente números.
- Formate respostas com Markdown: use **negrito**, tabelas e listas quando ajudar.

## Regras de Ouro
- Ao mencionar valores monetários, use o formato R$ X.XXX,XX.
- Responda SEMPRE em Português do Brasil.
"""


def construir_contexto_banco(dados_banco: dict) -> str:
    """Serializa os dados do banco em um contexto estruturado para a IA."""
    stats    = dados_banco.get("stats", {})
    pedidos  = dados_banco.get("pedidos", [])
    fornecs  = dados_banco.get("fornecedores", [])
    catalogo = dados_banco.get("catalogo", [])

    pedidos_resumo = []
    for p in pedidos[:30]:
        pedidos_resumo.append({
            "id_nf":      p.get("id_nf"),
            "destino":    p.get("destino"),
            "data":       p.get("data_emissao"),
            "valor":      p.get("valor_total"),
            "prejuizo":   p.get("prejuizo_total_est"),
            "status":     p.get("status"),
            "fornecedor": p.get("fornecedor")
        })

    contexto = f"""{SYSTEM_PROMPT_TORRE}

---
## SNAPSHOT DO BANCO DE DADOS (tempo real)
- Total de NFs: {stats.get('total_nfs', 0)}
- Volume Financeiro Total: R$ {stats.get('volume_total', 0):,.2f}
- Prejuízo Logístico Estimado: R$ {stats.get('prejuizo_total', 0):,.2f}

### Últimas Notas Fiscais
{json.dumps(pedidos_resumo, ensure_ascii=False, indent=2)}

### Fornecedores Ativos
{json.dumps(fornecs[:10], ensure_ascii=False, indent=2)}

### Catálogo de Produtos (Amostra)
{json.dumps(catalogo[:30], ensure_ascii=False, indent=2)}
---
"""
    return contexto


def conversar_com_agente(historico: list, contexto_banco: str) -> str:
    """Envia o histórico de conversa + contexto do banco para a IA e retorna a resposta."""
    messages = [{"role": "system", "content": contexto_banco}]
    for msg in historico:
        messages.append({"role": msg["role"], "content": msg["content"]})
    return _chamar_api(messages, model=MODEL_CHAT)


# ─────────────────────────────────────────────
#  EXTRAÇÃO DE NF (PDF / IMAGEM)
# ─────────────────────────────────────────────

PROMPT_EXTRACAO = """
Sua ÚNICA função é extrair dados deste documento e retornar um objeto JSON.
NÃO escreva "Aqui está o JSON", não use formatação Markdown (```json), não cumprimente.
O PRIMEIRO caractere da sua resposta deve ser { e o ÚLTIMO deve ser }.

Estrutura OBRIGATÓRIA:
{
  "CNPJ": "00.000.000/0000-00",
  "fornecedor": "Razão Social da Empresa Emissora",
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

Regras Cruciais:
1. Valores financeiros devem ser FLOAT numérico.
2. Utilize PONTO (.) como separador de casas decimais (Exemplo correto: 1950.00). NUNCA use vírgula.
3. Se um dado não existir, coloque null.
"""


def _extrair_texto_pdf(arquivo) -> str:
    """Extrai texto de um PDF usando pdfplumber (Robusto para tabelas e NFs)."""
    try:
        arquivo.seek(0)
        texto = ""
        with pdfplumber.open(arquivo) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
        
        texto = texto.strip()
        print(f"\n[DEBUG] pdfplumber conseguiu ler {len(texto)} caracteres do PDF.")
        if len(texto) > 0:
            print(f"[DEBUG] Amostra do Texto:\n{texto[:300]}...\n")
        else:
            print("[DEBUG] ⚠️ O PDF parece ser uma imagem escaneada. Nenhum texto detectável.")
            
        return texto
    except Exception as e:
        print(f"\n[DEBUG] ❌ Erro CRÍTICO ao ler PDF com pdfplumber: {e}\n")
        return ""


def processar_nota(arquivo) -> dict | None:
    """Processa arquivo PDF/Imagem com logs de debug no console."""
    nome = arquivo.name.lower()
    print(f"\n========== INICIANDO EXTRAÇÃO: {nome} ==========")

    if nome.endswith(".pdf"):
        texto = _extrair_texto_pdf(arquivo)
        if not texto:
            print("[DEBUG] Falha: Nenhum texto encontrado no PDF.")
            return None
        
        messages = [
            {"role": "system", "content": PROMPT_EXTRACAO},
            {"role": "user",   "content": f"Extraia os dados desta Nota Fiscal:\n\n{texto}"}
        ]
        model = MODEL_CHAT

    elif nome.endswith((".png", ".jpg", ".jpeg")):
        arquivo.seek(0)
        b64 = base64.b64encode(arquivo.read()).decode("utf-8")
        messages = [
            {"role": "system", "content": PROMPT_EXTRACAO},
            {
                "role": "user",
                "content": [
                    {"type": "text",      "text": "Extraia os dados desta imagem de Nota Fiscal:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }
        ]
        model = MODEL_VISAO
    else:
        print("[DEBUG] Formato de arquivo não suportado.")
        return None

    print(f"[DEBUG] Enviando texto para IA: {model}...")
    resposta = _chamar_api(messages, model=model, max_tokens=1024)

    print(f"\n[DEBUG] RESPOSTA BRUTA DA IA:\n{resposta}\n")

    if str(resposta).startswith(("⚠️", "❌", "⏱️")):
        return None

    try:
        # Limpeza agressiva: arranca fora o que a IA costuma mandar de lixo
        res_limpa = str(resposta).replace("```json", "").replace("```", "").strip()
        
        # Encontra onde o JSON começa e termina de verdade
        inicio = res_limpa.find('{')
        fim = res_limpa.rfind('}')
        
        if inicio != -1 and fim != -1:
            json_puro = res_limpa[inicio:fim+1]
            dados_parseados = json.loads(json_puro)
            print("[DEBUG] ✅ JSON decodificado com sucesso!")
            return dados_parseados
        else:
            print("[DEBUG] ❌ Erro: Não foi possível encontrar as chaves '{' e '}' na resposta da IA.")
            return None
            
    except json.JSONDecodeError as e:
        print(f"[DEBUG] ❌ Falha ao decodificar (JSONDecodeError): {e}")
        return None