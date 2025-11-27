import streamlit as st
import pandas as pd
import time
import base64
import os
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Expert System - Ultimate AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- BASE DIR & CSS GLOBAL ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# KITA GABUNG CSS DI SINI BIAR RAPI
st.markdown("""
<style>
    /* =========================================
       1. CSS UNTUK BACKGROUND GAMBAR SAMAR
    ========================================= */
    /* Target container utama Streamlit */
    .stApp {
        /* Pastikan posisi relatif */
        position: relative;
    }

    /* Membuat lapisan "palsu" di belakang layar (pseudo-element) */
    .stApp::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        
        /* --- GANTI URL GAMBAR DI SINI --- */
        /* Saya pakai contoh gambar sirkuit dari Unsplash */
        background-image: url('https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D');
        /* -------------------------------- */

        background-size: cover;      /* Gambar menutupi seluruh layar */
        background-position: center; /* Gambar di tengah */
        background-repeat: no-repeat;
        background-attachment: fixed; /* Gambar diam saat di-scroll (opsional) */

        /* --- ATUR TINGKAT KESAMARAN (OPACITY) DI SINI --- */
        /* Nilai 0.0 (hilang) sampai 1.0 (jelas banget) */
        opacity: 0.10; 
        /* ----------------------------------------------- */

        /* Taruh di paling belakang agar tidak menutupi konten */
        z-index: -1;
        /* Agar klik tembus ke belakang */
        pointer-events: none;
        /* Filter tambahan biar agak gelap/blur (opsional) */
        filter: grayscale(100%) contrast(120%);
    }

    /* =========================================
       2. CSS UNTUK LANDING PAGE
    ========================================= */
    .big-font {
        font-size: 60px !important;
        font-weight: 800;
        background: -webkit-linear-gradient(#eee, #333);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0px;
        /* Tambah shadow biar teks tetap terbaca di atas background */
        text-shadow: 2px 2px 4px rgba(255,255,255,0.5);
    }
    .sub-font {
        font-size: 20px !important;
        text-align: center;
        color: #444; /* Warna agak digelapin dikit */
        margin-bottom: 50px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# (Fungsi load_css file eksternal dihapus karena sudah digabung di atas biar praktis)

# --- HELPER FUNCTIONS ---
def get_img_as_base64(kasus_type):
    filename = "banner_laptop.jpg" if kasus_type == "Laptop" else "banner_cabai.jpg"
    img_path = os.path.join(BASE_DIR, "images", filename)
    try:
        with open(img_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

# --- DATABASE MANAGEMENT ---
@st.cache_data
def load_data(kasus_type):
    data_folder = os.path.join(BASE_DIR, "data")
    try:
        if kasus_type == "Laptop":
            df_gejala = pd.read_csv(os.path.join(data_folder, "gejala_laptop.csv"))
            df_solusi = pd.read_csv(os.path.join(data_folder, "solusi_laptop.csv"))
            df_kasus = pd.read_csv(os.path.join(data_folder, "kasus_laptop.csv"))
        else:
            df_gejala = pd.read_csv(os.path.join(data_folder, "gejala_cabai.csv"))
            df_solusi = pd.read_csv(os.path.join(data_folder, "solusi_cabai.csv"))
            df_kasus = pd.read_csv(os.path.join(data_folder, "kasus_cabai.csv"))
        
        df_kasus.dropna(subset=['id_kasus', 'solusi_final'], inplace=True)
        df_gejala['id_gejala'] = df_gejala['id_gejala'].astype(str)
        df_kasus['id_kasus'] = df_kasus['id_kasus'].astype(str)
        df_kasus['solusi_final'] = df_kasus['solusi_final'].astype(str)
        
        return df_gejala, df_solusi, df_kasus
    except:
        return None, None, None

def simpan_kasus_baru(pilihan_kasus, gejala_baru_ids, solusi_benar_id, df_kasus):
    data_folder = os.path.join(BASE_DIR, "data")
    prefix = "K" if pilihan_kasus == "Laptop" else "KC"
    file_path = os.path.join(data_folder, f"kasus_{'laptop' if pilihan_kasus == 'Laptop' else 'cabai'}.csv")
    
    try:
        last_id = df_kasus.iloc[-1]['id_kasus']
        last_number = int(''.join(filter(str.isdigit, last_id)))
        new_id = f"{prefix}{last_number + 1:02d}"
    except:
        new_id = f"{prefix}01"

    gejala_str = ",".join(gejala_baru_ids)
    new_row = {'id_kasus': new_id, 'gejala_terkait': gejala_str, 'solusi_final': solusi_benar_id}
    
    try:
        df_lama = pd.read_csv(file_path)
        df_baru = pd.concat([df_lama, pd.DataFrame([new_row])], ignore_index=True)
        df_baru.to_csv(file_path, index=False)
        return new_id
    except Exception as e:
        st.error(f"Gagal simpan: {e}")
        return None

# --- ENGINE CBR ---
def hitung_similarity(user_gejala, df_kasus, df_gejala):
    results = []
    total_bobot_user = 0
    for u_gejala in user_gejala:
        bobot_data = df_gejala[df_gejala['id_gejala'] == u_gejala]['bobot'].values
        if len(bobot_data) > 0: total_bobot_user += int(bobot_data[0])

    for index, row in df_kasus.iterrows():
        kasus_gejala_list = str(row['gejala_terkait']).split(',')
        match_bobot = 0
        total_bobot_kasus = 0
        
        for k_gejala in kasus_gejala_list:
            bobot_data = df_gejala[df_gejala['id_gejala'] == k_gejala]['bobot'].values
            if len(bobot_data) > 0:
                bobot = int(bobot_data[0])
                total_bobot_kasus += bobot
                if k_gejala in user_gejala: match_bobot += bobot
        
        pembagi = (total_bobot_kasus + total_bobot_user) / 2
        similarity = (match_bobot / pembagi) * 100 if pembagi > 0 else 0
            
        results.append({
            'id_kasus': row['id_kasus'],
            'similarity': similarity,
            'solusi_id': row['solusi_final'],
            'gejala_kasus': kasus_gejala_list
        })
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results

# --- FITUR HISTORY LOG ---
def catat_riwayat(kasus_type, gejala_input, hasil_diagnosa, skor):
    file_path = os.path.join(BASE_DIR, "data", "riwayat_diagnosis.csv")
    if not os.path.exists(file_path):
        df_init = pd.DataFrame(columns=["Tanggal", "Studi Kasus", "Gejala", "Hasil", "Akurasi"])
        df_init.to_csv(file_path, index=False)
    
    new_log = {
        "Tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Studi Kasus": kasus_type,
        "Gejala": ", ".join(gejala_input),
        "Hasil": hasil_diagnosa,
        "Akurasi": f"{skor:.1f}%"
    }
    try:
        df_log = pd.read_csv(file_path)
        df_log = pd.concat([df_log, pd.DataFrame([new_log])], ignore_index=True)
        df_log.to_csv(file_path, index=False)
    except: pass

# =========================================================
# HALAMAN 1: LANDING PAGE
# =========================================================
def show_landing_page():
    st.write("")
    st.write("")
    st.markdown('<p class="big-font">SISTEM PAKAR CERDAS</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-font">Diagnosis Kerusakan Hardware & Penyakit Tanaman dengan Metode CBR + Active Learning</p>', unsafe_allow_html=True)
    
    st.write("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Pakai container biar teks di dalamnya lebih jelas di atas background
        with st.container(border=True):
            st.info("👋 Selamat Datang! Silakan mulai aplikasi untuk melakukan diagnosis.")
            if st.button("🚀 MULAI APLIKASI", type="primary", use_container_width=True):
                st.session_state['page'] = 'app'
                st.rerun()
            
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    # Footer dikasih background tipis biar kebaca
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 12px; background-color: rgba(255,255,255,0.7); padding: 10px; border-radius: 5px;">
    &copy; 2025 Mahasiswa IT - Tugas Besar Machine Learning<br>
    Developed with ❤️ using Python & Streamlit
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# HALAMAN 2: APLIKASI UTAMA
# =========================================================
def show_main_app():
    with st.sidebar:
        if st.button("🏠 Kembali ke Home"):
            st.session_state['page'] = 'landing'
            st.rerun()
            
        st.title("🎛️ System Control")
        st.subheader("📊 Statistik Data")
        pilihan_kasus = st.selectbox("Studi Kasus:", ["Laptop", "Tanaman Cabai"])
        df_gejala, df_solusi, df_kasus = load_data(pilihan_kasus)
        
        if df_gejala is not None:
            c1, c2 = st.columns(2)
            c1.metric("Gejala", len(df_gejala))
            c2.metric("Kasus", len(df_kasus))
            st.success(f"✅ Database {pilihan_kasus} Aktif")
        else:
            st.error("❌ Data Error!")

        st.markdown("---")
        st.subheader("⚙️ Menu Operasi")
        menu = st.radio("Pilih Menu:", ["Diagnosis (User)", "Evaluasi (Admin)", "Riwayat (Admin)"])
        
        is_admin = False
        if menu in ["Evaluasi (Admin)", "Riwayat (Admin)"]:
            passcode = st.text_input("🔑 Masukkan Kode Admin:", type="password")
            if passcode == "admin123":
                is_admin = True
                st.success("Akses Diterima!")
            else:
                st.warning("Menu terkunci.")

    if df_gejala is not None:
        # Pakai container putih transparan biar konten kebaca jelas
        with st.container(border=True):
            if menu == "Diagnosis (User)":
                img_base64 = get_img_as_base64(pilihan_kasus)
                if img_base64:
                    st.markdown(f"""
                    <div class="banner-container">
                        <img src="data:image/jpg;base64,{img_base64}" class="banner-image">
                        <div class="banner-overlay">
                            <div>
                                <div class="banner-text">Diagnosis: {pilihan_kasus}</div>
                                <div class="banner-subtext">AI Expert System with Active Learning</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.title(f"Diagnosis: {pilihan_kasus}")

                st.subheader("📝 Observasi Gejala")
                opsi_tampilan = [f"{row['nama_gejala']} ({row['id_gejala']})" for i, row in df_gejala.iterrows()]
                mapping_gejala = {f"{row['nama_gejala']} ({row['id_gejala']})": row['id_gejala'] for i, row in df_gejala.iterrows()}
                
                input_pilihan = st.multiselect("Gejala yang ditemukan:", options=opsi_tampilan)
                
                if 'hasil' not in st.session_state: st.session_state['hasil'] = None

                st.write("")
                if st.button("🚀 ANALISIS SEKARANG", type="primary"):
                    if not input_pilihan:
                        st.warning("⚠️ Pilih minimal satu gejala.")
                    else:
                        user_ids = [mapping_gejala[x] for x in input_pilihan]
                        with st.spinner('Sedang berpikir...'):
                            time.sleep(0.5)
                            hasil = hitung_similarity(user_ids, df_kasus, df_gejala)
                        
                        if len(hasil) > 0:
                            top = hasil[0]
                            try:
                                sol_row = df_solusi[df_solusi['id_solusi'] == top['solusi_id']]
                                sol_text = sol_row['nama_solusi'].values[0] if not sol_row.empty else "Solusi tidak ditemukan."
                            except: sol_text = "Error data."
                            
                            st.session_state['hasil'] = {'top': top, 'input': input_pilihan, 'ids': user_ids, 'solusi': sol_text}
                            catat_riwayat(pilihan_kasus, input_pilihan, sol_text, top['similarity'])
                        else:
                            st.error("Database Kosong!")

                if st.session_state['hasil']:
                    res = st.session_state['hasil']
                    score = res['top']['similarity']
                    
                    st.markdown("---")
                    c1, c2 = st.columns([1,4])
                    with c1:
                        icon = "190411" if score >= 80 else "190406" if score >= 50 else "190407"
                        st.image(f"https://cdn-icons-png.flaticon.com/512/190/{icon}.png")
                    with c2:
                        st.subheader("Hasil Diagnosis")
                        status = "Sangat Yakin" if score >= 80 else "Mungkin" if score >= 50 else "Tidak Tahu"
                        color = "green" if score >= 80 else "orange" if score >= 50 else "red"
                        st.markdown(f"Status: **:{color}[{status} ({score:.1f}%)]**")
                        st.markdown(f"**Solusi:** \n### {res['solusi']}")
                        st.caption(f"Ref Case: {res['top']['id_kasus']}")

                    st.markdown("---")
                    with st.expander("⚠️ Jawaban Salah? Ajari Saya (Active Learning)"):
                        list_sol = [f"{r['nama_solusi']} ({r['id_solusi']})" for i, r in df_solusi.iterrows()]
                        map_sol = {f"{r['nama_solusi']} ({r['id_solusi']})": r['id_solusi'] for i, r in df_solusi.iterrows()}
                        sol_benar = st.selectbox("Solusi Seharusnya:", options=list_sol)
                        if st.button("💾 Simpan Pengetahuan Baru"):
                            new_id = simpan_kasus_baru(pilihan_kasus, res['ids'], map_sol[sol_benar], df_kasus)
                            if new_id:
                                st.success(f"Terima kasih! Pengetahuan tersimpan (ID: {new_id})")
                                time.sleep(1.5)
                                st.rerun()

            elif menu == "Evaluasi (Admin)":
                st.header("📊 Evaluation Dashboard")
                if is_admin:
                    if st.button("▶️ JALANKAN SELF-TESTING"):
                        benar = 0
                        total = len(df_kasus)
                        logs = []
                        bar = st.progress(0)
                        for i, row in df_kasus.iterrows():
                            test_ids = str(row['gejala_terkait']).split(',')
                            res = hitung_similarity(test_ids, df_kasus, df_gejala)
                            match = row['solusi_final'] == res[0]['solusi_id']
                            if match: benar += 1
                            logs.append({"ID": row['id_kasus'], "Real": row['solusi_final'], "Pred": res[0]['solusi_id'], "Match": "✅" if match else "❌"})
                            time.sleep(0.01)
                            bar.progress((i+1)/total)
                        st.metric("Akurasi Model", f"{(benar/total)*100:.1f}%" if total > 0 else "0%")
                        st.dataframe(pd.DataFrame(logs))
                else: st.error("Akses Ditolak.")

            elif menu == "Riwayat (Admin)":
                st.header("📜 Riwayat Diagnosis")
                if is_admin:
                    hist_path = os.path.join(BASE_DIR, "data", "riwayat_diagnosis.csv")
                    if os.path.exists(hist_path):
                        st.dataframe(pd.read_csv(hist_path), use_container_width=True)
                        if st.button("Hapus Riwayat"):
                            os.remove(hist_path)
                            st.success("Riwayat dihapus.")
                            st.rerun()
                    else: st.info("Belum ada riwayat.")
                else: st.error("Akses Ditolak.")
    else:
        st.error("Critical: Data tidak ditemukan.")

# =========================================================
# MAIN ROUTER
# =========================================================
if 'page' not in st.session_state:
    st.session_state['page'] = 'landing'

if st.session_state['page'] == 'landing':
    show_landing_page()
else:
    show_main_app()