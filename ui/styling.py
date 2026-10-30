
import streamlit as st


def apply_theme():

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .stApp {
        background-color: #0b1120;
        color: #e5e7eb;
        font-family: 'Inter', sans-serif;
    }

    [data-testid="stSidebar"] {
        background-color: #101a2d;
        border-right: 1px solid #263449;
    }

    h1, h2, h3 {
        color: #f1f5f9 !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetric"] {
        background: #131f33;
        border: 1px solid #263449;
        padding: 18px;
        border-radius: 12px;
    }

    [data-testid="stMetricValue"] {
        color: #38bdf8 !important;
    }

    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #111c30;
        border-color: #263449 !important;
        border-radius: 12px;
    }

    .stButton > button {
        background: #0891b2;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 18px;
    }

    .stButton > button:hover {
        background: #0e7490;
        color: white;
        border: none;
    }

    [data-testid="stProgressBar"] > div > div {
        background-color: #06b6d4;
    }

    hr {
        border-color: #263449;
    }

    </style>
    """, unsafe_allow_html=True)
