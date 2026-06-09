import streamlit as st


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
