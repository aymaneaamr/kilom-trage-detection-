import streamlit as st
import pandas as pd
from datetime import datetime
import io
import base64
import json
import re
import anthropic
from PIL import Image

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tramway Counter Extractor",
    page_icon="🚋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');

:root {
    --bg: #0a0e1a;
    --surface: #111827;
    --surface2: #1a2236;
    --accent: #f59e0b;
    --accent2: #3b82f6;
    --text: #f1f5f9;
    --muted: #64748b;
    --success: #10b981;
    --error: #ef4444;
    --border: #1e293b;
}

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

.stApp { background-color: var(--bg) !important; }

/* Header */
.hero-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    border: 1px solid var(--accent);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        45deg,
        transparent,
        transparent 40px,
        rgba(245,158,11,0.03) 40px,
        rgba(245,158,11,0.03) 41px
    );
}
.hero-icon { font-size: 3.5rem; }
.hero-title {
    font-size: 2rem;
    font-weight: 800;
    color: var(--accent);
    letter-spacing: -0.02em;
    margin: 0;
}
.hero-sub { color: var(--muted); font-size: 0.95rem; margin-top: 0.25rem; }

/* Cards */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.card-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Result boxes */
.result-box {
    background: var(--surface2);
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    border-left: 4px solid var(--accent);
    margin: 0.5rem 0;
    font-family: 'Space Mono', monospace;
}
.result-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--muted);
    margin-bottom: 0.3rem;
    font-family: 'Syne', sans-serif;
}
.result-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--text);
}
.result-box.blue { border-left-color: var(--accent2); }
.result-box.green { border-left-color: var(--success); }

/* Badge */
.badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    font-family: 'Space Mono', monospace;
}
.badge-ok { background: rgba(16,185,129,0.15); color: var(--success); border: 1px solid var(--success); }
.badge-fail { background: rgba(239,68,68,0.15); color: var(--error); border: 1px solid var(--error); }
.badge-warn { background: rgba(245,158,11,0.15); color: var(--accent); border: 1px solid var(--accent); }

/* Table */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* Buttons */
.stButton > button {
    background: var(--accent) !important;
    color: #0a0e1a !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-family: 'Syne', sans-serif !important;
    letter-spacing: 0.05em !important;
    padding: 0.6rem 1.4rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #d97706 !important;
    transform: translateY(-1px) !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(245,158,11,0.15) !important;
}

/* Divider */
hr { border-color: var(--border) !important; }

/* File uploader */
.stFileUploader > div {
    background: var(--surface2) !important;
    border: 2px dashed var(--border) !important;
    border-radius: 10px !important;
}
.stFileUploader > div:hover { border-color: var(--accent) !important; }

/* Metric */
[data-testid="stMetricValue"] {
    font-family: 'Space Mono', monospace !important;
    color: var(--accent) !important;
    font-size: 2rem !important;
}

/* Tabs */
.stTabs [data-baseweb="tab"] {
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    color: var(--muted) !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

/* Status tag */
.status-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.25rem 0.75rem;
    border-radius: 6px;
    font-family: 'Space Mono', monospace;
}

/* Spinner overlay */
.processing-msg {
    text-align: center;
    padding: 2rem;
    color: var(--accent);
    font-family: 'Space Mono', monospace;
    font-size: 0.9rem;
    letter-spacing: 0.05em;
}

