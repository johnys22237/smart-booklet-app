"""
Smart YouTube Booklet - Gerador de Apostilas a partir de Playlists do YouTube
Uma aplicação Streamlit que transforma playlists do YouTube em apostilas em PDF com resumos e explicações detalhadas.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import re
import pytz

# Importações para YouTube e API
import googleapiclient.discovery
# yt_dlp removido - causa bloqueios de IP em servidores web
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

# Importações para Gemini
import google.generativeai as genai

# Importações para PDF
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors

# Importação para Google OAuth
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import google.auth.transport.requests

# ==================== CONFIGURAÇÕES DE MONETIZAÇÃO ====================

# Seu email (para exceção de limites) - Configure via st.secrets ou variável de ambiente
ADMIN_EMAIL = st.secrets.get("ADMIN_EMAIL", os.environ.get("ADMIN_EMAIL", "johny.jvc@gmail.com"))

# Limite máximo de vídeos por apostila
MAX_VIDEOS_PER_BOOKLET = 5

# Limite de apostilas grátis por dia
FREE_BOOKLETS_PER_DAY = 3

# Dias de assinatura premium
PREMIUM_DAYS = 30

# Link de pagamento Mercado Pago
MERCADO_PAGO_LINK = "https://mpago.la/2GxAskk"

# Timezone de Brasília
BRASILIA_TZ = pytz.timezone('America/Sao_Paulo')

# ==================== CONFIGURAÇÕES GOOGLE OAUTH ====================

# Credenciais OAuth do Google Cloud Console
# Configure estas variáveis no Streamlit Cloud Secrets ou .streamlit/secrets.toml
GOOGLE_CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", os.environ.get("GOOGLE_CLIENT_ID", ""))
GOOGLE_CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", os.environ.get("GOOGLE_CLIENT_SECRET", ""))

# URL de redirecionamento - ajuste para produção
# Local: http://localhost:8501
# Produção: https://seu-app.streamlit.app
REDIRECT_URI = st.secrets.get("REDIRECT_URI", os.environ.get("REDIRECT_URI", "http://localhost:8501"))

# Scopes necessários para autenticação
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(
    page_title="Smart YouTube Booklet",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Credenciais
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", os.environ.get("YOUTUBE_API_KEY", ""))
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

# ==================== INTERNACIONALIZAÇÃO (i18n) ====================

# Idiomas disponíveis para interface
UI_LANGUAGES = {
    "pt": "🇧🇷 Português",
    "en": "🇬🇧 English"
}

# Idiomas disponíveis para a apostila gerada
BOOKLET_LANGUAGES = {
    "pt": "🇧🇷 Português",
    "en": "🇬🇧 English", 
    "es": "🇪🇸 Español"
}

# Traduções da interface
TRANSLATIONS = {
    "pt": {
        # Navegação
        "nav_home": "Início",
        "nav_generator": "Gerar Apostila",
        "nav_info": "Informações",
        "nav_title": "Navegação",
        
        # Sidebar
        "sidebar_language": "Idioma da Interface",
        "sidebar_select_language": "Selecione o idioma:",
        "sidebar_model": "Modelo de IA",
        "sidebar_select_model": "Escolha o modelo:",
        "sidebar_model_help": "Gemini 2.5 Flash é mais preciso. Gemini 1.5 Flash-8B é mais econômico.",
        "sidebar_info": "📌 Informações",
        "sidebar_version": "Versão",
        "sidebar_technologies": "Tecnologias",
        "sidebar_languages": "Idiomas",
        "sidebar_year": "Ano",
        "sidebar_links": "🔗 Links",
        
        # Header
        "header_title": "📚 Smart YouTube Booklet",
        "header_subtitle": "Transforme Playlists do YouTube em Apostilas Profissionais em PDF",
        
        # Home
        "home_what_is": "🎯 O que é Smart YouTube Booklet?",
        "home_description": """O **Smart YouTube Booklet** é uma aplicação revolucionária que utiliza Inteligência Artificial para 
transformar playlists educacionais do YouTube em apostilas profissionais em PDF. 

Combinando a potência da API do YouTube com o modelo avançado de IA Gemini, nossa ferramenta:""",
        "home_feature1_title": "🎥 Processa Playlists Inteiras",
        "home_feature1_desc": "Cole o link da sua playlist e deixe conosco! Nossa aplicação automaticamente navega por todos os vídeos e extrai as informações relevantes.",
        "home_feature2_title": "📝 Transcrições Automáticas",
        "home_feature2_desc": "Utilizamos a API do YouTube para extrair transcrições de cada vídeo, capturando 100% do conteúdo educacional.",
        "home_feature3_title": "🤖 IA Generativa (Gemini)",
        "home_feature3_desc": "Nossa IA analisa profundamente cada transcrição e gera resumos estruturados com conceitos, explicações detalhadas e exemplos práticos.",
        "home_feature4_title": "📖 Apostila em PDF",
        "home_feature4_desc": "Todos os resumos são compilados em uma apostila profissional e bem formatada, pronta para estudo ou impressão.",
        "home_main_features": "💎 Funcionalidades Principais",
        "home_features_list": """✅ **Acesso a Playlists Públicas** - Suporta playlists públicas do YouTube

✅ **Análise Inteligente** - Utiliza Gemini para gerar resumos contextualizados

✅ **Transcrições Multilingues** - Suporta português, inglês e mais idiomas

✅ **Estrutura Acadêmica** - Conceitos, explicações, exemplos e conclusões

✅ **PDF Profissional** - Formatação limpa e bem organizada

✅ **Histórico de Contexto** - IA mantém continuidade entre vídeos""",
        "home_how_to_use": "🚀 Como Usar",
        "home_how_to_steps": """1. Acesse a aba **"Gerar Apostila"** no menu lateral
2. Cole a URL da sua playlist do YouTube
3. Escolha o idioma da apostila
4. Clique em "Processar Playlist"
5. Acompanhe o progresso em tempo real
6. Faça o download da apostila em PDF""",
        "home_requirements": "⚙️ Requisitos",
        "home_requirements_list": """- Link de playlist do YouTube (pública)
- Conexão com internet
- Navegador moderno""",
        "home_tip1": "💡 **Dica**: Use playlists com transcrições disponíveis para melhores resultados",
        "home_tip2": "⏱️ **Tempo**: O processamento leva alguns minutos dependendo da quantidade de vídeos",
        "home_tip3": "📊 **Qualidade**: Quanto melhor a qualidade da transcrição, melhor o resultado",
        
        # Generator
        "gen_title": "📚 Gerar Apostila",
        "gen_input_label": "Cole o link da sua playlist do YouTube:",
        "gen_input_placeholder": "https://www.youtube.com/playlist?list=...",
        "gen_input_help": "Use uma playlist pública do YouTube",
        "gen_booklet_language": "🌐 Idioma da Apostila:",
        "gen_booklet_language_help": "A apostila será gerada neste idioma",
        "gen_process_button": "🚀 Processar",
        "gen_invalid_url": "❌ URL inválida! Por favor, verifique o link da playlist.",
        "gen_valid_urls": "Exemplos de URLs válidas:",
        "gen_searching": "🔍 Buscando vídeos da playlist...",
        "gen_error_playlist": "❌ Não foi possível obter os vídeos da playlist.",
        "gen_found_videos": "✅ Encontrados {count} vídeos na playlist!",
        "gen_view_videos": "📹 Ver {count} vídeos da playlist",
        "gen_processing": "⚙️ Processando Vídeos...",
        "gen_processing_video": "Processando {current}/{total}: **{title}**",
        "gen_no_transcript": "⚠️ Transcrição não disponível para: {title}",
        "gen_completed": "✅ Processamento concluído!",
        "gen_no_transcripts": "❌ Nenhuma transcrição foi processada. Verifique se a playlist possui vídeos com transcrições.",
        "gen_summaries_generated": "✅ {count} resumos gerados com sucesso!",
        "gen_summaries_title": "📋 Resumos Gerados",
        "gen_summary": "Resumo:",
        "gen_concepts": "Conceitos:",
        "gen_detailed_explanations": "Explicações Detalhadas:",
        "gen_generate_pdf": "📄 Gerar PDF",
        "gen_download_pdf": "📥 Gerar e Baixar PDF",
        "gen_click_download": "✅ Clique para Baixar",
        "gen_pdf_success": "✅ PDF gerado com sucesso!",
        "gen_pdf_error": "❌ Erro ao gerar PDF: {error}",
        "gen_save_json": "💾 Salvar Resumos em JSON",
        "gen_json_success": "✅ Resumos salvos em JSON!",
        "gen_generating_pdf": "🔨 Gerando PDF...",
        
        # Info page
        "info_title": "ℹ️ Informações",
        "info_active_model": "🤖 **Modelo ativo**: {name} - {description}",
        "info_about_title": "Sobre o Smart YouTube Booklet",
        "info_about_desc": """Esta aplicação foi desenvolvida para democratizar o acesso ao conhecimento,
transformando conteúdo educacional disponível no YouTube em materiais 
de estudo estruturados e acessíveis.""",
        "info_tech_title": "🛠️ Tecnologias Utilizadas",
        "info_models_title": "💰 Modelos de IA Disponíveis",
        "info_models_tip": "💡 **Dica**: O modelo 1.5 Flash-8B é ~50% mais barato e funciona bem para a maioria dos vídeos!",
        "info_how_works": "⚙️ Como Funciona",
        "info_resources": "✅ Recursos",
        "info_limitations": "⚠️ Limitações",
        "info_cost_estimate": "📊 Estimativa de Custos",
        "info_privacy": "🔒 Privacidade",
        "info_copyright": "Smart YouTube Booklet v4.0 © 2026 - Todos os direitos reservados",
        
        # Modelos
        "model_advanced": "Modelo mais avançado e preciso (recomendado)",
        "model_economic": "Modelo econômico (~50% mais barato)",
        
        # Monetização - v5
        "gen_select_videos": "Selecione os Vídeos",
        "gen_limit_reached": "Você atingiu o limite diário de apostilas gratuitas!",
        "gen_videos_limit": "Máximo de {max} vídeos por apostila",
        "gen_videos_selected": "{count}/{max} vídeos selecionados",
        "gen_generate_booklet": "Gerar Apostila ({count} vídeos)",
        "gen_select_at_least_one": "Selecione ao menos um vídeo!",
    },
    "en": {
        # Navigation
        "nav_home": "Home",
        "nav_generator": "Generate Booklet",
        "nav_info": "Information",
        "nav_title": "Navigation",
        
        # Sidebar
        "sidebar_language": "Interface Language",
        "sidebar_select_language": "Select language:",
        "sidebar_model": "AI Model",
        "sidebar_select_model": "Choose model:",
        "sidebar_model_help": "Gemini 2.5 Flash is more accurate. Gemini 1.5 Flash-8B is more economical.",
        "sidebar_info": "📌 Information",
        "sidebar_version": "Version",
        "sidebar_technologies": "Technologies",
        "sidebar_languages": "Languages",
        "sidebar_year": "Year",
        "sidebar_links": "🔗 Links",
        
        # Header
        "header_title": "📚 Smart YouTube Booklet",
        "header_subtitle": "Transform YouTube Playlists into Professional PDF Booklets",
        
        # Home
        "home_what_is": "🎯 What is Smart YouTube Booklet?",
        "home_description": """**Smart YouTube Booklet** is a revolutionary application that uses Artificial Intelligence to 
