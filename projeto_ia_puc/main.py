import streamlit as st
import json
import pandas as pd
import numpy as np
import extrator
import ia_engine
import validador
import database
import previsao_clima
import gerador_nf

# ==========================================
# 1. INICIALIZAÇÃO E MEMÓRIA DO SISTEMA
# ==========================================
database.criar_banco()

if "carrinho_compras" not in st.session_state:
    st.session_state["carrinho_compras"] = []
if "tela_atual" not in st.session_state:
    st.session_state["tela_atual"] = "home"
if "pedido_emitido" not in st.session_state:
    st.session_state["pedido_emitido"] = False
if "dados_finais_pedido" not in st.session_state:
    st.session_state["dados_finais_pedido"] = {}

st.set_page_config(page_title="IA Suprimentos", page_icon="🤖", layout="wide")
st.title("🤖 Agente IA Logístico - Torre de Controlo")
st.markdown("---")

# ==========================================
# TELA 0: HOME
# ==========================================
if st.session_state["tela_atual"] == "home":
    st.markdown("### Bem-vindo(a)! O que deseja fazer na operação hoje?")
    st.write("Selecione um dos módulos abaixo para iniciar o fluxo logístico.")
    st.write("") 
    
    col_in, col_out, col_hist = st.columns(3)
    
    with col_in:
        st.info("#### 📥 INBOUND (Receber)\n\nEntrada de mercadorias. Faça o upload de uma Nota Fiscal e extraia os dados com IA.")
        if st.button("Módulo de Recebimento", use_container_width=True):
            st.session_state["tela_atual"] = "inbound"
            st.rerun()
            
    with col_out:
        st.success("#### 📝 OUTBOUND (Emitir)\n\nSaída de mercadorias. Crie um novo pedido, emita o DANFE e preveja riscos na rota.")
        if st.button("Módulo de Emissão", use_container_width=True):
            st.session_state["tela_atual"] = "outbound"
            st.rerun()
            
    with col_hist:
        st.warning("#### 🗄️ HISTÓRICO (Dashboard)\n\nConsulte a base de dados. Veja todos os pedidos e notas processadas e valores operacionais.")
        if st.button("Módulo de Histórico", use_container_width=True):
            st.session_state["tela_atual"] = "historico"
            st.rerun()

# ==========================================
# TELA 1: FLUXO DE RECEBIMENTO (INBOUND)
# ==========================================
elif st.session_state["tela_atual"] == "inbound":
    if st.button("⬅️ Voltar ao Menu Principal"):
        st.session_state["tela_atual"] = "home"
        st.rerun()
        
    st.markdown("---")
    st.subheader("📥 Recebimento Inteligente de Notas Fiscais")
    upload = st.file_uploader("Faça upload da Nota Fiscal (PDF)", type="pdf")

    if upload:
        with open("temp.pdf", "wb") as f:
            f.write(upload.getbuffer())
        
        with st.status("A analisar Documento...", expanded=True) as status:
            st.write("🔍 A aplicar Visão Computacional (OCR)...")
            texto = extrator.obter_texto_pdf("temp.pdf")
            
            st.write("⚡ A extrair dados com IA Otimizada...")
            # Prompt Otimizado (One-Shot) para maior velocidade
            prompt_extracao = f"""
Você é um extrator de dados logísticos. Leia a nota fiscal abaixo e retorne EXCLUSIVAMENTE um objeto JSON válido. 
Não adicione markdown (```json), explicações ou textos fora das chaves.
As chaves devem ser exatamente estas: "fornecedor", "cnpj", "valor_total", "data_emissao".

Nota Fiscal:
{texto}
"""
            json_str = ia_engine.chamar_modelo("nvidia/nemotron-3-super-120b-a12b:free", prompt_extracao)
            
            try:
                json_limpo = json_str.replace('```json', '').replace('```', '').strip()
                dados = json.loads(json_limpo)
                status.update(label="Processamento Concluído!", state="complete", expanded=False)
            except Exception as e:
                st.error("Erro ao processar resposta da IA.")
                st.stop()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📄 Dados Extraídos")
            st.write(f"**Fornecedor:** {dados.get('fornecedor')}")
            st.write(f"**CNPJ:** {dados.get('cnpj')}")
            st.write(f"**Data:** {dados.get('data_emissao')}")
            st.info(f"💰 **Valor LIDO: R$ {dados.get('valor_total', 0)}**")

        with col2:
            st.subheader("⚖️ Validação de Compliance")
            status_val, motivo = validador.validar_logistica(dados)
            if status_val == "APROVADA":
                st.success(f"**Status:** {status_val}")
                st.balloons()
            else:
                st.warning(f"**Status:** {status_val}")
            st.write(f"**Parecer:** {motivo}")
            database.salvar_nota(dados, status_val, motivo)

