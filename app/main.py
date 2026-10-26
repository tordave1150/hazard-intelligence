import streamlit as st

st.set_page_config(
    page_title="Weather Advisor",
    page_icon="⛈",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page("home.py", title="Home", icon="🏠", default=True),
    st.Page("forecast.py", title="Weather Forecast", icon="🌍"),
    st.Page("historical.py", title="Historical Rain Report", icon="🌧"),
])

# Force start on Home page for new sessions (overrides browser cache of last visited page)
if "first_visit" not in st.session_state:
    st.session_state["first_visit"] = True
    st.switch_page("home.py")

pg.run()