transform educational YouTube playlists into professional PDF booklets. 

Combining the power of the YouTube API with the advanced Gemini AI model, our tool:""",
        "home_feature1_title": "🎥 Process Entire Playlists",
        "home_feature1_desc": "Paste your playlist link and let us handle it! Our application automatically navigates through all videos and extracts relevant information.",
        "home_feature2_title": "📝 Automatic Transcriptions",
        "home_feature2_desc": "We use the YouTube API to extract transcriptions from each video, capturing 100% of educational content.",
        "home_feature3_title": "🤖 Generative AI (Gemini)",
        "home_feature3_desc": "Our AI deeply analyzes each transcript and generates structured summaries with concepts, detailed explanations and practical examples.",
        "home_feature4_title": "📖 PDF Booklet",
        "home_feature4_desc": "All summaries are compiled into a professional and well-formatted booklet, ready for study or printing.",
        "home_main_features": "💎 Main Features",
        "home_features_list": """✅ **Public Playlist Access** - Supports public YouTube playlists

✅ **Intelligent Analysis** - Uses Gemini to generate contextualized summaries

✅ **Multilingual Transcriptions** - Supports Portuguese, English and more languages

✅ **Academic Structure** - Concepts, explanations, examples and conclusions

✅ **Professional PDF** - Clean and well-organized formatting

✅ **Context History** - AI maintains continuity between videos""",
        "home_how_to_use": "🚀 How to Use",
        "home_how_to_steps": """1. Go to the **"Generate Booklet"** tab in the sidebar
2. Paste your YouTube playlist URL
3. Choose the booklet language
4. Click "Process Playlist"
5. Follow the progress in real time
6. Download your PDF booklet""",
        "home_requirements": "⚙️ Requirements",
        "home_requirements_list": """- YouTube playlist link (public)
- Internet connection
- Modern browser""",
        "home_tip1": "💡 **Tip**: Use playlists with available transcriptions for best results",
        "home_tip2": "⏱️ **Time**: Processing takes a few minutes depending on the number of videos",
        "home_tip3": "📊 **Quality**: The better the transcription quality, the better the result",
        
        # Generator
        "gen_title": "📚 Generate Booklet",
        "gen_input_label": "Paste your YouTube playlist link:",
        "gen_input_placeholder": "https://www.youtube.com/playlist?list=...",
        "gen_input_help": "Use a public YouTube playlist",
        "gen_booklet_language": "🌐 Booklet Language:",
        "gen_booklet_language_help": "The booklet will be generated in this language",
        "gen_process_button": "🚀 Process",
        "gen_invalid_url": "❌ Invalid URL! Please check the playlist link.",
        "gen_valid_urls": "Valid URL examples:",
        "gen_searching": "🔍 Searching playlist videos...",
        "gen_error_playlist": "❌ Could not get playlist videos.",
        "gen_found_videos": "✅ Found {count} videos in the playlist!",
        "gen_view_videos": "📹 View {count} playlist videos",
        "gen_processing": "⚙️ Processing Videos...",
        "gen_processing_video": "Processing {current}/{total}: **{title}**",
        "gen_no_transcript": "⚠️ Transcript not available for: {title}",
        "gen_completed": "✅ Processing completed!",
        "gen_no_transcripts": "❌ No transcripts were processed. Check if the playlist has videos with transcriptions.",
        "gen_summaries_generated": "✅ {count} summaries generated successfully!",
        "gen_summaries_title": "📋 Generated Summaries",
        "gen_summary": "Summary:",
        "gen_concepts": "Concepts:",
        "gen_detailed_explanations": "Detailed Explanations:",
        "gen_generate_pdf": "📄 Generate PDF",
        "gen_download_pdf": "📥 Generate and Download PDF",
        "gen_click_download": "✅ Click to Download",
        "gen_pdf_success": "✅ PDF generated successfully!",
        "gen_pdf_error": "❌ Error generating PDF: {error}",
        "gen_save_json": "💾 Save Summaries as JSON",
        "gen_json_success": "✅ Summaries saved as JSON!",
        "gen_generating_pdf": "🔨 Generating PDF...",
        
        # Info page
        "info_title": "ℹ️ Information",
        "info_active_model": "🤖 **Active model**: {name} - {description}",
        "info_about_title": "About Smart YouTube Booklet",
        "info_about_desc": """This application was developed to democratize access to knowledge,