# ==========================================
# TELA 2: FLUXO DE EMISSÃO E PÓS-VENDA (OUTBOUND)
# ==========================================
elif st.session_state["tela_atual"] == "outbound":
    
    # FASE DO CARRINHO
    if not st.session_state["pedido_emitido"]:
        if st.button("⬅️ Cancelar e Voltar"):
            st.session_state["tela_atual"] = "home"
            st.session_state["carrinho_compras"] = []
            st.rerun()
            
        st.markdown("---")
        st.subheader("📝 1. Montagem do Pedido")
        
        catalogo_produtos = {
            # --- FRUTAS E VERDURAS ---
            "Maçã Gala (Caixa 18kg)": {"categoria": "Frutas Frescas", "preco": 120.00},
            "Pera Williams (Caixa 20kg)": {"categoria": "Frutas Frescas", "preco": 150.00},
            "Banana Nanica (Caixa 20kg)": {"categoria": "Frutas Frescas", "preco": 85.00},
            "Laranja Pera (Saco 20kg)": {"categoria": "Frutas Frescas", "preco": 50.00},
            "Morango (Caixa 4 bandejas)": {"categoria": "Frutas Frescas", "preco": 30.00},
            "Uva Thompson (Caixa 5kg)": {"categoria": "Frutas Frescas", "preco": 75.00},
            "Manga Palmer (Caixa 6kg)": {"categoria": "Frutas Frescas", "preco": 45.00},
            "Melancia (Unidade ~10kg)": {"categoria": "Frutas Frescas", "preco": 25.00},
            "Abacaxi Pérola (Caixa 15 un)": {"categoria": "Frutas Frescas", "preco": 65.00},
            "Limão Tahiti (Saco 20kg)": {"categoria": "Frutas Frescas", "preco": 40.00},
            "Alface Crespa (Caixa 24 un)": {"categoria": "Frutas Frescas", "preco": 35.00},
            "Tomate Carmem (Caixa 20kg)": {"categoria": "Frutas Frescas", "preco": 110.00},
            "Cebola Pera (Saco 20kg)": {"categoria": "Frutas Frescas", "preco": 80.00},
            "Batata Lavada (Saco 50kg)": {"categoria": "Frutas Frescas", "preco": 150.00},
            "Cenoura Suja (Caixa 20kg)": {"categoria": "Frutas Frescas", "preco": 70.00},
            "Brócolis Ninja (Caixa 10 un)": {"categoria": "Frutas Frescas", "preco": 45.00},
            "Pimentão Verde (Caixa 10kg)": {"categoria": "Frutas Frescas", "preco": 55.00},

            # --- CARNES E CONGELADOS ---
            "Carne Bovina - Alcatra (Kg)": {"categoria": "Carnes/Congelados", "preco": 35.00},
            "Carne Bovina - Picanha (Peça 1.5kg)": {"categoria": "Carnes/Congelados", "preco": 110.00},
            "Carne Bovina - Patinho (Kg)": {"categoria": "Carnes/Congelados", "preco": 32.00},
            "Carne Bovina - Costela (Kg)": {"categoria": "Carnes/Congelados", "preco": 22.00},
            "Carne Suína - Costelinha (Kg)": {"categoria": "Carnes/Congelados", "preco": 28.00},
            "Carne Suína - Lombo (Kg)": {"categoria": "Carnes/Congelados", "preco": 25.00},
            "Frango Inteiro Congelado (Caixa 20kg)": {"categoria": "Carnes/Congelados", "preco": 160.00},
            "Peito de Frango / Filé (Caixa 15kg)": {"categoria": "Carnes/Congelados", "preco": 195.00},
            "Filé de Tilápia Congelado (Caixa 10kg)": {"categoria": "Carnes/Congelados", "preco": 320.00},
            "Salmão Chileno (Peça Inteira Kg)": {"categoria": "Carnes/Congelados", "preco": 75.00},
            "Hambúrguer Bovino (Caixa 36 un)": {"categoria": "Carnes/Congelados", "preco": 95.00},

            # --- ELETRÔNICOS E CARGA SECA ---
            "Notebook Dell Inspiron": {"categoria": "Eletrônicos/Vidro", "preco": 4500.00},
            "Monitor LG 27 Pol": {"categoria": "Eletrônicos/Vidro", "preco": 1200.00},
            "Smart TV Samsung 50 Pol": {"categoria": "Eletrônicos/Vidro", "preco": 2300.00},
            "Soja em Grãos (Saca 60kg)": {"categoria": "Carga Seca", "preco": 135.00},
            "Milho em Grãos (Saca 60kg)": {"categoria": "Carga Seca", "preco": 85.00},
            "Cimento Votorantim (Saco 50kg)": {"categoria": "Carga Seca", "preco": 32.00}
        }
        
        col_emissor, col_carrinho = st.columns(2)
        with col_emissor:
            novo_fornecedor = st.text_input("Emissor da Nota", value="Distribuidora Padrão LTDA")
            novo_cnpj = st.text_input("CNPJ", value="00.000.000/0001-00")
            
        with col_carrinho:
            produto_selecionado = st.selectbox("Selecione o Produto", list(catalogo_produtos.keys()))
            quantidade = st.number_input("Quantidade", min_value=1, value=5, step=1)
            if st.button("➕ Adicionar ao Pedido", use_container_width=True):
                preco_u = catalogo_produtos[produto_selecionado]["preco"]
                st.session_state["carrinho_compras"].append({
                    "produto": produto_selecionado,
                    "quantidade": quantidade,
                    "preco_unitario": preco_u,
                    "total": preco_u * quantidade,
                    "categoria": catalogo_produtos[produto_selecionado]["categoria"]
                })
                st.rerun()

        st.markdown("#### 🛒 Resumo do Pedido")
        if len(st.session_state["carrinho_compras"]) > 0:
            df_carrinho = pd.DataFrame(st.session_state["carrinho_compras"])
            valor_total_pedido = df_carrinho['total'].sum()
            
            df_visual = df_carrinho[['quantidade', 'produto', 'preco_unitario', 'total']].copy()
            df_visual['preco_unitario'] = df_visual['preco_unitario'].apply(lambda x: f"R$ {x:,.2f}")
            df_visual['total'] = df_visual['total'].apply(lambda x: f"R$ {x:,.2f}")
            st.table(df_visual)
            st.info(f"💰 **VALOR TOTAL: R$ {valor_total_pedido:,.2f}**")
            
            if st.button("🚀 Confirmar e Emitir NF", type="primary", use_container_width=True):
                with st.spinner("A desenhar Nota e a Guardar na Base de Dados..."):
                    img_path, data_emissao = gerador_nf.criar_imagem_nf(novo_fornecedor, novo_cnpj, st.session_state["carrinho_compras"], valor_total_pedido)
                    
                    # SALVA NO BANCO DE DADOS
                    dados_mock = {
                        "fornecedor": novo_fornecedor,
                        "cnpj": novo_cnpj,
                        "data_emissao": data_emissao,
                        "valor_total": valor_total_pedido
                    }
                    status_val, motivo = validador.validar_logistica(dados_mock)
                    database.salvar_nota(dados_mock, status_val, motivo)
                    
                    st.session_state["dados_finais_pedido"] = {
                        "img_path": img_path,
                        "valor_total": valor_total_pedido,
                        "categoria_principal": st.session_state["carrinho_compras"][0]["categoria"]
                    }
                    st.session_state["pedido_emitido"] = True
                    st.rerun()

    # FASE DE ROTEAMENTO (Checkout)
    else:
        st.success("✅ **PEDIDO CONFIRMADO E NOTA FISCAL EMITIDA!** O registo foi gravado na base de dados.")
        st.markdown("---")
        
        col_nf, col_logistica = st.columns([1, 1.2])
        with col_nf:
            st.subheader("📄 DANFE")
            st.image(st.session_state["dados_finais_pedido"]["img_path"], use_container_width=True)
            
        with col_logistica:
            st.subheader("🚚 2. Roteamento e Seguro de Carga")
            st.info(f"**Categoria da Carga:** {st.session_state['dados_finais_pedido']['categoria_principal']}")
            cidade_destino = st.text_input("Cidade de Destino", value="Manaus")
            dias_entrega = st.number_input("Tempo de Viagem Estimado (Dias SLA)", min_value=1, max_value=30, value=5)
            
            if st.button("📡 Consultar Satélite e Calcular Seguro", type="primary"):
                with st.spinner("A procurar dados meteorológicos..."):
                    clima, erro = previsao_clima.obter_clima(cidade_destino)
                    
                if erro:
                    st.error(erro)
                else:
                    categoria = st.session_state["dados_finais_pedido"]["categoria_principal"]
                    
                    if categoria == "Frutas Frescas":
                        risco_diario = 1.5 if clima['temperatura'] <= 28 else 3.5
                    elif categoria == "Carnes/Congelados":
                        risco_diario = 1.2 if clima['temperatura'] <= 30 else 4.0
                    elif categoria == "Eletrônicos/Vidro":
                        risco_diario = 0.8 if "Chuva" not in clima['condicao'] else 2.5
                    else:
                        risco_diario = 0.3
                        
                    fator_clima = clima.get('fator_risco', 1.0)
                    
                    perda_final_pct = 0.5 + (dias_entrega * risco_diario * fator_clima * 0.8)
                    perda_final_pct = np.clip(perda_final_pct, 0, 100)
                    
                    valor_da_nota = st.session_state["dados_finais_pedido"]["valor_total"]
                    prejuizo = valor_da_nota * (perda_final_pct / 100)
                    
                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Clima Destino", f"{clima['temperatura']}°C", clima['condicao'], delta_color="off")
                    c2.metric("Perda Estimada", f"{perda_final_pct:.1f}%")
                    c3.metric("Reembolso Previsto", f"R$ -{prejuizo:,.2f}", delta_color="inverse")
                    
                    if perda_final_pct > 15:
                        st.error(f"🚨 **CARGA EM RISCO CRÍTICO:** O clima extremo pode causar perda de R$ {prejuizo:,.2f}.")
                    else:
                        st.success("✅ Rota considerada segura.")
                        
        st.markdown("---")
        if st.button("🔄 Finalizar Operação e Voltar ao Início", type="primary", use_container_width=True):
            st.session_state["pedido_emitido"] = False
            st.session_state["carrinho_compras"] = []
            st.session_state["dados_finais_pedido"] = {}
            st.session_state["tela_atual"] = "home"
            st.rerun()

