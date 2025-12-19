import os
import pandas as pd
import streamlit as st
import datetime as dt


def get_base_dir() -> str:
    """Diretório do projeto (onde está o app.py)."""
    return os.path.dirname(os.path.abspath(__file__))


def get_excel_path() -> str:
    """Caminho fixo do Excel dentro da pasta Planilhas."""
    base_dir = get_base_dir()
    return os.path.join(base_dir, "Planilhas", "Controle de Horas Mills.xlsx")


def recortar_planilha(df: pd.DataFrame) -> pd.DataFrame:
    # Limita até a coluna K
    df2 = df.iloc[:, :10].copy()
    # Para na primeira linha onde a Coluna A == "Soma"
    col_a = df2.iloc[:, 0].astype(str).str.strip().str.casefold()
    idx_soma = col_a[col_a == "Soma"].index
    if len(idx_soma) > 0:
        stop = idx_soma[0]
        df2 = df2.loc[:stop - 1]
    df2 = df2.dropna(how="all")
    return df2


@st.cache_data(show_spinner=False)
def list_sheets(excel_path: str) -> list[str]:
    """Lista as worksheets do Excel."""
    return pd.ExcelFile(excel_path).sheet_names


@st.cache_data(show_spinner=False)
def load_sheet(excel_path: str, sheet_name: str) -> pd.DataFrame:
    """Carrega uma worksheet do Excel."""
    return pd.read_excel(excel_path, sheet_name=sheet_name)


def fmt_hhmmss_from_seconds(total_seconds: float) -> str:
    if pd.isna(total_seconds):
        return ""
    total_seconds = int(round(total_seconds))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}" 

def excel_duration_to_hhmmss(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)) or (isinstance(x, str) and x.strip() == ""):
        return ""
    total_seconds = None

    # timedelta 
    if isinstance(x, dt.timedelta):
        total_seconds = int(x.total_seconds())

    # datetime.time
    elif isinstance(x, dt.time):
        total_seconds = x.hour * 3600 + x.minute * 60 + x.second

    # float / int do Excel
    elif isinstance(x, (int, float)):
        total_seconds = int(round(float(x) * 86400))

    #string [hh]:mm:ss
    elif isinstance(x, str):
        try:
            td = pd.to_timedelta(x)
            total_seconds = int(td.total_seconds())
        except Exception:
            return str(x)

    else:
        return str(x)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def fix_duration_column(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    if col_name not in df.columns:
        return df
    df[col_name] = df[col_name].map(excel_duration_to_hhmmss).astype("string")
    return df


def hhmmss_to_minutes(x: str) -> float:
    if not isinstance(x, str) or ":" not in x:
        return 0.0
    try:
        h, m, s = x.split(":")
        return int(h) * 60 + int(m) + int(s) / 60
    except Exception:
        return 0.0