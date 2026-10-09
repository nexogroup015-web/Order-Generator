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
SHOPIFY_REDIRECT_URI = "https://example.com"

APP_USERS_RAW = os.environ.get("APP_USERS", "admin:nexogroup")

def _parse_users():
    users = {}
    for entry in APP_USERS_RAW.split(","):
        parts = entry.strip().split(":", 1)
        if len(parts) == 2:
            users[parts[0].strip()] = hashlib.sha256(parts[1].strip().encode()).hexdigest()
    return users

APP_USERS = _parse_users()

st.set_page_config(page_title="Nexo Group", page_icon="📦", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, .stApp { background-color: #000000 !important; }
* { font-family: 'Inter', sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }

.stButton > button[kind="primary"] {
    background: #ffffff !important;
    color: #000000 !important;
    border: none !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: #888 !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)


def get_token():
    return SHOPIFY_ACCESS_TOKEN or st.session_state.get("access_token", "")


def exchange_code(code):
    resp = requests.post(
        f"https://{SHOPIFY_STORE}/admin/oauth/access_token",
        json={"client_id": SHOPIFY_CLIENT_ID, "client_secret": SHOPIFY_CLIENT_SECRET, "code": code},
    )
    return resp.json().get("access_token", "")


# ── Login ──────────────────────────────────────────────────────────────────────
if not st.session_state.get("logged_in"):
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center; margin-bottom:32px;'>
        <span style='font-size:2.2rem; font-weight:800; color:#fff;'>Nexo Group</span><br>
        <span style='font-size:0.65rem; letter-spacing:0.2em; color:#555; text-transform:uppercase;'>
            Order Generator
        </span>
    </div>
    """, unsafe_allow_html=True)

    username = st.text_input("Usuário", placeholder="seu usuário")
    password = st.text_input("Senha", type="password", placeholder="••••••••")

    if st.button("Entrar", type="primary", use_container_width=True):
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        if username in APP_USERS and APP_USERS[username] == pw_hash:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    st.stop()


# ── Conectar Shopify (sem token) ───────────────────────────────────────────────
token = get_token()

if not token:
    st.title("Nexo Group")
    st.caption("Order Generator · Supplier Document Builder")
    st.divider()
    st.subheader("Conectar Shopify")

    install_url = (
        f"https://{SHOPIFY_STORE}/admin/oauth/authorize?"
        + urlencode({"client_id": SHOPIFY_CLIENT_ID, "scope": SCOPES,
                     "redirect_uri": SHOPIFY_REDIRECT_URI, "state": "setup"})
    )
    st.write("**Passo 1 —** Autorize o app no Shopify:")
    st.link_button("🔗 Autorizar no Shopify", install_url, type="primary")
    st.write("**Passo 2 —** Cole a URL completa após o redirecionamento:")
    st.caption("Começa com `https://example.com/?code=...`")

    pasted_url = st.text_input("URL:", placeholder="https://example.com/?code=...")
    if pasted_url and st.button("✅ Conectar", type="primary"):
        try:
            params = parse_qs(urlparse(pasted_url).query)
            code = params.get("code", [None])[0]
            if code:
                with st.spinner("Obtendo token..."):
                    new_token = exchange_code(code)
                if new_token:
                    st.session_state["access_token"] = new_token
                    st.rerun()
                else:
                    st.error("Código expirado. Repita o Passo 1.")
            else:
                st.error("Código não encontrado na URL.")
        except Exception as e:
            st.error(f"Erro: {e}")
    st.stop()


# ── Exibe token novo para salvar no Render ─────────────────────────────────────
if "access_token" in st.session_state and not SHOPIFY_ACCESS_TOKEN:
    st.success("Shopify conectado!")
    st.warning("Salve o token abaixo como `SHOPIFY_ACCESS_TOKEN` no Render:")
    st.code(st.session_state["access_token"], language=None)
    st.divider()


# ── Header principal ───────────────────────────────────────────────────────────
col_t, col_out = st.columns([5, 1])
with col_t:
    st.title("Nexo Group")
    st.caption(f"Order Generator · {st.session_state.get('username', '')}")
with col_out:
    st.write("")
    if st.button("Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.divider()

# ── Carregar pedidos ───────────────────────────────────────────────────────────
col_s, col_b, col_m = st.columns([3, 1, 2])
with col_s:
    store_label = SHOPIFY_STORE.replace(".myshopify.com", "").title()
    st.selectbox("Loja", [store_label], disabled=True)
with col_b:
    st.write("")
    load = st.button("Carregar", type="primary", use_container_width=True)
with col_m:
    if "orders" in st.session_state:
        st.metric("Pedidos", len(st.session_state["orders"]))

if load:
    with st.spinner("Buscando pedidos..."):
        try:
            orders = fetch_orders(SHOPIFY_STORE, token)
            st.session_state["orders"] = orders
            st.session_state["selected_ids"] = set()
            st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

st.divider()
orders = st.session_state.get("orders", [])
if not orders:
    st.stop()

# ── Lista de pedidos ───────────────────────────────────────────────────────────
col_a, col_d = st.columns(2)
with col_a:
    if st.button("Selecionar todos"):
        st.session_state["selected_ids"] = {o["id"] for o in orders}
        st.rerun()
with col_d:
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
        or f"{cust.get('first_name','')} {cust.get('last_name','')}".strip()
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

# ── Gerar documento ────────────────────────────────────────────────────────────
st.divider()
col_i, col_g = st.columns([3, 1])
with col_i:
    st.info(f"**{len(selected_ids)} pedido(s) selecionado(s)**")
with col_g:
    gen = st.button("📄 Gerar Word", type="primary",
                    disabled=len(selected_ids) == 0, use_container_width=True)

if gen:
    selected_orders = [o for o in orders if o["id"] in selected_ids]
    with st.spinner("Gerando..."):
        buf = generate_document(selected_orders)
    st.download_button(
        "⬇️ Baixar .docx", data=buf,
        file_name="pedidos_fornecedor.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
