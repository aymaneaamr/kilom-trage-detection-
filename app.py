import streamlit as st
import pandas as pd
from datetime import datetime
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import re
import io
import numpy as np

# Configuration automatique de Tesseract selon l'OS
import platform

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

# Fonction de prétraitement améliorée pour chiffres sur fond sombre
def preprocess_image(image):
    """Prétraitement spécifique pour compteurs numériques"""
    # Convertir en niveaux de gris
    gray = image.convert('L')
    
    # Augmenter le contraste radicalement
    enhancer = ImageEnhance.Contrast(gray)
    high_contrast = enhancer.enhance(4.0)
    
    # Augmenter la netteté
    sharpener = ImageEnhance.Sharpness(high_contrast)
    sharp = sharpener.enhance(3.0)
    
    # Redimensionner pour améliorer la reconnaissance (x2)
    width, height = sharp.size
    enlarged = sharp.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
    
    # Binarisation avec seuil adaptatif
    threshold = 180
    binary = enlarged.point(lambda x: 0 if x < threshold else 255, '1')
    
    return binary

# Fonction d'extraction du texte spécifique pour chiffres
def extract_numbers_from_image(image):
    """Extrait uniquement les chiffres de l'image"""
    try:
        # Prétraiter l'image
        processed = preprocess_image(image)
        
        # Configuration OCR spéciale chiffres
        custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789'
        
        # Extraire le texte
        text = pytesseract.image_to_string(processed, config=custom_config)
        
        # Nettoyer pour ne garder que les chiffres
        numbers = re.sub(r'[^0-9]', '', text)
        
        return numbers
    except Exception as e:
        st.error(f"Erreur OCR: {str(e)}")
        return ""

# Fonction pour extraire les deux compteurs
def extract_counters(image):
    """Extrait les valeurs des compteurs"""
    width, height = image.size
    
    # Découper l'image (30% haut pour heure, 70% bas pour km)
    # Ajusté car l'heure est en haut et km en bas
    heure_region = image.crop((0, 0, width, int(height * 0.4)))
    km_region = image.crop((0, int(height * 0.4), width, height))
    
    # Extraire les chiffres
    heure_raw = extract_numbers_from_image(heure_region)
    km_raw = extract_numbers_from_image(km_region)
    
    return heure_raw, km_raw

# Fonction pour formater l'heure
def format_heure(raw_numbers):
    """Formate les chiffres en heure HH:MM"""
    if not raw_numbers:
        return None
    
    # Prendre les 4 premiers chiffres
    if len(raw_numbers) >= 4:
        heure_str = raw_numbers[:4]
        return f"{heure_str[:2]}:{heure_str[2:4]}"
    elif len(raw_numbers) == 3:
        return f"0{raw_numbers[0]}:{raw_numbers[1:3]}"
    elif len(raw_numbers) == 2:
        return f"00:{raw_numbers}"
    return None

# Fonction pour formater le kilométrage
def format_kilometrage(raw_numbers):
    """Formate les chiffres en kilométrage"""
    if not raw_numbers:
        return None
    
    # Convertir en nombre
    try:
        km = int(raw_numbers)
        return km
    except:
        return None

