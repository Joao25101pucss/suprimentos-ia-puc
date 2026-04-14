"""
database.py — Camada de dados do ERP Logística Visionary
  • db_cadastros.db   → Fornecedores, Produtos, Usuários (Master Data)
  • db_operacional.db → Notas Fiscais, Itens (Transacional)
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta

DB_CADASTROS   = "db_cadastros.db"
DB_OPERACIONAL = "db_operacional.db"


def _conectar(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()


# ─────────────────────────────────────────────
#  INICIALIZAÇÃO
# ─────────────────────────────────────────────

def inicializar_bancos():
    with _conectar(DB_CADASTROS) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS Fornecedores (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nome      TEXT    UNIQUE NOT NULL,
                cnpj      TEXT    NOT NULL DEFAULT '00.000.000/0001-00',
                regiao    TEXT    NOT NULL DEFAULT 'Centro',
                categoria TEXT    NOT NULL DEFAULT 'Geral',
                latitude  REAL,
                longitude REAL,
                ativo     INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS Produtos_Catalogo (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nome            TEXT    NOT NULL,
                categoria       TEXT    NOT NULL DEFAULT 'Geral',
                preco_base      REAL    NOT NULL DEFAULT 0.0,
                unidade         TEXT    NOT NULL DEFAULT 'un',
                fornecedor_nome TEXT    NOT NULL,
                ativo           INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (fornecedor_nome) REFERENCES Fornecedores(nome)
            );
            CREATE TABLE IF NOT EXISTS Usuarios (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                login      TEXT    UNIQUE NOT NULL,
                senha_hash TEXT    NOT NULL,
                nome       TEXT    NOT NULL,
                perfil     TEXT    NOT NULL CHECK(perfil IN ('admin','cliente','fornecedor')),
                empresa    TEXT    DEFAULT '',
                ativo      INTEGER NOT NULL DEFAULT 1
            );
        """)

    with _conectar(DB_OPERACIONAL) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS Notas_Fiscais (
                id_nf              TEXT PRIMARY KEY,
                cliente_login      TEXT NOT NULL DEFAULT 'sistema',
                cliente_nome       TEXT NOT NULL DEFAULT 'Matriz',
                cnpj_cliente       TEXT NOT NULL DEFAULT '00.000.000/0001-00',
                fornecedor_nome    TEXT NOT NULL DEFAULT 'Desconhecido',
                destino            TEXT NOT NULL DEFAULT 'Centro',
                data_emissao       TEXT NOT NULL,
                valor_total        REAL NOT NULL DEFAULT 0.0,
                prejuizo_total_est REAL NOT NULL DEFAULT 0.0,
                status             TEXT NOT NULL DEFAULT 'AGUARDANDO_FORNECEDOR',
                tipo               TEXT NOT NULL DEFAULT 'OUTBOUND',
                observacao         TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS Itens_NF (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                id_nf                 TEXT    NOT NULL,
                produto               TEXT    NOT NULL,
                fornecedor_origem     TEXT    NOT NULL DEFAULT 'Desconhecido',
                quantidade            INTEGER NOT NULL DEFAULT 1,
                preco_unitario        REAL    NOT NULL DEFAULT 0.0,
                subtotal              REAL    NOT NULL DEFAULT 0.0,
                dias_entrega          INTEGER NOT NULL DEFAULT 3,
                data_prevista_chegada TEXT,
                status             TEXT,
                perda_estimada        REAL    NOT NULL DEFAULT 0.0,
                reembolso_estimado    REAL    NOT NULL DEFAULT 0.0,
                FOREIGN KEY (id_nf) REFERENCES Notas_Fiscais(id_nf)
            );
        """)


# ─────────────────────────────────────────────
#  USUÁRIOS
# ─────────────────────────────────────────────

def criar_usuario(login, senha, nome, perfil, empresa=""):
    try:
        with _conectar(DB_CADASTROS) as conn:
            conn.execute(
                "INSERT INTO Usuarios (login,senha_hash,nome,perfil,empresa) VALUES (?,?,?,?,?)",
                (login, _hash(senha), nome, perfil, empresa)
            )
        return True
    except sqlite3.IntegrityError:
        return False

def autenticar(login, senha):
    with _conectar(DB_CADASTROS) as conn:
        row = conn.execute(
            "SELECT * FROM Usuarios WHERE login=? AND senha_hash=? AND ativo=1",
            (login, _hash(senha))
        ).fetchone()
    return dict(row) if row else None

def listar_usuarios():
    with _conectar(DB_CADASTROS) as conn:
        rows = conn.execute(
            "SELECT id,login,nome,perfil,empresa,ativo FROM Usuarios ORDER BY perfil,nome"
        ).fetchall()
    return [dict(r) for r in rows]

def deletar_usuario(uid):
    with _conectar(DB_CADASTROS) as conn:
        conn.execute("UPDATE Usuarios SET ativo=0 WHERE id=?", (uid,))


# ─────────────────────────────────────────────
#  FORNECEDORES & PRODUTOS
# ─────────────────────────────────────────────

def cadastrar_fornecedor(nome, regiao, categoria, coord, cnpj="00.000.000/0001-00"):
    inicializar_bancos()
    with _conectar(DB_CADASTROS) as conn:
        conn.execute("""
            INSERT OR IGNORE INTO Fornecedores (nome,cnpj,regiao,categoria,latitude,longitude)
            VALUES (?,?,?,?,?,?)
        """, (nome, cnpj, regiao, categoria, coord[0], coord[1]))

def obter_fornecedores():
    inicializar_bancos()
    with _conectar(DB_CADASTROS) as conn:
        rows = conn.execute("SELECT * FROM Fornecedores WHERE ativo=1 ORDER BY nome").fetchall()
    return [dict(r) for r in rows]

def cadastrar_produto(nome, categoria, preco, fornecedor_nome, unidade="un"):
    inicializar_bancos()
    with _conectar(DB_CADASTROS) as conn:
        existe = conn.execute(
            "SELECT id FROM Produtos_Catalogo WHERE nome=? AND fornecedor_nome=?",
            (nome, fornecedor_nome)
        ).fetchone()
        if not existe:
            conn.execute("""
                INSERT INTO Produtos_Catalogo (nome,categoria,preco_base,unidade,fornecedor_nome)
                VALUES (?,?,?,?,?)
            """, (nome, categoria, preco, unidade, fornecedor_nome))

def obter_produtos():
    inicializar_bancos()
    with _conectar(DB_CADASTROS) as conn:
        rows = conn.execute(
            "SELECT * FROM Produtos_Catalogo WHERE ativo=1 ORDER BY categoria,nome"
        ).fetchall()
    return [dict(r) for r in rows]

def obter_produtos_por_fornecedor(nome_fornecedor):
    inicializar_bancos()
    with _conectar(DB_CADASTROS) as conn:
        rows = conn.execute(
            "SELECT * FROM Produtos_Catalogo WHERE fornecedor_nome=? AND ativo=1",
            (nome_fornecedor,)
        ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
#  NOTAS FISCAIS
# ─────────────────────────────────────────────

def salvar_operacao(dados_nf, status="AGUARDANDO_FORNECEDOR"):
    inicializar_bancos()
    id_nf        = dados_nf.get("id_nf", f"NF-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    data_emissao = dados_nf.get("data_emissao", datetime.now().strftime("%Y-%m-%d %H:%M"))

    try:
        dt_base = datetime.strptime(data_emissao.split()[0], "%d/%m/%Y") \
                  if "/" in data_emissao \
                  else datetime.strptime(data_emissao.split()[0], "%Y-%m-%d")
    except ValueError:
        dt_base = datetime.now()

    itens = dados_nf.get("itens", [])
    fornecedor_principal = dados_nf.get("fornecedor_nome") or \
                           (itens[0].get("fornecedor_origem") if itens else "Desconhecido")

    with _conectar(DB_OPERACIONAL) as conn:
        # 1. Salva a "Capa" do Pedido na tabela Notas_Fiscais
        conn.execute("""
            INSERT OR REPLACE INTO Notas_Fiscais
              (id_nf,cliente_login,cliente_nome,cnpj_cliente,
               fornecedor_nome,destino,data_emissao,
               valor_total,prejuizo_total_est,status,tipo,observacao)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            id_nf,
            dados_nf.get("cliente_login",  "sistema"),
            dados_nf.get("cliente_nome",   "Matriz"),
            dados_nf.get("cnpj_cliente",   "00.000.000/0001-00"),
            fornecedor_principal,
            dados_nf.get("destino",        "Centro"),
            data_emissao,
            dados_nf.get("valor_total",        0.0),
            dados_nf.get("prejuizo_estimado",  0.0),
            status,
            dados_nf.get("tipo", "OUTBOUND"),
            dados_nf.get("observacao", ""),
        ))
        
        # 2. Salva os produtos na tabela Itens_NF (agora com a coluna STATUS)
        for item in itens:
            dias       = item.get("dias_entrega", 3)
            dt_chegada = (dt_base + timedelta(days=dias)).strftime("%Y-%m-%d")
            conn.execute("""
                INSERT INTO Itens_NF
                  (id_nf,produto,fornecedor_origem,quantidade,
                   preco_unitario,subtotal,dias_entrega,
                   data_prevista_chegada, status, perda_estimada, reembolso_estimado)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                id_nf,
                item.get("produto", "N/D"),
                item.get("fornecedor_origem", fornecedor_principal),
                item.get("quantidade", 1),
                item.get("preco_unitario", 0.0),
                item.get("subtotal", 0.0),
                dias, 
                dt_chegada,
                status,  # <-- Coluna nova sendo preenchida aqui
                item.get("perda", 0.0),
                item.get("reembolso", 0.0),
            ))

def atualizar_status_nf(id_nf, novo_status, observacao=""):
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Monta a nova linha de log com a data, hora, status e a justificativa
    if observacao:
        nova_linha_log = f"[{data_hora} | {novo_status}] {observacao}"
    else:
        nova_linha_log = f"[{data_hora} | {novo_status}] Status atualizado."

    with _conectar(DB_OPERACIONAL) as conn:
        # 1. Busca a observação/histórico atual para não apagar o passado
        row = conn.execute("SELECT observacao FROM Notas_Fiscais WHERE id_nf=?", (id_nf,)).fetchone()
        obs_atual = row["observacao"] if row and row["observacao"] else ""

        # Concatena o log antigo com o novo evento
        obs_final = f"{obs_atual}\n{nova_linha_log}" if obs_atual else nova_linha_log

        # 2. Atualiza a tabela Notas_Fiscais (Capa do Pedido)
        conn.execute(
            "UPDATE Notas_Fiscais SET status=?, observacao=? WHERE id_nf=?",
            (novo_status, obs_final, id_nf)
        )
        
        # 3. NOVO: Atualiza a sua coluna de status em TODOS os itens dessa nota na tabela Itens_NF
        conn.execute(
            "UPDATE Itens_NF SET status=? WHERE id_nf=?",
            (novo_status, id_nf)
        )
def obter_historico(filtro_cliente=None, filtro_fornecedor=None, filtro_status=None):
    inicializar_bancos()
    query  = "SELECT * FROM Notas_Fiscais"
    params = []
    where  = []
    if filtro_cliente:
        where.append("cliente_login=?"); params.append(filtro_cliente)
    if filtro_fornecedor:
        where.append("fornecedor_nome=?"); params.append(filtro_fornecedor)
    if filtro_status:
        where.append("status=?"); params.append(filtro_status)
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY data_emissao DESC"

    with _conectar(DB_OPERACIONAL) as conn:
        notas = [dict(r) for r in conn.execute(query, params).fetchall()]
        for nota in notas:
            itens = conn.execute("SELECT * FROM Itens_NF WHERE id_nf=?", (nota["id_nf"],)).fetchall()
            nota["itens"] = [dict(i) for i in itens]
    return notas

def obter_estatisticas(filtro_cliente=None, filtro_fornecedor=None):
    inicializar_bancos()
    base = """
        SELECT COUNT(*) AS total_nfs,
               COALESCE(SUM(valor_total),0)        AS volume_total,
               COALESCE(SUM(prejuizo_total_est),0)  AS prejuizo_total,
               COUNT(CASE WHEN status='AGUARDANDO_FORNECEDOR'  THEN 1 END) AS aguardando,
               COUNT(CASE WHEN status='CONFIRMADO_FORNECEDOR'  THEN 1 END) AS confirmados,
               COUNT(CASE WHEN status='EM_TRANSITO'            THEN 1 END) AS em_transito,
               COUNT(CASE WHEN status='ENTREGUE'               THEN 1 END) AS entregues,
               COUNT(CASE WHEN status='BLOQUEADO'              THEN 1 END) AS bloqueadas
        FROM Notas_Fiscais
    """
    params = []
    where  = []
    if filtro_cliente:
        where.append("cliente_login=?"); params.append(filtro_cliente)
    if filtro_fornecedor:
        where.append("fornecedor_nome=?"); params.append(filtro_fornecedor)
    if where:
        base += " WHERE " + " AND ".join(where)
    with _conectar(DB_OPERACIONAL) as conn:
        row = conn.execute(base, params).fetchone()
    return dict(row) if row else {}


# ─────────────────────────────────────────────
#  SETUP COMPLETO
# ─────────────────────────────────────────────

def configurar_ambiente():
    inicializar_bancos()
    _popular_dados_iniciais()
    _criar_usuarios_padrao()

def _popular_dados_iniciais():
    with _conectar(DB_CADASTROS) as conn:
        qtd = conn.execute("SELECT COUNT(*) FROM Produtos_Catalogo").fetchone()[0]
    if qtd > 0:
        return

    fornecedores = [
        ("Frigorífico Norte", "00.111.222/0001-01","Zona Norte","Carnes",          -23.50,-46.60),
        ("Hortifruti Leste",  "00.333.444/0001-02","Zona Leste","Frutas e Verduras",-23.54,-46.45),
        ("Tech Hub Oeste",    "00.555.666/0001-03","Zona Oeste","Eletrônicos",      -23.53,-46.70),
        ("Distribuidora Sul", "00.777.888/0001-04","Zona Sul",  "Limpeza",          -23.65,-46.68),
        ("Mercado Central",   "00.999.000/0001-05","Centro",    "Mercearia",        -23.55,-46.63),
    ]
    with _conectar(DB_CADASTROS) as conn:
        for f in fornecedores:
            conn.execute(
                "INSERT OR IGNORE INTO Fornecedores (nome,cnpj,regiao,categoria,latitude,longitude) VALUES (?,?,?,?,?,?)", f
            )

    produtos = [
        ("Picanha Bovina Premium","Carnes",89.90,"kg","Frigorífico Norte"),
        ("Alcatra em Peça","Carnes",45.50,"kg","Frigorífico Norte"),
        ("Maminha Bovina","Carnes",42.00,"kg","Frigorífico Norte"),
        ("Fraldinha Bovina","Carnes",38.90,"kg","Frigorífico Norte"),
        ("Contrafilé Resfriado","Carnes",48.00,"kg","Frigorífico Norte"),
        ("Acém Moído","Carnes",29.90,"kg","Frigorífico Norte"),
        ("Peito Bovino","Carnes",25.50,"kg","Frigorífico Norte"),
        ("Costela Bovina Ripão","Carnes",22.90,"kg","Frigorífico Norte"),
        ("Cupim Bovino","Carnes",34.90,"kg","Frigorífico Norte"),
        ("Lagarto Redondo","Carnes",36.50,"kg","Frigorífico Norte"),
        ("Coxão Mole","Carnes",41.00,"kg","Frigorífico Norte"),
        ("Coxão Duro","Carnes",37.50,"kg","Frigorífico Norte"),
        ("Patinho em Cubos","Carnes",43.00,"kg","Frigorífico Norte"),
        ("Músculo Traseiro","Carnes",28.00,"kg","Frigorífico Norte"),
        ("Frango Inteiro Congelado","Carnes",12.90,"kg","Frigorífico Norte"),
        ("Peito de Frango S/ Osso","Carnes",19.90,"kg","Frigorífico Norte"),
        ("Coxinha da Asa","Carnes",18.50,"kg","Frigorífico Norte"),
        ("Coração de Frango","Carnes",24.90,"kg","Frigorífico Norte"),
        ("Pernil Suíno S/ Osso","Carnes",21.00,"kg","Frigorífico Norte"),
        ("Costelinha Suína","Carnes",28.90,"kg","Frigorífico Norte"),
        ("Maçã Gala","Frutas",8.50,"kg","Hortifruti Leste"),
        ("Maçã Fuji","Frutas",9.00,"kg","Hortifruti Leste"),
        ("Banana Prata","Frutas",6.50,"kg","Hortifruti Leste"),
        ("Banana Nanica","Frutas",5.00,"kg","Hortifruti Leste"),
        ("Pera Williams","Frutas",12.00,"kg","Hortifruti Leste"),
        ("Uva Thompson S/ Semente","Frutas",18.00,"kg","Hortifruti Leste"),
        ("Morango Bandeja","Frutas",8.00,"un","Hortifruti Leste"),
        ("Melão Amarelo","Frutas",7.50,"kg","Hortifruti Leste"),
        ("Melancia Baby","Frutas",5.90,"kg","Hortifruti Leste"),
        ("Mamão Papaya","Frutas",11.00,"kg","Hortifruti Leste"),
        ("Abacate Avocado","Frutas",15.00,"kg","Hortifruti Leste"),
        ("Limão Tahiti","Frutas",4.50,"kg","Hortifruti Leste"),
        ("Laranja Pera","Frutas",3.50,"kg","Hortifruti Leste"),
        ("Alface Crespa","Verduras",3.00,"un","Hortifruti Leste"),
        ("Rúcula Fresca","Verduras",4.00,"un","Hortifruti Leste"),
        ("Tomate Carmem","Legumes",8.00,"kg","Hortifruti Leste"),
        ("Tomate Cereja","Legumes",12.00,"kg","Hortifruti Leste"),
        ("Cebola Branca","Legumes",5.50,"kg","Hortifruti Leste"),
        ("Batata Inglesa","Legumes",6.00,"kg","Hortifruti Leste"),
        ("Cenoura","Legumes",5.00,"kg","Hortifruti Leste"),
        ("Monitor Gamer 144Hz 24","Eletrônicos",1250.00,"un","Tech Hub Oeste"),
        ("Monitor UltraWide 29","Eletrônicos",1500.00,"un","Tech Hub Oeste"),
        ("Teclado Mecânico RGB","Eletrônicos",350.00,"un","Tech Hub Oeste"),
        ("Mouse Gamer 16000DPI","Eletrônicos",220.00,"un","Tech Hub Oeste"),
        ("Headset Gamer 7.1","Eletrônicos",280.00,"un","Tech Hub Oeste"),
        ("Placa Mãe B450M","Eletrônicos",600.00,"un","Tech Hub Oeste"),
        ("Processador Ryzen 5","Eletrônicos",950.00,"un","Tech Hub Oeste"),
        ("Memória RAM 16GB DDR4","Eletrônicos",320.00,"un","Tech Hub Oeste"),
        ("SSD NVMe 1TB","Eletrônicos",450.00,"un","Tech Hub Oeste"),
        ("Placa de Vídeo RTX 3060","Eletrônicos",2100.00,"un","Tech Hub Oeste"),
        ("Webcam Full HD 1080p","Eletrônicos",190.00,"un","Tech Hub Oeste"),
        ("Detergente Neutro 500ml","Limpeza",2.50,"un","Distribuidora Sul"),
        ("Sabão em Pó 1kg","Limpeza",14.90,"un","Distribuidora Sul"),
        ("Amaciante 2L","Limpeza",12.00,"un","Distribuidora Sul"),
        ("Água Sanitária 2L","Limpeza",5.50,"un","Distribuidora Sul"),
        ("Desinfetante Pinho 1L","Limpeza",8.90,"un","Distribuidora Sul"),
        ("Saco de Lixo 100L 10un","Limpeza",9.00,"un","Distribuidora Sul"),
        ("Papel Higiênico 12un","Higiene",18.90,"un","Distribuidora Sul"),
        ("Sabonete em Barra 90g","Higiene",2.20,"un","Distribuidora Sul"),
        ("Shampoo 350ml","Higiene",12.00,"un","Distribuidora Sul"),
        ("Refrigerante Cola 2L","Bebidas",8.50,"un","Mercado Central"),
        ("Refrigerante Guaraná 2L","Bebidas",7.50,"un","Mercado Central"),
        ("Água Mineral S/ Gás 1.5L","Bebidas",3.00,"un","Mercado Central"),
        ("Cerveja Pilsen Lata 350ml","Bebidas",3.90,"un","Mercado Central"),
        ("Arroz Branco Tipo 1 5kg","Mercearia",25.90,"un","Mercado Central"),
        ("Feijão Carioca 1kg","Mercearia",8.50,"un","Mercado Central"),
        ("Feijão Preto 1kg","Mercearia",9.50,"un","Mercado Central"),
        ("Açúcar Refinado 1kg","Mercearia",4.50,"un","Mercado Central"),
        ("Café Torrado e Moído 500g","Mercearia",15.90,"un","Mercado Central"),
        ("Óleo de Soja 900ml","Mercearia",6.50,"un","Mercado Central"),
        ("Azeite Extra Virgem 500ml","Mercearia",28.90,"un","Mercado Central"),
        ("Macarrão Espaguete 500g","Mercearia",4.50,"un","Mercado Central"),
    ]
    with _conectar(DB_CADASTROS) as conn:
        for p in produtos:
            try:
                conn.execute(
                    "INSERT INTO Produtos_Catalogo (nome,categoria,preco_base,unidade,fornecedor_nome) VALUES (?,?,?,?,?)", p
                )
            except Exception:
                pass

def _criar_usuarios_padrao():
    demos = [
        ("admin",        "admin123",   "Dev / Administrador",   "admin",      "ERP Visionary"),
        ("supermercado", "cliente123", "Supermercado BomPreço", "cliente",    "BomPreço LTDA"),
        ("frigorifico",  "forn123",    "Frigorífico Norte",     "fornecedor", "Frigorífico Norte"),
        ("hortifruti",   "forn123",    "Hortifruti Leste",      "fornecedor", "Hortifruti Leste"),
        ("techhub",      "forn123",    "Tech Hub Oeste",        "fornecedor", "Tech Hub Oeste"),
        ("distribsul",   "forn123",    "Distribuidora Sul",     "fornecedor", "Distribuidora Sul"),
        ("merccentral",  "forn123",    "Mercado Central",       "fornecedor", "Mercado Central"),
    ]
    for login, senha, nome, perfil, empresa in demos:
        criar_usuario(login, senha, nome, perfil, empresa)