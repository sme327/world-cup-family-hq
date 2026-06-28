import streamlit as st
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from components.bracket_board import render_knockout_bracket_shell

# Bracket page: override Streamlit's default container padding so the board
# can use nearly the full viewport width (layout="wide" is already set in app.py).
st.markdown("""
<style>
[data-testid="stMainBlockContainer"] {
    max-width: none !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
    padding-top: 0.5rem !important;
}
</style>
""", unsafe_allow_html=True)

render_knockout_bracket_shell()
