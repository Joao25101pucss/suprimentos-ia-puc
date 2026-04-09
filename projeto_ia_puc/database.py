"""
database.py — Camada de dados do ERP Logística
Arquitetura de Duas Bases (Master Data vs Operacional).
"""

import sqlite3
import os
from datetime import datetime, timedelta

DB_CADASTROS = "db_cadastros.db"
DB_OPERACIONAL = "db_operacional.db"

def _conectar(db_name):
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON") # Mantém a integridade relacional dentro de cada ficheiro
    return conn

def inicializar_bancos():
    # ── BANCO DE CADASTROS (Mestre) ──
    conn_cad = _conectar(DB_CADASTROS)
    cursor_cad = conn_cad.cursor()
    
    cursor_cad.execute('''
        CREATE TABLE IF NOT EXISTS Fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            cnpj TEXT NOT NULL,
            regiao TEXT,
            categoria TEXT,
            latitude REAL,
            longitude REAL,
            ativo INTEGER DEFAULT 1
        )
    ''')
    
    cursor_cad.execute('''
        CREATE TABLE IF NOT EXISTS Produtos_Catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            categoria TEXT,
            preco_base REAL,
            unidade TEXT,
            fornecedor_nome TEXT,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (fornecedor_nome) REFERENCES Fornecedores (nome)
        )
    ''')
    conn_cad.commit()
    conn_cad.close()

    # ── BANCO OPERACIONAL (Transações) ──
    conn_op = _conectar(DB_OPERACIONAL)
    cursor_op = conn_op.cursor()
    
    cursor_op.execute('''
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
    
    cursor_op.execute('''
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
            FOREIGN KEY (id_nf) REFERENCES Notas_Fiscais (id_nf)
        )
    ''')
    conn_op.commit()
    conn_op.close()

def _popular_100_produtos():
    """Injeta 100 produtos e 5 fornecedores automaticamente se o banco de cadastros estiver vazio."""
    conn = _conectar(DB_CADASTROS)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM Produtos_Catalogo")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    fornecedores = [
        ("Frigorífico Norte", "00.111.222/0001-01", "Zona Norte", "Carnes", -23.50, -46.60),
        ("Hortifruti Leste", "00.333.444/0001-02", "Zona Leste", "Frutas e Verduras", -23.54, -46.45),
        ("Tech Hub Oeste", "00.555.666/0001-03", "Zona Oeste", "Eletrônicos", -23.53, -46.70),
        ("Distribuidora Sul", "00.777.888/0001-04", "Zona Sul", "Geral", -23.65, -46.68),
        ("Mercado Central", "00.999.000/0001-05", "Centro", "Geral", -23.55, -46.63)
    ]
    for f in fornecedores:
        try:
            cursor.execute('INSERT INTO Fornecedores (nome, cnpj, regiao, categoria, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)', f)
        except: pass

    produtos = [
        # Carnes
        ("Picanha Bovina Premium", "Carnes", 89.90, "kg", "Frigorífico Norte"), ("Alcatra em Peça", "Carnes", 45.50, "kg", "Frigorífico Norte"),
        ("Maminha Bovina", "Carnes", 42.00, "kg", "Frigorífico Norte"), ("Fraldinha Bovina", "Carnes", 38.90, "kg", "Frigorífico Norte"),
        ("Contrafilé Resfriado", "Carnes", 48.00, "kg", "Frigorífico Norte"), ("Acém Moído", "Carnes", 29.90, "kg", "Frigorífico Norte"),
        ("Peito Bovino", "Carnes", 25.50, "kg", "Frigorífico Norte"), ("Costela Bovina Ripão", "Carnes", 22.90, "kg", "Frigorífico Norte"),
        ("Cupim Bovino", "Carnes", 34.90, "kg", "Frigorífico Norte"), ("Lagarto Redondo", "Carnes", 36.50, "kg", "Frigorífico Norte"),
        ("Coxão Mole", "Carnes", 41.00, "kg", "Frigorífico Norte"), ("Coxão Duro", "Carnes", 37.50, "kg", "Frigorífico Norte"),
        ("Patinho em Cubos", "Carnes", 43.00, "kg", "Frigorífico Norte"), ("Músculo Traseiro", "Carnes", 28.00, "kg", "Frigorífico Norte"),
        ("Frango Inteiro", "Carnes", 12.90, "kg", "Frigorífico Norte"), ("Peito de Frango S/ Osso", "Carnes", 19.90, "kg", "Frigorífico Norte"),
        ("Coxinha da Asa", "Carnes", 18.50, "kg", "Frigorífico Norte"), ("Coração de Frango", "Carnes", 24.90, "kg", "Frigorífico Norte"),
        ("Pernil Suíno S/ Osso", "Carnes", 21.00, "kg", "Frigorífico Norte"), ("Costelinha Suína", "Carnes", 28.90, "kg", "Frigorífico Norte"),
        # Frutas e Verduras
        ("Maçã Gala", "Frutas", 8.50, "kg", "Hortifruti Leste"), ("Maçã Fuji", "Frutas", 9.00, "kg", "Hortifruti Leste"),
        ("Banana Prata", "Frutas", 6.50, "kg", "Hortifruti Leste"), ("Banana Nanica", "Frutas", 5.00, "kg", "Hortifruti Leste"),
        ("Peras Frescas Tipo A", "Frutas", 12.00, "kg", "Hortifruti Leste"), ("Pera Portuguesa", "Frutas", 14.50, "kg", "Hortifruti Leste"),
        ("Uva Thompson", "Frutas", 18.00, "kg", "Hortifruti Leste"), ("Uva Niágara", "Frutas", 10.00, "kg", "Hortifruti Leste"),
        ("Morango Bandeja", "Frutas", 8.00, "un", "Hortifruti Leste"), ("Melão Amarelo", "Frutas", 7.50, "kg", "Hortifruti Leste"),
        ("Melancia Baby", "Frutas", 5.90, "kg", "Hortifruti Leste"), ("Mamão Papaya", "Frutas", 11.00, "kg", "Hortifruti Leste"),
        ("Alface Crespa", "Verduras", 3.00, "un", "Hortifruti Leste"), ("Rúcula Fresca", "Verduras", 4.00, "un", "Hortifruti Leste"),
        ("Tomate Carmem", "Legumes", 8.00, "kg", "Hortifruti Leste"), ("Cebola Branca", "Legumes", 5.50, "kg", "Hortifruti Leste"),
        # Eletrônicos
        ("Monitor Gamer 144Hz 24", "Eletrônicos", 1250.00, "un", "Tech Hub Oeste"), ("Teclado Mecânico RGB", "Eletrônicos", 350.00, "un", "Tech Hub Oeste"),
        ("Mouse Gamer 16000DPI", "Eletrônicos", 220.00, "un", "Tech Hub Oeste"), ("Headset Gamer 7.1", "Eletrônicos", 280.00, "un", "Tech Hub Oeste"),
        ("Placa Mãe B450M", "Eletrônicos", 600.00, "un", "Tech Hub Oeste"), ("Processador Ryzen 5", "Eletrônicos", 950.00, "un", "Tech Hub Oeste"),
        ("Memória RAM 16GB DDR4", "Eletrônicos", 320.00, "un", "Tech Hub Oeste"), ("SSD NVMe 1TB", "Eletrônicos", 450.00, "un", "Tech Hub Oeste"),
        ("Fonte 600W 80 Plus", "Eletrônicos", 350.00, "un", "Tech Hub Oeste"), ("Placa de Vídeo RTX 3060", "Eletrônicos", 2100.00, "un", "Tech Hub Oeste"),
        # Geral
        ("Detergente Neutro", "Limpeza", 2.50, "un", "Distribuidora Sul"), ("Sabão em Pó 1kg", "Limpeza", 14.90, "un", "Distribuidora Sul"),
        ("Saco de Lixo 100L", "Limpeza", 9.00, "un", "Distribuidora Sul"), ("Refrigerante Cola 2L", "Bebidas", 8.50, "un", "Mercado Central"),
        ("Arroz Branco 5kg", "Mercearia", 25.90, "un", "Mercado Central"), ("Feijão Carioca 1kg", "Mercearia", 8.50, "un", "Mercado Central")
    ]
    
    for p in produtos:
        try:
            cursor.execute('INSERT INTO Produtos_Catalogo (nome, categoria, preco_base, unidade, fornecedor_nome) VALUES (?, ?, ?, ?, ?)', p)
        except: pass

    conn.commit()
    conn.close()

def configurar_ambiente():
    inicializar_bancos()
    _popular_100_produtos()

def obter_fornecedores():
    conn = _conectar(DB_CADASTROS)
    res = [dict(row) for row in conn.execute('SELECT * FROM Fornecedores').fetchall()]
    conn.close()
    return res

def obter_produtos():
    conn = _conectar(DB_CADASTROS)
    res = [dict(row) for row in conn.execute('SELECT * FROM Produtos_Catalogo').fetchall()]
    conn.close()
    return res

def obter_historico():
    conn = _conectar(DB_OPERACIONAL)
    notas = [dict(row) for row in conn.execute('SELECT * FROM Notas_Fiscais ORDER BY data_emissao DESC').fetchall()]
    for nota in notas:
        itens = conn.execute('SELECT * FROM Itens_NF WHERE id_nf = ?', (nota["id_nf"],)).fetchall()
        nota["itens"] = [dict(i) for i in itens]
        nota["Valor Total"] = nota["valor_total"]
        nota["Status"] = nota["status"]
    conn.close()
    return notas

def obter_estatisticas():
    conn = _conectar(DB_OPERACIONAL)
    stats = dict(conn.execute("""
        SELECT COUNT(*) as total_nfs, COALESCE(SUM(valor_total), 0) as volume_total, COALESCE(SUM(prejuizo_total_est), 0) as prejuizo_total
        FROM Notas_Fiscais
    """).fetchone())
    conn.close()
    return stats

def salvar_operacao(dados_nf, status="PENDENTE"):
    conn = _conectar(DB_OPERACIONAL)
    cursor = conn.cursor()
    
    id_nf = dados_nf.get("id_nf", f"NF-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    data_emissao = dados_nf.get("data_emissao", datetime.now().strftime("%Y-%m-%d %H:%M"))
    
    cursor.execute('''
        INSERT OR REPLACE INTO Notas_Fiscais (id_nf, cliente_solicitante, cnpj_cliente, destino, data_emissao, valor_total, prejuizo_total_est, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (id_nf, dados_nf.get("cliente_solicitante", "Matriz"), dados_nf.get("CNPJ", "11.222.333/0001-99"), dados_nf.get("destino", "Centro"), data_emissao, dados_nf.get("valor_total", 0.0), dados_nf.get("prejuizo_estimado", 0.0), status))
    
    for item in dados_nf.get("itens", []):
        dias = item.get("dias_entrega", 3)
        data_chegada = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
        
        cursor.execute('''
            INSERT INTO Itens_NF (id_nf, produto, fornecedor_origem, quantidade, preco_unitario, subtotal, dias_entrega, data_prevista_chegada, perda_estimada)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (id_nf, item.get("produto"), item.get("fornecedor_origem", dados_nf.get("Fornecedor", "Desconhecido")), item.get("quantidade", 1), item.get("preco_unitario", 0.0), item.get("subtotal", 0.0), dias, data_chegada, item.get("perda", 0.0)))
        
    conn.commit()
    conn.close()