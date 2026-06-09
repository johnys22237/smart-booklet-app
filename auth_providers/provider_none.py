import streamlit as st
import re


def _is_valid_email(email: str) -> bool:
    """Validação simples de email para fallback manual."""
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""))


def activate_manual_fallback_user(email: str, first_name: str, last_name: str) -> tuple[bool, str]:
    """Ativa sessão manual de usuário para contornar loop de autenticação."""
    safe_email = (email or "").strip().lower()
    safe_first = (first_name or "").strip()
    safe_last = (last_name or "").strip()

    if not _is_valid_email(safe_email):
        return False, "Informe um email válido."

    display_name = f"{safe_first} {safe_last}".strip()
    if not display_name:
        display_name = safe_email.split("@")[0]

    st.session_state.user_logged_in = True
    st.session_state.user_email = safe_email
    st.session_state.user_name = display_name
    st.session_state.user_picture = ""
    st.session_state.manual_auth_fallback = True
    return True, "ok"


def render_no_auth_login() -> bool:
    """Bypass de autenticação para destravar acesso ao app."""
    if not st.session_state.get("user_logged_in", False):
        st.session_state.user_logged_in = True
        st.session_state.user_email = st.session_state.get("user_email") or "guest@local"
        st.session_state.user_name = st.session_state.get("user_name") or "Guest User"
        st.session_state.user_picture = st.session_state.get("user_picture") or ""
    return True


def handle_no_auth_logout() -> None:
    """Logout no modo sem autenticação mantém acesso liberado."""
    st.session_state.user_logged_in = True
    st.session_state.user_email = st.session_state.get("user_email") or "guest@local"
    st.session_state.user_name = st.session_state.get("user_name") or "Guest User"
    st.session_state.user_picture = st.session_state.get("user_picture") or ""
