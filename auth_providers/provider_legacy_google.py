import os
import streamlit as st
from google_auth_oauthlib.flow import Flow

_AUTH_CFG = st.secrets.get("auth", {})

# Prioriza nomenclatura legada, com fallback para [auth] para compatibilidade.
GOOGLE_CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", os.environ.get("GOOGLE_CLIENT_ID", "")) or _AUTH_CFG.get("client_id", "")
GOOGLE_CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", os.environ.get("GOOGLE_CLIENT_SECRET", "")) or _AUTH_CFG.get("client_secret", "")
REDIRECT_URI = st.secrets.get("REDIRECT_URI", os.environ.get("REDIRECT_URI", "http://localhost:8501"))

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _get_google_auth_url():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return None

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    st.session_state.oauth_state = state
    return auth_url


def _handle_google_callback() -> bool:
    query_params = st.query_params

    if "code" in query_params:
        code = query_params.get("code")
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [REDIRECT_URI],
                    }
                },
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI,
            )

            flow.fetch_token(code=code)
            credentials = flow.credentials

            import requests

            userinfo_response = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"},
                timeout=15,
            )

            if userinfo_response.status_code == 200:
                userinfo = userinfo_response.json()
                st.session_state.user_email = userinfo.get("email", "")
                st.session_state.user_name = userinfo.get("name", userinfo.get("email", "Usuário"))
                st.session_state.user_picture = userinfo.get("picture", "")
                st.session_state.user_logged_in = True
                st.query_params.clear()
                return True

        except Exception as e:
            st.error(f"Erro na autenticação: {str(e)}")
            st.query_params.clear()
            return False

    return False


def render_legacy_google_login() -> bool:
    if _handle_google_callback():
        st.rerun()
        return True

    if st.session_state.get("user_logged_in", False):
        return True

    lang = st.session_state.get("ui_language", "pt")
    title = "📚 Smart YouTube Booklet"
    subtitle = (
        "Transforme playlists do YouTube em apostilas educacionais"
        if lang == "pt"
        else "Transform YouTube playlists into educational booklets"
    )
    login_text = (
        "Faça login com sua conta Google para continuar"
        if lang == "pt"
        else "Login with your Google account to continue"
    )
    btn_text = "Entrar com Google" if lang == "pt" else "Sign in with Google"

    st.markdown(
        f"""
        <div style=\"background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:3rem;border-radius:20px;text-align:center;color:white;margin:2rem auto;max-width:500px;\">
            <h1>{title}</h1>
            <p>{subtitle}</p>
            <p>{login_text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    auth_url = _get_google_auth_url()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if auth_url:
            st.markdown(
                f"""
                <a href=\"{auth_url}\" target=\"_self\" style=\"display:inline-block;width:100%;text-align:center;padding:12px 18px;background:#fff;color:#222;text-decoration:none;border-radius:8px;font-weight:600;\">
                    {btn_text}
                </a>
                """,
                unsafe_allow_html=True,
            )
            return False

        st.error("OAuth não configurado." if lang == "pt" else "OAuth not configured.")
        if st.button("Entrar (Demo)", type="primary", use_container_width=True):
            st.session_state.user_email = "demo@local"
            st.session_state.user_name = "Demo"
            st.session_state.user_logged_in = True
            st.rerun()

    return False


def handle_legacy_google_logout() -> None:
    keys_to_clear = [
        "user_email",
        "user_name",
        "user_picture",
        "user_logged_in",
        "oauth_credentials",
        "oauth_state",
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