# ==========================================
# TELA 3: HISTÓRICO DE OPERAÇÕES
# ==========================================
elif st.session_state["tela_atual"] == "historico":
    if st.button("⬅️ Voltar ao Menu Principal"):
        st.session_state["tela_atual"] = "home"
        st.rerun()
        
    st.markdown("---")
    st.subheader("🗄️ Histórico de Operações (Dashboard Financeiro)")
    st.write("Abaixo está a listagem de todos os pedidos processados e notas armazenadas na Base de Dados SQLite.")
    
    dados_historico = database.obter_historico()
    
    if len(dados_historico) == 0:
        st.info("Nenhuma operação registada na base de dados ainda.")
    else:
        df_historico = pd.DataFrame(dados_historico)
        
        total_notas = len(df_historico)
        valor_total_movimentado = df_historico['Valor Total'].sum()
        notas_aprovadas = len(df_historico[df_historico['Status'] == 'APROVADA'])
        taxa_aprovacao = (notas_aprovadas / total_notas) * 100 if total_notas > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📦 Volume de Operações", f"{total_notas} Notas")
        c2.metric("💰 Faturamento Total", f"R$ {valor_total_movimentado:,.2f}")
        c3.metric("✅ Taxa de Conformidade", f"{taxa_aprovacao:.1f}%")
        
        st.markdown("---")
        df_visual = df_historico.copy()
        df_visual['Valor Total'] = df_visual['Valor Total'].apply(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_visual, use_container_width=True, hide_index=True)