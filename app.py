import streamlit as st
import pandas as pd
from datetime import datetime
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import re
import io
import numpy as np

# Configuration automatique de Tesseract selon l'OS
import platform
import subprocess

# Configuration de Tesseract
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
elif platform.system() == "Linux":
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
elif platform.system() == "Darwin":
    pytesseract.pytesseract.tesseract_cmd = "/usr/local/bin/tesseract"

# Configuration de la page
st.set_page_config(
    page_title="Extraction Tramway",
    page_icon="🚋",
    layout="wide"
)

# Titre de l'application
st.title("🚋 Extraction Automatique des Données Tramway")
st.markdown("---")

# Fonction de prétraitement de l'image (version PIL seulement)
def preprocess_image(image):
    """Améliore la qualité de l'image pour l'OCR en utilisant PIL"""
    # Convertir en niveaux de gris
    gray = image.convert('L')
    
    # Améliorer le contraste
    enhancer = ImageEnhance.Contrast(gray)
    enhanced = enhancer.enhance(2.0)
    
    # Augmenter la netteté
    sharpener = ImageEnhance.Sharpness(enhanced)
    sharp = sharpener.enhance(2.0)
    
    # Réduire le bruit (filtre médian)
    denoised = sharp.filter(ImageFilter.MedianFilter(size=3))
    
    return denoised

# Fonction d'extraction du texte
def extract_text_from_image(image):
    """Extrait le texte de l'image"""
    try:
        # Prétraiter l'image
        processed_img = preprocess_image(image)
        
        # Configuration pour pytesseract
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789:.,hkm '
        
        # Extraire le texte
        text = pytesseract.image_to_string(processed_img, config=custom_config, lang='fra+eng')
        
        return text
    except Exception as e:
        st.error(f"Erreur lors de l'extraction: {str(e)}")
        return ""

# Fonction d'extraction du kilométrage
def extract_kilometrage(text):
    """Extrait le kilométrage du texte"""
    patterns = [
        r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(?:km|KM|Km|kilomètres?)?',
        r'(\d{4,6}(?:[.,]\d{1,2})?)',
        r'(\d+[.,]\d+)\s*km',
        r'(\d{4,6})'  # Pour les nombres simples de 4 à 6 chiffres
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Nettoyer et convertir
            km_str = str(matches[0]).replace(',', '.').strip()
            # Enlever les caractères non numériques sauf le point
            km_str = re.sub(r'[^\d.]', '', km_str)
            if km_str and km_str != '.':
                try:
                    return float(km_str)
                except:
                    continue
    return None

# Fonction d'extraction de l'heure
def extract_time(text):
    """Extrait l'heure du texte"""
    time_patterns = [
        r'(\d{1,2}[:h]\d{2})',
        r'(\d{1,2})[:h](\d{2})',
        r'(\d{1,2})[.:](\d{2})',
        r'(\d{2})[.:](\d{2})'  # Format HH.MM ou HH:MM
    ]
    
    for pattern in time_patterns:
        matches = re.findall(pattern, text)
        if matches:
            if isinstance(matches[0], tuple):
                heure = f"{matches[0][0]}:{matches[0][1]}"
            else:
                heure = matches[0].replace('h', ':')
            # Valider que l'heure est plausible
            try:
                parts = heure.split(':')
                if 0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59:
                    return heure
            except:
                continue
    return None

# Fonction principale de traitement
def process_image(image, tram_number):
    """Traite une image et extrait les informations"""
    
    # Extraire le texte de l'image
    with st.spinner("Analyse de l'image en cours..."):
        text = extract_text_from_image(image)
        
    # Afficher le texte extrait (debug)
    with st.expander(f"Texte extrait de l'image"):
        st.code(text if text else "Aucun texte détecté")
    
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
    
    st.markdown("---")
    st.subheader("⚙️ Paramètres")
    
    need_manual_input = st.checkbox("Saisie manuelle si extraction échoue")
    
    # Informations
    st.markdown("---")
    st.info(
        "💡 **Conseils pour les photos:**\n"
        "- Bon éclairage\n"
        "- Photo nette\n"
        "- Cadrer le compteur\n"
        "- Éviter les reflets\n"
        "- Chiffres bien lisibles"
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
            progress_bar = st.progress(0)
            for idx, file in enumerate(uploaded_files):
                # Lire l'image
                image = Image.open(file)
                
                # Afficher l'image
                st.image(image, caption=f"Photo: {file.name}", width=200)
                
                # Traiter l'image
                result = process_image(image, tram_number)
                st.session_state.data_list.append(result)
                
                # Mettre à jour la progression
                progress_bar.progress((idx + 1) / len(uploaded_files))
                
                # Afficher le résultat
                st.success(f"✅ Traitement de {file.name} terminé")
            
            st.success(f"🎉 Traitement terminé! {len(uploaded_files)} image(s) traitée(s)")
                
    # Afficher les données
    if st.session_state.data_list:
        df = pd.DataFrame(st.session_state.data_list)
        st.dataframe(df, use_container_width=True)
        
        # Statistiques
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        with col_stats1:
            st.metric("Total images", len(st.session_state.data_list))
        
        # Compter les kilométrages détectés
        km_detected = sum(1 for x in st.session_state.data_list if x["Kilométrage (km)"] != "Non détecté")
        with col_stats2:
            st.metric("Kilométrages détectés", f"{km_detected}/{len(st.session_state.data_list)}")
        
        with col_stats3:
            st.metric("Heures extraites", len(st.session_state.data_list))
        
        # Bouton d'export Excel
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
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
        
        if st.button("📥 Exporter vers Excel", type="primary"):
            st.download_button(
                label="💾 Télécharger le fichier Excel",
                data=excel_buffer.getvalue(),
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
    
    1. **Installer Tesseract OCR** sur votre système
    2. **Lancer l'application**: `streamlit run app.py`
    3. **Saisir le numéro du tramway**
    4. **Télécharger les photos** des compteurs
    5. **Cliquer sur "Traiter les images"**
    6. **Exporter les données** en Excel
    
    ### Pour le déploiement sur Streamlit Cloud:
    Créez un fichier `packages.txt` avec:
