import streamlit as st
import pandas as pd
import joblib
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. KONFIGURASI HALAMAN & CUSTOM CSS
# ==========================================
st.set_page_config(
    page_title="Jira Smart Helpdesk Portal",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk mempercantik UI seperti Enterprise Web App
st.markdown("""
    <style>
        /* Background & Font */
        .main {
            background-color: #f8f9fa;
        }
        
        /* Gaya Kartu Modern */
        .card-container {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            border: 1px solid #e9ecef;
            margin-bottom: 20px;
        }
        
        /* Kartu Hasil Bawah (AI Metrics) */
        .metric-box {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            color: #ffffff;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        .metric-title {
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #94a3b8;
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 22px;
            font-weight: 700;
        }
        
        /* Badge Status Prioritas */
        .badge-very-high { color: #ef4444; font-weight: bold; }
        .badge-high { color: #f97316; font-weight: bold; }
        .badge-medium { color: #eab308; font-weight: bold; }
        .badge-low { color: #22c55e; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION STATE & LOGIN IT
# ==========================================
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
if 'last_ticket' not in st.session_state:
    st.session_state['last_ticket'] = None

# Sidebar Authentication
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/906/906343.png", width=70)
st.sidebar.title("IT Operations Portal")

if not st.session_state['is_logged_in']:
    st.sidebar.subheader("🔒 Login Petugas IT")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Masuk sebagai IT"):
        # Kredensial demo (bisa Anda ganti)
        if username == "admin" and password == "admin123":
            st.session_state['is_logged_in'] = True
            st.sidebar.success("Login Berhasil!")
            st.rerun()
        else:
            st.sidebar.error("Username / Password salah!")
else:
    st.sidebar.success("✅ Logged in as: **IT Support Team**")
    if st.sidebar.button("Logout"):
        st.session_state['is_logged_in'] = False
        st.rerun()

# ==========================================
# 3. LOAD MODEL DARI KAGGLE ARTIFACT
# ==========================================
@st.cache_resource
def load_model():
    return joblib.load('jira_ticket_system.pkl')

try:
    model_bundle = load_model()
    task_model = model_bundle['task_pipeline']
    prio_model = model_bundle['priority_pipeline']
except Exception as e:
    st.error(f"Model file 'jira_ticket_system.pkl' tidak ditemukan. Error: {e}")
    st.stop()

# ==========================================
# 4. KONEKSI GOOGLE SHEETS
# ==========================================
SHEET_NAME = "IT_Ticket_Database"

def get_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    else:
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

def clean_text(text):
    text = re.sub(r'\[.*?\|http.*?\]', ' ', str(text))
    text = re.sub(r'http\S+|www\S+', ' ', text)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    return re.sub(r'\s+', ' ', text.lower()).strip()

# ==========================================
# 5. HALAMAN DASHBOARD IT (JIKA LOGIN)
# ==========================================
if st.session_state['is_logged_in']:
    st.title("👨‍💻 IT Management Dashboard")
    st.markdown("Monitoring antrean tiket masuk yang telah diklasifikasikan secara otomatis oleh Machine Learning.")
    
    col_dash1, col_dash2 = st.columns([4, 1])
    with col_dash2:
        st.link_button("📂 Buka Google Sheets", f"https://docs.google.com/spreadsheets/d/", use_container_width=True)
    
    try:
        sheet = get_google_sheet()
        records = sheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
            
            # Metric Card Bar Atas
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Tiket Masuk", len(df))
            m2.metric("Tiket Critical / High", len(df[df['Pred_Priority'].isin(['Very High', 'High'])]))
            m3.metric("Service Requests", len(df[df['Pred_Task'].str.contains('Service', case=False, na=False)]))
            m4.metric("Insiden Operasional", len(df[df['Pred_Task'].str.contains('Incident|Task', case=False, na=False)]))
            
            st.write("### 📋 Antrean Tiket Terbaru")
            st.dataframe(df.tail(20), use_container_width=True)
        else:
            st.info("Database Google Sheets masih kosong.")
    except Exception as e:
        st.warning(f"Menghubungkan ke Google Sheets... Detail: {e}")

    st.divider()

# ==========================================
# 6. PORTAL SUBMIT TIKET (KARTU KIRI & KANAN)
# ==========================================
st.title("🎫 Portal Layanan Mandiri IT (Self-Service)")
st.caption("Laporkan permasalahan teknis Anda. AI akan menganalisis prioritas dan mendisposisikan tiket secara otomatis.")

col_left, col_right = st.columns([1, 1])

# --- KARTU SISI KIRI: INPUT FORM ---
with col_left:
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    st.subheader("📝 Buat Tiket Kendala")
    
    with st.form("ticket_form", clear_on_submit=True):
        input_nama = st.text_input("Nama Pelapor / Email", placeholder="contoh: irvan.herviansyah@jiva.ag")
        input_dept = st.selectbox("Departemen", ["Operation", "HR", "Finance", "IT Support", "Marketing", "Logistics", "General"])
        input_summary = st.text_input("Ringkasan Kendala (Summary)", placeholder="contoh: Error Retool access timeout 504")
        input_detail = st.text_area("Detail Masalah (Description)", placeholder="Jelaskan secara lengkap gejala kendala...", height=130)
        
        btn_submit = st.form_submit_button("Kirim Tiket Sekarang 🚀", use_container_width=True)
        
    st.markdown('</div>', unsafe_allow_html=True)

# Logika Pemrosesan Model saat Submit
if btn_submit:
    if not input_summary or not input_detail:
        st.error("Gagal: Ringkasan dan Detail kendala wajib diisi!")
    else:
        with st.spinner("AI sedang menganalisis teks tiket..."):
            features = clean_text(input_summary) + " " + clean_text(input_detail) + " " + input_dept.lower()
            
            # Prediksi Model
            pred_task = task_model.predict([features])[0]
            pred_prio = prio_model.predict([features])[0]
            
            # Hitung SLA Target Response
            sla_dict = {
                "Very High": "< 1 Jam (Critical Emergency)",
                "High": "< 4 Jam (High Priority)",
                "Medium": "< 24 Jam (Normal)",
                "Low": "< 48 Jam (Minor/Planning)"
            }
            target_sla = sla_dict.get(pred_prio, "< 24 Jam")
            
            # Simpan ke Session State untuk ditampilkan di kartu kanan & bawah
            st.session_state['last_ticket'] = {
                "nama": input_nama if input_nama else "Anonymous User",
                "dept": input_dept,
                "summary": input_summary,
                "detail": input_detail,
                "task": pred_task,
                "prio": pred_prio,
                "sla": target_sla,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Simpan ke Google Sheet
            try:
                sheet = get_google_sheet()
                sheet.append_row([
                    st.session_state['last_ticket']['time'],
                    st.session_state['last_ticket']['nama'],
                    st.session_state['last_ticket']['dept'],
                    st.session_state['last_ticket']['summary'],
                    st.session_state['last_ticket']['detail'],
                    pred_task,
                    pred_prio,
                    target_sla
                ])
                st.toast("Tiket berhasil disimpan ke Google Sheets!", icon="✅")
            except Exception as e:
                st.error(f"Gagal simpan ke Sheets: {e}")

# --- KARTU SISI KANAN: STATUS TIKET DIBUAT ---
with col_right:
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    st.subheader("📋 Status Penerimaan Tiket")
    
    ticket = st.session_state['last_ticket']
    if ticket:
        st.success(f"✅ Tiket Terdaftar: #{ticket['time'].replace('-', '').replace(':', '').replace(' ', '')[-8:]}")
        st.markdown(f"**Nama Pelapor :** {ticket['nama']}")
        st.markdown(f"**Departemen :** `{ticket['dept']}`")
        st.markdown(f"**Ringkasan :** *{ticket['summary']}*")
        st.markdown(f"**Detail :**")
        st.info(ticket['detail'])
        st.caption(f"Waktu Registrasi: {ticket['time']}")
    else:
        st.info("ℹ️ Belum ada tiket yang dikirim. Silakan isi formulir di sebelah kiri untuk membuat tiket baru.")
        st.image("https://illustrations.popertee.com/illustrations/customer-support.png", width=220)
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 7. KARTU SISI BAWAH: TASK | PRIORITY | SLA
# ==========================================
if ticket:
    st.write("### 🤖 Hasil Analisis Otomatisasi AI (Task & Triage)")
    b1, b2, b3 = st.columns(3)
    
    with b1:
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-title">Klasifikasi Jenis Pekerjaan</div>
                <div class="metric-value">📌 {ticket['task']}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with b2:
        # Warna prioritas dinamis
        p_class = f"badge-{ticket['prio'].lower().replace(' ', '-')}"
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-title">Tingkat Urgensi (Triage)</div>
                <div class="metric-value"><span class="{p_class}">🚨 {ticket['prio']}</span></div>
            </div>
        """, unsafe_allow_html=True)
        
    with b3:
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-title">Target Response Time (SLA)</div>
                <div class="metric-value">⏱️ {ticket['sla']}</div>
            </div>
        """, unsafe_allow_html=True)
