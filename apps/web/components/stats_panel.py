from collections import Counter
from typing import Iterable, Mapping

import streamlit as st


def render_counts(items: Iterable[Mapping]) -> None:
    labels = [it.get("label") for it in items if it]
    counts = Counter(labels)
    st.subheader("Counts by label")
    for k, v in counts.items():
        st.text(f"{k}: {v}")
