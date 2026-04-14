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

# Fonction de prétraitement avancée de l'image
def preprocess_image(image):
    """Améliore la qualité de l'image pour l'OCR avec plusieurs techniques"""
    
    # Convertir en niveaux de gris
    gray = image.convert('L')
    
    # Essayer plusieurs méthodes de prétraitement
    processed_images = []
    
    # Méthode 1: Contraste élevé
    enhancer = ImageEnhance.Contrast(gray)
    high_contrast = enhancer.enhance(3.0)
    processed_images.append(high_contrast)
    
    # Méthode 2: Netteté et contraste
    sharpener = ImageEnhance.Sharpness(gray)
    sharp = sharpener.enhance(2.0)
    contrast_enhancer = ImageEnhance.Contrast(sharp)
    sharp_contrast = contrast_enhancer.enhance(2.0)
    processed_images.append(sharp_contrast)
    
    # Méthode 3: Inverser les couleurs (pour texte clair sur fond sombre)
    inverted = ImageOps.invert(gray)
    inverted_enhanced = ImageEnhance.Contrast(inverted).enhance(2.0)
    processed_images.append(inverted_enhanced)
    
    # Méthode 4: Binarisation (noir et blanc pur)
    threshold = 150
    binary = gray.point(lambda x: 0 if x < threshold else 255, '1')
    processed_images.append(binary)
    
    return processed_images

# Fonction d'extraction du texte avec plusieurs tentatives
def extract_text_from_image(image):
    """Extrait le texte de l'image avec plusieurs méthodes OCR"""
    try:
        # Obtenir différentes versions prétraitées
        processed_images = preprocess_image(image)
        
        best_text = ""
        best_confidence = 0
        
        # Configurations OCR à essayer
        configs = [
            r'--oem 3 --psm 6',  # Bloc de texte uniforme
            r'--oem 3 --psm 7',  # Ligne de texte unique
            r'--oem 3 --psm 8',  # Mot unique
            r'--oem 3 --psm 13', # Ligne de texte brute
            r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789:.,hkm '  # Chiffres seulement
        ]
        
        for img in processed_images:
            for config in configs:
                try:
                    # Extraire le texte
                    text = pytesseract.image_to_string(img, config=config, lang='fra+eng')
                    
                    # Nettoyer le texte
                    text = text.strip()
                    
                    # Vérifier si on a trouvé des nombres
                    if text and len(text) > len(best_text):
                        # Vérifier si le texte contient des chiffres
                        if re.search(r'\d', text):
                            best_text = text
                            
                except Exception as e:
                    continue
        
        return best_text if best_text else ""
        
    except Exception as e:
        st.error(f"Erreur lors de l'extraction: {str(e)}")
        return ""

# Fonction avancée d'extraction du kilométrage
def extract_kilometrage(text):
    """Extrait le kilométrage du texte avec plusieurs patterns"""
    if not text:
        return None
    
    # Nettoyer le texte
    text = text.replace(' ', '').replace('\n', ' ')
    
    # Patterns pour le kilométrage
    patterns = [
        # Pattern pour nombre avec virgule ou point (ex: 12,345 ou 12345.6)
        r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)',
        # Pattern pour nombre de 4 à 7 chiffres (kilométrage typique)
        r'(\d{4,7})',
        # Pattern pour nombre avec point décimal
        r'(\d+\.\d+)',
        # Pattern pour nombre avec virgule décimale
        r'(\d+,\d+)',
    ]
    
    all_matches = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Nettoyer et convertir
            km_str = str(match).replace(',', '.')
            # Enlever tout sauf chiffres et point
            km_str = re.sub(r'[^\d.]', '', km_str)
            if km_str and km_str != '.':
                try:
                    value = float(km_str)
                    # Filtrer les valeurs plausibles (entre 0 et 999999)
                    if 0 < value < 1000000:
                        all_matches.append(value)
                except:
                    continue
    
    # Retourner la valeur la plus élevée (probablement le kilométrage)
    if all_matches:
        return max(all_matches)
    return None

# Fonction avancée d'extraction de l'heure
def extract_time(text):
    """Extrait l'heure du texte avec plusieurs formats"""
    if not text:
        return None
    
    # Nettoyer le texte
    text = text.replace(' ', '')
    
    # Patterns pour l'heure
    time_patterns = [
        # Format HH:MM
        r'(\d{1,2}:\d{2})',
        # Format HHhMM
        r'(\d{1,2})h(\d{2})',
        # Format HH.MM
        r'(\d{1,2})\.(\d{2})',
        # Format HHMM (sans séparateur)
        r'(\d{2})(\d{2})',
    ]
    
    for pattern in time_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if isinstance(match, tuple):
                    if len(match) == 2:
                        heure = f"{match[0]}:{match[1]}"
                    else:
                        continue
                else:
                    heure = match
                
                # Nettoyer et valider
                if ':' in heure:
                    parts = heure.split(':')
                    if len(parts) == 2:
                        h = int(parts[0])
                        m = int(parts[1])
                        if 0 <= h <= 23 and 0 <= m <= 59:
                            return f"{h:02d}:{m:02d}"
            except:
                continue
    
    return None

# Fonction pour extraire la région spécifique de l'image
def crop_counters(image):
    """Découpe l'image pour isoler les compteurs (haut = heure, bas = km)"""
    width, height = image.size
    
    # Découper la moitié supérieure pour l'heure
    heure_region = image.crop((0, 0, width, height // 2))
    
    # Découper la moitié inférieure pour le kilométrage
    km_region = image.crop((0, height // 2, width, height))
    
    return heure_region, km_region

# Fonction principale de traitement améliorée
def process_image(image, tram_number):
    """Traite une image et extrait les informations"""
    
    # Essayer d'extraire de l'image complète d'abord
    with st.spinner("Analyse de l'image en cours..."):
        full_text = extract_text_from_image(image)
        
        # Découper l'image pour isoler heure et km
        heure_region, km_region = crop_counters(image)
        heure_text = extract_text_from_image(heure_region)
        km_text = extract_text_from_image(km_region)
    
    # Afficher les textes extraits (debug)
    with st.expander("Texte extrait de l'image complète"):
        st.code(full_text if full_text else "Aucun texte détecté")
    
    with st.expander("Texte extrait - Zone Heure (haut)"):
        st.code(heure_text if heure_text else "Aucun texte détecté")
    
    with st.expander("Texte extrait - Zone Kilométrage (bas)"):
        st.code(km_text if km_text else "Aucun texte détecté")
    
    # Extraire les données avec priorité aux zones spécifiques
    # Pour l'heure, d'abord la zone heure, puis l'image complète
    heure = extract_time(heure_text)
    if not heure:
        heure = extract_time(full_text)
    
    # Pour le kilométrage, d'abord la zone km, puis l'image complète
    kilometrage = extract_kilometrage(km_text)
    if not kilometrage:
        kilometrage = extract_kilometrage(full_text)
    
    # Si l'heure n'est pas trouvée, utiliser l'heure actuelle
    if not heure:
        heure = datetime.now().strftime("%H:%M")
        st.warning("⚠️ Heure non détectée, utilisation de l'heure actuelle")
    else:
        st.success(f"✅ Heure détectée: {heure}")
    
    if kilometrage:
        st.success(f"✅ Kilométrage détecté: {kilometrage} km")
    else:
        st.warning("⚠️ Kilométrage non détecté")
    
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
    
    # Option pour ajuster le seuillage
    threshold = st.slider("Seuil de binarisation", 50, 200, 120, 
                         help="Ajustez pour améliorer la reconnaissance des chiffres")
    
    # Informations
    st.markdown("---")
    st.info(
        "💡 **Conseils pour les photos:**\n"
        "- Bon éclairage\n"
        "- Photo nette\n"
        "- Cadrer le compteur\n"
        "- Éviter les reflets\n"
        "- Chiffres bien lisibles\n"
        "- Prendre la photo de face"
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
                st.image(image, caption=f"Photo: {file.name}", width=300)
                
                # Traiter l'image
                result = process_image(image, tram_number)
                st.session_state.data_list.append(result)
                
                # Mettre à jour la progression
                progress_bar.progress((idx + 1) / len(uploaded_files))
            
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
    **Comment utiliser l'application:**
    
    1. Saisir le numéro du tramway
    2. Télécharger les photos des compteurs
    3. Cliquer sur 'Traiter les images'
    4. Vérifier les données extraites
    5. Exporter vers Excel
    
    **Améliorations apportées:**
    - Découpage automatique de l'image (haut = heure, bas = km)
    - Multiples méthodes de prétraitement
    - Plusieurs configurations OCR
    - Extraction avancée des chiffres
    
    **Si l'extraction échoue:**
    - Vérifiez que la photo est nette
    - Assurez un bon contraste
    - Recadrez manuellement si nécessaire
    - Utilisez l'option de saisie manuelle
    """)

# Footer
st.markdown("---")
st.markdown("🔧 Application développée pour l'extraction automatique des données tramway")
