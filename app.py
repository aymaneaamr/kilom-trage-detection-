import streamlit as st
import pandas as pd
from datetime import datetime
import io
import requests
from PIL import Image, ImageEnhance, ImageOps
import re

st.set_page_config(page_title="Extraction Tramway", layout="wide")
st.title("🚋 Extraction automatique des compteurs tramway")

# Ta clé API OCR.space
API_KEY = "AQ.Ab8RN6Jmi2Vk4bz7UfIvfDvsHfjBNwFOnIni_KtemuXjESrrhg"

def preprocess_image(image):
    """Améliore l'image pour la reconnaissance des chiffres"""
    # Convertir en niveaux de gris
    img = image.convert('L')
    
    # Augmenter le contraste fortement
    img = ImageEnhance.Contrast(img).enhance(3.0)
    
    # Égalisation de l'histogramme
    img = ImageOps.equalize(img)
    
    # Binarisation pour ne garder que le noir et blanc
    threshold = 160
    img = img.point(lambda x: 0 if x < threshold else 255, '1')
    
    # Redimensionner pour agrandir les chiffres
    width, height = img.size
    img = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
    
    return img

def ocr_space_file(image):
    """Envoie l'image à l'API OCR.space et retourne le texte"""
    # Prétraiter l'image
    processed = preprocess_image(image)
    
    # Convertir en bytes
    buffered = io.BytesIO()
    processed.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    
    # Préparer la requête
    payload = {
        'apikey': API_KEY,
        'language': 'eng',
        'isOverlayRequired': False,
        'OCREngine': 2,
        'scale': True,
        'detectOrientation': True,
    }
    files = {'file': ('image.png', img_bytes, 'image/png')}
    
    try:
        response = requests.post('https://api.ocr.space/parse/image', files=files, data=payload, timeout=30)
        result = response.json()
        
        if result.get('IsErroredOnProcessing'):
            st.error(f"Erreur API: {result.get('ErrorMessage')}")
            return ""
        
        if result.get('ParsedResults'):
            text = result['ParsedResults'][0]['ParsedText']
            return text
        return ""
    except Exception as e:
        st.error(f"Erreur de connexion: {e}")
        return ""

def extract_numbers(text):
    """Extrait tous les nombres du texte (groupes de chiffres)"""
    numbers = re.findall(r'\b\d{2,}\b', text)
    return numbers

def extract_two_values(numbers_list):
    """Extrait deux valeurs : la plus grande (km) et l'autre (temps)"""
    if not numbers_list:
        return None, None
    
    # Convertir en entiers
    int_numbers = []
    for n in numbers_list:
        try:
            int_numbers.append(int(n))
        except:
            pass
    
    if len(int_numbers) == 0:
        return None, None
    elif len(int_numbers) == 1:
        return None, int_numbers[0]
    else:
        int_numbers.sort()
        valeur_basse = int_numbers[0]
        valeur_haute = int_numbers[-1]
        return valeur_basse, valeur_haute

def process_image(image):
    """Analyse l'image entière et extrait les deux valeurs"""
    with st.spinner("Analyse de l'image en cours..."):
        full_text = ocr_space_file(image)
    
    all_numbers = extract_numbers(full_text)
    valeur1, valeur2 = extract_two_values(all_numbers)
    
    return valeur1, valeur2, full_text, all_numbers

# Interface Streamlit
with st.sidebar:
    tram = st.text_input("Numéro du tramway", placeholder="Ex: 1234")
    st.markdown("---")
    st.success("✅ API OCR.space connectée")
    st.info("""
    **Conseils :**
    - Photo bien éclairée
    - Cadrez serré sur les chiffres
    - Évitez les reflets
    """)

uploaded_files = st.file_uploader("Photos des compteurs", type=['jpg','png','jpeg'], accept_multiple_files=True)

