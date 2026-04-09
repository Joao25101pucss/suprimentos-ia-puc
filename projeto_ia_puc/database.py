import json
import os

# Nome do arquivo que servirá como nosso banco de dados (JSON)
DB_FILE = "logistica_db.json"

def inicializar_db():
    """Garante que o arquivo de banco de dados exista para evitar erros de leitura."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

def salvar_operacao(dados_nf, status="PENDENTE"):
    """
    Salva uma operação completa no banco de dados.
    Inclui colunas de itens, prejuízo e tempo de chegada.
    """
    inicializar_db()
    
    # Carrega o histórico existente
    with open(DB_FILE, "r", encoding="utf-8") as f:
        historico = json.load(f)
    
    # Criamos o registro com a estrutura completa que a IA vai ler
    novo_registro = {
        "Fornecedor": dados_nf.get("Fornecedor", "N/A"),
        "CNPJ": dados_nf.get("CNPJ", "N/A"),
        "Data": dados_nf.get("Data", ""),
        "Valor Total": dados_nf.get("valor_total", 0.0),
        "Status": status,
        # Colunas detalhadas para análise de IA:
        "itens": dados_nf.get("itens", []),  # Lista de produtos, quantidades e preços
        "prejuizo_estimado": dados_nf.get("prejuizo_estimado", 0.0),
        "tempo_chegada_dias": dados_nf.get("tempo_chegada_dias", 0)
    }
    
    # Adiciona ao início da lista (mais recentes primeiro)
    historico.insert(0, novo_registro)
    
    # Salva de volta no arquivo
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=4, ensure_ascii=False)

def obter_historico():
    """Retorna a lista completa de operações registradas."""
    inicializar_db()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def limpar_banco():
    """Função utilitária para resetar os dados se necessário."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)