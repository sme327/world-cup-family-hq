import streamlit as st
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from components.radial_bracket import render_radial_bracket
from components.bracket_board import render_knockout_bracket_shell

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

tab_radial, tab_paper = st.tabs(["🌐 Radial Bracket", "📋 Wall Bracket"])

with tab_radial:
    render_radial_bracket()

with tab_paper:
    render_knockout_bracket_shell()
