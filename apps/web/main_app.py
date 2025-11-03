import streamlit as st

from apps.web import api_client

APP_TITLE = "Reachy Emotion Labeling — Web"


def get_api_base() -> str:
    return api_client.media_api_base()


def get_gateway_base() -> str:
    return api_client.gateway_api_base()


def get_token_present() -> bool:
    return bool(api_client._headers().get("Authorization"))


def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)

    with st.sidebar:
        st.header("Navigation")
        st.markdown("Use the Pages section in the left sidebar to switch between views.")
        st.divider()
        st.subheader("API Configuration")
        st.caption("Derived from environment variables or defaults.")
        st.code(f"REACHY_API_BASE = {get_api_base()}")
        st.code(f"REACHY_GATEWAY_BASE = {get_gateway_base()}")
        token_msg = "present" if get_token_present() else "not set"
        st.code(f"REACHY_API_TOKEN = <{token_msg}>")
        st.divider()
        st.caption("Tip: Run with 'streamlit run apps/web/main_app.py'.")

    st.info("This is the Streamlit entrypoint. Select a page from the sidebar to begin.")
    st.write(
        """
        Pages:
        - 00_Home: Upload, generate, classify, and promote videos end-to-end.
        - 01_Generate: Prototype inputs for generating synthetic clips (legacy placeholder).
        - 02_Label: Browse temp clips and preview promote dry-runs.
        - 03_Train: Rebuild manifests and view dataset readiness (placeholder).
        - 04_Deploy: View deployment status and actions (placeholder).
        """
    )


if __name__ == "__main__":
    main()
