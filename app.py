import streamlit as st
import pandas as pd
import joblib
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
st.set_page_config(
    page_title="AutoTriage AI | IT Helpdesk",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk mempercantik UI seperti Web App Enterprise
st.markdown("""
<style>
    /* Import Google Font Inter */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Background & Main Padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    
    /* Hero Header Card */
    .hero-card {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        border-radius: 16px;
        padding: 30px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.3);
    }
    .hero-title {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .hero-subtitle {
        font-size: 15px;
        opacity: 0.9;
        font-weight: 400;
    }
    
    /* Card Container */
    .custom-card {
        background: #ffffff;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Priority Badges */
    .badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 14px;
        letter-spacing: 0.3px;
    }
    .badge-critical { background-color: #FEE2E2; color: #991B1B; border: 1px solid #F87171; }
    .badge-high     { background-color: #FFEDD5; color: #9A3412; border: 1px solid #FB923C; }
    .badge-medium   { background-color: #FEF9C3; color: #854D0E; border: 1px solid #FACC15; }
    .badge-low      { background-color: #DCFCE7; color: #166534; border: 1px solid #4ADE80; }
    
    /* Metrics Box */
    .metric-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 700;
        color: #0F172A;
        margin-top: 4px;
    }
    .metric-label {
        font-size: 12px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_model():
    return joblib.load('jira_ticket_system.pkl')

try:
    model_bundle = load_model()
    task_model = model_bundle['task_pipeline']
    prio_model = model_bundle['priority_pipeline']
except Exception as e:
    st.error(f"Artefak model gagal dimuat: {e}")
    st.stop()

def get_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    else:
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
    client = gspread.authorize(creds)
    return client.open("IT_Ticket_Database").sheet1

def preprocess_text(text):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r'\[.*?\|http.*?\]', ' ', text)
    text = re.sub(r'http\S+|www\S+', ' ', text)
    text = re.sub(r'\b[0-9a-f:]{15,}\b', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    return re.sub(r'\s+', ' ', text.lower()).strip()

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9167/9167027.png", width=64)
    st.title("AutoTriage Engine")
    st.caption("AI-Powered Ticket Dispatcher v2.1")
    st.divider()
    
    st.markdown("### 🟢 Status Sistem")
    st.success("Model Status: **Active (NLP Pipeline)**")
    st.info("Database: **Google Sheets Sync Live**")
    
    st.divider()
    st.markdown("### ⏱️ Standar SLA Respon")
    st.markdown("""
    - 🔴 **Very High:** $\le$ 1 Jam *(Critical)*
    - 🟠 **High:** $\le$ 4 Jam *(Urgent)*
    - 🟡 **Medium:** $\le$ 24 Jam *(Normal)*
    - 🟢 **Low:** $\le$ 48 Jam *(Routine)*
    """)
    st.divider()
    st.caption("Dikembangkan untuk Tugas Akhir Data Mining.")

st.markdown("""
<div class="hero-card">
    <div class="hero-title">⚡ Intelligent IT Service Triage</div>
    <div class="hero-subtitle">Otomatisasi pengelompokan jenis tugas (Task) dan penetapan prioritas SLA antrean tiket secara instan bertenaga Machine Learning.</div>
</div>
""", unsafe_allow_html=True)


tab1, tab2 = st.tabs(["🚀 Buat Tiket Baru (Live AI)", "📑 Database Tiket Masuk (Google Sheets)"])

with tab1:
    col_left, col_right = st.columns([3, 2], gap="large")
    
    with col_left:
        st.markdown("### 📝 Form Pelaporan Masalah")
        with st.container():
            col_a, col_b = st.columns(2)
            with col_a:
                requestor = st.text_input("👤 Nama / Email Pemohon", placeholder="contoh: ardi.firmansyah@company.com")
            with col_b:
                department = st.selectbox("🏢 Departemen Asal", ["IT", "Human Resources", "Finance", "Operations", "Sales & Marketing", "General"])
            
            summary = st.text_input("📌 Judul Tiket (Summary)", placeholder="Ringkasan kendala (contoh: Database Timeout 504 di Aplikasi Kasir)")
            description = st.text_area("📄 Rincian Kendala (Description)", height=150, placeholder="Jelaskan kronologi kendala, pesan error spesifik, atau kebutuhan akses...")
            
            submit = st.button("✨ Analisis & Terbitkan Tiket", use_container_width=True, type="primary")

    with col_right:
        st.markdown("### 🎯 Hasil Analisis AI")
        if submit:
            if not summary or not description:
                st.warning("Silakan lengkapi judul dan deskripsi masalah terlebih dahulu!")
            else:
                with st.spinner("NLP Model sedang memproses konteks teks..."):
                    # Preprocess & Inferensi
                    clean_input = preprocess_text(summary) + " " + preprocess_text(description) + " " + department.lower()
                    pred_task = task_model.predict([clean_input])[0]
                    pred_prio = prio_model.predict([clean_input])[0]
                    
                    conf_task = task_model.predict_proba([clean_input]).max() * 100
                    conf_prio = prio_model.predict_proba([clean_input]).max() * 100
                    avg_conf = (conf_task + conf_prio) / 2
                    
                    # Tentukan badge class
                    badge_class = {
                        "Very High": "badge-critical",
                        "High": "badge-high",
                        "Medium": "badge-medium",
                        "Low": "badge-low"
                    }.get(pred_prio, "badge-low")
                    
                    # Render Kartu Hasil Cantik
                    st.markdown(f"""
                    <div class="custom-card">
                        <div style="font-size:13px; color:#64748B; font-weight:600; margin-bottom:8px;">HASIL PREDIKSI ENGINE</div>
                        <div style="font-size:22px; font-weight:700; color:#1E293B; margin-bottom:16px;">
                            🏷️ {pred_task}
                        </div>
                        <div style="margin-bottom:16px;">
                            <span class="badge {badge_class}">Prioritas: {pred_prio.upper()}</span>
                        </div>
                        <hr style="border:none; border-top:1px solid #E2E8F0; margin: 15px 0;">
                        <div style="display:flex; justify-content:space-between;">
                            <div>
                                <div style="font-size:12px; color:#64748B;">Keyakinan Model</div>
                                <div style="font-size:18px; font-weight:700; color:#2563EB;">{avg_conf:.1f}%</div>
                            </div>
                            <div>
                                <div style="font-size:12px; color:#64748B;">Target Respon</div>
                                <div style="font-size:18px; font-weight:700; color:#0F172A;">
                                    {"1 Jam" if pred_prio == "Very High" else "4 Jam" if pred_prio == "High" else "24 Jam"}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Simpan ke Google Sheets
                    try:
                        sheet = get_google_sheet()
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        sheet.append_row([now, requestor, department, summary, description, pred_task, pred_prio, f"{avg_conf:.1f}%"])
                        st.toast("✅ Tiket tersimpan di Google Sheets!", icon="📥")
                    except Exception as e:
                        st.error(f"Gagal simpan ke database: {e}")
        else:
            st.info("Ketik laporan di formulir sebelah kiri dan klik tombol untuk melihat prediksi instan.")

with tab2:
    st.markdown("### 📊 Log Tiket Masuk di Cloud Database")
    col_ref, col_info = st.columns([1, 4])
    with col_ref:
        if st.button("🔄 Sinkronkan Data", use_container_width=True):
            st.experimental_rerun()
            
    try:
        sheet = get_google_sheet()
        records = sheet.get_all_records()
        if records:
            df_view = pd.DataFrame(records)
            
            # Tampilkan metrik ringkas di atas tabel
            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(f'<div class="metric-box"><div class="metric-label">Total Tiket Masuk</div><div class="metric-value">{len(df_view)}</div></div>', unsafe_allow_html=True)
            with m2:
                critical_count = len(df_view[df_view['Pred_Priority'].isin(['Very High', 'High'])]) if 'Pred_Priority' in df_view else 0
                st.markdown(f'<div class="metric-box"><div class="metric-label">Tiket Kritis (High/V.High)</div><div class="metric-value" style="color:#DC2626;">{critical_count}</div></div>', unsafe_allow_html=True)
            with m3:
                st.markdown(f'<div class="metric-box"><div class="metric-label">Koneksi Database</div><div class="metric-value" style="color:#16A34A;">Online</div></div>', unsafe_allow_html=True)
            
            st.write("")
            st.dataframe(df_view, use_container_width=True)
        else:
            st.info("Database masih kosong.")
    except Exception as e:
        st.warning(f"Menunggu koneksi Google Sheets... ({e})")
