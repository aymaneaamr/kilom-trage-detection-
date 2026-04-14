import streamlit as st
import pandas as pd
from datetime import datetime
import io
from PIL import Image
import numpy as np
import cv2
from paddleocr import PaddleOCR
import re

# Initialisation de PaddleOCR
@st.cache_resource
def init_ocr():
    return PaddleOCR(use_angle_cls=True, lang='en', show_log=False)

ocr = init_ocr()

st.set_page_config(page_title="Auto Tramway", layout="wide")
st.title("🚋 Extraction automatique des compteurs")

# Prétraitement agressif
def preprocess_for_digits(image):
    img = np.array(image.convert('L'))  # niveaux de gris
    # Seuillage adaptatif
    binary = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    # Inversion si nécessaire (chiffres clairs sur fond sombre)
    if np.mean(binary) < 127:
        binary = cv2.bitwise_not(binary)
    # Redimensionnement
    h, w = binary.shape
    if w < 800:
        scale = 800 / w
        new_w = int(w * scale)
        new_h = int(h * scale)
        binary = cv2.resize(binary, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    return binary

def extract_text_paddle(image):
    processed = preprocess_for_digits(image)
    result = ocr.ocr(processed, det=True, rec=True, cls=False)
    texts = []
    for line in result:
        for item in line:
            texts.append(item[1][0])  # texte reconnu
    return ' '.join(texts)

# Découpage haut/bas
def split_image(image):
    w, h = image.size
    top = image.crop((0, 0, w, h//2))
    bottom = image.crop((0, h//2, w, h))
    return top, bottom

# Extraction des chiffres
def extract_numbers(text):
    return re.sub(r'[^0-9]', '', text)

# Interface
with st.sidebar:
    tram = st.text_input("Numéro tramway")
    st.markdown("---")
    st.warning("Pour une bonne reconnaissance : photo nette, chiffres bien visibles, pas de reflets.")

uploaded = st.file_uploader("Photos des compteurs", type=['jpg','png','jpeg'], accept_multiple_files=True)

if st.button("Lancer l'extraction automatique") and uploaded and tram:
    data = []
    progress = st.progress(0)
    for i, file in enumerate(uploaded):
        img = Image.open(file)
        st.image(img, caption=file.name, width=200)
        top, bottom = split_image(img)
        
        # Extraction texte
        text_top = extract_text_paddle(top)
        text_bottom = extract_text_paddle(bottom)
        
        numbers_top = extract_numbers(text_top)
        numbers_bottom = extract_numbers(text_bottom)
        
        # Interprétation
        heure = None
        if len(numbers_top) >= 4:
            heure = f"{numbers_top[:2]}:{numbers_top[2:4]}"
        if not heure:
            heure = datetime.now().strftime("%H:%M")
        
        km = None
        if len(numbers_bottom) >= 4:
            km = int(numbers_bottom)
        
        data.append({
            "Tramway": tram,
            "Kilométrage": km if km else "Non détecté",
            "Heure": heure,
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        progress.progress((i+1)/len(uploaded))
    
    df = pd.DataFrame(data)
    st.dataframe(df)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    st.download_button("Exporter Excel", buffer.getvalue(), file_name="tramway.xlsx")
