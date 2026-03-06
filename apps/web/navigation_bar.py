from __future__ import annotations

import streamlit as st

# Intentionally excludes: landing page, Label, and Video Management.
NAV_ITEMS: list[tuple[str, str]] = [
    ("pages/00_Home.py", "Home"),
    ("pages/01_Generate.py", "Generate"),
    ("pages/03_Train.py", "Train"),
    ("pages/04_Deploy.py", "Deploy"),
    ("pages/06_Dashboard.py", "Dashboard"),
    ("pages/07_Fine_Tune.py", "Fine Tune"),
    ("pages/08_Compare.py", "Compare"),
]


def render_navigation_bar() -> None:
    # Hide Streamlit's built-in multipage menu so only this custom navigation
    # section is visible (single link per page).
    st.markdown(
        """
<style>
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {
    display: none;
}
section[data-testid="stSidebar"] div[data-testid="stSidebarNavSeparator"] {
    display: none;
}
</style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Navigation")
        for page_path, label in NAV_ITEMS:
            st.page_link(page_path, label=label, use_container_width=True)
