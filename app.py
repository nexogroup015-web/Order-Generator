import hashlib
import os
import requests
import streamlit as st
from urllib.parse import urlencode, urlparse, parse_qs

from shopify_api import fetch_orders
from doc_generator import generate_document

SHOPIFY_CLIENT_ID = os.environ.get("SHOPIFY_CLIENT_ID", "")
SHOPIFY_CLIENT_SECRET = os.environ.get("SHOPIFY_CLIENT_SECRET", "")
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE", "")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
SCOPES = "read_orders"

# URL registrada no app Shopify (application_url da versão ativa)
SHOPIFY_REDIRECT_URI = "https://example.com"

# Credenciais de acesso — formato: "usuario:senha,usuario2:senha2"
APP_USERS_RAW = os.environ.get("APP_USERS", "admin:nexogroup")

def _parse_users():
    users = {}
    for entry in APP_USERS_RAW.split(","):
        parts = entry.strip().split(":", 1)
        if len(parts) == 2:
            u, p = parts
            users[u.strip()] = hashlib.sha256(p.strip().encode()).hexdigest()
    return users

APP_USERS = _parse_users()

st.set_page_config(page_title="Nexo Group", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: #080808 !important;
    font-family: 'Inter', sans-serif !important;
}

#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {
    display: none !important;
}

[data-testid="stSidebar"] { display: none !important; }

/* Inputs */
input[type="text"], input[type="password"] {
    background: #161616 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 12px 16px !important;
}
input[type="text"]:focus, input[type="password"]:focus {
    border-color: #444 !important;
    box-shadow: none !important;
}
.stTextInput label, .stSelectbox label {
    color: #888 !important;
    font-size: 0.82rem !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: 0.03em;
}

/* Botão primário — branco */
.stButton > button[kind="primary"], button[kind="primary"] {
    background: #ffffff !important;
    color: #111111 !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    height: 46px !important;
    transition: opacity 0.15s;
}
.stButton > button[kind="primary"]:hover { opacity: 0.88 !important; }

/* Botão secundário */
.stButton > button[kind="secondary"] {
    background: #1a1a1a !important;
    color: #ccc !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
}

