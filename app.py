import streamlit as st
import pandas as pd
from datetime import datetime
import io
from PIL import Image
import numpy as np
import cv2
from paddleocr import PaddleOCR
import re

# Configuration de la page
st.set_page_config(page_title="Extraction Tramway Auto", page_icon="🚋", layout="wide")
st.title("🚋 Extraction Automatique des Données Tramway")

# Initialisation de PaddleOCR (chargé une seule fois)
@st.cache_resource
def load_ocr():
    return PaddleOCR(use_angle_cls=False, lang='en', show_log=False)

ocr = load_ocr()

def preprocess_image(image):
    """Prétraitement agressif pour les compteurs à chiffres"""
    # Conversion en niveaux de gris
    img = np.array(image.convert('L'))
    # Application d'un seuillage adaptatif pour binariser l'image
    binary = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    # Redimensionnement pour améliorer la reconnaissance
    h, w = binary.shape
    if w < 800:
        scale = 800 / w
        new_w = int(w * scale)
        new_h = int(h * scale)
        binary = cv2.resize(binary, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    return binary

def extract_text_from_region(image_region):
    """Extrait le texte d'une région d'image avec PaddleOCR"""
    try:
        processed = preprocess_image(image_region)
        result = ocr.ocr(processed, det=True, rec=True, cls=False)
        texts = []
        if result and result[0]:
            for line in result[0]:
                texts.append(line[1][0])  # texte détecté
        return ' '.join(texts)
    except Exception as e:
        st.warning(f"Erreur OCR sur une région: {str(e)}")
        return ""

def extract_numbers(text):
    """Extrait uniquement les chiffres du texte"""
    return re.sub(r'[^0-9]', '', text)

def format_heure(raw_numbers):
    """Formate une chaîne de chiffres en HH:MM:SS ou HH:MM"""
    if not raw_numbers:
        return None
    if len(raw_numbers) >= 6:
        return f"{raw_numbers[:2]}:{raw_numbers[2:4]}:{raw_numbers[4:6]}"
    elif len(raw_numbers) >= 4:
        return f"{raw_numbers[:2]}:{raw_numbers[2:4]}"
    return None

def format_kilometrage(raw_numbers):
    """Convertit une chaîne de chiffres en entier"""
    if not raw_numbers:
        return None
    try:
        return int(raw_numbers)
    except:
        return None

# Interface Streamlit
with st.sidebar:
    tram_number = st.text_input("Numéro du Tramway:", placeholder="Ex: 1234")
    st.markdown("---")
    st.info("💡 **Conseils pour les photos :**\n- Cadrez bien les chiffres\n- Évitez les reflets\n- Bonne luminosité")

uploaded_files = st.file_uploader("Téléchargez les photos des compteurs",
                                  type=['jpg', 'jpeg', 'png'],
                                  accept_multiple_files=True)

if st.button("🚀 Lancer l'extraction automatique", type="primary"):
    if not tram_number:
        st.error("Veuillez entrer le numéro du tramway")
    elif not uploaded_files:
        st.error("Veuillez télécharger au moins une photo")
    else:
        if 'data' not in st.session_state:
            st.session_state.data = []
        progress_bar = st.progress(0)
        for idx, file in enumerate(uploaded_files):
            image = Image.open(file)
            st.image(image, caption=file.name, width=250)
            # Découpage de l'image (moitié supérieure pour l'heure, moitié inférieure pour le km)
            w, h = image.size
            top = image.crop((0, 0, w, h//2))
            bottom = image.crop((0, h//2, w, h))
            # Extraction des textes
            text_top = extract_text_from_region(top)
            text_bottom = extract_text_from_region(bottom)
            numbers_top = extract_numbers(text_top)
            numbers_bottom = extract_numbers(text_bottom)
            # Formatage
            heure = format_heure(numbers_top)
            if not heure:
                heure = datetime.now().strftime("%H:%M")
                st.warning("Heure non détectée, utilisation de l'heure actuelle")
            km = format_kilometrage(numbers_bottom)
            if not km:
                st.error("Kilométrage non détecté")
            # Sauvegarde
            st.session_state.data.append({
                "Numéro Tramway": tram_number,
                "Kilométrage (km)": km if km else "Non détecté",
                "Heure": heure,
                "Date extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Fichier": file.name
            })
            progress_bar.progress((idx + 1) / len(uploaded_files))
        st.success(f"Traitement terminé ! {len(uploaded_files)} photo(s) traitée(s).")

# Affichage des résultats
if 'data' in st.session_state and st.session_state.data:
    df = pd.DataFrame(st.session_state.data)
    st.dataframe(df)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Télécharger le fichier Excel",
                       data=buffer.getvalue(),
                       file_name=f"tramway_{tram_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
