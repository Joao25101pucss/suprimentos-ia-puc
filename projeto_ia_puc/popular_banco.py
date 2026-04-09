"""
popular_banco.py — Script para popular o banco de Cadastros (Produtos e Fornecedores)
Rode este arquivo UMA ÚNICA VEZ para injetar 100 produtos variados.
"""

import sqlite3
import random

DB_CADASTROS = "db_cadastros.db"

def popular_dados_iniciais():
    conn = sqlite3.connect(DB_CADASTROS)
    cursor = conn.cursor()

    # 1. Garantir que os Fornecedores básicos existem (baseado no seu setup inicial)
    fornecedores_base = [
        ("Frigorífico Norte", "00.111.222/0001-01", "Zona Norte", "Carnes", -23.50, -46.60),
        ("Hortifruti Leste", "00.333.444/0001-02", "Zona Leste", "Frutas e Verduras", -23.54, -46.45),
        ("Tech Hub Oeste", "00.555.666/0001-03", "Zona Oeste", "Eletrônicos", -23.53, -46.70),
        ("Distribuidora Sul", "00.777.888/0001-04", "Zona Sul", "Geral", -23.65, -46.68),
        ("Mercado Central", "00.999.000/0001-05", "Centro", "Geral", -23.55, -46.63)
    ]

    for f in fornecedores_base:
        try:
            cursor.execute('''
                INSERT INTO Fornecedores (nome, cnpj, regiao, categoria, latitude, longitude, ativo)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', f)
        except sqlite3.IntegrityError:
            pass # Ignora se o fornecedor já existir

    # 2. Lista massiva de 100 Produtos
    produtos = [
        # --- CARNES (Frigorífico Norte) ---
        ("Picanha Bovina Premium", "Carnes", 89.90, "kg", "Frigorífico Norte"),
        ("Alcatra em Peça", "Carnes", 45.50, "kg", "Frigorífico Norte"),
        ("Maminha Bovina", "Carnes", 42.00, "kg", "Frigorífico Norte"),
        ("Fraldinha Bovina", "Carnes", 38.90, "kg", "Frigorífico Norte"),
        ("Contrafilé Resfriado", "Carnes", 48.00, "kg", "Frigorífico Norte"),
        ("Acém Moído", "Carnes", 29.90, "kg", "Frigorífico Norte"),
        ("Peito Bovino", "Carnes", 25.50, "kg", "Frigorífico Norte"),
        ("Costela Bovina Ripão", "Carnes", 22.90, "kg", "Frigorífico Norte"),
        ("Cupim Bovino", "Carnes", 34.90, "kg", "Frigorífico Norte"),
        ("Lagarto Redondo", "Carnes", 36.50, "kg", "Frigorífico Norte"),
        ("Coxão Mole", "Carnes", 41.00, "kg", "Frigorífico Norte"),
        ("Coxão Duro", "Carnes", 37.50, "kg", "Frigorífico Norte"),
        ("Patinho em Cubos", "Carnes", 43.00, "kg", "Frigorífico Norte"),
        ("Músculo Traseiro", "Carnes", 28.00, "kg", "Frigorífico Norte"),
        ("Frango Inteiro Congelado", "Carnes", 12.90, "kg", "Frigorífico Norte"),
        ("Peito de Frango S/ Osso", "Carnes", 19.90, "kg", "Frigorífico Norte"),
        ("Coxinha da Asa", "Carnes", 18.50, "kg", "Frigorífico Norte"),
        ("Coração de Frango", "Carnes", 24.90, "kg", "Frigorífico Norte"),
        ("Pernil Suíno S/ Osso", "Carnes", 21.00, "kg", "Frigorífico Norte"),
        ("Costelinha Suína", "Carnes", 28.90, "kg", "Frigorífico Norte"),
        
        # --- HORTIFRUTI (Hortifruti Leste) ---
        ("Maçã Gala", "Frutas", 8.50, "kg", "Hortifruti Leste"),
        ("Maçã Fuji", "Frutas", 9.00, "kg", "Hortifruti Leste"),
        ("Banana Prata", "Frutas", 6.50, "kg", "Hortifruti Leste"),
        ("Banana Nanica", "Frutas", 5.00, "kg", "Hortifruti Leste"),
        ("Pera Williams", "Frutas", 12.00, "kg", "Hortifruti Leste"),
        ("Pera Portuguesa", "Frutas", 14.50, "kg", "Hortifruti Leste"),
        ("Uva Thompson S/ Semente", "Frutas", 18.00, "kg", "Hortifruti Leste"),
        ("Uva Niágara", "Frutas", 10.00, "kg", "Hortifruti Leste"),
        ("Morango Bandeja", "Frutas", 8.00, "un", "Hortifruti Leste"),
        ("Melão Amarelo", "Frutas", 7.50, "kg", "Hortifruti Leste"),
        ("Melancia Baby", "Frutas", 5.90, "kg", "Hortifruti Leste"),
        ("Mamão Papaya", "Frutas", 11.00, "kg", "Hortifruti Leste"),
        ("Mamão Formosa", "Frutas", 6.50, "kg", "Hortifruti Leste"),
        ("Abacate Avocado", "Frutas", 15.00, "kg", "Hortifruti Leste"),
        ("Limão Tahiti", "Frutas", 4.50, "kg", "Hortifruti Leste"),
        ("Laranja Pera", "Frutas", 3.50, "kg", "Hortifruti Leste"),
        ("Alface Crespa", "Verduras", 3.00, "un", "Hortifruti Leste"),
        ("Alface Americana", "Verduras", 4.50, "un", "Hortifruti Leste"),
        ("Rúcula Fresca", "Verduras", 4.00, "un", "Hortifruti Leste"),
        ("Agrião", "Verduras", 3.50, "un", "Hortifruti Leste"),
        ("Couve Manteiga", "Verduras", 3.00, "un", "Hortifruti Leste"),
        ("Espinafre", "Verduras", 4.50, "un", "Hortifruti Leste"),
        ("Tomate Carmem", "Legumes", 8.00, "kg", "Hortifruti Leste"),
        ("Tomate Cereja", "Legumes", 12.00, "kg", "Hortifruti Leste"),
        ("Cebola Branca", "Legumes", 5.50, "kg", "Hortifruti Leste"),
        ("Alho Nacional", "Legumes", 25.00, "kg", "Hortifruti Leste"),
        ("Batata Inglesa", "Legumes", 6.00, "kg", "Hortifruti Leste"),
        ("Batata Doce", "Legumes", 4.50, "kg", "Hortifruti Leste"),
        ("Cenoura", "Legumes", 5.00, "kg", "Hortifruti Leste"),
        ("Beterraba", "Legumes", 4.00, "kg", "Hortifruti Leste"),

        # --- ELETRÔNICOS (Tech Hub Oeste) ---
        ("Monitor Gamer 144Hz 24'", "Eletrônicos", 1250.00, "un", "Tech Hub Oeste"),
        ("Monitor UltraWide 29'", "Eletrônicos", 1500.00, "un", "Tech Hub Oeste"),
        ("Teclado Mecânico RGB", "Eletrônicos", 350.00, "un", "Tech Hub Oeste"),
        ("Teclado Membrana Office", "Eletrônicos", 80.00, "un", "Tech Hub Oeste"),
        ("Mouse Gamer 16000DPI", "Eletrônicos", 220.00, "un", "Tech Hub Oeste"),
        ("Mouse Sem Fio Ergonômico", "Eletrônicos", 110.00, "un", "Tech Hub Oeste"),
        ("Headset Gamer 7.1", "Eletrônicos", 280.00, "un", "Tech Hub Oeste"),
        ("Fone Bluetooth TWS", "Eletrônicos", 150.00, "un", "Tech Hub Oeste"),
        ("Placa Mãe B450M", "Eletrônicos", 600.00, "un", "Tech Hub Oeste"),
        ("Processador Ryzen 5", "Eletrônicos", 950.00, "un", "Tech Hub Oeste"),
        ("Processador Core i5", "Eletrônicos", 1050.00, "un", "Tech Hub Oeste"),
        ("Memória RAM 8GB DDR4", "Eletrônicos", 180.00, "un", "Tech Hub Oeste"),
        ("Memória RAM 16GB DDR4", "Eletrônicos", 320.00, "un", "Tech Hub Oeste"),
        ("SSD NVMe 500GB", "Eletrônicos", 280.00, "un", "Tech Hub Oeste"),
        ("SSD NVMe 1TB", "Eletrônicos", 450.00, "un", "Tech Hub Oeste"),
        ("Fonte 600W 80 Plus", "Eletrônicos", 350.00, "un", "Tech Hub Oeste"),
        ("Placa de Vídeo RTX 3060", "Eletrônicos", 2100.00, "un", "Tech Hub Oeste"),
        ("Gabinete ATX Vidro", "Eletrônicos", 250.00, "un", "Tech Hub Oeste"),
        ("Cabo HDMI 2.0 2m", "Eletrônicos", 35.00, "un", "Tech Hub Oeste"),
        ("Webcam Full HD 1080p", "Eletrônicos", 190.00, "un", "Tech Hub Oeste"),

        # --- GERAL / LIMPEZA (Distribuidora Sul) ---
        ("Detergente Neutro 500ml", "Limpeza", 2.50, "un", "Distribuidora Sul"),
        ("Sabão em Pó 1kg", "Limpeza", 14.90, "un", "Distribuidora Sul"),
        ("Amaciante 2L", "Limpeza", 12.00, "un", "Distribuidora Sul"),
        ("Água Sanitária 2L", "Limpeza", 5.50, "un", "Distribuidora Sul"),
        ("Desinfetante Pinho 1L", "Limpeza", 8.90, "un", "Distribuidora Sul"),
        ("Limpador Multiuso 500ml", "Limpeza", 4.50, "un", "Distribuidora Sul"),
        ("Esponja de Aço 8un", "Limpeza", 3.00, "un", "Distribuidora Sul"),
        ("Esponja Dupla Face 3un", "Limpeza", 5.00, "un", "Distribuidora Sul"),
        ("Saco de Lixo 100L 10un", "Limpeza", 9.00, "un", "Distribuidora Sul"),
        ("Papel Higiênico Folha Dupla 12un", "Higiene", 18.90, "un", "Distribuidora Sul"),
        ("Sabonete em Barra 90g", "Higiene", 2.20, "un", "Distribuidora Sul"),
        ("Creme Dental 90g", "Higiene", 4.50, "un", "Distribuidora Sul"),
        ("Shampoo 350ml", "Higiene", 12.00, "un", "Distribuidora Sul"),
        ("Condicionador 350ml", "Higiene", 14.00, "un", "Distribuidora Sul"),
        ("Desodorante Aerosol", "Higiene", 15.90, "un", "Distribuidora Sul"),

        # --- BEBIDAS E MERCEARIA (Mercado Central) ---
        ("Refrigerante Cola 2L", "Bebidas", 8.50, "un", "Mercado Central"),
        ("Refrigerante Guaraná 2L", "Bebidas", 7.50, "un", "Mercado Central"),
        ("Água Mineral S/ Gás 1.5L", "Bebidas", 3.00, "un", "Mercado Central"),
        ("Água Mineral C/ Gás 1.5L", "Bebidas", 3.50, "un", "Mercado Central"),
        ("Cerveja Pilsen Lata 350ml", "Bebidas", 3.90, "un", "Mercado Central"),
        ("Suco de Uva Integral 1L", "Bebidas", 14.00, "un", "Mercado Central"),
        ("Arroz Branco Tipo 1 5kg", "Mercearia", 25.90, "un", "Mercado Central"),
        ("Feijão Carioca 1kg", "Mercearia", 8.50, "un", "Mercado Central"),
        ("Feijão Preto 1kg", "Mercearia", 9.50, "un", "Mercado Central"),
        ("Açúcar Refinado 1kg", "Mercearia", 4.50, "un", "Mercado Central"),
        ("Café Torrado e Moído 500g", "Mercearia", 15.90, "un", "Mercado Central"),
        ("Óleo de Soja 900ml", "Mercearia", 6.50, "un", "Mercado Central"),
        ("Azeite Extra Virgem 500ml", "Mercearia", 28.90, "un", "Mercado Central"),
        ("Macarrão Espaguete 500g", "Mercearia", 4.50, "un", "Mercado Central"),
        ("Extrato de Tomate 340g", "Mercearia", 3.80, "un", "Mercado Central")
    ]

    produtos_inseridos = 0
    for p in produtos:
        try:
            cursor.execute('''
                INSERT INTO Produtos_Catalogo (nome, categoria, preco_base, unidade, fornecedor_nome, ativo)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', p)
            produtos_inseridos += 1
        except sqlite3.IntegrityError:
            pass # Produto já existe, ignora

    conn.commit()
    conn.close()
    
    print(f"✅ Banco populado com sucesso! {produtos_inseridos} produtos novos foram adicionados.")

if __name__ == "__main__":
    popular_dados_iniciais()