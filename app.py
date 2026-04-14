import streamlit as st
import pandas as pd
from datetime import datetime
import io
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import easyocr
import re

# Initialisation du reader EasyOCR (une seule fois)
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)  # 'en' suffit pour les chiffres

reader = load_ocr_reader()

st.set_page_config(page_title="Extraction Tramway Auto", page_icon="🚋", layout="wide")
st.title("🚋 Extraction Automatique des Données Tramway")
st.markdown("---")

# Prétraitement agressif pour les chiffres
def preprocess_image(image):
    """Améliore l'image spécifiquement pour les chiffres"""
    # Convertir en numpy array
    img = np.array(image)
    
    # Niveaux de gris
    if len(img.shape) == 3:
        gray = np.dot(img[...,:3], [0.299, 0.587, 0.114])
    else:
        gray = img
    
    # Égalisation d'histogramme pour améliorer le contraste
    from skimage import exposure
    gray = exposure.equalize_hist(gray)
    
    # Seuillage adaptatif
    from skimage.filters import threshold_local
    block_size = 35
    local_thresh = threshold_local(gray, block_size, offset=10)
    binary = (gray > local_thresh).astype(np.uint8) * 255
    
    return binary

def extract_numbers_easyocr(image):
    """Extrait les chiffres avec EasyOCR"""
    # Prétraiter
    processed = preprocess_image(image)
    
    # Lire avec EasyOCR
    results = reader.readtext(processed, detail=0, paragraph=False)
    full_text = ' '.join(results)
    
    # Ne garder que les chiffres
    numbers = re.sub(r'[^0-9]', '', full_text)
    return numbers

def crop_counters(image):
    """Découpe l'image en zones heure (haut) et km (bas)"""
    width, height = image.size
    # Supposons que l'heure est dans les 40% supérieurs, km dans les 60% inférieurs
    heure_zone = image.crop((0, 0, width, int(height * 0.4)))
    km_zone = image.crop((0, int(height * 0.4), width, height))
    return heure_zone, km_zone

def format_heure(raw_numbers):
    """Convertit une chaîne de chiffres en HH:MM:SS ou HH:MM"""
    if not raw_numbers:
        return None
    # Si plus de 4 chiffres, on prend les 6 premiers (HHMMSS)
    if len(raw_numbers) >= 6:
        h = raw_numbers[:2]
        m = raw_numbers[2:4]
        s = raw_numbers[4:6]
        return f"{h}:{m}:{s}"
    elif len(raw_numbers) >= 4:
        h = raw_numbers[:2]
        m = raw_numbers[2:4]
        return f"{h}:{m}"
    elif len(raw_numbers) >= 2:
        return f"00:{raw_numbers}"
    return None

def format_kilometrage(raw_numbers):
    """Convertit la chaîne en nombre"""
    if not raw_numbers:
        return None
    try:
        return int(raw_numbers)
    except:
        return None

# Interface
with st.sidebar:
    tram_number = st.text_input("Numéro du Tramway:", placeholder="Ex: 1234")
    st.markdown("---")
    st.info("💡 **Astuces photo:**\n- Cadrez serré sur les chiffres\n- Évitez les reflets\n- Photo nette")

col1, col2 = st.columns([1, 1])

with col1:
    uploaded_files = st.file_uploader("Photos des compteurs", type=['jpg','jpeg','png'], accept_multiple_files=True)

with col2:
    if st.button("🔄 Lire automatiquement les photos", type="primary"):
        if not tram_number:
            st.error("Entrez le numéro du tramway")
        elif not uploaded_files:
            st.error("Téléchargez des photos")
        else:
            if 'data_list' not in st.session_state:
                st.session_state.data_list = []
            
            for file in uploaded_files:
                image = Image.open(file)
                st.image(image, caption=file.name, width=200)
                
                # Découpage
                heure_img, km_img = crop_counters(image)
                
                # Extraction
                heure_raw = extract_numbers_easyocr(heure_img)
                km_raw = extract_numbers_easyocr(km_img)
                
                # Affichage debug
                with st.expander(f"Résultats bruts pour {file.name}"):
                    st.write(f"Heure brute: {heure_raw}")
                    st.write(f"KM brut: {km_raw}")
                
                # Formatage
                heure = format_heure(heure_raw)
                km = format_kilometrage(km_raw)
                
                if not heure:
                    heure = datetime.now().strftime("%H:%M")
                    st.warning("Heure non détectée, heure actuelle utilisée")
                if not km:
                    st.error("Kilométrage non détecté - essaie avec une meilleure photo")
                
                st.session_state.data_list.append({
                    "Numéro Tramway": tram_number,
                    "Kilométrage": km if km else "Non détecté",
                    "Heure": heure,
                    "Date extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Fichier": file.name
                })
            
            st.success(f"Traité {len(uploaded_files)} photo(s)")

# Affichage des données
if 'data_list' in st.session_state and st.session_state.data_list:
    df = pd.DataFrame(st.session_state.data_list)
    st.dataframe(df)
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Exporter Excel", data=excel_buffer.getvalue(),
                       file_name=f"tramway_{tram_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
