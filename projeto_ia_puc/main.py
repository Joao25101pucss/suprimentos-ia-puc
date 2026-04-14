"""
main.py — ERP Logística Visionary
Sistema multi-perfil com login:
  • admin      → visão total + IA + cadastros
  • cliente    → faz pedidos, acompanha suas NFs
  • fornecedor → recebe pedidos, confirma/envia, faz upload de NF
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
from datetime import datetime

import database
import ia_engine

# ══════════════════════════════════════════════════════
#  CONFIGURAÇÃO GLOBAL
# ══════════════════════════════════════════════════════
st.set_page_config(
    page_title="ERP Logística Visionary",
    layout="wide",
    page_icon="📦",
    initial_sidebar_state="expanded",
)

# Paleta de cores por perfil
CORES_PERFIL = {
    "admin":      {"bg": "#0f172a", "accent": "#6366f1", "label": "⚙️ Admin"},
    "cliente":    {"bg": "#0c1a0e", "accent": "#22c55e", "label": "🏪 Cliente"},
    "fornecedor": {"bg": "#1a0c0c", "accent": "#f97316", "label": "🏭 Fornecedor"},
}

# Tenta puxar o usuário. Se ele for None, força a ser um dicionário vazio {}
usuario_atual = st.session_state.get("usuario") or {}

# Agora busca o perfil com segurança
perfil_atual = usuario_atual.get("perfil", "admin")
cor = CORES_PERFIL.get(perfil_atual, CORES_PERFIL["admin"])
st.markdown(f"""
<style>
    .block-container {{ padding-top: 1.2rem; }}
    [data-testid="stSidebar"] {{ background: {cor['bg']}; }}
    [data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}
    [data-testid="stSidebar"] hr {{ border-color: #334155 !important; }}
    div[data-testid="metric-container"] {{
        background: #1e293b; border-radius: 10px;
        padding: 14px; border: 1px solid #334155;
    }}
    div[data-testid="metric-container"] label {{ color: #94a3b8 !important; font-size:.8rem; }}
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {{ color: #f1f5f9 !important; }}
    .tag {{
        display:inline-block; padding:3px 10px; border-radius:20px;
        font-size:.75rem; font-weight:700; letter-spacing:.4px;
    }}
    .tag-aguardando {{ background:#422006; color:#fb923c; }}
    .tag-confirmado  {{ background:#1e3a5f; color:#60a5fa; }}
    .tag-transito    {{ background:#312e81; color:#a5b4fc; }}
    .tag-entregue    {{ background:#14532d; color:#4ade80; }}
    .tag-bloqueado   {{ background:#450a0a; color:#f87171; }}
    .tag-emitida     {{ background:#1e3a5f; color:#60a5fa; }}
    .login-box {{
        max-width:420px; margin:80px auto; padding:40px;
        background:#1e293b; border-radius:16px;
        border:1px solid #334155; box-shadow:0 8px 32px rgba(0,0,0,.4);
    }}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  SETUP DO BANCO (uma vez na inicialização)
# ══════════════════════════════════════════════════════
@st.cache_resource
def _setup():
    database.configurar_ambiente()
_setup()

# ══════════════════════════════════════════════════════
#  ESTADO DA SESSÃO
# ══════════════════════════════════════════════════════
for k, v in {
    "usuario": None,
    "tela": "home",
    "carrinho": [],
    "nf_gerada": None,
    "chat_msgs": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════
def ir(tela):
    st.session_state["tela"] = tela
    st.rerun()

def sair():
    for k in ["usuario","tela","carrinho","nf_gerada","chat_msgs"]:
        st.session_state[k] = None if k == "usuario" else ("home" if k == "tela" else ([] if k == "carrinho" else None))
    st.rerun()

def calcular_item(item, regiao_cliente):
    fornecs   = database.obter_fornecedores()
    f_info    = next((f for f in fornecs if f["nome"] == item.get("fornecedor_origem","")), {})
    mesma_reg = f_info.get("regiao","") == regiao_cliente
    dias      = 1 if mesma_reg else 3
    risco     = 0.005 if item.get("categoria","") == "Eletrônicos" else (0.01 if mesma_reg else 0.05)
    perda     = item["subtotal"] * risco
    return dias, perda, perda * 0.8

def tag_status(s):
    cls = {
        "AGUARDANDO_FORNECEDOR": "tag-aguardando",
        "CONFIRMADO_FORNECEDOR": "tag-confirmado",
        "EM_TRANSITO":           "tag-transito",
        "ENTREGUE":              "tag-entregue",
        "BLOQUEADO":             "tag-bloqueado",
        "EMITIDA":               "tag-emitida",
        "RECUSADO_FORNECEDOR":   "tag-bloqueado", # Reutilizamos a cor vermelha
    }.get(s, "tag-aguardando")
    
    labels = {
        "AGUARDANDO_FORNECEDOR": "⏳ Aguardando",
        "CONFIRMADO_FORNECEDOR": "✅ Confirmado",
        "EM_TRANSITO":           "🚚 Em Trânsito",
        "ENTREGUE":              "📦 Entregue",
        "BLOQUEADO":             "🚫 Bloqueado",
        "EMITIDA":               "📄 Emitida",
        "RECUSADO_FORNECEDOR":   "❌ Recusado",
    }
    return f'<span class="tag {cls}">{labels.get(s, s)}</span>'

def render_danfe(nf):
    linhas = ""
    for item in nf.get("itens", []):
        linhas += f"""
        <tr>
          <td style="padding:9px;border-bottom:1px solid #e5e7eb">{item['produto']}</td>
          <td style="padding:9px;border-bottom:1px solid #e5e7eb">{item['fornecedor_origem']}</td>
          <td style="padding:9px;border-bottom:1px solid #e5e7eb;text-align:center">{item['quantidade']}</td>
          <td style="padding:9px;border-bottom:1px solid #e5e7eb;text-align:center">{item.get('dias_entrega','—')}d</td>
          <td style="padding:9px;border-bottom:1px solid #e5e7eb;text-align:right">
            R$ {float(item.get('subtotal',0)):,.2f}
          </td>
        </tr>"""
    html = f"""
    <style>
      body{{margin:0;font-family:'Segoe UI',Arial,sans-serif;background:transparent}}
      .danfe{{background:#fff;color:#111;padding:32px;border-radius:8px;border:1px solid #d1d5db;box-shadow:0 4px 16px rgba(0,0,0,.08)}}
      h2{{margin:0;font-size:1.15rem;letter-spacing:2px}}
      table{{width:100%;border-collapse:collapse;font-size:.85rem}}
      thead tr{{background:#f9fafb}}
      th{{padding:9px;text-align:left;border-bottom:2px solid #111;font-size:.78rem;text-transform:uppercase}}
    </style>
    <div class="danfe">
      <div style="text-align:center;border-bottom:2px dashed #111;padding-bottom:12px;margin-bottom:16px">
        <h2>DANFE SIMPLIFICADO</h2>
        <p style="margin:4px 0 0;font-size:.72rem;color:#6b7280">
          Documento Auxiliar da NF-e · ERP Logística Visionary
        </p>
      </div>
      <div style="display:flex;justify-content:space-between;margin-bottom:16px;
                  font-size:.83rem;border-bottom:1px solid #e5e7eb;padding-bottom:12px">
        <div><strong>NF / Chave:</strong><br>{nf.get('id_nf','—')}</div>
        <div><strong>Cliente:</strong><br>{nf.get('cliente_nome','—')}</div>
        <div><strong>Emissão:</strong><br>{nf.get('data_emissao','—')}</div>
        <div><strong>Destino:</strong><br>{nf.get('destino','—')}</div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Produto</th><th>Origem</th>
            <th style="text-align:center">Qtd</th>
            <th style="text-align:center">Lead</th>
            <th style="text-align:right">Subtotal</th>
          </tr>
        </thead>
        <tbody>{linhas}</tbody>
      </table>
      <div style="border-top:2px dashed #111;padding-top:16px;margin-top:8px;text-align:right">
        <span style="font-size:1.15rem;font-weight:700">
          TOTAL: R$ {float(nf.get('valor_total',0)):,.2f}
        </span><br>
        <span style="color:#dc2626;font-size:.85rem;font-weight:600">
          ⚠️ Risco Logístico Est.: R$ {float(nf.get('prejuizo_estimado', nf.get('prejuizo_total_est',0))):,.2f}
        </span>
      </div>
      <div style="text-align:center;margin-top:24px;font-size:.68rem;color:#9ca3af;
                  border-top:1px solid #f3f4f6;padding-top:8px">
        Gerado via ERP Visionary · Autenticidade verificável no banco SQLite local.
      </div>
    </div>"""
    components.html(html, height=520, scrolling=True)


# ══════════════════════════════════════════════════════
#  TELA DE LOGIN
# ══════════════════════════════════════════════════════
def tela_login():
    st.markdown("""
    <div style="text-align:center;margin-top:60px">
      <span style="font-size:3rem">📦</span>
      <h1 style="margin:8px 0 4px;color:#f1f5f9">ERP Logística Visionary</h1>
      <p style="color:#64748b;font-size:.95rem">Sistema de Gestão de Supply Chain com IA</p>
    </div>
    """, unsafe_allow_html=True)

    col = st.columns([1, 1.2, 1])[1]
    with col:
        st.markdown("<br>", unsafe_allow_html=True)
        login = st.text_input("Login", placeholder="ex: admin")
        senha = st.text_input("Senha", type="password", placeholder="••••••••")

        if st.button("Entrar →", use_container_width=True, type="primary"):
            usuario = database.autenticar(login, senha)
            if usuario:
                st.session_state["usuario"] = usuario
                st.rerun()
            else:
                st.error("Login ou senha inválidos.")

        st.markdown("""
        <div style="margin-top:24px;padding:16px;background:#0f172a;border-radius:10px;
                    border:1px solid #1e293b;font-size:.78rem;color:#64748b">
          <strong style="color:#94a3b8">Acessos demo:</strong><br><br>
          <code>admin</code> / <code>admin123</code> — Administrador<br>
          <code>supermercado</code> / <code>cliente123</code> — Cliente<br>
          <code>frigorifico</code> / <code>forn123</code> — Fornecedor<br>
          <code>hortifruti</code> / <code>forn123</code> — Fornecedor<br>
          <code>techhub</code> / <code>forn123</code> — Fornecedor
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
#  SIDEBAR GENÉRICA
# ══════════════════════════════════════════════════════
def render_sidebar(menus):
    u = st.session_state["usuario"]
    cor_p = CORES_PERFIL[u["perfil"]]
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:12px 0 8px">
          <div style="font-size:1.2rem;font-weight:700;color:{cor_p['accent']}">
            📦 ERP Visionary
          </div>
          <div style="font-size:.75rem;color:#64748b;margin-top:2px">
            {cor_p['label']} · {u['nome']}
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        for tela_id, label in menus:
            ativo = st.session_state["tela"] == tela_id
            if st.button(label, use_container_width=True,
                         type="primary" if ativo else "secondary"):
                ir(tela_id)

        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            sair()


# ══════════════════════════════════════════════════════
#  PORTAL CLIENTE
# ══════════════════════════════════════════════════════
def portal_cliente():
    u = st.session_state["usuario"]
    render_sidebar([
        ("home",     "🛒  Fazer Pedido"),
        ("pedidos",  "📋  Meus Pedidos"),
    ])

    tela = st.session_state["tela"]

    # ── FAZER PEDIDO ──────────────────────────────────
    if tela == "home":
        st.title("🛒 Fazer Novo Pedido")
        st.caption(f"Olá, **{u['nome']}**! Selecione os produtos e finalize seu pedido.")

        if not st.session_state["nf_gerada"]:
            regioes  = ["Centro","Zona Norte","Zona Sul","Zona Leste","Zona Oeste"]
            prods_db = database.obter_produtos()
            cats     = sorted(set(p["categoria"] for p in prods_db))

            col_form, col_cart = st.columns([1, 1.3])

            with col_form:
                st.subheader("Catálogo")
                regiao  = st.selectbox("📍 Região de Entrega", regioes)
                cat_sel = st.selectbox("Categoria", ["Todas"] + cats)
                filtrado = prods_db if cat_sel == "Todas" \
                           else [p for p in prods_db if p["categoria"] == cat_sel]
                prod_sel = st.selectbox("Produto", [p["nome"] for p in filtrado])
                qtd      = st.number_input("Quantidade", min_value=1, step=1, value=1)

                p_info = next((p for p in filtrado if p["nome"] == prod_sel), None)
                if p_info:
                    st.caption(
                        f"Fornecedor: **{p_info['fornecedor_nome']}** · "
                        f"R$ {p_info['preco_base']:,.2f}/{p_info.get('unidade','un')} · "
                        f"Subtotal: **R$ {qtd * p_info['preco_base']:,.2f}**"
                    )

                if st.button("➕ Adicionar", use_container_width=True):
                    if p_info:
                        st.session_state["carrinho"].append({
                            "produto":           p_info["nome"],
                            "categoria":         p_info["categoria"],
                            "fornecedor_origem": p_info["fornecedor_nome"],
                            "quantidade":        qtd,
                            "preco_unitario":    p_info["preco_base"],
                            "subtotal":          qtd * p_info["preco_base"],
                        })
                        st.rerun()

            with col_cart:
                st.subheader("🧾 Carrinho")
                if not st.session_state["carrinho"]:
                    st.info("Carrinho vazio.")
                else:
                    total = 0
                    for item in st.session_state["carrinho"]:
                        dias, perda, _ = calcular_item(item, regiao)
                        total += item["subtotal"]
                        st.write(f"**{item['produto']}** — {item['quantidade']} {item.get('unidade','un')} · "
                                 f"R$ {item['subtotal']:,.2f} · ⏱️ {dias}d")

                    st.metric("Total do Pedido", f"R$ {total:,.2f}")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🗑️ Limpar", use_container_width=True):
                            st.session_state["carrinho"] = []
                            st.rerun()
                    with c2:
                        if st.button("✅ Finalizar Pedido", type="primary", use_container_width=True):
                            resumo = []
                            for item in st.session_state["carrinho"]:
                                d, p, r = calcular_item(item, regiao)
                                resumo.append({**item, "dias_entrega": d, "perda": p, "reembolso": r})

                            # Agrupa por fornecedor (gera uma NF por fornecedor)
                            from collections import defaultdict
                            por_forn = defaultdict(list)
                            for item in resumo:
                                por_forn[item["fornecedor_origem"]].append(item)

                            ultima_nf = None
                            for forn_nome, itens_forn in por_forn.items():
                                nf = {
                                    "id_nf":          f"NF-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}",
                                    "cliente_login":  u["login"],
                                    "cliente_nome":   u["nome"],
                                    "cnpj_cliente":   u.get("cnpj", "00.000.000/0001-00"),
                                    "fornecedor_nome":forn_nome,
                                    "destino":        regiao,
                                    "data_emissao":   datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    "itens":          itens_forn,
                                    "valor_total":    sum(i["subtotal"] for i in itens_forn),
                                    "prejuizo_estimado": sum(i["perda"] for i in itens_forn),
                                    "tipo":           "OUTBOUND",
                                }
                                database.salvar_operacao(nf, status="AGUARDANDO_FORNECEDOR")
                                ultima_nf = nf

                            st.session_state["nf_gerada"] = ultima_nf
                            st.session_state["carrinho"]  = []
                            st.rerun()
        else:
            nf = st.session_state["nf_gerada"]
            st.success("✅ Pedido enviado! Aguardando confirmação do fornecedor.")
            render_danfe(nf)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🆕 Novo Pedido"):
                st.session_state["nf_gerada"] = None
                st.rerun()

    # ── MEUS PEDIDOS ─────────────────────────────────
    elif tela == "pedidos":
        st.title("📋 Meus Pedidos")
        pedidos = database.obter_historico(filtro_cliente=u["login"])

        if not pedidos:
            st.info("Você ainda não fez nenhum pedido.")
        else:
            stats = database.obter_estatisticas(filtro_cliente=u["login"])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total de Pedidos",  stats.get("total_nfs", 0))
            c2.metric("Volume Total",      f"R$ {stats.get('volume_total',0):,.2f}")
            c3.metric("Aguardando",        stats.get("aguardando", 0))
            c4.metric("Entregues",         stats.get("entregues", 0))
            st.markdown("---")

            for p in pedidos:
                with st.expander(
                    f"📄 {p['id_nf']} · {p['fornecedor_nome']} · "
                    f"R$ {p['valor_total']:,.2f} · {p['data_emissao']}"
                ):
                    st.markdown(tag_status(p["status"]), unsafe_allow_html=True)
                    if p.get("observacao"):
                        st.caption(f"Obs: {p['observacao']}")
                    itens_df = pd.DataFrame(p.get("itens", []))
                    if not itens_df.empty:
                        cols_show = [c for c in ["produto","fornecedor_origem","quantidade","subtotal","dias_entrega","data_prevista_chegada"] if c in itens_df.columns]
                        st.dataframe(itens_df[cols_show], use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════
#  PORTAL FORNECEDOR
# ══════════════════════════════════════════════════════
def portal_fornecedor():
    u = st.session_state["usuario"]
    nome_empresa = u.get("empresa", u["nome"])

    render_sidebar([
        ("home",      "📬  Pedidos Recebidos"),
        ("catalogo",  "📦  Meu Catálogo"),
        ("inbound",   "📥  Upload NF Entrada"),
    ])

    tela = st.session_state["tela"]

    # ── PEDIDOS RECEBIDOS ─────────────────────────────
    if tela == "home":
        st.title("📬 Pedidos Recebidos")
        st.caption(f"Empresa: **{nome_empresa}** · Gerencie e atualize o status dos pedidos.")

        pedidos = database.obter_historico(filtro_fornecedor=nome_empresa)
        stats   = database.obter_estatisticas(filtro_fornecedor=nome_empresa)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Recebidos",  stats.get("total_nfs", 0))
        c2.metric("Volume Total",     f"R$ {stats.get('volume_total',0):,.2f}")
        c3.metric("Aguardando",       stats.get("aguardando", 0))
        c4.metric("Em Trânsito",      stats.get("em_transito", 0))
        st.markdown("---")

        if not pedidos:
            st.info("Nenhum pedido recebido ainda.")
        else:
            # Fluxo de status que o fornecedor pode avançar
            ACOES = {
                "AGUARDANDO_FORNECEDOR": ("✅ Confirmar Pedido",   "CONFIRMADO_FORNECEDOR"),
                "CONFIRMADO_FORNECEDOR": ("🚚 Marcar Em Trânsito", "EM_TRANSITO"),
                "EM_TRANSITO":           ("📦 Confirmar Entrega",  "ENTREGUE"),
            }

            for p in pedidos:
                with st.expander(
                    f"📄 {p['id_nf']} · **{p['cliente_nome']}** · "
                    f"R$ {p['valor_total']:,.2f} · {p['data_emissao']}"
                ):
                    st.markdown(tag_status(p["status"]), unsafe_allow_html=True)
                    if p.get("observacao"):
                        st.caption(f"Obs fornecedor: {p['observacao']}")

                    itens_df = pd.DataFrame(p.get("itens", []))
                    if not itens_df.empty:
                        cols = [c for c in ["produto","quantidade","preco_unitario","subtotal","dias_entrega","data_prevista_chegada"] if c in itens_df.columns]
                        st.dataframe(itens_df[cols], use_container_width=True, hide_index=True)

                    if p["status"] in ACOES:
                        label_btn, prox_status = ACOES[p["status"]]
                        obs_key = f"obs_{p['id_nf']}"
                        obs = st.text_input("Observação (justificativa de atraso ou recusa)", key=obs_key, 
                                            placeholder="ex: separado, sem estoque...")

                        c_btn1, c_btn2 = st.columns(2)
                        
                        with c_btn1:
                            if st.button(label_btn, key=f"btn_acc_{p['id_nf']}", type="primary", use_container_width=True):
                                database.atualizar_status_nf(p["id_nf"], prox_status, obs)
                                st.success(f"Status atualizado para **{prox_status}**")
                                st.rerun()

                        # Se o pedido acabou de chegar, mostra o botão de recusar ao lado
                        if p["status"] == "AGUARDANDO_FORNECEDOR":
                            with c_btn2:
                                if st.button("❌ Recusar Pedido", key=f"btn_rec_{p['id_nf']}", use_container_width=True):
                                    if not obs:
                                        st.warning("⚠️ Para recusar, você deve preencher o motivo na observação acima.")
                                    else:
                                        database.atualizar_status_nf(p["id_nf"], "RECUSADO_FORNECEDOR", obs)
                                        st.rerun()
                                        
                    elif p["status"] == "ENTREGUE":
                        st.success("✅ Entrega confirmada.")
                    elif p["status"] == "RECUSADO_FORNECEDOR":
                        st.error("❌ Você recusou este pedido.")

    # ── MEU CATÁLOGO ──────────────────────────────────
    elif tela == "catalogo":
        st.title("📦 Meu Catálogo de Produtos")
        prods = database.obter_produtos_por_fornecedor(nome_empresa)
        if prods:
            df = pd.DataFrame(prods).drop(columns=["id","ativo"], errors="ignore")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum produto cadastrado para sua empresa.")

        with st.expander("➕ Adicionar Produto ao Catálogo"):
            with st.form("form_prod_forn"):
                nome_p  = st.text_input("Nome do Produto")
                cat_p   = st.text_input("Categoria")
                preco_p = st.number_input("Preço Base (R$)", min_value=0.01, value=10.00, step=1.0)
                unid_p  = st.text_input("Unidade", value="un")
                if st.form_submit_button("Salvar", type="primary"):
                    if nome_p:
                        database.cadastrar_produto(nome_p, cat_p, preco_p, nome_empresa, unid_p)
                        st.success("Produto adicionado!")
                        st.rerun()

    # ── UPLOAD NF ENTRADA ─────────────────────────────
    elif tela == "inbound":
        st.title("📥 Upload de Nota Fiscal de Entrada")
        st.caption("Envie NFs recebidas de seus fornecedores para registro no sistema.")

        arquivo = st.file_uploader("Selecione o arquivo (PDF ou imagem)",
                                   type=["pdf","png","jpg","jpeg"])
        if arquivo and st.button("⚡ Processar NF", type="primary"):
            with st.spinner("IA extraindo dados..."):
                dados = ia_engine.processar_nota(arquivo)
            if not dados:
                st.error("Não foi possível extrair os dados. Verifique o arquivo.")
            else:
                st.success("Dados extraídos com sucesso!")
                st.json(dados)
                soma   = sum(float(i.get("subtotal", 0)) for i in dados.get("itens", []))
                total  = float(dados.get("valor_total") or 0)
                divergencia = abs(soma - total)
                dados["cliente_login"]  = u["login"]
                dados["cliente_nome"]   = u["nome"]
                dados["fornecedor_nome"]= nome_empresa
                dados["tipo"]           = "INBOUND"

                if divergencia < 0.05:
                    database.salvar_operacao(dados, status="ENTREGUE")
                    st.success("✅ NF registrada com status ENTREGUE.")
                    st.balloons()
                else:
                    st.warning(f"Divergência de R$ {divergencia:,.2f} detectada.")
                    if st.button("Registrar mesmo assim"):
                        dados["prejuizo_estimado"] = divergencia
                        database.salvar_operacao(dados, status="BLOQUEADO")
                        st.warning("NF registrada com status BLOQUEADO.")


# ══════════════════════════════════════════════════════
#  PORTAL ADMIN
# ══════════════════════════════════════════════════════
def portal_admin():
    u = st.session_state["usuario"]
    render_sidebar([
        ("home",      "🤖  Torre de Comando (IA)"),
        ("dashboard", "📊  BI & Dashboard"),
        ("inbound",   "📥  Inbound — NF Entrada"),
        ("outbound",  "📤  Outbound — Emitir Pedido"),
        ("cadastros", "🗃️  Cadastros & Usuários"),
    ])

    tela = st.session_state["tela"]

    # ── TORRE DE COMANDO (CHAT IA) ────────────────────
    if tela == "home":
        st.title("🤖 Torre de Comando — ARIA")
        st.caption("Analista autônoma de supply chain · Acesso total ao banco de dados SQL.")

        if st.session_state["chat_msgs"] is None:
            stats = database.obter_estatisticas()
            st.session_state["chat_msgs"] = [{
                "role": "assistant",
                "content": (
                    f"Olá, **{u['nome']}**! Sou **ARIA**, sua analista de logística.\n\n"
                    f"O banco possui **{stats.get('total_nfs',0)} Notas Fiscais** · "
                    f"Volume: **R$ {stats.get('volume_total',0):,.2f}** · "
                    f"Aguardando fornecedor: **{stats.get('aguardando',0)}**.\n\n"
                    "Posso analisar pedidos, fornecedores, riscos e gargalos. O que deseja saber?"
                )
            }]

        for msg in st.session_state["chat_msgs"]:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ex: Quais fornecedores têm pedidos aguardando confirmação?"):
            st.session_state["chat_msgs"].append({"role":"user","content":prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            dados_banco = {
                "stats":        database.obter_estatisticas(),
                "pedidos":      database.obter_historico(),
                "fornecedores": database.obter_fornecedores(),
                "catalogo":     database.obter_produtos(),
            }
            contexto = ia_engine.construir_contexto_banco(dados_banco)
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("ARIA analisando..."):
                    resp = ia_engine.conversar_com_agente(st.session_state["chat_msgs"], contexto)
                    st.markdown(resp)
            st.session_state["chat_msgs"].append({"role":"assistant","content":resp})

        if st.session_state["chat_msgs"] and len(st.session_state["chat_msgs"]) > 1:
            if st.button("🗑️ Limpar conversa"):
                st.session_state["chat_msgs"] = None
                st.rerun()

    # ── DASHBOARD ─────────────────────────────────────
    elif tela == "dashboard":
        st.title("📊 Business Intelligence — Visão Global")
        stats   = database.obter_estatisticas()
        pedidos = database.obter_historico()

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total NFs",        stats.get("total_nfs", 0))
        c2.metric("Volume Total",     f"R$ {stats.get('volume_total',0):,.2f}")
        c3.metric("Risco Estimado",   f"R$ {stats.get('prejuizo_total',0):,.2f}")
        c4.metric("Aguardando",       stats.get("aguardando", 0))
        c5.metric("Entregues",        stats.get("entregues", 0))
        st.markdown("---")

        if not pedidos:
            st.info("Nenhuma operação registrada.")
            return

        col_f1, col_f2, col_f3 = st.columns(3)
        filtro_status = col_f1.selectbox("Status", ["Todos","AGUARDANDO_FORNECEDOR","CONFIRMADO_FORNECEDOR","EM_TRANSITO","ENTREGUE","BLOQUEADO"])
        filtro_tipo   = col_f2.selectbox("Tipo",   ["Todos","OUTBOUND","INBOUND"])

        pf = pedidos
        if filtro_status != "Todos": pf = [p for p in pf if p["status"] == filtro_status]
        if filtro_tipo   != "Todos": pf = [p for p in pf if p.get("tipo") == filtro_tipo]

        df = pd.DataFrame([{
            "NF":          p["id_nf"],
            "Cliente":     p["cliente_nome"],
            "Fornecedor":  p["fornecedor_nome"],
            "Destino":     p["destino"],
            "Emissão":     p["data_emissao"],
            "Tipo":        p.get("tipo","—"),
            "Valor (R$)":  p["valor_total"],
            "Risco (R$)":  p["prejuizo_total_est"],
            "Status":      p["status"],
            "Itens":       len(p.get("itens",[])),
        } for p in pf])

        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={
                         "Valor (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                         "Risco (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                     })

        if len(pf) > 1:
            st.markdown("#### Volume por Fornecedor")
            df_forn = df.groupby("Fornecedor")["Valor (R$)"].sum().reset_index()
            st.bar_chart(df_forn, x="Fornecedor", y="Valor (R$)")

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Exportar CSV",
                           data=csv,
                           file_name=f"erp_{datetime.now().strftime('%Y%m%d')}.csv",
                           mime="text/csv")

    # ── INBOUND ───────────────────────────────────────
    elif tela == "inbound":
        st.title("📥 Inbound — Processar NF de Entrada")
        arquivo = st.file_uploader("Upload (PDF/imagem)", type=["pdf","png","jpg","jpeg"])
        if arquivo and st.button("⚡ Processar", type="primary"):
            with st.spinner("IA extraindo dados..."):
                dados = ia_engine.processar_nota(arquivo)
            if not dados:
                st.error("Falha na extração. Verifique o arquivo.")
            else:
                prods_db = database.obter_produtos()
                forn_det = "Desconhecido"
                for item in dados.get("itens", []):
                    nome_item = item.get("produto","").lower()
                    for p in prods_db:
                        if p["nome"].lower() in nome_item or nome_item in p["nome"].lower():
                            forn_det = p["fornecedor_nome"]
                            break
                    if forn_det != "Desconhecido":
                        break

                soma = sum(float(i.get("subtotal",0)) for i in dados.get("itens",[]))
                total = float(dados.get("valor_total") or 0)
                div   = abs(soma - total)

                c1, c2, c3 = st.columns(3)
                c1.metric("Fornecedor", forn_det)
                c2.metric("Valor Total", f"R$ {total:,.2f}")
                c3.metric("Divergência", f"R$ {div:,.2f}", delta_color="inverse" if div>0.05 else "normal")

                if dados.get("itens"):
                    st.dataframe(pd.DataFrame(dados["itens"]), use_container_width=True, hide_index=True)

                dados["fornecedor_nome"] = forn_det
                dados["cliente_login"]   = u["login"]
                dados["cliente_nome"]    = u["nome"]
                dados["tipo"]            = "INBOUND"

                if div < 0.05:
                    database.salvar_operacao(dados, status="APROVADA")
                    st.success("✅ NF aprovada e salva.")
                    st.balloons()
                else:
                    st.warning(f"Divergência de R$ {div:,.2f}")
                    ca, cb = st.columns(2)
                    with ca:
                        if st.button("Registrar com divergência"):
                            dados["prejuizo_estimado"] = div
                            database.salvar_operacao(dados, status="BLOQUEADO")
                            st.warning("NF salva como BLOQUEADO.")
                    with cb:
                        if st.button("Descartar"):
                            st.info("Descartada.")

    # ── OUTBOUND ──────────────────────────────────────
    elif tela == "outbound":
        st.title("📤 Outbound — Emitir Pedido Interno")

        if not st.session_state["nf_gerada"]:
            regioes  = ["Centro","Zona Norte","Zona Sul","Zona Leste","Zona Oeste"]
            prods_db = database.obter_produtos()
            cats     = sorted(set(p["categoria"] for p in prods_db))

            col_form, col_cart = st.columns([1, 1.3])

            with col_form:
                st.subheader("🛒 Montar Pedido")
                regiao   = st.selectbox("Região de Destino", regioes)
                cat_sel  = st.selectbox("Categoria", ["Todas"] + cats)
                filtrado = prods_db if cat_sel == "Todas" \
                           else [p for p in prods_db if p["categoria"] == cat_sel]
                prod_sel = st.selectbox("Produto", [p["nome"] for p in filtrado])
                qtd      = st.number_input("Quantidade", min_value=1, step=1, value=1)

                p_info = next((p for p in filtrado if p["nome"] == prod_sel), None)
                if p_info:
                    st.caption(
                        f"Fornecedor: **{p_info['fornecedor_nome']}** · "
                        f"R$ {p_info['preco_base']:,.2f}/{p_info.get('unidade','un')} · "
                        f"Subtotal: **R$ {qtd*p_info['preco_base']:,.2f}**"
                    )
                if st.button("➕ Adicionar", use_container_width=True):
                    if p_info:
                        st.session_state["carrinho"].append({
                            "produto":           p_info["nome"],
                            "categoria":         p_info["categoria"],
                            "fornecedor_origem": p_info["fornecedor_nome"],
                            "quantidade":        qtd,
                            "preco_unitario":    p_info["preco_base"],
                            "subtotal":          qtd * p_info["preco_base"],
                        })
                        st.rerun()

            with col_cart:
                st.subheader("📋 Análise de Risco")
                if not st.session_state["carrinho"]:
                    st.info("Nenhum item adicionado.")
                else:
                    total = perda_total = 0
                    for item in st.session_state["carrinho"]:
                        dias, perda, _ = calcular_item(item, regiao)
                        total      += item["subtotal"]
                        perda_total += perda
                        st.write(f"**{item['produto']}** · {item['fornecedor_origem']} · "
                                 f"R$ {item['subtotal']:,.2f} · ⏱️ {dias}d · Risco R$ {perda:.2f}")

                    cc1, cc2 = st.columns(2)
                    cc1.metric("Total Bruto",       f"R$ {total:,.2f}")
                    cc2.metric("Risco Est.",         f"R$ {perda_total:,.2f}", delta_color="inverse")

                    cx, cy = st.columns(2)
                    with cx:
                        if st.button("🗑️ Limpar", use_container_width=True):
                            st.session_state["carrinho"] = []
                            st.rerun()
                    with cy:
                        if st.button("✅ Emitir DANFE", type="primary", use_container_width=True):
                            resumo = []
                            for item in st.session_state["carrinho"]:
                                d, p, r = calcular_item(item, regiao)
                                resumo.append({**item, "dias_entrega": d, "perda": p, "reembolso": r})

                            nf = {
                                "id_nf":           f"NF-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                "cliente_login":   u["login"],
                                "cliente_nome":    u["nome"],
                                "destino":         regiao,
                                "data_emissao":    datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "itens":           resumo,
                                "valor_total":     sum(i["subtotal"] for i in resumo),
                                "prejuizo_estimado": sum(i["perda"] for i in resumo),
                                "tipo":            "OUTBOUND",
                            }
                            database.salvar_operacao(nf, status="AGUARDANDO_FORNECEDOR")
                            st.session_state["nf_gerada"] = nf
                            st.session_state["carrinho"]  = []
                            st.rerun()
        else:
            nf = st.session_state["nf_gerada"]
            st.success("✅ DANFE emitida e salva no banco operacional!")
            render_danfe(nf)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📄 Emitir Nova Nota"):
                st.session_state["nf_gerada"] = None
                st.rerun()

    # ── CADASTROS & USUÁRIOS ──────────────────────────
    elif tela == "cadastros":
        st.title("🗃️ Cadastros & Gestão de Usuários")
        tab_u, tab_f, tab_p = st.tabs(["👥 Usuários", "🏭 Fornecedores", "📦 Produtos"])

        with tab_u:
            st.subheader("Usuários do Sistema")
            usuarios = database.listar_usuarios()
            df_u = pd.DataFrame(usuarios)
            if not df_u.empty:
                st.dataframe(df_u, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Criar Novo Usuário")
            with st.form("form_user"):
                col1, col2 = st.columns(2)
                login_n  = col1.text_input("Login")
                senha_n  = col2.text_input("Senha", type="password")
                nome_n   = col1.text_input("Nome Completo")
                perfil_n = col2.selectbox("Perfil", ["cliente","fornecedor","admin"])
                empresa_n= st.text_input("Empresa / Razão Social")
                if st.form_submit_button("Criar Usuário", type="primary"):
                    if login_n and senha_n and nome_n:
                        ok = database.criar_usuario(login_n, senha_n, nome_n, perfil_n, empresa_n)
                        if ok:
                            st.success(f"Usuário **{login_n}** criado!")
                            st.rerun()
                        else:
                            st.error("Login já existe.")
                    else:
                        st.error("Preencha todos os campos obrigatórios.")

        with tab_f:
            st.subheader("Fornecedores")
            df_f = pd.DataFrame(database.obter_fornecedores()).drop(columns=["id","ativo"], errors="ignore")
            if not df_f.empty:
                st.dataframe(df_f, use_container_width=True, hide_index=True)
            with st.expander("➕ Cadastrar Fornecedor"):
                with st.form("form_forn"):
                    n = st.text_input("Razão Social")
                    c = st.text_input("CNPJ", value="00.000.000/0001-00")
                    r = st.selectbox("Região", ["Centro","Zona Norte","Zona Sul","Zona Leste","Zona Oeste"])
                    cat = st.text_input("Categoria")
                    la = st.number_input("Latitude",  value=-23.55, format="%.4f")
                    lo = st.number_input("Longitude", value=-46.63, format="%.4f")
                    if st.form_submit_button("Salvar", type="primary"):
                        if n:
                            database.cadastrar_fornecedor(n, r, cat, (la, lo), c)
                            st.success("Fornecedor cadastrado!")
                            st.rerun()

        with tab_p:
            st.subheader("Catálogo de Produtos")
            df_p = pd.DataFrame(database.obter_produtos()).drop(columns=["id","ativo"], errors="ignore")
            if not df_p.empty:
                st.dataframe(df_p, use_container_width=True, hide_index=True)
            with st.expander("➕ Adicionar Produto"):
                fornec_nomes = [f["nome"] for f in database.obter_fornecedores()]
                with st.form("form_prod"):
                    np_ = st.text_input("Nome")
                    cp_ = st.text_input("Categoria")
                    pp_ = st.number_input("Preço Base (R$)", min_value=0.01, value=10.0, step=1.0)
                    up_ = st.text_input("Unidade", value="un")
                    fp_ = st.selectbox("Fornecedor", fornec_nomes) if fornec_nomes else st.text_input("Fornecedor")
                    if st.form_submit_button("Salvar", type="primary"):
                        if np_ and fp_:
                            database.cadastrar_produto(np_, cp_, pp_, fp_, up_)
                            st.success("Produto salvo!")
                            st.rerun()


# ══════════════════════════════════════════════════════
#  ROTEADOR PRINCIPAL
# ══════════════════════════════════════════════════════
if not st.session_state["usuario"]:
    tela_login()
else:
    perfil = st.session_state["usuario"]["perfil"]
    if perfil == "cliente":
        portal_cliente()
    elif perfil == "fornecedor":
        portal_fornecedor()
    elif perfil == "admin":
        portal_admin()
    else:
        st.error("Perfil desconhecido. Faça login novamente.")
        sair()