transforming educational content available on YouTube into structured 
and accessible study materials.""",
        "info_tech_title": "🛠️ Technologies Used",
        "info_models_title": "💰 Available AI Models",
        "info_models_tip": "💡 **Tip**: The 1.5 Flash-8B model is ~50% cheaper and works well for most videos!",
        "info_how_works": "⚙️ How It Works",
        "info_resources": "✅ Resources",
        "info_limitations": "⚠️ Limitations",
        "info_cost_estimate": "📊 Cost Estimate",
        "info_privacy": "🔒 Privacy",
        "info_copyright": "Smart YouTube Booklet v4.0 © 2026 - All rights reserved",
        
        # Models
        "model_advanced": "Most advanced and accurate model (recommended)",
        "model_economic": "Economic model (~50% cheaper)",
        
        # Monetization - v5
        "gen_select_videos": "Select Videos",
        "gen_limit_reached": "You've reached the daily free booklet limit!",
        "gen_videos_limit": "Maximum of {max} videos per booklet",
        "gen_videos_selected": "{count}/{max} videos selected",
        "gen_generate_booklet": "Generate Booklet ({count} videos)",
        "gen_select_at_least_one": "Select at least one video!",
    }
}

def t(key: str, **kwargs) -> str:
    """Retorna a tradução para a chave especificada no idioma atual"""
    lang = st.session_state.get('ui_language', 'pt')
    text = TRANSLATIONS.get(lang, TRANSLATIONS['pt']).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text

# Modelos Gemini disponíveis
GEMINI_MODELS = {
    "gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash",
        "description_pt": "Modelo mais avançado e preciso (recomendado)",
        "description_en": "Most advanced and accurate model (recommended)",
        "price_input": "$0.30/1M tokens",
        "price_output": "$2.50/1M tokens",
        "context_window": "1M tokens"
    },
    "gemini-2.5-flash-lite": {
        "name": "Gemini 2.5 Flash-Lite",
        "description_pt": "Modelo econômico (~70% mais barato)",
        "description_en": "Economic model (~70% cheaper)",
        "price_input": "$0.10/1M tokens",
        "price_output": "$0.40/1M tokens",
        "context_window": "1M tokens"
    }
}

def get_model_description(model_key: str) -> str:
    """Retorna a descrição do modelo no idioma atual"""
    lang = st.session_state.get('ui_language', 'pt')
    model = GEMINI_MODELS.get(model_key, {})
    return model.get(f'description_{lang}', model.get('description_pt', ''))

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)

# ==================== SISTEMA DE MONETIZAÇÃO ====================

def get_brasilia_date():
    """Retorna a data atual no fuso de Brasília"""
    return datetime.now(BRASILIA_TZ).date()

def init_monetization_state():
    """Inicializa variáveis de estado para monetização"""
    # Modo dev (bypass de limites)
    if 'dev_mode' not in st.session_state:
        st.session_state.dev_mode = False
    
    # Controle de anúncio inicial
    if 'app_liberado' not in st.session_state:
        st.session_state.app_liberado = False
    
    # Autenticação (simulada por enquanto, substituir por Google OAuth)
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'user_name' not in st.session_state:
        st.session_state.user_name = None
    if 'user_logged_in' not in st.session_state:
        st.session_state.user_logged_in = False
    
    # Contagem de apostilas do dia
    if 'booklets_today' not in st.session_state:
        st.session_state.booklets_today = 0
    if 'last_count_date' not in st.session_state:
        st.session_state.last_count_date = get_brasilia_date().isoformat()
    
    # Premium status
    if 'is_premium' not in st.session_state:
        st.session_state.is_premium = False
    if 'premium_expiry' not in st.session_state:
        st.session_state.premium_expiry = None

def reset_daily_count_if_needed():
    """Reseta o contador de apostilas se for um novo dia em Brasília"""
    today = get_brasilia_date().isoformat()
    if st.session_state.last_count_date != today:
        st.session_state.booklets_today = 0
        st.session_state.last_count_date = today

def is_admin_user():
    """Verifica se o usuário logado é o admin"""
    return st.session_state.get('user_email', '').lower() == ADMIN_EMAIL.lower()

def can_generate_booklet():
    """Verifica se o usuário pode gerar uma apostila"""
    # Modo dev = sem limites
    if st.session_state.get('dev_mode', False):
        return True, ""
    
    # Admin = sem limites
    if is_admin_user():
        return True, ""
    
    # Premium ativo = sem limites
    if st.session_state.get('is_premium', False):
        expiry = st.session_state.get('premium_expiry')
        if expiry:
            expiry_date = datetime.fromisoformat(expiry).date()
            if get_brasilia_date() <= expiry_date:
                return True, ""
            else:
                # Premium expirou
                st.session_state.is_premium = False
                st.session_state.premium_expiry = None
    
    # Checar limite diário
    reset_daily_count_if_needed()
    if st.session_state.booklets_today >= FREE_BOOKLETS_PER_DAY:
        return False, "daily_limit_reached"
    
    return True, ""

def increment_booklet_count():
    """Incrementa o contador de apostilas do dia"""
    if not st.session_state.get('dev_mode', False) and not is_admin_user():
        st.session_state.booklets_today += 1

def get_remaining_booklets():
    """Retorna quantas apostilas restam hoje"""
    if st.session_state.get('dev_mode', False) or is_admin_user():
        return "∞"
    if st.session_state.get('is_premium', False):
        return "∞"
    reset_daily_count_if_needed()
    return FREE_BOOKLETS_PER_DAY - st.session_state.booklets_today

def activate_premium():
    """Ativa o status premium por 30 dias"""
    st.session_state.is_premium = True
    expiry = get_brasilia_date() + timedelta(days=PREMIUM_DAYS)
    st.session_state.premium_expiry = expiry.isoformat()

def liberar_acesso():
    """Callback para liberar acesso após visualizar anúncio"""
    st.session_state.app_liberado = True

def show_lock_screen():
    """Exibe tela de bloqueio com anúncio"""
    st.markdown("""
    <style>
    .lock-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        color: white;
        margin: 2rem 0;
    }
    .lock-title {
        font-size: 2rem;
        margin-bottom: 1rem;
    }
    .lock-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-bottom: 2rem;
    }
    .ad-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1.5rem 0;
        min-height: 250px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    lang = st.session_state.get('ui_language', 'pt')
    
    if lang == 'pt':
        title = "📚 Smart YouTube Booklet"
        subtitle = "Para acessar o app gratuitamente, por favor visualize o anúncio abaixo"
        btn_text = "🔓 Já visualizei o anúncio - LIBERAR APP"
        wait_text = "Por favor, aguarde alguns segundos antes de liberar..."
    else:
        title = "📚 Smart YouTube Booklet"
        subtitle = "To access the app for free, please view the ad below"
        btn_text = "🔓 I've viewed the ad - UNLOCK APP"
        wait_text = "Please wait a few seconds before unlocking..."
    
    st.markdown(f"""
    <div class="lock-container">
        <div class="lock-title">{title}</div>
        <div class="lock-subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Container do anúncio
    st.markdown('<div class="ad-container">', unsafe_allow_html=True)
    
    # Aqui vai o script do anúncio - substituir pelo seu próprio
    # Exemplo usando pl28325401.effectivegatecpm.com como na referência:
    ad_html = """
    <div style="text-align: center; padding: 20px;">
        <p style="color: #666; font-size: 0.9rem;">📢 Espaço para anúncio</p>
        <p style="color: #999; font-size: 0.8rem;">Ad placeholder - configure seu provedor de anúncios aqui</p>
        <!-- Substitua pelo script do seu provedor de anúncios -->
        <!--
        <script type="text/javascript">
            atOptions = {
                'key' : 'seu_key_aqui',
                'format' : 'iframe',
                'height' : 250,
                'width' : 300,
                'params' : {}
            };
        </script>
        <script type="text/javascript" src="//seu-provedor-de-anuncios.com/invoke.js"></script>
        -->
    </div>
    """
    components.html(ad_html, height=280)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.info(wait_text)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.button(btn_text, on_click=liberar_acesso, type="primary", use_container_width=True)

def show_payment_popup():
    """Exibe popup para pagamento quando limite é atingido"""
    lang = st.session_state.get('ui_language', 'pt')
    
    if lang == 'pt':
        title = "🍺 Me pague uma cerveja para continuar!"
        msg = f"""
        Você atingiu o limite de **{FREE_BOOKLETS_PER_DAY} apostilas gratuitas** por dia.
        
        Para continuar usando sem limites por **30 dias**, faça uma contribuição de **R$ 23,00**.
        
        Após o pagamento:
        1. Anote o email usado na transação
        2. Clique no botão abaixo para confirmar
        """
        pay_btn = "💳 Pagar R$ 23,00 (Mercado Pago)"
        confirm_btn = "✅ Já paguei - Ativar Premium"
        cancel_btn = "❌ Cancelar"
        email_label = "Email usado no pagamento:"
        success_msg = "🎉 Premium ativado por 30 dias!"
    else:
        title = "🍺 Buy me a beer to continue!"
        msg = f"""
        You've reached the limit of **{FREE_BOOKLETS_PER_DAY} free booklets** per day.
        
        To continue using without limits for **30 days**, make a contribution of **R$ 23.00** (~$4.50 USD).
        
        After payment:
        1. Note the email used in the transaction
        2. Click the button below to confirm
        """
        pay_btn = "💳 Pay R$ 23.00 (Mercado Pago)"
        confirm_btn = "✅ I've paid - Activate Premium"
        cancel_btn = "❌ Cancel"
        email_label = "Email used for payment:"
        success_msg = "🎉 Premium activated for 30 days!"
    
    st.markdown("""
    <style>
    .payment-popup {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown(f"### {title}")
        st.markdown(msg)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.link_button(pay_btn, MERCADO_PAGO_LINK, type="primary", use_container_width=True)
        
        with col2:
            # Popup de confirmação de pagamento
            with st.expander(confirm_btn):
                payment_email = st.text_input(email_label, key="payment_email")
                if st.button("✅ Confirmar", key="confirm_payment"):
                    if payment_email:
                        # TODO: Implementar verificação real via API do Mercado Pago
                        # Por enquanto, aceita qualquer email como confirmação
                        activate_premium()
                        st.success(success_msg)
                        st.rerun()
                    else:
                        st.warning("Por favor, informe o email usado no pagamento." if lang == 'pt' else "Please enter the email used for payment.")

def show_dev_toggle():
    """Força o modo DEV ou USER automático baseado no email do usuário"""
    # Inicializar dev_mode se não existir
    if 'dev_mode' not in st.session_state:
        st.session_state.dev_mode = is_admin_user()
    
    # Se o usuário estiver logado, forçar o modo correto
    if st.session_state.get('user_logged_in', False):
        # Admin = DEV MODE automático
        if is_admin_user():
            st.session_state.dev_mode = True
        # Usuário normal = USER MODE automático (forçado)
        else:
            st.session_state.dev_mode = False
    
    # Mostrar status do modo (apenas informativo, não permite mudar)
    with st.sidebar:
        st.divider()
        
        if st.session_state.get('dev_mode', False):
            st.success("🛠️ DEV MODE (Admin)" if st.session_state.get('ui_language', 'pt') == 'pt' else "🛠️ DEV MODE (Admin)")
        else:
            st.info("👤 USER MODE (com limites)" if st.session_state.get('ui_language', 'pt') == 'pt' else "👤 USER MODE (with limits)")

def show_user_status():
    """Mostra status do usuário na sidebar"""
    lang = st.session_state.get('ui_language', 'pt')
    
    with st.sidebar:
        st.divider()
        
        # Status de login
        if st.session_state.get('user_logged_in', False):
            user_name = st.session_state.get('user_name', 'Usuário')
            user_email = st.session_state.get('user_email', '')
            st.markdown(f"👤 **{user_name}**")
            st.caption(user_email)
            
            if is_admin_user():
                st.success("👑 Admin" if lang == 'pt' else "👑 Admin")
            elif st.session_state.get('is_premium', False):
                expiry = st.session_state.get('premium_expiry', '')
                st.success(f"⭐ Premium até {expiry}" if lang == 'pt' else f"⭐ Premium until {expiry}")
            else:
                remaining = get_remaining_booklets()
                st.info(f"📚 Apostilas restantes hoje: {remaining}" if lang == 'pt' else f"📚 Booklets remaining today: {remaining}")
        else:
            st.warning("⚠️ Faça login para usar o app" if lang == 'pt' else "⚠️ Please login to use the app")

# ==================== AUTENTICAÇÃO GOOGLE OAUTH ====================

import requests
import uuid

def get_google_auth_url():
    """Gera a URL de autenticação do Google OAuth usando requisições diretas"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return None
    
    try:
        redirect_uri = st.secrets.get("REDIRECT_URI", os.environ.get("REDIRECT_URI", "http://localhost:8501"))
        
        # Gerar um state aleatório para verificação de segurança
        state = str(uuid.uuid4())
        st.session_state.oauth_state = state
        
        # Construir a URL de autenticação do Google
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"access_type=offline&"
            f"prompt=consent&"
            f"state={state}"
        )
        
        return auth_url
    except Exception as e:
        return None

def handle_oauth_callback():
    """Processa o callback do OAuth após login do Google"""
    query_params = st.query_params
    
    if "code" in query_params:
        code = query_params.get("code")
        state = query_params.get("state")
        
        try:
            # Validar state
            if state != st.session_state.get("oauth_state"):
                st.error("❌ State mismatch - possível ataque CSRF")
                return False
            
            redirect_uri = st.secrets.get("REDIRECT_URI", os.environ.get("REDIRECT_URI", "http://localhost:8501"))
            
            # Trocar código por token
            token_response = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            
            if token_response.status_code != 200:
                st.error(f"❌ Erro ao obter token: {token_response.text}")
                return False
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                st.error("❌ Não foi possível obter o token de acesso")
                return False
            
            # Obter informações do usuário
            userinfo_response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code == 200:
                userinfo = userinfo_response.json()
                
                # Salvar dados do usuário no session_state
                st.session_state.user_email = userinfo.get("email", "")
                st.session_state.user_name = userinfo.get("name", userinfo.get("email", "Usuário"))
                st.session_state.user_picture = userinfo.get("picture", "")
                st.session_state.user_logged_in = True
                st.session_state.oauth_token = access_token
                
                # Limpar parâmetros da URL
                st.query_params.clear()
                st.rerun()
                
                return True
            else:
                st.error(f"❌ Erro ao obter informações do usuário: {userinfo_response.status_code}")
                return False
                
        except Exception as e:
            st.error(f"❌ Erro na autenticação: {str(e)}")
            return False
        finally:
            # Sempre limpar parâmetros da URL
            if "code" in st.query_params:
                st.query_params.clear()
    
    return False

def show_login_screen():
    """Exibe tela de login com Google OAuth"""
    lang = st.session_state.get('ui_language', 'pt')
    
    # Verificar callback OAuth primeiro
    if handle_oauth_callback():
        st.rerun()
        return
    
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
    .login-title {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    .login-subtitle {
        font-size: 1.2rem;
        opacity: 0.9;
        margin-bottom: 2rem;
    }
    .google-btn {
        background: white;
        color: #333 !important;
        padding: 14px 28px;
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        font-weight: 600;
        font-size: 16px;
        text-decoration: none !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
        width: 100%;
        max-width: 300px;
        margin: 20px auto;
    }
    .google-btn:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        transform: translateY(-2px);
    }
    .google-icon {
        width: 20px;
        height: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if lang == 'pt':
        title = "📚 Smart YouTube Booklet"
        subtitle = "Transforme playlists do YouTube em apostilas educacionais"
        login_text = "Faça login com sua conta Google para continuar"
        btn_text = "Entrar com Google"
        error_config = "⚠️ OAuth não configurado. Configure as credenciais no Google Cloud Console."
    else:
        title = "📚 Smart YouTube Booklet"
        subtitle = "Transform YouTube playlists into educational booklets"
        login_text = "Login with your Google account to continue"
        btn_text = "Sign in with Google"
        error_config = "⚠️ OAuth not configured. Configure credentials in Google Cloud Console."
    
    st.markdown(f"""
    <div class="login-container">
        <div class="login-title">{title}</div>
        <div class="login-subtitle">{subtitle}</div>
        <p>{login_text}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Gerar URL de autenticação
        auth_url = get_google_auth_url()
        
        if auth_url:
            # Botão de login real com Google
            google_logo = "https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
            
            st.markdown(f"""
            <a href="{auth_url}" class="google-btn" target="_self">
                <img src="{google_logo}" class="google-icon" alt="Google">
                {btn_text}
            </a>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Informação sobre privacidade
            if lang == 'pt':
                st.caption("🔒 Usamos apenas seu email e nome para identificação. Não acessamos nenhum outro dado da sua conta Google.")
            else:
                st.caption("🔒 We only use your email and name for identification. We don't access any other data from your Google account.")
        
        else:
            # OAuth não configurado - mostrar erro ou modo demo para desenvolvimento
            st.error(error_config)
            
            st.markdown("---")
            
            # Modo demo para desenvolvimento local
            if lang == 'pt':
                st.markdown("**🔧 Modo Desenvolvimento (apenas local):**")
            else:
                st.markdown("**🔧 Development Mode (local only):**")
            
            demo_email = st.text_input("Email:", key="demo_email", placeholder="seu@email.com")
            demo_name = st.text_input("Nome:", key="demo_name", placeholder="Seu Nome")
            
            if st.button("🔐 Entrar (Demo)", type="primary", use_container_width=True):
                if demo_email and demo_name:
                    st.session_state.user_email = demo_email
                    st.session_state.user_name = demo_name
                    st.session_state.user_logged_in = True
                    st.rerun()
                else:
                    st.error("Por favor, preencha email e nome." if lang == 'pt' else "Please fill in email and name.")

def logout_user():
    """Faz logout do usuário"""
    keys_to_clear = ['user_email', 'user_name', 'user_picture', 'user_logged_in', 
                     'oauth_credentials', 'oauth_state']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

# Inicializar session_state
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "gemini-2.5-flash"
if 'ui_language' not in st.session_state:
    st.session_state.ui_language = "pt"
if 'booklet_language' not in st.session_state:
    st.session_state.booklet_language = "pt"

# Inicializar monetização
init_monetization_state()

def get_gemini_model():
    """Retorna o modelo Gemini selecionado pelo usuário"""
    return genai.GenerativeModel(st.session_state.selected_model)

# ==================== FORMATAÇÃO DE FÓRMULAS ====================

def format_formula_unicode(formula: str) -> str:
    """
    Converte fórmulas matemáticas para notação com tags HTML do ReportLab.
    Usa <sub> e <super> que são suportados nativamente pelo ReportLab.
    
    IMPORTANTE: Só converte símbolos quando são palavras isoladas (não parte de texto comum).
    Exemplo: F_m = |q| * v * B * sen(theta) → F<sub>m</sub> = |q| · v · B · sen(θ)
    """
    if not formula:
        return formula
    
    result = formula
    
    # ==================== SÍMBOLOS GREGOS (COMPLETOS) ====================
    # Usa word boundary (\b) para não substituir dentro de palavras
    greek_map = {
        # Minúsculas - ordenar por tamanho decrescente para evitar conflitos
        r'\bepsilon\b': 'ε',
        r'\bomicron\b': 'ο',
        r'\bupsilon\b': 'υ',
        r'\blambda\b': 'λ',
        r'\bsigma\b': 'σ',
        r'\btheta\b': 'θ',
        r'\bkappa\b': 'κ',
        r'\bgamma\b': 'γ',
        r'\bdelta\b': 'δ',
        r'\balpha\b': 'α',
        r'\bomega\b': 'ω',
        r'\bzeta\b': 'ζ',
        r'\biota\b': 'ι',
        r'\bbeta\b': 'β',
        r'(?<![a-zA-Z])eta(?![a-zA-Z])': 'η',  # eta - padrão especial para não conflitar com beta
        r'\bphi\b': 'φ',
        r'\bchi\b': 'χ',
        r'\bpsi\b': 'ψ',
        r'\brho\b': 'ρ',
        r'\btau\b': 'τ',
        r'\bmu\b': 'μ',
        r'\bnu\b': 'ν',
        r'\bxi\b': 'ξ',
        r'\bpi\b': 'π',
        r'\bomega\b': 'ω',
        # Maiúsculas (mais comuns)
        r'\bAlpha\b': 'Α',
        r'\bBeta\b': 'Β',
        r'\bGamma\b': 'Γ',
        r'\bDelta\b': 'Δ',
        r'\bTheta\b': 'Θ',
        r'\bLambda\b': 'Λ',
        r'\bPi\b': 'Π',
        r'\bSigma\b': 'Σ',
        r'\bPhi\b': 'Φ',
        r'\bPsi\b': 'Ψ',
        r'\bOmega\b': 'Ω',
    }
    
    # Aplicar substituições gregas com regex (case sensitive)
    for pattern, symbol in greek_map.items():
        result = re.sub(pattern, symbol, result)
    
    # ==================== OPERADORES E SÍMBOLOS MATEMÁTICOS ====================
    # Ordem importa: substituir padrões maiores primeiro
    
    # Operadores compostos (substituir ANTES dos simples)
    result = result.replace('**', ' · ')      # Potência como multiplicação
    result = result.replace('<=', '≤')        # Menor ou igual
    result = result.replace('>=', '≥')        # Maior ou igual
    result = result.replace('!=', '≠')        # Diferente
    result = result.replace('==', '=')        # Igual (programação)
    result = result.replace('+-', '±')        # Mais ou menos
    result = result.replace('-+', '∓')        # Menos ou mais
    result = result.replace('...', '…')       # Reticências
    result = result.replace('->', '→')        # Seta direita
    result = result.replace('<-', '←')        # Seta esquerda
    result = result.replace('<->', '↔')       # Seta dupla
    result = result.replace('=>', '⇒')        # Implica
    result = result.replace('<=>', '⇔')       # Se e somente se
    
    # Multiplicação (substituir * por · mas com cuidado)
    # Não substituir se for parte de ** (já tratado acima)
    result = re.sub(r'(?<!\*)\*(?!\*)', ' · ', result)
    
    # ==================== FUNÇÕES MATEMÁTICAS COM SÍMBOLOS ====================
    # Usar word boundary para não afetar texto comum
    
    # Raiz quadrada - só quando isolado ou no início de expressão
    result = re.sub(r'\bsqrt\b', '√', result)
    
    # Infinito - MUITO IMPORTANTE: só quando é palavra isolada
    # NÃO substitui "inf" dentro de "infinito", "informação", "influenciaram", etc.
    result = re.sub(r'\binf\b(?![a-zA-Záéíóúâêîôûãõàèìòùç])', '∞', result)
    
    # Somatório
    result = re.sub(r'\bsum\b', 'Σ', result)
    result = re.sub(r'\bSum\b', 'Σ', result)
    result = re.sub(r'\bSUM\b', 'Σ', result)
    
    # Produto
    result = re.sub(r'\bprod\b', 'Π', result)
    result = re.sub(r'\bProd\b', 'Π', result)
    
    # Integral
    result = re.sub(r'\bint\b(?![a-zA-Z])', '∫', result)  # Cuidado com "integer", "into"
    result = re.sub(r'\bintegral\b', '∫', result)
    
    # Derivada parcial
    result = re.sub(r'\bpartial\b', '∂', result)
    
    # Nabla/Gradiente
    result = re.sub(r'\bnabla\b', '∇', result)
    result = re.sub(r'\bgrad\b', '∇', result)
    
    # Para todo / Existe
    result = re.sub(r'\bforall\b', '∀', result)
    result = re.sub(r'\bexists\b', '∃', result)
    
    # Pertence / Não pertence
    result = re.sub(r'\bin\b(?=\s*[A-Z{])', '∈', result)  # "in" só quando seguido de conjunto
    result = re.sub(r'\bnotin\b', '∉', result)
    
    # Subconjunto
    result = re.sub(r'\bsubset\b', '⊂', result)
    result = re.sub(r'\bsubseteq\b', '⊆', result)
    result = re.sub(r'\bsupset\b', '⊃', result)
    result = re.sub(r'\bsupseteq\b', '⊇', result)
    
    # União / Interseção
    result = re.sub(r'\bunion\b', '∪', result)
    result = re.sub(r'\bintersect\b', '∩', result)
    
    # Aproximadamente
    result = re.sub(r'\bapprox\b', '≈', result)
    result = result.replace('~=', '≈')
    result = result.replace('~~', '≈')
    
    # Proporcional
    result = re.sub(r'\bpropto\b', '∝', result)
    
    # Perpendicular / Paralelo
    result = re.sub(r'\bperp\b', '⊥', result)
    result = result.replace('||', '∥')
    
    # Ângulo
    result = re.sub(r'\bangle\b', '∠', result)
    
    # Graus
    result = re.sub(r'\bdeg\b', '°', result)
    result = result.replace('^o', '°')
    result = result.replace('^O', '°')
    
    # Vezes (multiplicação)
    result = re.sub(r'\btimes\b', '×', result)
    
    # Divisão
    result = re.sub(r'\bdiv\b(?![a-zA-Z])', '÷', result)  # Cuidado com "divide", "division"
    
    # ==================== NOTAÇÕES CIENTÍFICAS ESPECÍFICAS ====================
    
    # Seno, Cosseno, Tangente (manter como texto mas formatar bonito)
    # Não substituir, apenas garantir que não sejam afetados
    
    # Log, ln, exp (manter como texto)
    
    # ==================== SUBSCRITOS (X_y ou X_{abc}) ====================
    def replace_subscript(match):
        base = match.group(1) if match.group(1) else ''
        sub_content = match.group(2)
        return f'{base}<sub>{sub_content}</sub>'
    
    # Padrão: letra_{conteudo} (com chaves) - processa primeiro
    result = re.sub(r'([A-Za-zα-ωΑ-Ω0-9])_\{([^}]+)\}', replace_subscript, result)
    
    # Padrão: letra_caractere (sem chaves, único caractere alfanumérico)
    # Inclui números e letras gregas
    result = re.sub(r'([A-Za-zα-ωΑ-Ω0-9])_([A-Za-z0-9α-ωΑ-Ω])', replace_subscript, result)
    
    # ==================== SOBRESCRITOS/EXPOENTES (X^y ou X^{abc}) ====================
    def replace_superscript(match):
        base = match.group(1) if match.group(1) else ''
        sup_content = match.group(2)
        return f'{base}<super>{sup_content}</super>'
    
    # Padrão: base^{conteudo} (com chaves) - processa primeiro
    result = re.sub(r'([A-Za-z0-9α-ωΑ-Ω\)])?\^\{([^}]+)\}', replace_superscript, result)
    
    # Padrão: base^caractere (sem chaves)
    result = re.sub(r'([A-Za-z0-9α-ωΑ-Ω\)])\^([A-Za-z0-9α-ωΑ-Ω+\-])', replace_superscript, result)
    
    # ==================== CONVERTER SUBSCRITO/SOBRESCRITO UNICODE PARA HTML ====================
    # Caso o Gemini retorne caracteres Unicode de subscrito/sobrescrito diretamente,
    # convertemos para tags HTML que o ReportLab suporta melhor
    
    # Mapa de subscritos Unicode → caractere normal
    unicode_subscripts = {
        '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
        '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9',
        'ₐ': 'a', 'ₑ': 'e', 'ₕ': 'h', 'ᵢ': 'i', 'ⱼ': 'j',
        'ₖ': 'k', 'ₗ': 'l', 'ₘ': 'm', 'ₙ': 'n', 'ₒ': 'o',
        'ₚ': 'p', 'ᵣ': 'r', 'ₛ': 's', 'ₜ': 't', 'ᵤ': 'u',
        'ᵥ': 'v', 'ₓ': 'x', 'ᵧ': 'y', 'ᵦ': 'β', 'ᵧ': 'γ',
        'ᵨ': 'ρ', 'ᵩ': 'φ', 'ᵪ': 'χ',
    }
    
    # Mapa de sobrescritos Unicode → caractere normal
    unicode_superscripts = {
        '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
        '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
        'ᵃ': 'a', 'ᵇ': 'b', 'ᶜ': 'c', 'ᵈ': 'd', 'ᵉ': 'e',
        'ᶠ': 'f', 'ᵍ': 'g', 'ʰ': 'h', 'ⁱ': 'i', 'ʲ': 'j',
        'ᵏ': 'k', 'ˡ': 'l', 'ᵐ': 'm', 'ⁿ': 'n', 'ᵒ': 'o',
        'ᵖ': 'p', 'ʳ': 'r', 'ˢ': 's', 'ᵗ': 't', 'ᵘ': 'u',
        'ᵛ': 'v', 'ʷ': 'w', 'ˣ': 'x', 'ʸ': 'y', 'ᶻ': 'z',
        '⁺': '+', '⁻': '-', '⁼': '=', '⁽': '(', '⁾': ')',
        'ᵀ': 'T',  # Transposta
    }
    
    # Converter grupos consecutivos de subscritos Unicode
    def convert_unicode_subscripts(text):
        i = 0
        new_text = ""
        while i < len(text):
            # Verificar se começa um grupo de subscritos
            if text[i] in unicode_subscripts:
                sub_chars = ""
                while i < len(text) and text[i] in unicode_subscripts:
                    sub_chars += unicode_subscripts[text[i]]
                    i += 1
                new_text += f"<sub>{sub_chars}</sub>"
            else:
                new_text += text[i]
                i += 1
        return new_text
    
    # Converter grupos consecutivos de sobrescritos Unicode
    def convert_unicode_superscripts(text):
        i = 0
        new_text = ""
        while i < len(text):
            # Verificar se começa um grupo de sobrescritos
            if text[i] in unicode_superscripts:
                sup_chars = ""
                while i < len(text) and text[i] in unicode_superscripts:
                    sup_chars += unicode_superscripts[text[i]]
                    i += 1
                new_text += f"<super>{sup_chars}</super>"
            else:
                new_text += text[i]
                i += 1
        return new_text
    
    result = convert_unicode_subscripts(result)
    result = convert_unicode_superscripts(result)
    
    # ==================== SÍMBOLOS ESPECIAIS EXTRAS ====================
    
    # Símbolos de conjuntos numéricos
    result = re.sub(r'\bR\b(?=\s*[,\.\)]|$)', 'ℝ', result)  # Reais (cuidado)
    result = re.sub(r'\bN\b(?=\s*[,\.\)]|$)', 'ℕ', result)  # Naturais
    result = re.sub(r'\bZ\b(?=\s*[,\.\)]|$)', 'ℤ', result)  # Inteiros
    result = re.sub(r'\bQ\b(?=\s*[,\.\)]|$)', 'ℚ', result)  # Racionais
    result = re.sub(r'\bC\b(?=\s*[,\.\)]|$)', 'ℂ', result)  # Complexos
    
    # h-bar (constante de Planck reduzida) - física quântica
    result = re.sub(r'\bhbar\b', 'ℏ', result)
    
    # Limpar espaços extras
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result


def format_formula_for_pdf(text: str) -> str:
    """
    Formata texto que pode conter fórmulas para exibição no PDF.
    Detecta padrões de fórmulas e aplica formatação HTML.
    Também processa texto geral para encontrar fórmulas embutidas.
    """
    if not text:
        return text
    
    # Primeiro, escapar & que não fazem parte de entidades HTML
    # (precisamos fazer isso ANTES de adicionar tags HTML)
    text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', text)
    
    # Aplicar formatação de fórmulas usando HTML tags
    result = format_formula_unicode(text)
    
    return result


def generate_booklet_title(summaries: List[Dict], booklet_language: str = "pt") -> str:
    """
    Gera um título inteligente para a apostila baseado nos resumos gerados.
    Usa o Gemini para criar um título sugestivo que sintetize o conteúdo.
    """
    if not summaries:
        return "Apostila"
    
    # Extrair títulos e conceitos principais dos resumos
    titles = [s.get("titulo", "") for s in summaries if s.get("titulo")]
    concepts = []
    for s in summaries:
        if s.get("conceitos_principais"):
            concepts.extend(s["conceitos_principais"][:3])  # Primeiros 3 de cada
    
    # Limitar para não ficar muito grande
    titles_text = ", ".join(titles[:5])
    concepts_text = ", ".join(concepts[:10])
    
    # Definir idioma
    lang_instruction = {
        "pt": "em português brasileiro",
        "en": "in English",
        "es": "en español"
    }.get(booklet_language, "em português brasileiro")
    
    prompt = f"""Você é um especialista em criar títulos de apostilas educacionais.
    
Com base nos seguintes títulos de vídeos: {titles_text}
E nos conceitos abordados: {concepts_text}

Gere UM título sugestivo e descritivo para uma apostila {lang_instruction}.

REGRAS:
1. O título deve sintetizar o tema principal do conteúdo
2. Máximo de 60 caracteres
3. Deve ser atraente e profissional
4. Não use aspas na resposta
5. Responda APENAS com o título, nada mais

Exemplos de bons títulos:
- "Física Quântica: Fundamentos e Aplicações"
- "Deep Learning: Redes Neurais Convolucionais"
- "Cálculo Diferencial e Integral Completo"
- "Machine Learning: Do Zero ao Avançado"
"""
    
    try:
        gemini_model = get_gemini_model()
        response = gemini_model.generate_content(prompt)
        title = response.text.strip().strip('"').strip("'")
        
        # Limitar tamanho
        if len(title) > 60:
            title = title[:57] + "..."
        
        return title if title else "Apostila Educacional"
    except Exception as e:
        print(f"Erro ao gerar título: {e}")
        # Fallback: usar primeiro título
        if titles:
            return titles[0][:60] if len(titles[0]) > 60 else titles[0]
        return "Apostila Educacional"


def generate_pdf_filename(booklet_title: str) -> str:
    """
    Gera um nome de arquivo seguro para o PDF.
    Máximo de 54 caracteres (sem extensão).
    """
    import unicodedata
    
    # Remover acentos
    normalized = unicodedata.normalize('NFKD', booklet_title)
    ascii_text = normalized.encode('ASCII', 'ignore').decode('ASCII')
    
    # Substituir caracteres especiais por underscore
    safe_name = re.sub(r'[^\w\s-]', '', ascii_text)
    safe_name = re.sub(r'[-\s]+', '_', safe_name).strip('_')
    
    # Adicionar timestamp curto
    timestamp = datetime.now().strftime('%Y%m%d')
    
    # Calcular espaço disponível para o nome (54 - timestamp - underscore - .pdf)
    # 54 - 8 - 1 = 45 caracteres para o nome
    max_name_length = 45
    
    if len(safe_name) > max_name_length:
        safe_name = safe_name[:max_name_length]
    
    filename = f"{safe_name}_{timestamp}.pdf"
    
    return filename


# ==================== FUNÇÕES AUXILIARES ====================

@st.cache_resource
def get_youtube_service():
    """Retorna o serviço da API do YouTube"""
    return googleapiclient.discovery.build(
        "youtube", "v3", developerKey=YOUTUBE_API_KEY
    )

def extract_playlist_id(url: str) -> Optional[str]:
    """Extrai o ID da playlist de uma URL do YouTube"""
    patterns = [
        r'(?:youtube\.com.*[?&]list=([^&\n]+))',
        r'(?:youtu\.be.*[?&]list=([^&\n]+))',
        r'(?:youtube\.com/playlist\?.*list=([^&\n]+))',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_playlist_videos(playlist_id: str) -> List[Dict]:
    """Obtém todos os vídeos de uma playlist"""
    youtube = get_youtube_service()
    videos = []
    next_page_token = None
    
    try:
        while True:
            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response.get("items", []):
                video_id = item["snippet"]["resourceId"]["videoId"]
                title = item["snippet"]["title"]
                description = item["snippet"]["description"]
                
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "description": description,
                    "position": len(videos) + 1
                })
            
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
                
    except Exception as e:
        st.error(f"❌ Erro ao acessar a playlist: {str(e)}")
        return []
    
    return videos

def get_video_transcript(video_id: str) -> Optional[str]:
    """
    Obtém a transcrição do vídeo com proteção contra bloqueio de IP.
    Usa YouTubeTranscriptApi com fallback de idiomas.
    Preparado para deploy em produção (web).
    """
    # Lista de idiomas para tentar (ordem de prioridade)
    IDIOMAS_PRIORITARIOS = ['pt', 'pt-BR', 'en', 'en-US', 'es', 'es-ES']
    
    try:
        print(f"DEBUG - Buscando transcript para video_id: {video_id}")
        
        # Delay aleatório para evitar rate limiting (entre 1-3 segundos)
        delay = random.uniform(1.0, 3.0)
        time.sleep(delay)
        
        # -----------------------------
        # Método 1: YouTubeTranscriptApi direta (mais confiável para web)
        # -----------------------------
        transcript_raw = None
        idioma_usado = None
        
        # Tentar obter transcript nos idiomas prioritários
        for idioma in IDIOMAS_PRIORITARIOS:
            try:
                transcript_raw = YouTubeTranscriptApi().fetch(video_id, languages=[idioma])
                idioma_usado = idioma
                print(f"DEBUG - Transcript obtido em: {idioma}")
                break
            except (TranscriptsDisabled, NoTranscriptFound):
                continue
            except Exception as e:
                # Se for erro de bloqueio, aguardar mais
                if "Too Many Requests" in str(e) or "blocked" in str(e).lower():
                    print(f"DEBUG - Rate limit detectado, aguardando 5s...")
                    time.sleep(5)
                continue
        
        # Se não conseguiu com idiomas específicos, tentar pegar qualquer um disponível
        if transcript_raw is None:
            try:
                # Listar transcripts disponíveis
                transcript_list = YouTubeTranscriptApi().list(video_id)
                
                # Pegar o primeiro disponível (manual > automático)
                for transcript_info in transcript_list:
                    try:
                        transcript_raw = transcript_info.fetch()
                        idioma_usado = transcript_info.language_code
                        print(f"DEBUG - Usando transcript alternativo: {idioma_usado}")
                        break
                    except:
                        continue
            except Exception as e:
                print(f"DEBUG - Erro ao listar transcripts: {e}")
        
        if transcript_raw is None:
            print(f"DEBUG - Nenhum transcript disponível para {video_id}")
            return None
        
        # -----------------------------
        # Montar texto com timestamps
        # -----------------------------
        linhas = []
        
        for seg in transcript_raw:
            tempo_seg = seg.start

            h = int(tempo_seg // 3600)
            m = int((tempo_seg % 3600) // 60)
            s = int(tempo_seg % 60)

            tempo_formatado = f"[{h:02d}:{m:02d}:{s:02d}]"
            texto = seg.text.strip()

            if texto:
                linhas.append(f"{tempo_formatado} {texto}")

        transcript_com_tempo = "\n".join(linhas)
        print(f"DEBUG - Total linhas: {len(linhas)} | Total chars: {len(transcript_com_tempo)}")

        if transcript_com_tempo and len(transcript_com_tempo) > 50:
            return transcript_com_tempo

        return None

    except (TranscriptsDisabled, NoTranscriptFound):
        print(f"DEBUG - Legendas desativadas ou não encontradas para {video_id}")
        return None
    except Exception as e:
        print(f"DEBUG - Erro ao obter transcript: {e}")
        return None
        return None


def generate_summary_with_gemini(video_title: str, transcript: str, previous_summaries: str = "", booklet_language: str = "pt") -> Dict:
    """Gera resumo e explicações detalhadas usando Gemini no idioma especificado"""
    
    # Definir instruções de idioma
    language_instructions = {
        "pt": "Responda TODA a apostila em PORTUGUÊS BRASILEIRO.",
        "en": "Respond the ENTIRE booklet in ENGLISH.",
        "es": "Responda TODA la apostila en ESPAÑOL."
    }
    
    language_instruction = language_instructions.get(booklet_language, language_instructions["pt"])
    
    try:
        # Enviar transcript COMPLETO sem limitação
        transcript_completo = transcript
        print(f"DEBUG - Enviando {len(transcript_completo)} chars para Gemini (transcript completo) - Idioma: {booklet_language}")
        
        context = f"""
Você é um professor especialista criando material de estudo COMPLETO e DETALHADO.
Analise a transcrição COMPLETA do vídeo '{video_title}' e extraia TODO o conteúdo educacional.

*** IDIOMA DA APOSTILA: {language_instruction} ***

IMPORTANTE: Esta é uma aula/videoaula. Você DEVE:
1. Identificar TODOS os exercícios resolvidos no vídeo (ENEM, vestibulares, etc.)
2. Extrair TODAS as fórmulas mencionadas com suas explicações
3. Detalhar CADA passo da resolução dos exercícios
4. Explicar regras e macetes mencionados (ex: regra da mão direita, regra da mão esquerda)
5. Incluir dicas e observações do professor

FORMATAÇÃO DE FÓRMULAS - MUITO IMPORTANTE:
Use notação matemática clara com subscritos e sobrescritos assim:
- Para subscritos use underscore: F_m (força magnética), v_0 (velocidade inicial), F_{{mag}} (índice composto)
- Para expoentes use circunflexo: x^2 (x ao quadrado), v^2 (velocidade ao quadrado), 10^{{-6}} (potência de 10)
- Use símbolos gregos por nome: theta (θ), alpha (α), beta (β), delta (δ), omega (ω), pi (π)
- Multiplicação use ponto: F_m = |q| * v * B * sen(theta)
- Exemplo correto: "F_m = |q| * v * B * sen(theta)" será convertido para "Fₘ = |q| · v · B · sen(θ)"

Histórico de tópicos anteriores (para manter coerência):
{previous_summaries if previous_summaries else "Este é o primeiro vídeo da playlist"}

=== TRANSCRIÇÃO COMPLETA DO VÍDEO ===
{transcript_completo}
=== FIM DA TRANSCRIÇÃO ===

Gere uma resposta em JSON com a seguinte estrutura DETALHADA:
{{
    "titulo": "Título descritivo do tópico principal",
    "resumo": "Resumo abrangente do vídeo (3-4 parágrafos cobrindo todos os tópicos)",
    "conceitos_principais": ["conceito1", "conceito2", "conceito3", "conceito4"],
    "formulas": [
        {{"nome": "Força Magnética", "formula": "F_m = |q| * v * B * sen(theta)", "explicacao": "Força sobre carga em movimento no campo magnético. q=carga, v=velocidade, B=campo magnético, theta=ângulo entre v e B"}},
        {{"nome": "Outra fórmula", "formula": "use_notação_correta", "explicacao": "..."}}
    ],
    "explicacoes_detalhadas": {{
        "conceito1": "Explicação COMPLETA e DETALHADA do conceito, incluindo definições, aplicações e observações do professor",
        "conceito2": "Explicação COMPLETA...",
        "regras_e_macetes": "Regras mencionadas como 'regra da mão direita', 'regra da mão esquerda', etc. com explicação passo-a-passo de como aplicar"
    }},
    "exercicios_resolvidos": [
        {{
            "enunciado": "Transcreva o enunciado completo do exercício (ENEM, vestibular, etc.)",
            "resolucao_passo_a_passo": [
                "Passo 1: Identificar os dados do problema...",
                "Passo 2: Aplicar a fórmula X porque...",
                "Passo 3: Calcular...",
                "Passo 4: Resposta final..."
            ],
            "resposta": "Alternativa correta ou valor final",
            "dica_professor": "Observação ou macete que o professor mencionou"
        }}
    ],
    "exemplos_praticos": ["Exemplo prático 1 com contexto real", "Exemplo prático 2"],
    "dicas_estudo": ["Dica 1 do professor", "Dica 2", "O que mais cai em provas"],
    "conclusao": "Síntese do conteúdo e conexão com próximos tópicos"
}}

LEMBRE-SE: {language_instruction}
ATENÇÃO: Seja DETALHISTA! Uma apostila de estudo precisa de PROFUNDIDADE.
Responda APENAS com o JSON válido, sem explicações adicionais.
"""
        
        # Usar o modelo selecionado pelo usuário
        gemini_model = get_gemini_model()
        response = gemini_model.generate_content(context)
        
        # Tentar parsear como JSON
        try:
            content = response.text
            # Remove marcas de código se presentes
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            summary_data = json.loads(content.strip())
            print(f"DEBUG - Gemini retornou: {list(summary_data.keys())}")
            return summary_data
        except json.JSONDecodeError:
            # Se falhar, retornar estrutura padrão
            return {
                "titulo": video_title,
                "resumo": response.text,
                "conceitos_principais": [],
                "formulas": [],
                "explicacoes_detalhadas": {},
                "exercicios_resolvidos": [],
                "exemplos_praticos": [],
                "dicas_estudo": [],
                "conclusao": ""
            }
    except Exception as e:
        st.error(f"❌ Erro ao gerar resumo com Gemini: {str(e)}")
        return None

def create_pdf_booklet(playlist_title: str, summaries: List[Dict]) -> bytes:
    """Cria um PDF com as apostilas"""
    from io import BytesIO
    
    pdf_buffer = BytesIO()
    
    # Criar documento PDF
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        title=f"Apostila: {playlist_title}"
    )
    
    # Definir estilos
    styles = getSampleStyleSheet()
    
    # Estilos customizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=1,  # Centro
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#2ca02c'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        alignment=4,  # Justificado
        spaceAfter=12,
        leading=14
    )
    
    # Estilo especial para fórmulas matemáticas
    formula_style = ParagraphStyle(
        'FormulaStyle',
        parent=styles['Normal'],
        fontSize=13,
        textColor=HexColor('#0066cc'),  # Azul escuro
        spaceAfter=6,
        spaceBefore=6,
        leftIndent=20,
        fontName='Helvetica-Bold',
        backColor=HexColor('#f0f8ff'),  # Fundo azul claro
        borderPadding=5,
    )
    
    # Estilo para explicação da fórmula
    formula_desc_style = ParagraphStyle(
        'FormulaDescStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#444444'),
        spaceAfter=10,
        leftIndent=30,
        fontName='Helvetica-Oblique',  # Itálico
    )
    
    story = []
    
    # Capa
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph(playlist_title, title_style))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Apostila Gerada Automaticamente", styles['Heading3']))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Paragraph("Smart YouTube Booklet © 2026", styles['Normal']))
    story.append(PageBreak())
    
    # Índice
    story.append(Paragraph("Índice", title_style))
    story.append(Spacer(1, 0.2*inch))
    for i, summary in enumerate(summaries, 1):
        titulo = summary.get("titulo", f"Vídeo {i}")
        story.append(Paragraph(f"{i}. {titulo}", styles['Normal']))
    story.append(PageBreak())
    
    # Conteúdo
    for i, summary in enumerate(summaries, 1):
        # Título do capítulo
        titulo = summary.get("titulo", f"Vídeo {i}")
        story.append(Paragraph(f"Capítulo {i}: {titulo}", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Resumo
        if summary.get("resumo"):
            story.append(Paragraph("<b>📋 Resumo:</b>", heading_style))
            resumo_text = format_formula_for_pdf(str(summary["resumo"]).replace("\n", "<br/>"))
            story.append(Paragraph(resumo_text, body_style))
            story.append(Spacer(1, 0.2*inch))
        
        # Conceitos principais
        if summary.get("conceitos_principais"):
            story.append(Paragraph("<b>🎯 Conceitos Principais:</b>", heading_style))
            for conceito in summary["conceitos_principais"]:
                conceito_fmt = format_formula_for_pdf(str(conceito))
                story.append(Paragraph(f"• {conceito_fmt}", body_style))
            story.append(Spacer(1, 0.2*inch))
        
        # NOVO: Fórmulas com formatação Unicode melhorada
        if summary.get("formulas"):
            story.append(Paragraph("<b>📐 Fórmulas:</b>", heading_style))
            for formula in summary["formulas"]:
                if isinstance(formula, dict):
                    nome = formula.get("nome", "")
                    form_raw = formula.get("formula", "")
                    explicacao = formula.get("explicacao", "")
                    
                    # Aplicar formatação Unicode para fórmulas bonitas
                    form_formatted = format_formula_for_pdf(form_raw)
                    
                    # Renderizar nome da fórmula
                    story.append(Paragraph(f"<b>► {nome}</b>", styles['Normal']))
                    
                    # Renderizar fórmula com estilo destacado
                    story.append(Paragraph(f"    {form_formatted}", formula_style))
                    
                    # Renderizar explicação se houver
                    if explicacao:
                        explicacao_formatted = format_formula_for_pdf(explicacao)
                        story.append(Paragraph(f"↳ {explicacao_formatted}", formula_desc_style))
                    
                    story.append(Spacer(1, 0.1*inch))
            story.append(Spacer(1, 0.2*inch))
        
        # Explicações detalhadas
        if summary.get("explicacoes_detalhadas"):
            story.append(Paragraph("<b>📖 Explicações Detalhadas:</b>", heading_style))
            for conceito, explicacao in summary["explicacoes_detalhadas"].items():
                conceito_fmt = format_formula_for_pdf(str(conceito))
                story.append(Paragraph(f"<b>▸ {conceito_fmt}:</b>", styles['Normal']))
                explicacao_text = format_formula_for_pdf(str(explicacao).replace("\n", "<br/>"))
                story.append(Paragraph(explicacao_text, body_style))
                story.append(Spacer(1, 0.1*inch))
            story.append(Spacer(1, 0.2*inch))
        
        # NOVO: Exercícios Resolvidos (SEÇÃO PRINCIPAL)
        if summary.get("exercicios_resolvidos"):
            story.append(Paragraph("<b>✏️ EXERCÍCIOS RESOLVIDOS:</b>", heading_style))
            for j, exercicio in enumerate(summary["exercicios_resolvidos"], 1):
                if isinstance(exercicio, dict):
                    # Enunciado
                    enunciado = exercicio.get("enunciado", "")
                    if enunciado:
                        story.append(Paragraph(f"<b>Exercício {j}:</b>", styles['Normal']))
                        # Formatar fórmulas no enunciado
                        enunciado_fmt = format_formula_for_pdf(enunciado)
                        story.append(Paragraph(enunciado_fmt, body_style))
                        story.append(Spacer(1, 0.1*inch))
                    
                    # Resolução passo a passo
                    resolucao = exercicio.get("resolucao_passo_a_passo", [])
                    if resolucao:
                        story.append(Paragraph("<b>Resolução:</b>", styles['Normal']))
                        for passo in resolucao:
                            # Formatar fórmulas em cada passo
                            passo_fmt = format_formula_for_pdf(str(passo))
                            story.append(Paragraph(f"   {passo_fmt}", body_style))
                        story.append(Spacer(1, 0.1*inch))
                    
                    # Resposta
                    resposta = exercicio.get("resposta", "")
                    if resposta:
                        resposta_fmt = format_formula_for_pdf(str(resposta))
                        story.append(Paragraph(f"<b>✓ Resposta:</b> <font color='green'>{resposta_fmt}</font>", styles['Normal']))
                    
                    # Dica do professor
                    dica = exercicio.get("dica_professor", "")
                    if dica:
                        dica_fmt = format_formula_for_pdf(str(dica))
                        story.append(Paragraph(f"<i>💡 Dica do Professor: {dica_fmt}</i>", body_style))
                    
                    story.append(Spacer(1, 0.2*inch))
            story.append(Spacer(1, 0.2*inch))
        
        # Exemplos práticos
        if summary.get("exemplos_praticos"):
            story.append(Paragraph("<b>🔬 Exemplos Práticos:</b>", heading_style))
            for exemplo in summary["exemplos_praticos"]:
                exemplo_fmt = format_formula_for_pdf(str(exemplo))
                story.append(Paragraph(f"• {exemplo_fmt}", body_style))
            story.append(Spacer(1, 0.2*inch))
        
        # NOVO: Dicas de Estudo
        if summary.get("dicas_estudo"):
            story.append(Paragraph("<b>💡 Dicas de Estudo:</b>", heading_style))
            for dica in summary["dicas_estudo"]:
                dica_fmt = format_formula_for_pdf(str(dica))
                story.append(Paragraph(f"• {dica_fmt}", body_style))
            story.append(Spacer(1, 0.2*inch))
        
        # Conclusão
        if summary.get("conclusao"):
            story.append(Paragraph("<b>📌 Conclusão:</b>", heading_style))
            conclusao_text = format_formula_for_pdf(str(summary["conclusao"]).replace("\n", "<br/>"))
            story.append(Paragraph(conclusao_text, body_style))
        
        story.append(PageBreak())
    
    # Construir PDF
    doc.build(story)
    pdf_buffer.seek(0)
    
    return pdf_buffer.getvalue()

# ==================== INTERFACE STREAMLIT ====================

def show_home():
    """Exibe a página inicial com layout belíssimo"""
    
    # CSS customizado
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 40px 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
    }
    
    .main-header h1 {
        font-size: 48px;
        margin: 0;
        font-weight: bold;
    }
    
    .main-header p {
        font-size: 18px;
        margin: 10px 0 0 0;
        opacity: 0.9;
    }
    
    .feature-box {
        background: #f0f2f6;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 15px 0;
    }
    
    .feature-box h3 {
        color: #667eea;
        margin-top: 0;
    }
    
    .content-section {
        background: white;
        padding: 30px;
        border-radius: 10px;
        margin: 20px 0;
        border: 1px solid #e0e0e0;
    }
    
    .content-section h2 {
        border-bottom: 3px solid #667eea;
        padding-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header principal - usa tradução
    st.markdown(f"""
    <div class="main-header">
        <h1>{t('header_title')}</h1>
        <p>{t('header_subtitle')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Conteúdo principal - O que é
    st.markdown(f"## {t('home_what_is')}")
    st.markdown(t('home_description'))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="feature-box">
            <h3>{t('home_feature1_title')}</h3>
            <p>{t('home_feature1_desc')}</p>
        </div>
        
        <div class="feature-box">
            <h3>{t('home_feature2_title')}</h3>
            <p>{t('home_feature2_desc')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="feature-box">
            <h3>{t('home_feature3_title')}</h3>
            <p>{t('home_feature3_desc')}</p>
        </div>
        
        <div class="feature-box">
            <h3>{t('home_feature4_title')}</h3>
            <p>{t('home_feature4_desc')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
## {t('home_main_features')}

{t('home_features_list')}

## {t('home_how_to_use')}

{t('home_how_to_steps')}

## {t('home_requirements')}

{t('home_requirements_list')}
    """)
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(t('home_tip1'))
    with col2:
        st.info(t('home_tip2'))
    with col3:
        st.info(t('home_tip3'))

def show_generator():
    """Exibe a página de geração de apostilas"""
    
    st.title(t('gen_title'))
    st.markdown("---")
    
    # Inicializar session_state
    if 'playlist_url' not in st.session_state:
        st.session_state.playlist_url = ""
    if 'videos' not in st.session_state:
        st.session_state.videos = None
    if 'summaries' not in st.session_state:
        st.session_state.summaries = None
    if 'playlist_name' not in st.session_state:
        st.session_state.playlist_name = ""
    
    # Input da URL e seleção de idioma da apostila
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        playlist_url = st.text_input(
            t('gen_input_label'),
            placeholder=t('gen_input_placeholder'),
            help=t('gen_input_help'),
            value=st.session_state.playlist_url
        )
    
    with col2:
        # Seletor de idioma da apostila
        booklet_lang_options = list(BOOKLET_LANGUAGES.keys())
        booklet_lang_names = list(BOOKLET_LANGUAGES.values())
        
        selected_booklet_lang_idx = booklet_lang_options.index(st.session_state.booklet_language)
        
        selected_booklet_lang = st.selectbox(
            t('gen_booklet_language'),
            booklet_lang_names,
            index=selected_booklet_lang_idx,
            help=t('gen_booklet_language_help')
        )
        st.session_state.booklet_language = booklet_lang_options[booklet_lang_names.index(selected_booklet_lang)]
    
    with col3:
        st.write("")  # Espaço
        st.write("")  # Espaço para alinhar com o input
        process_button = st.button(t('gen_process_button'), use_container_width=True)
    
    st.markdown("---")
    
    # Se clicou no botão de processar - FASE 1: Buscar vídeos
    if process_button and playlist_url:
        st.session_state.playlist_url = playlist_url
        playlist_id = extract_playlist_id(playlist_url)
        
        if not playlist_id:
            st.error(t('gen_invalid_url'))
            st.info(f"{t('gen_valid_urls')}\n- https://www.youtube.com/playlist?list=PLxxx\n- https://youtu.be/video?list=PLxxx")
            return
        
        # Obter vídeos da playlist
        with st.spinner(t('gen_searching')):
            videos = get_playlist_videos(playlist_id)
        
        if not videos:
            st.error(t('gen_error_playlist'))
            return
        
        st.session_state.videos = videos
        st.session_state.selected_videos = None  # Reset seleção
        st.session_state.summaries = None  # Reset resumos
        st.success(t('gen_found_videos', count=len(videos)))
        st.rerun()
    
    # FASE 2: Se há vídeos carregados, mostrar seleção
    if st.session_state.videos and st.session_state.summaries is None:
        videos = st.session_state.videos
        lang = st.session_state.get('ui_language', 'pt')
        
        st.markdown(f"### 📋 {t('gen_select_videos') if 'gen_select_videos' in TRANSLATIONS.get(lang, {}) else 'Selecione os vídeos'}")
        
        # Mensagem de limite
        limit_msg = f"⚠️ Máximo de {MAX_VIDEOS_PER_BOOKLET} vídeos por apostila" if lang == 'pt' else f"⚠️ Maximum of {MAX_VIDEOS_PER_BOOKLET} videos per booklet"
        st.info(limit_msg)
        
        # Criar lista de opções
        video_options = [f"{v['position']}. {v['title']}" for v in videos]
        
        # Multiselect para escolher vídeos
        selected_label = "Selecione os vídeos para incluir na apostila:" if lang == 'pt' else "Select videos to include in the booklet:"
        
        selected_videos_display = st.multiselect(
            selected_label,
            options=video_options,
            default=video_options[:min(MAX_VIDEOS_PER_BOOKLET, len(video_options))],  # Default: primeiros 5
            max_selections=MAX_VIDEOS_PER_BOOKLET,
            help=limit_msg
        )
        
        # Converter seleção de volta para objetos de vídeo
        selected_indices = []
        for sel in selected_videos_display:
            # Extrair o número da posição
            pos = int(sel.split('.')[0])
            for i, v in enumerate(videos):
                if v['position'] == pos:
                    selected_indices.append(i)
                    break
        
        selected_videos = [videos[i] for i in selected_indices]
        
        # Mostrar contagem
        count_msg = f"📊 {len(selected_videos)}/{MAX_VIDEOS_PER_BOOKLET} vídeos selecionados" if lang == 'pt' else f"📊 {len(selected_videos)}/{MAX_VIDEOS_PER_BOOKLET} videos selected"
        st.caption(count_msg)
        
        # Verificar limite de apostilas do dia ANTES de processar
        can_generate, reason = can_generate_booklet()
        
        if not can_generate:
            st.error("🚫 " + (t('gen_limit_reached') if 'gen_limit_reached' in TRANSLATIONS.get(lang, {}) else "Você atingiu o limite diário de apostilas gratuitas!"))
            show_payment_popup()
            return
        
        # Botão para processar vídeos selecionados
        generate_btn_text = f"🚀 Gerar Apostila ({len(selected_videos)} vídeos)" if lang == 'pt' else f"🚀 Generate Booklet ({len(selected_videos)} videos)"
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(generate_btn_text, type="primary", use_container_width=True, disabled=len(selected_videos) == 0):
                if len(selected_videos) == 0:
                    st.warning("Selecione ao menos um vídeo!" if lang == 'pt' else "Select at least one video!")
                    return
                
                # Processar vídeos selecionados
                st.markdown(f"### {t('gen_processing')}")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                summaries = []
                previous_summaries = ""
                
                # Obter idioma da apostila selecionado
                booklet_lang = st.session_state.booklet_language
                
                for idx, video in enumerate(selected_videos):
                    # Atualizar progress
                    progress = (idx + 1) / len(selected_videos)
                    progress_bar.progress(progress)
                    status_text.write(t('gen_processing_video', current=idx+1, total=len(selected_videos), title=video['title']))
                    
                    # Pausa entre vídeos para evitar rate limiting (exceto no primeiro)
                    if idx > 0:
                        time.sleep(random.uniform(1.0, 2.0))
                    
                    # Obter transcrição
                    transcript = get_video_transcript(video['video_id'])
                    
                    if not transcript:
                        st.warning(t('gen_no_transcript', title=video['title']))
                        continue
                    
                    # Gerar resumo com Gemini no idioma selecionado
                    summary = generate_summary_with_gemini(
                        video['title'], 
                        transcript,
                        previous_summaries,
                        booklet_lang  # Passa o idioma selecionado
                    )
                    
                    if summary:
                        summaries.append(summary)
                        # Atualizar contexto para próximos vídeos
                        previous_summaries += f"\n- {summary.get('titulo', video['title'])}: {summary.get('resumo', '')[:200]}"
                
                status_text.write(t('gen_completed'))
                
                if not summaries:
                    st.error(t('gen_no_transcripts'))
                    return
                
                # INCREMENTAR CONTADOR DE APOSTILAS
                increment_booklet_count()
                
                # Gerar título inteligente para a apostila
                with st.spinner("🎯 Gerando título da apostila..." if st.session_state.get('ui_language', 'pt') == 'pt' else "🎯 Generating booklet title..."):
                    booklet_title = generate_booklet_title(summaries, st.session_state.booklet_language)
                
                # Armazenar no session_state
                st.session_state.summaries = summaries
                st.session_state.playlist_name = booklet_title
                
                st.success(t('gen_summaries_generated', count=len(summaries)))
                st.rerun()
    
    # Se há dados armazenados no session_state, mostrar resumos
    if st.session_state.summaries:
        summaries = st.session_state.summaries
        videos = st.session_state.videos
        playlist_name = st.session_state.playlist_name
        
        # Visualizar resumos
        st.markdown(f"### {t('gen_summaries_title')}")
        
        for i, summary in enumerate(summaries, 1):
            with st.expander(f"📄 {i}. {summary.get('titulo', f'Vídeo {i}')}"):
                st.write(f"**{t('gen_summary')}**")
                st.write(summary.get("resumo", "N/A"))
                
                if summary.get("conceitos_principais"):
                    st.write(f"**{t('gen_concepts')}**")
                    st.write(", ".join(summary["conceitos_principais"]))
                
                if summary.get("explicacoes_detalhadas"):
                    st.write(f"**{t('gen_detailed_explanations')}**")
                    for conceito, explicacao in summary["explicacoes_detalhadas"].items():
                        st.write(f"- **{conceito}**: {explicacao}")
        
        # Gerar PDF
        st.markdown(f"### {t('gen_generate_pdf')}")
        
        # Gerar nome de arquivo seguro (máximo 54 caracteres)
        pdf_name = generate_pdf_filename(playlist_name)
        
        # Mostrar título da apostila
        lang = st.session_state.get('ui_language', 'pt')
        st.info(f"📚 **{'Título da Apostila' if lang == 'pt' else 'Booklet Title'}:** {playlist_name}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(t('gen_download_pdf'), use_container_width=True, key="pdf_button"):
                with st.spinner(t('gen_generating_pdf')):
                    try:
                        pdf_content = create_pdf_booklet(playlist_name, summaries)
                        
                        st.download_button(
                            label=t('gen_click_download'),
                            data=pdf_content,
                            file_name=pdf_name,
                            mime="application/pdf",
                            use_container_width=True
                        )
                        st.success(t('gen_pdf_success'))
                    except Exception as e:
                        st.error(t('gen_pdf_error', error=str(e)))
        
        with col2:
            if st.button(t('gen_save_json'), use_container_width=True, key="json_button"):
                json_content = json.dumps(summaries, ensure_ascii=False, indent=2)
                st.download_button(
                    label=t('gen_click_download'),
                    data=json_content,
                    file_name=f"Resumos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
                st.success(t('gen_json_success'))
        
        # Botão para nova playlist
        st.markdown("---")
        lang = st.session_state.get('ui_language', 'pt')
        new_btn_text = "🔄 Processar Nova Playlist" if lang == 'pt' else "🔄 Process New Playlist"
        
        if st.button(new_btn_text, use_container_width=True):
            st.session_state.videos = None
            st.session_state.summaries = None
            st.session_state.playlist_url = ""
            st.session_state.playlist_name = ""
            st.rerun()

def show_info_page():
    """Página de informações com traduções"""
    st.title(f"ℹ️ {t('nav_info')}")
    
    # Info do modelo atual
    model_info = GEMINI_MODELS[st.session_state.selected_model]
    model_desc = get_model_description(st.session_state.selected_model)
    
    if st.session_state.ui_language == 'pt':
        st.info(f"🤖 **Modelo ativo**: {model_info['name']} - {model_desc}")
        
        st.markdown("""
        ## Sobre o Smart YouTube Booklet
        
        Esta aplicação foi desenvolvida para democratizar o acesso ao conhecimento,
        transformando conteúdo educacional disponível no YouTube em materiais 
        de estudo estruturados e acessíveis.
        
        ### 🛠️ Tecnologias Utilizadas
        
        | Tecnologia | Função |
        |------------|--------|
        | **Streamlit** | Framework web para aplicações Python |
        | **YouTube Transcript API** | Extração de transcrições dos vídeos |
        | **Google Gemini AI** | Processamento de linguagem natural e geração de conteúdo |
        | **ReportLab** | Geração de PDFs profissionais |
        
        ### ⚙️ Como Funciona
        
        1. **Extração**: Obtém a lista de vídeos da playlist via YouTube API
        2. **Transcrição**: Baixa as transcrições usando YouTube Transcript API (suporta PT, EN, ES)
        3. **Análise**: Gemini AI analisa cada transcrição completa
        4. **Síntese**: Gera resumos estruturados com exercícios, fórmulas e dicas
        5. **Compilação**: Monta uma apostila profissional em PDF
        
        ### ✅ Recursos
        
        - ✅ Suporte a playlists públicas do YouTube
        - ✅ Transcrições em múltiplos idiomas (PT, EN, ES, etc.)
        - ✅ Extração de exercícios resolvidos
        - ✅ Formatação de fórmulas matemáticas
        - ✅ PDF profissional com índice
        - ✅ Escolha entre modelos de IA (economia vs qualidade)
        - ✅ Delay inteligente para evitar bloqueios
        
        ### ⚠️ Limitações
        
        - Playlists devem ser públicas
        - Vídeos devem ter transcrições/legendas disponíveis
        - Limites de quota da API do YouTube e Gemini
        - Vídeos muito longos (>2h) podem gerar resumos menos detalhados
        
        ### 🔒 Privacidade
        
        - Não armazenamos transcrições ou dados pessoais
        - Processamento feito em tempo real
        - APIs oficiais do Google
        
        ---
        **Smart YouTube Booklet v4.0 © 2026 - Todos os direitos reservados**
        """)
    else:
        st.info(f"🤖 **Active model**: {model_info['name']} - {model_desc}")
        
        st.markdown("""
        ## About Smart YouTube Booklet
        
        This application was developed to democratize access to knowledge,
        transforming educational content available on YouTube into structured
        and accessible study materials.
        
        ### 🛠️ Technologies Used
        
        | Technology | Function |
        |------------|----------|
        | **Streamlit** | Web framework for Python applications |
        | **YouTube Transcript API** | Video transcript extraction |
        | **Google Gemini AI** | Natural language processing and content generation |
        | **ReportLab** | Professional PDF generation |
        
        ### ⚙️ How It Works
        
        1. **Extraction**: Gets the video list from the playlist via YouTube API
        2. **Transcription**: Downloads transcripts using YouTube Transcript API (supports PT, EN, ES)
        3. **Analysis**: Gemini AI analyzes each complete transcript
        4. **Synthesis**: Generates structured summaries with exercises, formulas, and tips
        5. **Compilation**: Creates a professional PDF booklet
        
        ### ✅ Features
        
        - ✅ Support for public YouTube playlists
        - ✅ Transcripts in multiple languages (PT, EN, ES, etc.)
        - ✅ Extraction of solved exercises
        - ✅ Mathematical formula formatting
        - ✅ Professional PDF with index
        - ✅ Choice between AI models (economy vs quality)
        - ✅ Smart delay to avoid blocks
        
        ### ⚠️ Limitations
        
        - Playlists must be public
        - Videos must have available transcripts/subtitles
        - YouTube and Gemini API quota limits
        - Very long videos (>2h) may generate less detailed summaries
        
        ### 🔒 Privacy
        
        - We do not store transcripts or personal data
        - Real-time processing
        - Official Google APIs
        
        ---
        **Smart YouTube Booklet v5.0 © 2026 - All rights reserved**
        """)

def main():
    """Função principal"""
    
    # Inicializar monetização
    init_monetization_state()
    
    # PASSO 1: Verificar tela de lock (anúncio inicial)
    if not st.session_state.get('app_liberado', False) and not st.session_state.get('dev_mode', False):
        show_lock_screen()
        return
    
    # PASSO 2: Verificar login obrigatório
    if not st.session_state.get('user_logged_in', False) and not st.session_state.get('dev_mode', False):
        show_login_screen()
        return
    
    # Menu lateral
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/books.png", use_container_width=False, width=100)
        st.title("Smart YouTube Booklet")
        st.markdown("---")
        
        # DEV MODE toggle
        show_dev_toggle()
        
        # Status do usuário
        show_user_status()
        
        st.markdown("---")
        
        # Seletor de idioma da interface
        st.markdown(f"### 🌐 {t('sidebar_language')}")
        lang_options = {"pt": "🇧🇷 Português", "en": "🇺🇸 English"}
        current_lang = st.session_state.ui_language
        
        selected_lang = st.selectbox(
            t('sidebar_select_language'),
            options=list(lang_options.keys()),
            format_func=lambda x: lang_options[x],
            index=list(lang_options.keys()).index(current_lang),
            key="lang_selector"
        )
        
        if selected_lang != current_lang:
            st.session_state.ui_language = selected_lang
            st.rerun()
        
        st.markdown("---")
        
        # Navegação traduzida
        nav_options = [
            f"🏠 {t('nav_home')}",
            f"📚 {t('nav_generator')}",
            f"ℹ️ {t('nav_info')}"
        ]
        
        pagina = st.radio(
            t('nav_title'),
            nav_options,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Seletor de modelo Gemini
        st.markdown(f"### 🤖 {t('sidebar_model')}")
        
        model_options = list(GEMINI_MODELS.keys())
        model_names = [GEMINI_MODELS[m]["name"] for m in model_options]
        
        selected_idx = model_options.index(st.session_state.selected_model)
        
        selected_model_name = st.selectbox(
            t('sidebar_select_model'),
            model_names,
            index=selected_idx,
            help=t('sidebar_model_help')
        )
        
        # Atualizar o modelo selecionado
        st.session_state.selected_model = model_options[model_names.index(selected_model_name)]
        
        # Mostrar info do modelo selecionado
        model_info = GEMINI_MODELS[st.session_state.selected_model]
        model_desc = get_model_description(st.session_state.selected_model)
        st.caption(f"📊 {model_desc}")
        st.caption(f"💰 Input: {model_info['price_input']}")
        st.caption(f"💰 Output: {model_info['price_output']}")
        
        st.markdown("---")
        
        # Botão de logout
        if st.session_state.get('user_logged_in', False):
            if st.button("🚪 Logout", use_container_width=True):
                logout_user()
                st.rerun()
        
        st.markdown("---")
        
        # Info do app traduzida
        if st.session_state.ui_language == 'pt':
            st.markdown("""
            ### 📌 Informações
            - **Versão**: 5.0.0
            - **Tecnologias**: Streamlit, YouTube Transcript API, Gemini AI, ReportLab
            - **Idiomas**: Português, English, Español
            - **Ano**: 2026
            
            ### 🔗 Links
            [YouTube](https://youtube.com) | [Gemini](https://ai.google.dev)
            """)
        else:
            st.markdown("""
            ### 📌 Information
            - **Version**: 5.0.0
            - **Technologies**: Streamlit, YouTube Transcript API, Gemini AI, ReportLab
            - **Languages**: Português, English, Español
            - **Year**: 2026
            
            ### 🔗 Links
            [YouTube](https://youtube.com) | [Gemini](https://ai.google.dev)
            """)
    
    # Renderizar página apropriada baseado na seleção
    if pagina == nav_options[0]:  # Home
        show_home()
    elif pagina == nav_options[1]:  # Generator
        show_generator()
    elif pagina == nav_options[2]:  # Info
        show_info_page()

if __name__ == "__main__":
    main()