# Interface principale - Sidebar
with st.sidebar:
    st.header("📋 Configuration")
    st.markdown("---")
    
    # Saisie manuelle du numéro de tramway
    tram_number = st.text_input("Numéro du Tramway:", placeholder="Ex: 1234")
    
    st.markdown("---")
    st.subheader("⚙️ Mode d'extraction")
    
    extraction_mode = st.radio(
        "Choisissez le mode:",
        ["Automatique (OCR)", "Manuel (saisie directe)"],
        help="Mode automatique tente de lire la photo, mode manuel permet de saisir les valeurs"
    )
    
    st.markdown("---")
    st.info(
        "💡 **Pour une meilleure reconnaissance:**\n\n"
        "• Photo bien éclairée\n"
        "• Cadrer uniquement les chiffres\n"
        "• Éviter les reflets\n"
        "• Photo nette et de face\n\n"
        "📌 **Structure du compteur:**\n"
        "• Haut: Heure (ex: 823743 → 82:37:43 ou 14:37)\n"
        "• Bas: Kilométrage (ex: 10406871)"
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
    
    # Traitement automatique
    if extraction_mode == "Automatique (OCR)":
        if st.button("🔄 Traiter les images avec OCR", type="primary"):
            if not tram_number:
                st.error("Veuillez entrer le numéro du tramway")
            elif not uploaded_files:
                st.error("Veuillez télécharger au moins une photo")
            else:
                for file in uploaded_files:
                    # Lire l'image
                    image = Image.open(file)
                    
                    # Afficher l'image
                    st.image(image, caption=f"Photo: {file.name}", width=250)
                    
                    # Extraire les compteurs
                    heure_raw, km_raw = extract_counters(image)
                    
                    # Afficher les résultats bruts
                    with st.expander(f"Détails extraction - {file.name}"):
                        st.write(f"Chiffres bruts heure: {heure_raw if heure_raw else 'Non détectés'}")
                        st.write(f"Chiffres bruts km: {km_raw if km_raw else 'Non détectés'}")
                    
                    # Formater les résultats
                    heure = format_heure(heure_raw)
                    kilometrage = format_kilometrage(km_raw)
                    
                    if not heure:
                        heure = datetime.now().strftime("%H:%M")
                        st.warning("⚠️ Heure non détectée, utilisation heure actuelle")
                    
                    if not kilometrage:
                        st.error("❌ Kilométrage non détecté - Utilisez le mode manuel")
                    
                    st.session_state.data_list.append({
                        "Numéro Tramway": tram_number,
                        "Kilométrage (km)": kilometrage if kilometrage else "Non détecté",
                        "Heure": heure,
                        "Date extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                
                st.success(f"Traitement terminé! {len(uploaded_files)} image(s)")
    
    # Traitement manuel
    else:
        st.markdown("### Saisie manuelle des données")
        
        if uploaded_files:
            for idx, file in enumerate(uploaded_files):
                image = Image.open(file)
                st.image(image, caption=f"Photo {idx+1}: {file.name}", width=200)
                
                # Créer des champs de saisie uniques pour chaque image
                heure_key = f"heure_{idx}_{file.name}"
                km_key = f"km_{idx}_{file.name}"
                
                col_h, col_km = st.columns(2)
                with col_h:
                    heure_manuelle = st.text_input(
                        f"Heure (HH:MM) - Image {idx+1}",
                        placeholder="Ex: 14:37",
                        key=heure_key
                    )
                with col_km:
                    km_manuelle = st.text_input(
                        f"Kilométrage - Image {idx+1}",
                        placeholder="Ex: 10406871",
                        key=km_key
                    )
                
                # Bouton pour ajouter cette image
                if st.button(f"✅ Ajouter Image {idx+1}", key=f"btn_{idx}"):
                    if heure_manuelle and km_manuelle:
                        st.session_state.data_list.append({
                            "Numéro Tramway": tram_number,
                            "Kilométrage (km)": km_manuelle,
                            "Heure": heure_manuelle,
                            "Date extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.success(f"Image {idx+1} ajoutée!")
                    else:
                        st.error("Veuillez remplir l'heure ET le kilométrage")
            
            # Bouton pour tout ajouter en lot
            if st.button("📦 Ajouter toutes les images en lot"):
                all_filled = True
                for idx, file in enumerate(uploaded_files):
                    heure_key = f"heure_{idx}_{file.name}"
                    km_key = f"km_{idx}_{file.name}"
                    
                    if heure_key in st.session_state and km_key in st.session_state:
                        if st.session_state[heure_key] and st.session_state[km_key]:
                            st.session_state.data_list.append({
                                "Numéro Tramway": tram_number,
                                "Kilométrage (km)": st.session_state[km_key],
                                "Heure": st.session_state[heure_key],
                                "Date extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                        else:
                            all_filled = False
                    else:
                        all_filled = False
                
                if all_filled:
                    st.success(f"{len(uploaded_files)} images ajoutées!")
                else:
                    st.error("Veuillez remplir toutes les données")
        else:
            st.info("Téléchargez des photos pour la saisie manuelle")
    
    # Affichage des données collectées
    if st.session_state.data_list:
        st.markdown("---")
        st.subheader("📋 Données collectées")
        
        df = pd.DataFrame(st.session_state.data_list)
        st.dataframe(df, use_container_width=True)
        
        # Statistiques
        st.metric("Total enregistrements", len(st.session_state.data_list))
        
        # Export Excel
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Données Tramway', index=False)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.download_button(
                label="📥 Exporter vers Excel",
                data=excel_buffer.getvalue(),
                file_name=f"tramway_{tram_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col_btn2:
            if st.button("🗑️ Effacer toutes les données"):
                st.session_state.data_list = []
                st.rerun()

# Instructions
with st.expander("📖 Mode d'emploi"):
    st.markdown("""
    ### Pour utiliser l'application:
    
    **Mode Automatique (OCR):**
    - L'application tente de lire automatiquement les chiffres
    - Si la reconnaissance échoue, passez en mode manuel
    
    **Mode Manuel (Recommandé pour vos photos):**
    1. Sélectionnez "Manuel (saisie directe)"
    2. Téléchargez les photos
    3. Saisissez l'heure (format HH:MM) ex: 14:37
    4. Saisissez le kilométrage ex: 10406871
    5. Cliquez sur "Ajouter"
    
    **Pour votre compteur:**
    - Heure lue: 823743 → à saisir comme 82:37:43 ou 14:37
    - Kilométrage: 10406871
    
    ### Format du fichier Excel exporté:
    - Numéro Tramway
    - Kilométrage (km)
    - Heure
    - Date extraction
    """)

# Footer
st.markdown("---")
st.markdown("🔧 Application développée pour l'extraction des données tramway")
