import streamlit as st
import pandas as pd
import json
import database
import ia_engine
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO INICIAL DA PÁGINA
# ==========================================
st.set_page_config(page_title="ERP Logística Inteligente", layout="wide", page_icon="📦")

# Inicialização de variáveis de sessão (Persistence)
if "tela_atual" not in st.session_state:
    st.session_state["tela_atual"] = "home"
if "carrinho_compras" not in st.session_state:
    st.session_state["carrinho_compras"] = []
if "pedido_emitido" not in st.session_state:
    st.session_state["pedido_emitido"] = False

# ==========================================
# MENU LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2760/2760114.png", width=80)
    st.title("Módulos ERP")
    st.markdown("---")
    
    if st.button("🤖 Torre de Comando (Agente)", use_container_width=True):
        st.session_state["tela_atual"] = "home"
    if st.button("📥 Inbound (Recebimento)", use_container_width=True):
        st.session_state["tela_atual"] = "inbound"
    if st.button("📤 Outbound (Emissão)", use_container_width=True):
        st.session_state["tela_atual"] = "outbound"
    if st.button("📊 Dashboard Histórico", use_container_width=True):
        st.session_state["tela_atual"] = "historico"

# ==========================================
# TELA 1: HOME (AGENTE DE IA COM ACESSO TOTAL)
# ==========================================
if st.session_state["tela_atual"] == "home":
    st.title("🤖 Agente Logístico Autônomo")
    st.write("Bem-vindo. Sou o copiloto deste ERP e analiso todos os dados de itens, prazos e prejuízos.")
    
    if "mensagens_agente" not in st.session_state:
        st.session_state["mensagens_agente"] = [
            {"role": "assistant", "content": "Olá! Estou conectado à base de dados. Posso detalhar produtos, calcular prejuízos e analisar tempos de entrega. O que você precisa?"}
        ]

    for msg in st.session_state["mensagens_agente"]:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    if prompt_usuario := st.chat_input("Perqunte sobre produtos, prejuízos ou prazos..."):
        st.session_state["mensagens_agente"].append({"role": "user", "content": prompt_usuario})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt_usuario)
            
        # EXTRAÇÃO DO BANCO COMPLETO PARA O AGENTE
        dados_historico = database.obter_historico() if hasattr(database, 'obter_historico') else []
        
        if dados_historico:
            # Transformamos o banco TODO em JSON para a IA ler as colunas novas
            contexto_dados = json.dumps(dados_historico, indent=2, ensure_ascii=False)
            contexto_sistema = f"""
            ESTES SÃO OS DADOS BRUTOS DO ERP (DUMP COMPLETO):
            {contexto_dados}
            
            DIRETRIZ: Responda usando os dados acima. Foque em detalhar 'itens', 'prejuizo_estimado' e 'tempo_chegada_dias'.
            """
        else:
            contexto_sistema = "Banco de dados vazio."

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analisando métricas de suprimentos..."):
                resposta = ia_engine.conversar_com_agente(st.session_state["mensagens_agente"], contexto_sistema)
                st.markdown(resposta)
        
        st.session_state["mensagens_agente"].append({"role": "assistant", "content": resposta})

# ==========================================
# TELA 2: INBOUND (CÁLCULOS E AUDITORIA)
# ==========================================
elif st.session_state["tela_atual"] == "inbound":
    st.title("📥 Inbound - Recebimento e Compliance")
    
    modelo_escolhido = st.selectbox("🧠 Motor de IA:", ["nvidia/nemotron-3-nano-30b-a3b:free", "google/gemini-2.0-flash-exp:free"])
    arquivo = st.file_uploader("Upload de Nota Fiscal", type=["pdf", "png", "jpg", "jpeg"])
    
    if arquivo:
        if st.button("Processar Documento", type="primary"):
            with st.spinner("IA extraindo dados e validando compliance..."):
                dados = ia_engine.processar_nota(arquivo, modelo_escolhido)
            
            if dados:
                st.subheader("📄 Dados Extraídos")
                st.json(dados)
                
                # CÁLCULOS LOGÍSTICOS (TABELANDO AS NOVAS COLUNAS)
                soma_itens = sum([float(i.get('subtotal', 0)) for i in dados.get('itens', [])])
                total_nf = float(dados.get('valor_total', 0))
                divergencia = abs(soma_itens - total_nf)
                
                # Simulando colunas de logística
                tempo_estimado = 3 # dias
                
                if divergencia < 0.05:
                    st.success(f"✅ Compliance OK! Soma: R$ {soma_itens:,.2f}")
                    if st.button("Salvar e Confirmar Entrada"):
                        dados["prejuizo_estimado"] = 0.0
                        dados["tempo_chegada_dias"] = tempo_estimado
                        database.salvar_operacao(dados, status="APROVADA")
                        st.balloons()
                else:
                    st.error(f"⚠️ Divergência de R$ {divergencia:,.2f} detectada!")
                    if st.button("Salvar com Alerta de Prejuízo"):
                        dados["prejuizo_estimado"] = divergencia
                        dados["tempo_chegada_dias"] = tempo_estimado + 5 # Auditoria atrasa a entrega
                        database.salvar_operacao(dados, status="PENDENTE_AUDITORIA")
                        st.warning("Salvo como 'Pendente'.")