/* Containers / cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #111111 !important;
    border: 1px solid #1f1f1f !important;
    border-radius: 12px !important;
}

/* Divider */
hr { border-color: #1f1f1f !important; }

/* Métricas */
[data-testid="stMetric"] { color: #fff !important; }
[data-testid="stMetricValue"] { color: #fff !important; font-family: 'Inter', sans-serif !important; }

/* Caption/texto secundário */
.stCaption, [data-testid="stCaptionContainer"] { color: #555 !important; }

/* Checkbox */
.stCheckbox label { color: #ccc !important; font-family: 'Inter', sans-serif !important; }

/* Info/warning/success */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* Títulos */
h1, h2, h3 {
    font-family: 'Inter', sans-serif !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)


def get_token():
    return SHOPIFY_ACCESS_TOKEN or st.session_state.get("access_token", "")


def exchange_code(code):
    url = f"https://{SHOPIFY_STORE}/admin/oauth/access_token"
    resp = requests.post(
        url,
        json={
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
            "code": code,
        },
    )
    return resp.json().get("access_token", "")


# ── Tela de Login ─────────────────────────────────────────────────────────────
if not st.session_state.get("logged_in"):
    st.markdown("<div style='height: 80px'></div>", unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 1.4, 1])
    with col_c:
        st.markdown("""
        <div style='text-align:center; margin-bottom: 36px;'>
            <div style='font-size:2.6rem; font-weight:800; color:#ffffff;
                        letter-spacing:-1.5px; font-family:Inter,sans-serif;'>
                Nexo Group
            </div>
            <div style='font-size:0.68rem; letter-spacing:0.22em; color:#444;
                        margin-top:6px; text-transform:uppercase;
                        font-family:Inter,sans-serif;'>
                Order Generator
            </div>
        </div>
        """, unsafe_allow_html=True)

        username = st.text_input("Usuário", placeholder="seu usuário", label_visibility="visible")
        password = st.text_input("Senha", type="password", placeholder="••••••••", label_visibility="visible")
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        if st.button("Entrar", type="primary", use_container_width=True):
            pw_hash = hashlib.sha256(password.encode()).hexdigest()
            if username in APP_USERS and APP_USERS[username] == pw_hash:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_logout = st.columns([6, 1])
with col_title:
    st.title("Nexo Group")
    st.caption(f"Order Generator · Supplier Document Builder · {st.session_state.get('username', '')}")
with col_logout:
    st.write("")
    st.write("")
    if st.button("Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()
st.divider()

token = get_token()

# ── Tela de conexão (sem token) ───────────────────────────────────────────────
if not token:
    st.subheader("Conectar Shopify")

    install_url = (
        f"https://{SHOPIFY_STORE}/admin/oauth/authorize?"
        + urlencode(
            {
                "client_id": SHOPIFY_CLIENT_ID,
                "scope": SCOPES,
                "redirect_uri": SHOPIFY_REDIRECT_URI,
                "state": "setup",
            }
        )
    )

    st.write("**Passo 1 —** Clique no botão abaixo para autorizar o app no Shopify:")
    st.link_button("🔗 Autorizar no Shopify", install_url, type="primary")

    st.write(
        "**Passo 2 —** Após autorizar, você será redirecionado para uma página de exemplo. "
        "Copie a **URL completa** do seu navegador e cole abaixo:"
    )
    st.caption("A URL vai começar com `https://example.com/?code=...`")

    pasted_url = st.text_input("Cole a URL aqui:", placeholder="https://example.com/?code=...")

    if pasted_url:
        if st.button("✅ Conectar", type="primary"):
            try:
                parsed = urlparse(pasted_url)
                params = parse_qs(parsed.query)
                code = params.get("code", [None])[0]
                if code:
                    with st.spinner("Obtendo token..."):
                        new_token = exchange_code(code)
                    if new_token:
                        st.session_state["access_token"] = new_token
                        st.rerun()
                    else:
                        st.error("Erro ao obter token. O código pode ter expirado — tente o Passo 1 novamente.")
                else:
                    st.error("Código não encontrado na URL. Verifique se copiou a URL correta.")
            except Exception as e:
                st.error(f"Erro: {e}")

    st.stop()

# ── Exibe token após OAuth (para salvar no Render) ────────────────────────────
if "access_token" in st.session_state and not SHOPIFY_ACCESS_TOKEN:
    st.success("Shopify conectado com sucesso!")
    st.warning(
        "Copie o token abaixo e adicione como variável **SHOPIFY_ACCESS_TOKEN** no Render. "
        "Após salvar, ele não será exibido novamente."
    )
    st.code(st.session_state["access_token"], language=None)
    st.divider()

# ── Seleção de loja e carregamento ────────────────────────────────────────────
store_label = SHOPIFY_STORE.replace(".myshopify.com", "").title()

col_store, col_btn, col_metric = st.columns([3, 1, 2])
with col_store:
    st.selectbox("Loja", [store_label], disabled=True)
with col_btn:
    st.write("")
    st.write("")
    load = st.button("Carregar Pedidos", type="primary", use_container_width=True)
with col_metric:
    if "orders" in st.session_state:
        st.metric("Pedidos carregados", len(st.session_state["orders"]))

if load:
    with st.spinner("Buscando pedidos..."):
        try:
            orders = fetch_orders(SHOPIFY_STORE, token)
            st.session_state["orders"] = orders
            st.session_state["selected_ids"] = set()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao buscar pedidos: {e}")

st.divider()
orders = st.session_state.get("orders", [])
if not orders:
    st.stop()

# ── Lista de pedidos ──────────────────────────────────────────────────────────
col_all, col_none = st.columns(2)
with col_all:
    if st.button("Selecionar todos"):
        st.session_state["selected_ids"] = {o["id"] for o in orders}
        st.rerun()
with col_none:
    if st.button("Desmarcar todos"):
        st.session_state["selected_ids"] = set()
        st.rerun()

selected_ids: set = st.session_state.get("selected_ids", set())

for order in orders:
    oid = order["id"]
    addr = order.get("shipping_address") or {}
    cust = order.get("customer") or {}
    customer_name = (
        addr.get("name")
        or f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip()
        or "—"
    )
    products = ", ".join(i["title"] for i in order.get("line_items", []))

    with st.container(border=True):
        checked = st.checkbox(
            f"**{order['name']}** · {customer_name}",
            value=oid in selected_ids,
            key=f"chk_{oid}",
        )
        st.caption(products)

    if checked:
        selected_ids.add(oid)
    else:
        selected_ids.discard(oid)

st.session_state["selected_ids"] = selected_ids

# ── Geração do documento ──────────────────────────────────────────────────────
st.divider()
col_info, col_gen = st.columns([3, 1])
with col_info:
    st.info(f"**{len(selected_ids)} pedido(s) selecionado(s)**")
with col_gen:
    gen = st.button(
        "📄 Gerar Documento Word",
        type="primary",
        disabled=len(selected_ids) == 0,
        use_container_width=True,
    )

if gen:
    selected_orders = [o for o in orders if o["id"] in selected_ids]
    with st.spinner("Gerando documento..."):
        buf = generate_document(selected_orders)
    st.download_button(
        label="⬇️ Baixar .docx",
        data=buf,
        file_name="pedidos_fornecedor.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
