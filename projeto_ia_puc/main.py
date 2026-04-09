"""
main.py — ERP Logística Visionary
Interface principal em Streamlit.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import sqlite3
from datetime import datetime

import database
import ia_engine

# ══════════════════════════════════════════════════════
#  CONFIGURAÇÃO DA PÁGINA
# ══════════════════════════════════════════════════════
st.set_page_config(
    page_title="ERP Logística Visionary",
    layout="wide",
    page_icon="📦",
    initial_sidebar_state="expanded",
)

# CSS global — pequenos ajustes visuais para deixar o sistema com cara de ERP Profissional
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    [data-testid="stSidebar"] { background: #0f172a; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] hr { border-color: #334155; }
    div[data-testid="metric-container"] {
        background: #1e293b; border-radius: 12px;
        padding: 16px; border: 1px solid #334155;
    }
    div[data-testid="metric-container"] label { color: #94a3b8 !important; font-weight: 600; }
    div[data-testid="metric-container"] div { color: #f8fafc !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
#  INICIALIZAÇÃO E ESTADO DA SESSÃO
# ══════════════════════════════════════════════════════
# Força a criação das tabelas e a injeção dos 100 produtos se o banco estiver vazio
database.configurar_ambiente()

if "tela_atual" not in st.session_state:
    st.session_state["tela_atual"] = "home"
if "carrinho_compras" not in st.session_state:
    st.session_state["carrinho_compras"] = []
if "nota_fiscal_gerada" not in st.session_state:
    st.session_state["nota_fiscal_gerada"] = None


# ══════════════════════════════════════════════════════
#  FUNÇÕES AUXILIARES LOGÍSTICAS
# ══════════════════════════════════════════════════════
def calcular_metricas_item(item, regiao_cliente):
    """Calcula tempo, perda e reembolso baseado na logística de São Paulo."""
    fornecedores = database.obter_fornecedores()
    f_info = next((f for f in fornecedores if f['nome'] == item['fornecedor_origem']), {})
    
    regiao_origem = f_info.get("regiao", "Centro")
    categoria = item.get("categoria", "Geral")
    
    # Matriz de Tempo Logístico
    if regiao_origem == regiao_cliente:
        dias = 1
        risco_perda = 0.01 
    else:
        dias = 3
        risco_perda = 0.05 
        
    # Eletrônicos não estragam como frutas
    if categoria == "Eletrônicos":
        risco_perda = 0.005 
        
    perda_financeira = item['subtotal'] * risco_perda
    reembolso_provavel = perda_financeira * 0.8 
    
    return dias, perda_financeira, reembolso_provavel

def cadastrar_produto_local(nome, cat, preco, unid, forn):
    """Função auxiliar para inserir produtos diretamente no banco de cadastros via Interface."""
    conn = sqlite3.connect("db_cadastros.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO Produtos_Catalogo (nome, categoria, preco_base, unidade, fornecedor_nome) VALUES (?, ?, ?, ?, ?)', 
            (nome, cat, preco, unid, forn)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# ══════════════════════════════════════════════════════
#  MENU LATERAL (SIDEBAR)
# ══════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2760/2760114.png", width=80)
    st.title("📦 ERP Visionary")
    st.markdown("---")
    
    if st.button("🤖 Torre de Comando", use_container_width=True): 
        st.session_state["tela_atual"] = "home"
    if st.button("📥 Inbound (Auto-Roteamento)", use_container_width=True): 
        st.session_state["tela_atual"] = "inbound"
    if st.button("📤 Outbound (Pedidos & DANFE)", use_container_width=True): 
        st.session_state["tela_atual"] = "outbound"
    if st.button("🗃️ Cadastros & Catálogo", use_container_width=True): 
        st.session_state["tela_atual"] = "cadastros"
    if st.button("📊 BI & Dashboard", use_container_width=True): 
        st.session_state["tela_atual"] = "historico"


# ══════════════════════════════════════════════════════
#  TELA 1: TORRE DE COMANDO (CHAT IA)
# ══════════════════════════════════════════════════════
if st.session_state["tela_atual"] == "home":
    st.title("🤖 Torre de Comando de Supply Chain")
    st.write("Visão holística ativada. Monitoramento em tempo real do banco de dados relacional SQL.")
    
    if "mensagens_agente" not in st.session_state:
        st.session_state["mensagens_agente"] = [
            {"role": "assistant", "content": "Olá! O banco está populado com mais de 100 produtos. Pode me perguntar sobre as rotas, fornecedores e furos logísticos."}
        ]

    for msg in st.session_state["mensagens_agente"]:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"): 
            st.markdown(msg["content"])

    if prompt_usuario := st.chat_input("Ex: Quantos produtos temos no catálogo?"):
        st.session_state["mensagens_agente"].append({"role": "user", "content": prompt_usuario})
        with st.chat_message("user", avatar="👤"): 
            st.markdown(prompt_usuario)
            
        contexto_completo = {
            "stats": database.obter_estatisticas(),
            "pedidos": database.obter_historico(),
            "fornecedores": database.obter_fornecedores(),
            "catalogo": database.obter_produtos()
        }
        
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Lendo tabelas e relacionamentos SQL via API NVIDIA..."):
                contexto_ia = ia_engine.construir_contexto_banco(contexto_completo)
                resposta_ia = ia_engine.conversar_com_agente(st.session_state["mensagens_agente"], contexto_ia)
                st.markdown(resposta_ia)
        st.session_state["mensagens_agente"].append({"role": "assistant", "content": resposta_ia})


# ══════════════════════════════════════════════════════
#  TELA 2: INBOUND (PROCESSAMENTO DE NF)
# ══════════════════════════════════════════════════════
elif st.session_state["tela_atual"] == "inbound":
    st.title("📥 Inbound - Processamento Inteligente")
    st.write("A IA lê a nota e descobre a origem cruzando o item com o nosso Catálogo.")
    
    arquivo = st.file_uploader("Upload da NF (PDF/Imagem)", type=["pdf", "png", "jpg", "jpeg"])
    
    if arquivo and st.button("Processar Documento e Auditar", type="primary"):
        with st.spinner("Extraindo dados com Nemotron/Llama Vision..."):
            dados_extraidos = ia_engine.processar_nota(arquivo)
            
            if dados_extraidos:
                produtos_db = database.obter_produtos()
                nome_fornecedor = "Desconhecido (Requer Cadastro)"
                
                if dados_extraidos.get("itens") and len(dados_extraidos["itens"]) > 0:
                    produto_nf = dados_extraidos["itens"][0].get("produto", "")
                    
                    for p in produtos_db:
                        if p["nome"].lower() in produto_nf.lower() or produto_nf.lower() in p["nome"].lower():
                            nome_fornecedor = p["fornecedor_nome"]
                            break
                
                dados_extraidos["Fornecedor"] = nome_fornecedor
                st.success(f"🎯 Roteamento Automático: Nota vinculada ao hub **{nome_fornecedor}**")
                
                st.subheader("📄 Dados Extraídos")
                st.json(dados_extraidos)
                
                # AUDITORIA FINANCEIRA
                soma_itens = sum([float(i.get('subtotal', 0)) for i in dados_extraidos.get('itens', [])])
                valor_total_nf = float(dados_extraidos.get('valor_total', 0))
                prejuizo = abs(soma_itens - valor_total_nf)
                
                st.markdown("---")
                if prejuizo < 0.05:
                    st.success("✅ Compliance Financeiro OK.")
                    dados_extraidos["prejuizo_estimado"] = 0.0
                    dados_extraidos["tempo_chegada_dias"] = 2
                    database.salvar_operacao(dados_extraidos, status="APROVADA")
                    st.balloons()
                else:
                    st.error(f"⚠️ Alerta de Divergência: Encontrado um furo de R$ {prejuizo:,.2f} nesta nota.")
                    if st.button("Registrar Operação com Divergência"):
                        dados_extraidos["prejuizo_estimado"] = prejuizo
                        dados_extraidos["tempo_chegada_dias"] = 6
                        database.salvar_operacao(dados_extraidos, status="BLOQUEADA")
                        st.warning("Salvo como 'Bloqueada'.")
            else:
                st.error("Falha ao extrair os dados da Nota Fiscal. Verifique se o documento está legível.")


# ══════════════════════════════════════════════════════
#  TELA 3: OUTBOUND (EMISSÃO DE PEDIDOS & DANFE)
# ══════════════════════════════════════════════════════
elif st.session_state["tela_atual"] == "outbound":
    st.title("📤 Outbound - Emissão de Pedidos e Roteamento")
    
    if not st.session_state["nota_fiscal_gerada"]:
        regioes_sp = ["Zona Norte", "Zona Sul", "Zona Leste", "Zona Oeste", "Centro"]
        regiao_destino = st.selectbox("📍 Para qual região vai o pedido?", regioes_sp)
        
        produtos_db = database.obter_produtos()
        nomes_prods = [p["nome"] for p in produtos_db]
        
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            st.subheader("🛒 Carrinho de Compras")
            prod_sel = st.selectbox("Selecione o Produto", nomes_prods)
            qtd = st.number_input("Quantidade", min_value=1, step=1)
            
            if st.button("Adicionar Item"):
                p_db = next(p for p in produtos_db if p["nome"] == prod_sel)
                st.session_state["carrinho_compras"].append({
                    "produto": p_db["nome"],
                    "categoria": p_db["categoria"],
                    "fornecedor_origem": p_db["fornecedor_nome"],
                    "quantidade": qtd,
                    "preco_unitario": p_db["preco_base"],
                    "subtotal": qtd * p_db["preco_base"]
                })
                st.rerun()
                
        with col2:
            st.subheader("📈 Análise Prévia de Logística e Risco")
            if st.session_state["carrinho_compras"]:
                total_carrinho = 0
                for item in st.session_state["carrinho_compras"]:
                    dias, perda, reembolso = calcular_metricas_item(item, regiao_destino)
                    total_carrinho += item['subtotal']
                    st.info(f"**{item['produto']}** -> Distribuído por: {item['fornecedor_origem']}\n\n"
                            f"⏱️ Lead Time: {dias} dia(s) | 💸 Risco de Perda: R$ {perda:.2f}")
                
                st.markdown(f"### Total Bruto: R$ {total_carrinho:,.2f}")
                
                if st.button("Finalizar Compra e Gerar DANFE", type="primary", use_container_width=True):
                    resumo_pedido = []
                    for item in st.session_state["carrinho_compras"]:
                        d, p, r = calcular_metricas_item(item, regiao_destino)
                        resumo_pedido.append({
                            **item, 
                            "dias_entrega": d, 
                            "perda": p, 
                            "reembolso": r
                        })
                    
                    nf = {
                        "id_nf": f"NF-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "destino": regiao_destino,
                        "data_emissao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "itens": resumo_pedido,
                        "valor_total": sum(i['subtotal'] for i in resumo_pedido),
                        "prejuizo_estimado": sum(i['perda'] for i in resumo_pedido)
                    }
                    database.salvar_operacao(nf, status="EMITIDA")
                    st.session_state["nota_fiscal_gerada"] = nf
                    st.session_state["carrinho_compras"] = []
                    st.rerun()
            else:
                st.info("Aguardando produtos no carrinho para calcular rotas.")
    else:
        nf = st.session_state["nota_fiscal_gerada"]
        st.success("✅ Roteamento concluído e Nota Fiscal Emitida com sucesso no Banco Operacional!")
        
        # --- MÁGICA DO VISUAL DE DOCUMENTO IMPRESSO (DANFE) ---
        linhas_tabela = ""
        for item in nf['itens']:
            linhas_tabela += f"""
            <tr>
                <td style='padding: 10px; border-bottom: 1px solid #ddd;'>{item['produto']}</td>
                <td style='padding: 10px; border-bottom: 1px solid #ddd;'>{item['fornecedor_origem']}</td>
                <td style='padding: 10px; border-bottom: 1px solid #ddd; text-align: center;'>{item['quantidade']}</td>
                <td style='padding: 10px; border-bottom: 1px solid #ddd; text-align: center;'>{item['dias_entrega']}</td>
                <td style='padding: 10px; border-bottom: 1px solid #ddd; text-align: right;'>R$ {item['subtotal']:,.2f}</td>
            </tr>
            """

        html_nota_fiscal = f"""
        <html>
        <head>
            <style>
                body {{
                    background-color: transparent;
                    margin: 0;
                    padding: 0;
                }}
                .danfe-container {{
                    background-color: #ffffff; 
                    color: #000000; 
                    padding: 40px; 
                    font-family: 'Courier New', Courier, monospace; 
                    border: 1px solid #ccc; 
                    border-radius: 4px; 
                    max-width: 100%; 
                    margin: 10px; 
                    box-shadow: 5px 5px 15px rgba(0,0,0,0.1);
                }}
                h2 {{ margin: 0; font-family: Arial, sans-serif; letter-spacing: 1px; }}
            </style>
        </head>
        <body>
            <div class="danfe-container">
                <div style="text-align: center; border-bottom: 2px dashed #000; padding-bottom: 15px; margin-bottom: 20px;">
                    <h2>DANFE SIMPLIFICADO</h2>
                    <p style="margin: 0; font-size: 12px; color: #555;">Documento Auxiliar da Nota Fiscal Eletrônica de Logística</p>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 20px; font-size: 14px; border-bottom: 1px solid #000; padding-bottom: 15px;">
                    <div><strong>CHAVE / Nº:</strong><br>{nf['id_nf']}</div>
                    <div><strong>DATA DE EMISSÃO:</strong><br>{nf['data_emissao']}</div>
                    <div><strong>DESTINO:</strong><br>{nf['destino']}</div>
                </div>

                <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 30px;">
                    <thead>
                        <tr style="background-color: #f4f4f4; border-bottom: 2px solid #000; text-align: left;">
                            <th style="padding: 10px;">PRODUTO</th>
                            <th style="padding: 10px;">ORIGEM (HUB)</th>
                            <th style="padding: 10px; text-align: center;">QTD</th>
                            <th style="padding: 10px; text-align: center;">DIAS</th>
                            <th style="padding: 10px; text-align: right;">SUBTOTAL</th>
                        </tr>
                    </thead>
                    <tbody>
                        {linhas_tabela}
                    </tbody>
                </table>

                <div style="border-top: 2px dashed #000; padding-top: 20px; text-align: right;">
                    <h2>TOTAL DA NOTA: R$ {nf['valor_total']:,.2f}</h2>
                    <p style="margin: 8px 0 0 0; color: #d9534f; font-weight: bold; font-size: 16px;">
                        ⚠️ Prejuízo Logístico Est.: R$ {nf['prejuizo_estimado']:,.2f}
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 40px; font-size: 11px; color: #888; border-top: 1px solid #eee; padding-top: 10px;">
                    Gerado via ERP Visionary - Agente Autônomo<br>
                    Consulte a autenticidade no banco SQLite local.
                </div>
            </div>
        </body>
        </html>
        """
        
        components.html(html_nota_fiscal, height=550, scrolling=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Emitir Nova Nota"):
            st.session_state["nota_fiscal_gerada"] = None
            st.rerun()


# ══════════════════════════════════════════════════════
#  TELA 4: CADASTROS (PRODUTOS E FORNECEDORES)
# ══════════════════════════════════════════════════════
elif st.session_state["tela_atual"] == "cadastros":
    st.title("🗃️ Gestão de Cadastros e Catálogo")
    st.write("Gerencie os dados mestres do sistema (Master Data).")
    
    tab_forn, tab_prod = st.tabs(["🏢 Fornecedores", "📦 Produtos"])
    
    with tab_forn:
        st.subheader("Fornecedores Ativos")
        fornecedores = database.obter_fornecedores()
        if fornecedores:
            df_f = pd.DataFrame(fornecedores).drop(columns=["id", "ativo"], errors="ignore")
            st.dataframe(df_f, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum fornecedor cadastrado.")
            
    with tab_prod:
        st.subheader("Catálogo de Produtos")
        prods = database.obter_produtos()
        if prods:
            df_p = pd.DataFrame(prods).drop(columns=["id", "ativo", "criado_em"], errors="ignore")
            st.dataframe(df_p, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum produto cadastrado.")

        with st.expander("➕ Cadastrar Novo Produto"):
            fornec_nomes = [f["nome"] for f in database.obter_fornecedores()]
            with st.form("form_produto"):
                nome_p  = st.text_input("Nome do Produto")
                cat_p   = st.text_input("Categoria")
                preco_p = st.number_input("Preço Base (R$)", min_value=0.01, value=10.00, step=0.5)
                unid_p  = st.text_input("Unidade (ex: un, kg, sc)", value="un")
                forn_p  = st.selectbox("Fornecedor (Relacional)", fornec_nomes) if fornec_nomes else st.text_input("Fornecedor")
                
                if st.form_submit_button("Salvar no Banco", type="primary"):
                    if nome_p and forn_p:
                        sucesso = cadastrar_produto_local(nome_p, cat_p, preco_p, unid_p, forn_p)
                        if sucesso:
                            st.success("✅ Produto cadastrado com sucesso! Atualize a página para ver na tabela.")
                        else:
                            st.error("⚠️ Erro: Produto já existe ou fornecedor inválido.")
                    else:
                        st.error("Informe o nome do produto e do fornecedor.")


# ══════════════════════════════════════════════════════
#  TELA 5: DASHBOARD HISTÓRICO (BI)
# ══════════════════════════════════════════════════════
elif st.session_state["tela_atual"] == "historico":
    st.title("📊 Business Intelligence")
    st.write("Métricas em tempo real extraídas do Banco Operacional.")
    
    pedidos = database.obter_historico()
    
    if pedidos:
        df = pd.DataFrame(pedidos)
        df['Valor Total'] = pd.to_numeric(df.get('Valor Total', df.get('valor_total', 0)), errors='coerce').fillna(0)
        df['prejuizo_total_est'] = pd.to_numeric(df.get('prejuizo_total_est', 0), errors='coerce').fillna(0)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de NFs Emitidas", f"{len(df)} Docs")
        c2.metric("Volume Financeiro Bruto", f"R$ {df['Valor Total'].sum():,.2f}")
        c3.metric("Furos/Perdas (Risco)", f"R$ {df['prejuizo_total_est'].sum():,.2f}", delta_color="inverse")
        
        st.markdown("---")
        df_display = df.drop(columns=['itens'], errors='ignore')
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Relatório SQL Completo", data=csv, file_name='db_logistica_operacional.csv', mime='text/csv')
    else:
        st.info("Banco de dados Operacional vazio. Faça movimentações no Inbound ou Outbound.")