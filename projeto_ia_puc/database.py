import sqlite3
import os
from datetime import datetime, timedelta

DB_FILE = "logistica_erp.db"

def get_conexao():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_bancos():
    conn = get_conexao()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE,
            cnpj TEXT,
            regiao TEXT,
            categoria TEXT,
            latitude REAL,
            longitude REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Produtos_Catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            categoria TEXT,
            preco_base REAL,
            fornecedor_nome TEXT,
            FOREIGN KEY (fornecedor_nome) REFERENCES Fornecedores (nome)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Notas_Fiscais (
            id_nf TEXT PRIMARY KEY,
            cliente_solicitante TEXT,
            cnpj_cliente TEXT,
            destino TEXT,
            data_emissao TEXT,
            valor_total REAL,
            prejuizo_total_est REAL,
            status TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Itens_NF (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_nf TEXT,
            produto TEXT,
            fornecedor_origem TEXT,
            quantidade INTEGER,
            preco_unitario REAL,
            subtotal REAL,
            dias_entrega INTEGER,
            data_prevista_chegada TEXT,
            perda_estimada REAL,
            reembolso_estimado REAL,
            FOREIGN KEY (id_nf) REFERENCES Notas_Fiscais (id_nf)
        )
    ''')
    
    conn.commit()
    conn.close()

def cadastrar_fornecedor(nome, regiao, categoria, coord, cnpj="00.000.000/0001-00"):
    inicializar_bancos()
    conn = get_conexao()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO Fornecedores (nome, cnpj, regiao, categoria, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nome, cnpj, regiao, categoria, coord[0], coord[1]))
        conn.commit()
    except sqlite3.IntegrityError:
        pass 
    conn.close()

def cadastrar_produto(nome, categoria, preco, fornecedor_nome):
    inicializar_bancos()
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM Produtos_Catalogo WHERE nome = ? AND fornecedor_nome = ?', (nome, fornecedor_nome))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO Produtos_Catalogo (nome, categoria, preco_base, fornecedor_nome)
            VALUES (?, ?, ?, ?)
        ''', (nome, categoria, preco, fornecedor_nome))
        conn.commit()
    conn.close()

def salvar_operacao(dados_nf, status="PENDENTE"):
    inicializar_bancos()
    conn = get_conexao()
    cursor = conn.cursor()
    
    id_nf = dados_nf.get("id_nf", f"NF-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    data_emissao = dados_nf.get("data_emissao", datetime.now().strftime("%Y-%m-%d %H:%M"))
    
    cursor.execute('''
        INSERT OR REPLACE INTO Notas_Fiscais 
        (id_nf, cliente_solicitante, cnpj_cliente, destino, data_emissao, valor_total, prejuizo_total_est, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        id_nf,
        dados_nf.get("cliente_solicitante", "Nossa Sede (Matriz)"),
        dados_nf.get("cnpj_cliente", "11.222.333/0001-99"),
        dados_nf.get("destino", "Centro"),
        data_emissao,
        dados_nf.get("valor_total", 0.0),
        dados_nf.get("prejuizo_estimado", 0.0),
        status
    ))
    
    itens = dados_nf.get("itens", [])
    data_emissao_obj = datetime.strptime(data_emissao.split()[0], "%d/%m/%Y") if "/" in data_emissao else datetime.strptime(data_emissao.split()[0], "%Y-%m-%d")

    for item in itens:
        dias = item.get("dias_entrega", 3)
        data_chegada = (data_emissao_obj + timedelta(days=dias)).strftime("%Y-%m-%d")
        
        cursor.execute('''
            INSERT INTO Itens_NF 
            (id_nf, produto, fornecedor_origem, quantidade, preco_unitario, subtotal, dias_entrega, data_prevista_chegada, perda_estimada, reembolso_estimado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            id_nf,
            item.get("produto"),
            item.get("fornecedor_origem", dados_nf.get("Fornecedor", "Desconhecido")),
            item.get("quantidade", 1),
            item.get("preco_unitario", item.get("preco_unitario", 0.0)),
            item.get("subtotal", item.get("subtotal", 0.0)),
            dias,
            data_chegada,
            item.get("perda", 0.0),
            item.get("reembolso", 0.0)
        ))
        
    conn.commit()
    conn.close()

def obter_fornecedores():
    inicializar_bancos()
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Fornecedores')
    resultado = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultado

def obter_produtos():
    inicializar_bancos()
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Produtos_Catalogo')
    resultado = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultado

def obter_historico():
    inicializar_bancos()
    conn = get_conexao()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM Notas_Fiscais ORDER BY data_emissao DESC')
    notas = [dict(row) for row in cursor.fetchall()]
    
    for nota in notas:
        cursor.execute('SELECT * FROM Itens_NF WHERE id_nf = ?', (nota["id_nf"],))
        nota["itens"] = [dict(row) for row in cursor.fetchall()]
        
        # Retrocompatibilidade com os dataframes do main
        nota["Valor Total"] = nota["valor_total"]
        nota["Status"] = nota["status"]
        
    conn.close()
    return notas