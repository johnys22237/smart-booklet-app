import streamlit as st
import time


def _get_streamlit_provider_name() -> str | None:
    """Retorna provider nomeado se estiver configurado em [auth.<provider>]."""
    auth_cfg = st.secrets.get("auth", {})
    if isinstance(auth_cfg, dict) and isinstance(auth_cfg.get("google"), dict):
        return "google"
    return None


def _start_streamlit_login() -> None:
    """Dispara login OIDC do Streamlit com provider nomeado quando disponível."""
    st.session_state.oidc_login_started_at = time.time()
    provider = _get_streamlit_provider_name()
    if provider:
        st.login(provider)
        return
    st.login()


def _sanitize_stale_callback_query_params() -> None:
    """Limpa parâmetros residuais de callback que podem reativar loop de autenticação."""
    try:
        has_oauth_params = any(k in st.query_params for k in ["code", "state", "provider", "error"])
        if not has_oauth_params:
            return

        # Se não houve tentativa de login recente, tratamos como callback stale.
        started_at = st.session_state.get("oidc_login_started_at", 0)
        recent_login_attempt = (time.time() - float(started_at)) < 30

        if not recent_login_attempt:
            st.query_params.clear()
            st.rerun()
    except Exception:
        pass


def _sync_user_from_streamlit() -> bool:
    """Sincroniza informações de usuário do st.user para session_state."""
    user = getattr(st, "user", None)
    is_logged_in = bool(getattr(user, "is_logged_in", False)) if user is not None else False

    if not is_logged_in:
        st.session_state.user_logged_in = False
        return False

    email = getattr(user, "email", None)
    name = getattr(user, "name", None)
    picture = getattr(user, "picture", None)

    st.session_state.user_logged_in = True
    st.session_state.user_email = email or st.session_state.get("user_email") or ""
    st.session_state.user_name = name or email or st.session_state.get("user_name") or "Usuário"
    st.session_state.user_picture = picture or st.session_state.get("user_picture") or ""

    # Evita replay de callback OAuth na Cloud quando a URL fica com params antigos.
    try:
        if any(k in st.query_params for k in ["code", "state", "provider"]):
            st.query_params.clear()
    except Exception:
        pass

    return True


def render_streamlit_oidc_login() -> bool:
    """Renderiza login usando OIDC nativo do Streamlit."""
    _sanitize_stale_callback_query_params()

    if _sync_user_from_streamlit():
        return True

    lang = st.session_state.get("ui_language", "pt")

    st.markdown("""
    <style>
    .login-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem;
        border-radius: 20px;
        text-align: center;
        color: white;
        margin: 2rem auto;
        max-width: 500px;
    }
    </style>
    """, unsafe_allow_html=True)

    if lang == "pt":
        title = "📚 Smart YouTube Booklet"
        subtitle = "Transforme playlists do YouTube em apostilas educacionais"
        login_text = "Faça login com sua conta Google para continuar"
        btn_text = "Entrar com Google"
    else:
        title = "📚 Smart YouTube Booklet"
        subtitle = "Transform YouTube playlists into educational booklets"
        login_text = "Login with your Google account to continue"
        btn_text = "Sign in with Google"

    st.markdown(
        f"""
        <div class=\"login-container\">
            <h1>{title}</h1>
            <p>{subtitle}</p>
            <p>{login_text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button(btn_text, type="primary", use_container_width=True):
            _start_streamlit_login()
            st.stop()

    return False


def handle_streamlit_oidc_logout() -> None:
    """Logout com OIDC nativo do Streamlit."""
    st.logout()
