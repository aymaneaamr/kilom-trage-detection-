import streamlit as st
import pandas as pd
from datetime import datetime
import io
from PIL import Image
import requests
import base64
import re

st.set_page_config(page_title="Tramway Auto", layout="wide")
st.title("🚋 Extraction automatique des compteurs (via OCR.space)")

# Configuration
API_KEY = "votre_cle_api_ici"  # Remplacez par votre clé OCR.space

def ocr_space_file(image, overlay=False, language='eng'):
    """Appelle l'API OCR.space pour reconnaître le texte dans l'image"""
    # Convertir PIL en bytes
    img_bytes = io.BytesIO()
    image.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    payload = {
        'apikey': API_KEY,
        'language': language,
        'isOverlayRequired': overlay,
        'filetype': 'PNG',
    }
    files = {'file': ('image.png', img_bytes, 'image/png')}
    response = requests.post('https://api.ocr.space/parse/image', files=files, data=payload)
    result = response.json()
    
    if result['IsErroredOnProcessing']:
        st.error(f"Erreur OCR: {result['ErrorMessage']}")
        return ""
    else:
        parsed_text = result['ParsedResults'][0]['ParsedText']
        return parsed_text

def extract_numbers(text):
    return re.sub(r'[^0-9]', '', text)

def format_heure(raw):
    if not raw:
        return None
    if len(raw) >= 6:
        return f"{raw[:2]}:{raw[2:4]}:{raw[4:6]}"
    elif len(raw) >= 4:
        return f"{raw[:2]}:{raw[2:4]}"
    return None

def format_km(raw):
    try:
        return int(raw)
    except:
        return None

# Interface
with st.sidebar:
    tram = st.text_input("Numéro de tramway")
    api_key_input = st.text_input("Clé API OCR.space", type="password", 
                                  help="Obtenez une clé gratuite sur https://ocr.space/OCRAPI")
    if api_key_input:
        API_KEY = api_key_input

uploaded = st.file_uploader("Photos des compteurs", type=['jpg','png','jpeg'], accept_multiple_files=True)

if st.button("🔍 Analyser automatiquement") and uploaded and tram:
    if not API_KEY:
        st.error("Veuillez entrer votre clé API OCR.space")
    else:
        data = []
        for file in uploaded:
            img = Image.open(file)
            st.image(img, caption=file.name, width=250)
            
            # Appel API
            with st.spinner(f"Analyse de {file.name}..."):
                text = ocr_space_file(img, language='eng')
                numbers = extract_numbers(text)
            
            st.text(f"Chiffres bruts détectés: {numbers if numbers else 'Aucun'}")
            
            # Découpage hypothétique (les 6 premiers chiffres = heure ?)
            if len(numbers) >= 10:
                heure_raw = numbers[:6]   # 6 chiffres HHMMSS
                km_raw = numbers[6:]
            elif len(numbers) >= 6:
                heure_raw = numbers[:6]
                km_raw = numbers[6:]
            else:
                heure_raw = numbers
                km_raw = ""
            
            heure = format_heure(heure_raw)
            km = format_km(km_raw)
            
            if not heure:
                heure = datetime.now().strftime("%H:%M")
                st.warning("Heure non reconnue")
            if not km:
                st.warning("Kilométrage non reconnu")
            
            data.append({
                "Tramway": tram,
                "Km": km if km else "?",
                "Heure": heure,
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df)
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button("📥 Excel", buffer.getvalue(), file_name=f"tramway_{tram}.xlsx")
