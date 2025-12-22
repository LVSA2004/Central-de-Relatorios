import os
import base64
import streamlit as st
from Paginas import relatorioHoras, roi
from PIL import Image
from planilhaLoader import get_base_dir

BASE_DIR = get_base_dir()
ICON_LOGO = os.path.join(BASE_DIR, "Logos", "mills_logo_branca.png")
LOGO_PATH = os.path.join(BASE_DIR, "Logos", "mills_logo_branca.svg")

st.logo(LOGO_PATH, icon_image=LOGO_PATH )

def img_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
logo_b64 = img_to_base64(ICON_LOGO ) if os.path.exists(ICON_LOGO) else ""
page_icon = Image.open(ICON_LOGO ) if os.path.exists(ICON_LOGO ) else None

st.set_page_config(
    page_title="Central de Relatórios", 
    page_icon=page_icon, 
    layout="wide"
)

st.markdown( 
    f""" 
    <style> 
    header[data-testid="stHeader"] {{ background-color: #F37021 !important; }} 
    .block-container {{ padding-top: 4rem; }} 
    button[kind="header"] {{ display: none !important; }} 
    </style> """, 
    unsafe_allow_html=True 
)
pages = {
    "Relatorios":[
        st.Page(relatorioHoras.exibir, title="Relatório de Horas"),
        st.Page(roi.exibirROI, title="ROI")
    ]
}
pg = st.navigation(pages, position="top")
pg.run()