if st.button("🚀 Extraire automatiquement", type="primary"):
    if not tram:
        st.error("Entrez le numéro du tramway")
    elif not uploaded_files:
        st.error("Téléchargez au moins une photo")
    else:
        if 'data' not in st.session_state:
            st.session_state.data = []
        
        for idx, file in enumerate(uploaded_files):
            st.markdown(f"### Photo {idx+1}")
            
            img = Image.open(file)
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.image(img, caption=file.name, width=250)
            
            with col2:
                valeur1, valeur2, full_text, all_numbers = process_image(img)
                
                with st.expander("Texte brut détecté"):
                    st.write(f"**Texte complet :** {full_text if full_text else 'rien'}")
                    st.write(f"**Nombres trouvés :** {all_numbers if all_numbers else 'rien'}")
                
                if valeur1 and valeur2:
                    st.success(f"✅ Temps/Heure : {valeur1}")
                    st.success(f"✅ Kilométrage : {valeur2}")
                    
                    st.session_state.data.append({
                        "Numéro Tramway": tram,
                        "Temps de fonctionnement": valeur1,
                        "Kilométrage (km)": valeur2,
                        "Date extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Fichier": file.name
                    })
                    st.success(f"✅ Photo {idx+1} enregistrée !")
                    
                elif valeur2 and not valeur1:
                    st.warning(f"⚠️ Un seul nombre trouvé : {valeur2}")
                    
                    col_man1, col_man2 = st.columns(2)
                    with col_man1:
                        man_v1 = st.text_input("Temps/Heure", key=f"v1_{idx}")
                    with col_man2:
                        man_v2 = st.text_input("Kilométrage", value=str(valeur2), key=f"v2_{idx}")
                    
                    if st.button(f"✅ Enregistrer", key=f"save_{idx}"):
                        if man_v1 and man_v2:
                            st.session_state.data.append({
                                "Numéro Tramway": tram,
                                "Temps de fonctionnement": man_v1,
                                "Kilométrage (km)": man_v2,
                                "Date extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Fichier": file.name
                            })
                            st.success(f"Photo {idx+1} enregistrée !")
                            st.rerun()
                else:
                    st.error("❌ Aucun nombre détecté")
                    
                    st.info("Saisie manuelle :")
                    col_man1, col_man2 = st.columns(2)
                    with col_man1:
                        man_v1 = st.text_input("Temps/Heure", key=f"v1_{idx}")
                    with col_man2:
                        man_v2 = st.text_input("Kilométrage", key=f"v2_{idx}")
                    
                    if st.button(f"✅ Enregistrer", key=f"save_{idx}"):
                        if man_v1 and man_v2:
                            st.session_state.data.append({
                                "Numéro Tramway": tram,
                                "Temps de fonctionnement": man_v1,
                                "Kilométrage (km)": man_v2,
                                "Date extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Fichier": file.name
                            })
                            st.success(f"Photo {idx+1} enregistrée !")
                            st.rerun()
        
        if st.session_state.data:
            st.balloons()
            st.success(f"Traitement terminé ! {len(st.session_state.data)} photo(s) enregistrée(s)")

# Affichage des données collectées
if 'data' in st.session_state and st.session_state.data:
    st.markdown("---")
    st.subheader("📊 Données extraites")
    
    df = pd.DataFrame(st.session_state.data)
    st.dataframe(df, use_container_width=True)
    
    # Statistiques
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total photos", len(st.session_state.data))
    with col2:
        nb_temps = sum(1 for x in st.session_state.data if x.get("Temps de fonctionnement"))
        st.metric("Temps détecté", f"{nb_temps}/{len(st.session_state.data)}")
    with col3:
        nb_km = sum(1 for x in st.session_state.data if x.get("Kilométrage (km)"))
        st.metric("Km détecté", f"{nb_km}/{len(st.session_state.data)}")
    
    # Export Excel
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Tramway', index=False)
        
        # Ajuster les largeurs
        worksheet = writer.sheets['Tramway']
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
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        st.download_button(
            label="📥 Exporter vers Excel",
            data=excel_buffer.getvalue(),
            file_name=f"tramway_{tram}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    with col_btn2:
        if st.button("🗑️ Effacer toutes les données"):
            st.session_state.data = []
            st.rerun()

st.markdown("---")
st.caption("🔧 Application d'extraction des données tramway - OCR.space")