# ==========================================
# TELA 3: OUTBOUND (CARRINHO E RUPTURA)
# ==========================================
elif st.session_state["tela_atual"] == "outbound":
    st.title("📤 Outbound - Saída de Mercadorias")
    
    if not st.session_state["pedido_emitido"]:
        col1, col2 = st.columns([1.5, 1])
        with col1:
            prod = st.text_input("Nome do Produto")
            qtd = st.number_input("Quantidade", min_value=1)
            prc = st.number_input("Preço Unitário (R$)", min_value=0.0)
            if st.button("Adicionar ao Carrinho"):
                st.session_state["carrinho_compras"].append({
                    "produto": prod, "quantidade": qtd, "preco_unitario": prc, "subtotal": qtd*prc
                })
                st.rerun()
        
        with col2:
            st.subheader("Itens do Pedido")
            if st.session_state["carrinho_compras"]:
                df_c = pd.DataFrame(st.session_state["carrinho_compras"])
                st.table(df_c)
                
                total_pedido = df_c['subtotal'].sum()
                st.markdown(f"**Total: R$ {total_pedido:,.2f}**")
                
                # Verificação de Ruptura
                estoque_base = {"Arroz": 1000, "Feijão": 500, "PERAS FRESCAS TIPO A": 3000}
                pode_salvar = True
                for item in st.session_state["carrinho_compras"]:
                    if item['quantidade'] > estoque_base.get(item['produto'], 100):
                        st.error(f"Ruptura: {item['produto']}!")
                        pode_salvar = False
                
                if pode_salvar and st.button("Finalizar Pedido", type="primary"):
                    dados_out = {
                        "Fornecedor": "Consumidor Final",
                        "Data": datetime.now().strftime("%Y-%m-%d"),
                        "Valor Total": total_pedido,
                        "itens": st.session_state["carrinho_compras"],
                        "prejuizo_estimado": 0.0,
                        "tempo_chegada_dias": 2
                    }
                    database.salvar_operacao(dados_out, status="ENVIADO")
                    st.session_state["pedido_emitido"] = True
                    st.rerun()
            else:
                st.info("Vazio.")
    else:
        st.success("Pedido registrado!")
        if st.button("Novo Pedido"):
            st.session_state["pedido_emitido"] = False
            st.session_state["carrinho_compras"] = []
            st.rerun()

# ==========================================
# TELA 4: DASHBOARD (HISTÓRICO COMPLETO)
# ==========================================
elif st.session_state["tela_atual"] == "historico":
    st.subheader("📊 Business Intelligence")
    dados = database.obter_historico()
    if dados:
        df = pd.DataFrame(dados)
        # Forçando conversão numérica para cálculos do Dashboard
        df['Valor Total'] = pd.to_numeric(df['Valor Total'], errors='coerce').fillna(0)
        df['prejuizo_estimado'] = pd.to_numeric(df.get('prejuizo_estimado', 0), errors='coerce').fillna(0)
        df['tempo_chegada_dias'] = pd.to_numeric(df.get('tempo_chegada_dias', 0), errors='coerce').fillna(0)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Registros", len(df))
        c2.metric("Faturamento", f"R$ {df['Valor Total'].sum():,.2f}")
        c3.metric("Prejuízo Total", f"R$ {df['prejuizo_estimado'].sum():,.2f}")
        c4.metric("Lead Time Médio", f"{df['tempo_chegada_dias'].mean():.1f} dias")
        
        st.markdown("---")
        st.write("Detalhamento da Base de Dados:")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exportar Relatório", csv, "relatorio.csv", "text/csv")
    else:
        st.info("Sem dados.")