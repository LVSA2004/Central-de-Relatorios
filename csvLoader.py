import os
import pandas as pd
import streamlit as st
import datetime as dt

def get_base_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def get_csv_path() -> str:
    base_dir = get_base_dir()
    return os.path.join(base_dir, "Planilhas", "roi.csv")