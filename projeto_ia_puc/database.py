import sqlite3

def criar_banco():
    conn = sqlite3.connect("dados_logistica.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notas_processadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fornecedor TEXT,
            cnpj TEXT,
            data_emissao TEXT,
            valor_total REAL,
            status_aprovacao TEXT,
            motivo TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_nota(dados, status, motivo):
    conn = sqlite3.connect("dados_logistica.db")
    cursor = conn.cursor()
    
    valor_bruto = dados.get('valor_total', 0)
    if isinstance(valor_bruto, (int, float)):
        valor = float(valor_bruto)
    else:
        v_str = str(valor_bruto).replace('R$', '').strip()
        if '.' in v_str and ',' in v_str:
            if v_str.rfind(',') > v_str.rfind('.'):
                v_str = v_str.replace('.', '').replace(',', '.')
            else:
                v_str = v_str.replace(',', '')
        elif ',' in v_str:
            v_str = v_str.replace(',', '.')
        try:
            valor = float(v_str)
        except ValueError:
            valor = 0.0
            
    cursor.execute('''
        INSERT INTO notas_processadas (fornecedor, cnpj, data_emissao, valor_total, status_aprovacao, motivo)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (dados.get('fornecedor'), dados.get('cnpj'), dados.get('data_emissao'), valor, status, motivo))
    
    conn.commit()
    conn.close()

# --- NOVA FUNÇÃO PARA LER O HISTÓRICO ---
def obter_historico():
    conn = sqlite3.connect("dados_logistica.db")
    cursor = conn.cursor()
    # Puxa tudo ordenado do mais recente para o mais antigo
    cursor.execute("SELECT id, fornecedor, cnpj, data_emissao, valor_total, status_aprovacao, motivo FROM notas_processadas ORDER BY id DESC")
    linhas = cursor.fetchall()
    conn.close()
    
    # Arruma os dados para a tela do site entender fácil
    dados = []
    for linha in linhas:
        dados.append({
            "ID": linha[0],
            "Fornecedor": linha[1],
            "CNPJ": linha[2],
            "Data": linha[3],
            "Valor Total": linha[4],
            "Status": linha[5],
            "Parecer / Motivo": linha[6]
        })
    return dados