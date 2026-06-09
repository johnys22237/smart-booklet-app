import os
import streamlit as st

from auth_providers.provider_legacy_google import render_legacy_google_login, handle_legacy_google_logout
from auth_providers.provider_streamlit_oidc import render_streamlit_oidc_login, handle_streamlit_oidc_logout
from auth_providers.provider_none import render_no_auth_login, handle_no_auth_logout

# Provider padrão inicia no método novo Streamlit, conforme solicitado.
AUTH_PROVIDER = "STREAMLIT_OIDC"


def get_auth_provider() -> str:
    """Retorna o provider ativo de autenticação."""
    configured = os.environ.get("AUTH_PROVIDER", AUTH_PROVIDER)
    provider = str(configured).strip().upper()
    valid = {"STREAMLIT_OIDC", "GOOGLE_LEGACY", "NONE"}
    if provider not in valid:
        provider = "STREAMLIT_OIDC"
    return provider


def ensure_auth_state() -> None:
    """Garante que as chaves de sessão usadas pelo app existam."""
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "user_name" not in st.session_state:
        st.session_state.user_name = None
    if "user_picture" not in st.session_state:
        st.session_state.user_picture = ""
    if "user_logged_in" not in st.session_state:
        st.session_state.user_logged_in = False


def require_auth() -> bool:
    """Executa o fluxo de autenticação do provider atual e retorna se usuário está autenticado."""
    ensure_auth_state()
    provider = get_auth_provider()

    if provider == "STREAMLIT_OIDC":
        return render_streamlit_oidc_login()
    if provider == "GOOGLE_LEGACY":
        return render_legacy_google_login()
    return render_no_auth_login()


def auth_logout() -> None:
    """Executa logout no provider ativo."""
    provider = get_auth_provider()

    if provider == "STREAMLIT_OIDC":
        handle_streamlit_oidc_logout()
        return
    if provider == "GOOGLE_LEGACY":
        handle_legacy_google_logout()
        return
    handle_no_auth_logout()