/* Radio */
.stRadio > div { gap: 0.5rem !important; }
.stRadio label { color: var(--text) !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def pil_to_b64(img: Image.Image, fmt="JPEG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.standard_b64encode(buf.getvalue()).decode()


def extract_via_claude(image: Image.Image, api_key: str) -> dict:
    """Use Claude Vision to extract hour and km from counter photo."""
    client = anthropic.Anthropic(api_key=api_key)

    b64 = pil_to_b64(image)
    media_type = "image/jpeg"

    prompt = """You are a specialist in reading analog/digital counter displays on tramways.
    
Carefully examine this counter image and extract:
1. The HOUR value shown on the counter (it may be in HH:MM or HH:MM:SS format, or raw digits like 823743 meaning 82h37m43s)
2. The KILOMETER value (odometer reading)

Return ONLY a JSON object with this exact structure (no extra text, no markdown):
{
  "heure_raw": "extracted hour digits or text exactly as seen",
  "kilometrage_raw": "extracted km digits exactly as seen",
  "heure_formatted": "HH:MM formatted if possible, else raw",
  "kilometrage_formatted": 1234567,
  "confidence": "high|medium|low",
  "notes": "any relevant observation"
}

If you cannot read a value clearly, set it to null. Be precise."""

    resp = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw = resp.content[0].text.strip()
    # strip possible markdown fences
    raw = re.sub(r"^```json?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ── Session state ─────────────────────────────────────────────────────────────

if "records" not in st.session_state:
    st.session_state.records = []

if "api_key" not in st.session_state:
    st.session_state.api_key = ""


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero-header">
  <div class="hero-icon">🚋</div>
  <div>
    <div class="hero-title">TRAMWAY COUNTER EXTRACTOR</div>
    <div class="hero-sub">Extraction automatique · Kilométrage &amp; Heures · Export Excel</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.markdown("---")

    api_key_input = st.text_input(
        "🔑 Clé API Anthropic",
        type="password",
        value=st.session_state.api_key,
        placeholder="sk-ant-...",
        help="Obtenez votre clé sur console.anthropic.com",
    )
    if api_key_input:
        st.session_state.api_key = api_key_input

    st.markdown("---")

    tram_number = st.text_input(
        "🚋 Numéro du Tramway",
        placeholder="Ex: T-1042",
    )

    st.markdown("---")

    mode = st.radio(
        "Mode d'extraction",
        ["🤖 Automatique (IA Vision)", "✏️ Manuel (saisie directe)"],
    )
    auto_mode = mode.startswith("🤖")

    st.markdown("---")
    st.markdown("""
    <div style="color:#64748b;font-size:0.8rem;line-height:1.6">
    <b style="color:#f59e0b">📌 Conseils photo:</b><br>
    • Bonne luminosité<br>
    • Cadrer les chiffres<br>
    • Éviter les reflets<br>
    • Photo nette et droite<br><br>
    <b style="color:#f59e0b">📂 Formats acceptés:</b><br>
    JPG, JPEG, PNG, BMP
    </div>
    """, unsafe_allow_html=True)


# ── Main layout ───────────────────────────────────────────────────────────────

left, right = st.columns([1, 1], gap="large")

# ── LEFT: Upload & preview ────────────────────────────────────────────────────

with left:
    st.markdown('<div class="card-title">📸 Photos des compteurs</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Glissez-déposez ou parcourez",
        type=["jpg", "jpeg", "png", "bmp"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded:
        for f in uploaded:
            img = Image.open(f)
            st.image(img, caption=f.name, use_container_width=True)
            st.markdown("<hr>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:3rem 1rem;color:#64748b;border:2px dashed #1e293b;border-radius:10px;margin-top:1rem">
          <div style="font-size:3rem">📷</div>
          <div style="margin-top:0.5rem;font-family:'Space Mono',monospace;font-size:0.85rem">
            Aucune photo chargée
          </div>
        </div>
        """, unsafe_allow_html=True)


# ── RIGHT: Extraction & results ───────────────────────────────────────────────

with right:
    st.markdown('<div class="card-title">📊 Extraction des données</div>', unsafe_allow_html=True)

    # ── AUTO MODE ─────────────────────────────────────────────────────────────
    if auto_mode:
        if st.button("🔄 Lancer l'extraction IA", use_container_width=True):
            if not st.session_state.api_key:
                st.error("❌ Veuillez entrer votre clé API Anthropic dans la barre latérale.")
            elif not tram_number:
                st.error("❌ Veuillez entrer le numéro du tramway.")
            elif not uploaded:
                st.error("❌ Veuillez télécharger au moins une photo.")
            else:
                progress = st.progress(0)
                for i, f in enumerate(uploaded):
                    img = Image.open(f)
                    with st.spinner(f"Analyse de {f.name}…"):
                        try:
                            result = extract_via_claude(img, st.session_state.api_key)
                        except Exception as e:
                            st.error(f"Erreur API pour {f.name}: {e}")
                            progress.progress((i + 1) / len(uploaded))
                            continue

                    conf = result.get("confidence", "low")
                    badge = "badge-ok" if conf == "high" else ("badge-warn" if conf == "medium" else "badge-fail")

                    st.markdown(f"""
                    <div class="card">
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
                        <div style="font-weight:600;color:#f1f5f9">{f.name}</div>
                        <span class="badge {badge}">Confiance: {conf}</span>
                      </div>
                    """, unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"""
                        <div class="result-box blue">
                          <div class="result-label">⏱ Heure</div>
                          <div class="result-value">{result.get('heure_formatted') or '—'}</div>
                          <div style="font-size:0.72rem;color:#64748b;margin-top:0.3rem;font-family:'Space Mono',monospace">
                            Brut: {result.get('heure_raw') or '—'}
                          </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        km_val = result.get("kilometrage_formatted")
                        km_disp = f"{km_val:,}".replace(",", " ") if km_val else "—"
                        st.markdown(f"""
                        <div class="result-box">
                          <div class="result-label">📏 Kilométrage</div>
                          <div class="result-value">{km_disp}</div>
                          <div style="font-size:0.72rem;color:#64748b;margin-top:0.3rem;font-family:'Space Mono',monospace">
                            Brut: {result.get('kilometrage_raw') or '—'}
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                    if result.get("notes"):
                        st.caption(f"📝 {result['notes']}")

                    st.markdown("</div>", unsafe_allow_html=True)

                    st.session_state.records.append({
                        "Numéro Tramway": tram_number,
                        "Kilométrage (km)": result.get("kilometrage_formatted") or result.get("kilometrage_raw") or "N/D",
                        "Heure": result.get("heure_formatted") or result.get("heure_raw") or "N/D",
                        "Confiance": conf,
                        "Fichier": f.name,
                        "Date extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })

                    progress.progress((i + 1) / len(uploaded))

                st.success(f"✅ {len(uploaded)} image(s) traitée(s)!")

    # ── MANUAL MODE ───────────────────────────────────────────────────────────
    else:
        if not uploaded:
            st.info("⬆️ Téléchargez des photos à gauche pour commencer la saisie.")
        else:
            for idx, f in enumerate(uploaded):
                with st.expander(f"✏️ Image {idx+1}: {f.name}", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        heure_val = st.text_input(
                            "⏱ Heure (HH:MM ou HH:MM:SS)",
                            placeholder="Ex: 14:37",
                            key=f"h_{idx}_{f.name}",
                        )
                    with c2:
                        km_val = st.text_input(
                            "📏 Kilométrage",
                            placeholder="Ex: 10406871",
                            key=f"k_{idx}_{f.name}",
                        )

                    if st.button(f"✅ Enregistrer", key=f"save_{idx}"):
                        if not tram_number:
                            st.error("Entrez d'abord le numéro du tramway (barre latérale).")
                        elif heure_val and km_val:
                            st.session_state.records.append({
                                "Numéro Tramway": tram_number,
                                "Kilométrage (km)": km_val,
                                "Heure": heure_val,
                                "Confiance": "manuel",
                                "Fichier": f.name,
                                "Date extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            })
                            st.success("Enregistré ✓")
                        else:
                            st.error("Veuillez remplir l'heure ET le kilométrage.")


# ── Records table & export ────────────────────────────────────────────────────

if st.session_state.records:
    st.markdown("---")
    st.markdown("## 📋 Données collectées")

    df = pd.DataFrame(st.session_state.records)

    # Summary metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Enregistrements", len(df))
    m2.metric("Tramway(s)", df["Numéro Tramway"].nunique())
    if "Kilométrage (km)" in df.columns:
        nums = pd.to_numeric(df["Kilométrage (km)"], errors="coerce").dropna()
        if not nums.empty:
            m3.metric("Km max", f"{int(nums.max()):,}".replace(",", " "))

    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Export ──────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Data sheet
        df.to_excel(writer, sheet_name="Données Tramway", index=False)

        # Summary sheet
        summary_data = {
            "Statistique": [
                "Total enregistrements",
                "Nombre de tramways",
                "Date de génération",
            ],
            "Valeur": [
                len(df),
                df["Numéro Tramway"].nunique(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ],
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Résumé", index=False)

    col_dl, col_clear = st.columns([2, 1])
    with col_dl:
        fname = f"tramway_{tram_number or 'export'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        st.download_button(
            label="📥 Exporter vers Excel",
            data=buf.getvalue(),
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col_clear:
        if st.button("🗑️ Effacer tout", use_container_width=True):
            st.session_state.records = []
            st.rerun()


# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#334155;font-family:'Space Mono',monospace;font-size:0.75rem;padding:1rem 0">
  🚋 Tramway Counter Extractor · Propulsé par Claude Vision (Anthropic)
</div>
""", unsafe_allow_html=True)
