import streamlit as st
import pandas as pd
from datetime import datetime
import pytesseract
from PIL import Image
import re
import io
import cv2
import numpy as np

# Configuration de la page
st.set_page_config(
    page_title="Extraction Tramway",
    page_icon="🚋",
    layout="wide"
)

# Titre de l'application
st.title("🚋 Extraction Automatique des Données Tramway")
st.markdown("---")

# Fonction de prétraitement de l'image
def preprocess_image(image):
    """Améliore la qualité de l'image pour l'OCR"""
    # Convertir en niveaux de gris
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    
    # Appliquer un seuillage adaptatif
    processed = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Réduire le bruit
    processed = cv2.medianBlur(processed, 3)
    
    return processed

# Fonction d'extraction du texte
def extract_text_from_image(image):
    """Extrait le texte de l'image"""
    try:
        # Prétraiter l'image
        processed_img = preprocess_image(image)
        
        # Configuration pour pytesseract
        custom_config = r'--oem 3 --psm 6'
        
        # Extraire le texte
        text = pytesseract.image_to_string(processed_img, config=custom_config, lang='fra+eng')
        
        return text
    except Exception as e:
        st.error(f"Erreur lors de l'extraction: {str(e)}")
        return ""

# Fonction d'extraction du kilométrage
def extract_kilometrage(text):
    """Extrait le kilométrage du texte"""
    # Pattern pour trouver les nombres (avec ou sans virgule)
    patterns = [
        r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(?:km|KM|Km|kilomètres?)?',
        r'(\d{4,6}(?:[.,]\d{1,2})?)',
        r'(\d+[.,]\d+)\s*km'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Nettoyer et convertir
            km_str = matches[0].replace(',', '.')
            try:
                return float(km_str)
            except:
                continue
    return None

# Fonction d'extraction de l'heure
def extract_time(text):
    """Extrait l'heure du texte"""
    # Pattern pour trouver les heures
    time_patterns = [
        r'(\d{1,2}[:h]\d{2})',
        r'(\d{1,2})[:h](\d{2})',
        r'(\d{1,2})[.:](\d{2})'
    ]
    
    for pattern in time_patterns:
        matches = re.findall(pattern, text)
        if matches:
            if isinstance(matches[0], tuple):
                heure = f"{matches[0][0]}:{matches[0][1]}"
            else:
                heure = matches[0].replace('h', ':')
            return heure
    return None

# Fonction principale de traitement
def process_image(image, tram_number):
    """Traite une image et extrait les informations"""
    
    # Extraire le texte de l'image
    with st.spinner("Analyse de l'image en cours..."):
        text = extract_text_from_image(image)
        
    # Afficher le texte extrait (debug)
    with st.expander("Texte extrait de l'image"):
        st.code(text)
    
    # Extraire les données
    kilometrage = extract_kilometrage(text)
    heure = extract_time(text)
    
    # Si l'heure n'est pas trouvée, utiliser l'heure actuelle
    if not heure:
        heure = datetime.now().strftime("%H:%M")
        st.warning("Heure non détectée, utilisation de l'heure actuelle")
    
    return {
        "Numéro Tramway": tram_number,
        "Kilométrage (km)": kilometrage if kilometrage else "Non détecté",
        "Heure": heure,
        "Date extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# Interface principale - Sidebar
with st.sidebar:
    st.header("📋 Configuration")
    st.markdown("---")
    
    # Saisie manuelle du numéro de tramway
    tram_number = st.text_input("Numéro du Tramway:", placeholder="Ex: 1234")
    
    # Option pour l'OCR
    st.markdown("---")
    st.subheader("⚙️ Paramètres OCR")
    
    need_manual_input = st.checkbox("Saisie manuelle si extraction échoue")
    
    # Informations
    st.markdown("---")
    st.info(
        "💡 **Conseils pour les photos:**\n"
        "- Bon éclairage\n"
        "- Photo nette\n"
        "- Cadrer le compteur\n"
        "- Éviter les reflets"
    )

# Zone principale
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Téléchargement des photos")
    
    # Upload de fichiers
    uploaded_files = st.file_uploader(
        "Choisissez les photos des compteurs",
        type=['jpg', 'jpeg', 'png', 'bmp'],
        accept_multiple_files=True
    )
    
    # Stockage des données
    if 'data_list' not in st.session_state:
        st.session_state.data_list = []

with col2:
    st.subheader("📊 Données extraites")
    
    # Bouton de traitement
    if st.button("🔄 Traiter les images", type="primary"):
        if not tram_number:
            st.error("Veuillez entrer le numéro du tramway")
        elif not uploaded_files:
            st.error("Veuillez télécharger au moins une photo")
        else:
            for file in uploaded_files:
                # Lire l'image
                image = Image.open(file)
                
                # Afficher l'image
                st.image(image, caption=f"Photo: {file.name}", width=200)
                
                # Traiter l'image
                result = process_image(image, tram_number)
                st.session_state.data_list.append(result)
                
                # Afficher le résultat
                st.success(f"✅ Traitement de {file.name} terminé")
                
    # Afficher les données
    if st.session_state.data_list:
        df = pd.DataFrame(st.session_state.data_list)
        st.dataframe(df, use_container_width=True)
        
        # Bouton d'export Excel
        if st.button("📥 Exporter vers Excel"):
            # Créer un fichier Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Données Tramway', index=False)
                
                # Ajuster les largeurs des colonnes
                worksheet = writer.sheets['Données Tramway']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Télécharger le fichier
            st.download_button(
                label="💾 Télécharger le fichier Excel",
                data=output.getvalue(),
                file_name=f"tramway_{tram_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # Bouton pour effacer
        if st.button("🗑️ Effacer toutes les données"):
            st.session_state.data_list = []
            st.rerun()

# Instructions
with st.expander("📖 Instructions d'utilisation"):
    st.markdown("""
    ### Comment utiliser l'application:
    
    1. **Installer les dépendances** (voir requirements.txt)
    2. **Installer Tesseract OCR** sur votre système
    3. **Lancer l'application**: `streamlit run app.py`
    4. **Saisir le numéro du tramway**
    5. **Télécharger les photos** des compteurs
    6. **Cliquer sur "Traiter les images"**
    7. **Exporter les données** en Excel
    
    ### Structure du fichier Excel généré:
    - Numéro Tramway
    - Kilométrage (km)
    - Heure
    - Date extraction
    
    ### Notes importantes:
    - Assurez-vous que les photos sont claires
    - Le kilométrage doit être visible sur l'image
    - L'heure peut être au format 12h ou 24h
    """)

# Footer
st.markdown("---")
st.markdown("🔧 Application développée pour l'extraction automatique des données tramway")
