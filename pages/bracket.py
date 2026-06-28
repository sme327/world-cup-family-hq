import streamlit as st
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from components.bracket_board import render_knockout_bracket_shell

st.markdown("""
<style>
/* Give the bracket page a bit of extra breathing room at the top */
[data-testid="stMainBlockContainer"] { padding-top: .5rem !important; }
</style>
""", unsafe_allow_html=True)

render_knockout_bracket_shell()
