import streamlit as st
from libapp import widgets

widgets.inject_css()

st.title("Diagnostic Territorial")
st.markdown(
    "Identifiez les zones sous-dotées en soins sur votre territoire "
    "et comprenez les facteurs qui expliquent ces inégalités."
)
st.markdown("---")

st.markdown("#### Que contient cet outil ?")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("🗺️ **Cartographie**  \nAccessibilité aux soins par commune")
with col2:
    st.markdown("📊 **Profils**  \nIndicateurs socio-sanitaires combinés")
with col3:
    st.markdown("🎯 **Clusters**  \nTypologies de territoires")
