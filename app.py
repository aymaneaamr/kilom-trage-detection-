import streamlit as st
import pandas as pd
from datetime import datetime
import io
from PIL import Image

# Configuration de la page
st.set_page_config(
    page_title="Saisie Tramway",
    page_icon="🚋",
    layout="wide"
)

st.title("🚋 Saisie Manuelle des Données Tramway")
st.markdown("---")

# Initialisation des données
if 'data_list' not in st.session_state:
    st.session_state.data_list = []

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    tram_number = st.text_input("Numéro du Tramway:", placeholder="Ex: 1234")
    st.markdown("---")
    st.info("📌 **Pour votre compteur:**\n- Heure: 823743 → saisir `82:37:43`\n- Kilométrage: `10406871`")
    st.markdown("---")
    if st.session_state.data_list:
        st.success(f"{len(st.session_state.data_list)} lecture(s) enregistrée(s)")

# Zone principale
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 1. Télécharger les photos")
    uploaded_files = st.file_uploader(
        "Photos des compteurs",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True
    )

with col2:
    st.subheader("✍️ 2. Saisir les valeurs")
    
    if uploaded_files:
        # Créer un onglet par photo
        tabs = st.tabs([f"Photo {i+1}" for i in range(len(uploaded_files))])
        
        for idx, (tab, file) in enumerate(zip(tabs, uploaded_files)):
            with tab:
                # Afficher la photo
                image = Image.open(file)
                st.image(image, caption=file.name, use_container_width=True)
                
                # Champs de saisie
                col_h, col_km = st.columns(2)
                with col_h:
                    heure = st.text_input(
                        "Heure (HH:MM ou HH:MM:SS)",
                        placeholder="Ex: 14:37 ou 82:37:43",
                        key=f"h_{idx}"
                    )
                with col_km:
                    km = st.text_input(
                        "Kilométrage (chiffres uniquement)",
                        placeholder="Ex: 10406871",
                        key=f"km_{idx}"
                    )
                
                # Bouton d'ajout
                if st.button(f"✅ Ajouter cette lecture", key=f"btn_{idx}"):
                    if not tram_number:
                        st.error("❌ Entrez le numéro du tramway dans la barre latérale")
                    elif not heure or not km:
                        st.error("❌ Remplissez l'heure ET le kilométrage")
                    else:
                        st.session_state.data_list.append({
                            "Numéro Tramway": tram_number,
                            "Kilométrage": km,
                            "Heure": heure,
                            "Date saisie": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Photo": file.name
                        })
                        st.success(f"✅ Lecture ajoutée !")
                        st.balloons()
    else:
        st.info("👈 Téléchargez des photos à gauche")

# Affichage des données collectées
if st.session_state.data_list:
    st.markdown("---")
    st.subheader("📋 3. Données enregistrées")
    
    df = pd.DataFrame(st.session_state.data_list)
    st.dataframe(df, use_container_width=True)
    
    # Export Excel
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Tramway', index=False)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Exporter vers Excel",
            data=excel_buffer.getvalue(),
            file_name=f"tramway_{tram_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    with col2:
        if st.button("🗑️ Effacer toutes les données"):
            st.session_state.data_list = []
            st.rerun()
