import streamlit as st
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Playwright Test")

st.title("Playwright Test")

if st.button("Browser starten"):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            st.success("✅ Chromium gestartet!")
            browser.close()

    except Exception as e:
        st.exception(e)
