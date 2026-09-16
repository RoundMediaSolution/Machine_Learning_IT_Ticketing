import streamlit as st
import pandas as pd
import joblib
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ==============================================================================
# 1. KONFIGURASI HALAMAN & CUSTOM CSS ENTERPRISE THEME
# ==============================================================================
st.set_page_config(
    page_title="JiraSmart - IT Triage Portal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk mempercantik antarmuka (Card styling, Fonts, Badge)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .main-header {
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
    }
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-very-high { background-color: #fee2e2; color: #dc2626; padding: 4px 10px; border-radius: 8px; font-weight: 700; }
    .badge-high { background-color: #ffedd5; color: #ea580c; padding: 4px 10px; border-radius: 8px; font-weight: 700; }
    .badge-medium { background-color: #fef9c3; color: #ca8a04; padding: 4px 10px; border-radius: 8px; font-weight: 700; }
    .badge-low { background-color: #dcfce7; color: #16a34a; padding: 4px 10px; border-radius: 8px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. SESSION STATE & MANAJEMEN AUTENTIKASI ADMIN
# ==============================================================================
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

def login_admin(username, password):
    # Kredensial Admin Sederhana (Bisa diganti atau ditaruh di secrets)
    ADMIN_USER = "admin"
    ADMIN_PASS = "admin123"
    if username == ADMIN_USER and password == ADMIN_PASS:
        st.session_state["admin_logged_in"] = True
        st.success("Login Berhasil sebagai IT Admin!")
        st.rerun()
    else:
        st.error("Username atau Password Admin salah!")

def logout_admin():
    st.session_state["admin_logged_in"] = False
    st.rerun()

# ==============================================================================
# 3. LOAD MODEL MACHINE LEARNING
# ==============================================================================
@st.cache_resource
def load_ml_models():
    return joblib.load('jira_ticket_system.pkl')

try:
    model_bundle = load_ml_models()
    task_model = model_bundle['task_pipeline']
    prio_model = model_bundle['priority_pipeline']
except Exception as e:
    st.error(f"Gagal memuat artefak model ML. Error: {e}")
    st.stop()

# ==============================================================================
# 4. KONEKSI GOOGLE SHEETS
# ==============================================================================
SPREADSHEET_NAME = "IT_Ticket_Database"

def get_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    else:
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).sheet1

def clean_input_text(text):
    text = str(text)
    text = re.sub(r'\[.*?\|http.*?\]', ' ', text)
    text = re.sub(r'http\S+|www\S+', ' ', text)
    text = re.sub(r'\b[0-9a-f:]{15,}\b', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    return re.sub(r'\s+', ' ', text.lower()).strip()

# ==============================================================================
# 5. SIDEBAR: NAVIGASI & LOGIN PORTAL
# ==============================================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/906/906343.png", width=60)
    st.title("IT Operations")
    st.caption("v2.1 • NLP-Powered ITSM Engine")
    st.markdown("---")

    menu_option = st.radio(
        "Menu Navigasi:",
        ["📝 Buat Tiket Baru", "🔒 Admin Workspace"],
        index=0
    )

    st.markdown("---")
    if st.session_state["admin_logged_in"]:
        st.success("🟢 Sesi: **IT Administrator**")
        if st.button("🚪 Logout Admin", use_container_width=True):
            logout_admin()
    else:
        st.info("Status: **Karyawan / User**")

# ==============================================================================
# 6. MENU 1: USER PORTAL - SUBMIT TIKET
# ==============================================================================
if menu_option == "📝 Buat Tiket Baru":
    # Header Modern
    st.markdown("""
    <div class="main-header">
        <h1 style='margin:0; font-size:28px;'>🎫 Layanan Bantuan IT & Otomatisasi Triage</h1>
        <p style='margin:5px 0 0 0; opacity:0.85;'>Laporkan kendala teknis Anda. Model AI kami akan menentukan tipe task dan prioritas secara instan.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("ticket_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            req_name = st.text_input("Nama Pelapor / Email Karyawan:", placeholder="contoh: andi.habibi@perusahaan.com")
            dept = st.selectbox("Departemen Anda:", ["Operation", "Finance", "HR", "Sales", "Engineering", "General"])
        with c2:
            summary = st.text_input("Ringkasan Kendala (Subject):", placeholder="contoh: Gagal login ke VPN GlobalProtect")

        description = st.text_area("Detail Keluhan Kendala:", placeholder="Sertakan kode error, link sistem, atau langkah yang sudah dicoba...", height=130)
        
        submitted = st.form_submit_button("🚀 Kirim Tiket Gangguan", use_container_width=True)

    if submitted:
        if not summary or not description or not req_name:
            st.warning("⚠️ Harap melengkapi semua kolom formulir!")
        else:
            with st.spinner("🤖 AI sedang memproses teks tiket & melakukan triage..."):
                # Preprocessing & Inference
                clean_text = clean_input_text(summary) + " " + clean_input_text(description) + " " + dept.lower()
                pred_task = task_model.predict([clean_text])[0]
                pred_prio = prio_model.predict([clean_text])[0]
                conf = ((task_model.predict_proba([clean_text]).max() + prio_model.predict_proba([clean_text]).max()) / 2) * 100

                # Penentuan badge & SLA
                prio_badge_class = f"badge-{pred_prio.lower().replace(' ', '-')}"
                sla_dict = {
                    "Very High": "⚡ Kritis: Maksimal 1 Jam",
                    "High": "⏳ Tinggi: Maksimal 4 Jam",
                    "Medium": "🕒 Normal: Maksimal 24 Jam",
                    "Low": "☕ Rendah: Maksimal 48 Jam"
                }

                # Simpan ke Google Sheets
                try:
                    sheet = get_sheet_connection()
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sheet.append_row([now, req_name, dept, summary, description, pred_task, pred_prio, f"{conf:.1f}%"])
                    success_save = True
                except Exception as e:
                    success_save = False
                    err_msg = str(e)

            # Tampilan Hasil Triage yang Menarik (Kartu Hasil)
            st.markdown("### 📋 Tiket Anda Berhasil Dibuat!")
            r1, r2, r3 = st.columns(3)
            with r1:
                st.markdown(f"<div class='metric-card'><small>Kategori Tugas (Task)</small><h3>🎯 {pred_task}</h3></div>", unsafe_allow_html=True)
            with r2:
                st.markdown(f"<div class='metric-card'><small>Prioritas Ditentukan</small><h3><span class='{prio_badge_class}'>{pred_prio}</span></h3></div>", unsafe_allow_html=True)
            with r3:
                st.markdown(f"<div class='metric-card'><small>Target Response (SLA)</small><h4>{sla_dict.get(pred_prio, '-')}</h4></div>", unsafe_allow_html=True)

            if success_save:
                st.toast("✅ Tiket tersimpan otomatis di database Google Sheets!", icon="💾")
            else:
                st.error(f"Gagal mencatat tiket ke Google Sheet: {err_msg}")

# ==============================================================================
# 7. MENU 2: ADMIN WORKSPACE (RESTRICTED AREA)
# ==============================================================================
elif menu_option == "🔒 Admin Workspace":
    # Form Login jika belum login
    if not st.session_state["admin_logged_in"]:
        st.subheader("🔐 Otentikasi IT Administrator")
        st.write("Area ini dilindungi. Masukkan kredensial admin untuk melihat antrean tiket.")
        
        with st.form("login_box"):
            u = st.text_input("Username:")
            p = st.text_input("Password:", type="password")
            btn_login = st.form_submit_button("Masuk ke Dashboard")
            if btn_login:
                login_admin(u, p)
    else:
        # Tampilan Admin yang Sudah Login
        st.markdown("""
        <div class="main-header" style="background: linear-gradient(90deg, #0F172A 0%, #334155 100%);">
            <h1 style='margin:0; font-size:26px;'>🛡️ IT Support Command Center</h1>
            <p style='margin:5px 0 0 0; opacity:0.85;'>Live monitoring antrean tiket, hasil triage machine learning, dan integrasi spreadsheet.</p>
        </div>
        """, unsafe_allow_html=True)

        try:
            with st.spinner("Mengambil database dari Google Sheets..."):
                sheet = get_sheet_connection()
                records = sheet.get_all_records()
                df_tickets = pd.DataFrame(records)

            if not df_tickets.empty:
                # 1. Summary Metrics
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    m1.metric("Total Tiket Masuk", len(df_tickets))
                with m2:
                    kritis_count = len(df_tickets[df_tickets['Pred_Priority'].str.contains("High", case=False, na=False)])
                    m2.metric("Tiket High/Critical", kritis_count, delta="Perlu Tindakan", delta_color="inverse")
                with m3:
                    top_dept = df_tickets['Department'].mode()[0] if 'Department' in df_tickets.columns else "-"
                    m3.metric("Departemen Teraktif", top_dept)
                with m4:
                    top_task = df_tickets['Pred_Task'].mode()[0] if 'Pred_Task' in df_tickets.columns else "-"
                    m4.metric("Kategori Dominan", top_task)

                st.markdown("---")

                # 2. Tab Tampilan Data & Direct Google Sheets
                subtab1, subtab2 = st.tabs(["📑 Tabel Antrean Real-Time", "🔗 Tautan Google Sheets Database"])
                
                with subtab1:
                    st.subheader("Daftar Tiket Terklasifikasi Otomatis")
                    st.dataframe(
                        df_tickets.sort_values(by="Timestamp", ascending=False),
                        use_container_width=True
                    )
                    
                    # Opsi Download Data CSV
                    csv_export = df_tickets.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Ekspor Database ke CSV",
                        data=csv_export,
                        file_name=f"it_tickets_export_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )

                with subtab2:
                    st.subheader("Akses Langsung ke Dokumen Google Sheets")
                    st.write("Semua data di atas disimpan langsung di lembar kerja Google Cloud berikut:")
                    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet.spreadsheet.id}"
                    st.link_button("🌐 Buka Langsung File Google Sheets", sheet_url)
                    st.info("💡 Perubahan atau penghapusan baris yang Anda lakukan di file Google Sheets tersebut akan langsung terefleksi di aplikasi ini saat halaman di-refresh.")

            else:
                st.info("Database Google Sheets masih kosong. Belum ada tiket yang disubmit.")

        except Exception as e:
            st.error(f"Gagal mengambil data dari Google Sheets: {e}")
