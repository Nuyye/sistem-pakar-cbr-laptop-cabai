import streamlit as st
import pandas as pd
import time
import base64
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Expert System - Self Learning",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNGSI LOAD CSS ---
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("⚠️ CSS tidak ditemukan.")

load_css("styles/main.css")

# --- FUNGSI LOAD GAMBAR LOKAL ---
def get_img_as_base64(file):
    try:
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

# --- DATABASE LOKASI GAMBAR ---
BANNER_PATHS = {
    "Laptop": "images/2banner_laptop.jpeg",
    "Tanaman Cabai": "images/1banner_cabai.jpg"
}

# --- FUNGSI LOAD DATA ---
# --- UPDATE FUNGSI LOAD DATA (ANTI NAN / BARIS KOSONG) ---
@st.cache_data
def load_data(kasus_type):
    folder = "data/"
    try:
        if kasus_type == "Laptop":
            df_gejala = pd.read_csv(f"{folder}gejala_laptop.csv")
            df_solusi = pd.read_csv(f"{folder}solusi_laptop.csv")
            df_kasus = pd.read_csv(f"{folder}kasus_laptop.csv")
        else:
            df_gejala = pd.read_csv(f"{folder}gejala_cabai.csv")
            df_solusi = pd.read_csv(f"{folder}solusi_cabai.csv")
            df_kasus = pd.read_csv(f"{folder}kasus_cabai.csv")
        
        # --- CLEANING DATA (PENTING BANGET) ---
        # 1. Buang baris yang ID Kasus atau Solusinya KOSONG (NaN)
        df_kasus.dropna(subset=['id_kasus', 'solusi_final'], inplace=True)
        
        # 2. Pastikan semua jadi String biar gak error baca angka
        df_gejala['id_gejala'] = df_gejala['id_gejala'].astype(str)
        df_kasus['id_kasus'] = df_kasus['id_kasus'].astype(str)
        df_kasus['solusi_final'] = df_kasus['solusi_final'].astype(str)
        
        # 3. Reset Index biar rapi
        df_kasus.reset_index(drop=True, inplace=True)

        return df_gejala, df_solusi, df_kasus
    except FileNotFoundError:
        return None, None, None
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None

# --- ENGINE CBR (RETRIEVE) ---
# --- UPDATE ENGINE CBR (LOGIKA LEBIH KETAT) ---
def hitung_similarity(user_gejala, df_kasus, df_gejala):
    results = []
    
    # 1. Hitung dulu total bobot input user (buat pembagi nanti)
    total_bobot_user = 0
    for u_gejala in user_gejala:
        bobot_data = df_gejala[df_gejala['id_gejala'] == u_gejala]['bobot'].values
        if len(bobot_data) > 0:
            total_bobot_user += int(bobot_data[0])

    # 2. Loop Kasus
    for index, row in df_kasus.iterrows():
        kasus_gejala_list = str(row['gejala_terkait']).split(',')
        match_bobot = 0
        total_bobot_kasus = 0
        
        for k_gejala in kasus_gejala_list:
            bobot_data = df_gejala[df_gejala['id_gejala'] == k_gejala]['bobot'].values
            if len(bobot_data) > 0:
                bobot = int(bobot_data[0])
                total_bobot_kasus += bobot
                
                # Cek kecocokan (Irisan)
                if k_gejala in user_gejala:
                    match_bobot += bobot
        
        # --- RUMUS BARU (DICE / SORENSEN LIKE) ---
        # Pembaginya adalah Rata-rata Bobot Kasus + Bobot User
        # Jadi kalau User bawa banyak sampah, nilai similarity TURUN.
        
        pembagi = (total_bobot_kasus + total_bobot_user) / 2
        
        if pembagi > 0:
            similarity = (match_bobot / pembagi) * 100
        else:
            similarity = 0
            
        results.append({
            'id_kasus': row['id_kasus'],
            'similarity': similarity,
            'solusi_id': row['solusi_final'],
            'gejala_kasus': kasus_gejala_list
        })
        
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results
# --- FITUR BARU: RETAIN (BELAJAR) ---
def simpan_kasus_baru(pilihan_kasus, gejala_baru_ids, solusi_benar_id, df_kasus):
    folder = "data/"
    if pilihan_kasus == "Laptop":
        file_path = f"{folder}kasus_laptop.csv"
        prefix = "K"
    else:
        file_path = f"{folder}kasus_cabai.csv"
        prefix = "KC"
    
    # 1. Generate ID Baru (Auto Increment)
    # Ambil angka dari ID terakhir (misal K14 -> 14)
    last_id = df_kasus.iloc[-1]['id_kasus']
    try:
        last_number = int(''.join(filter(str.isdigit, last_id)))
        new_id = f"{prefix}{last_number + 1:02d}"
    except:
        new_id = f"{prefix}99" # Fallback kalau error

    # 2. Format Gejala jadi String "G01,G02"
    gejala_str = ",".join(gejala_baru_ids)
    
    # 3. Siapkan Baris Baru
    new_data = pd.DataFrame({
        'id_kasus': [new_id],
        'gejala_terkait': [gejala_str],
        'solusi_final': [solusi_benar_id]
    })
    
    # 4. Append ke CSV (Mode 'a' = append) without header
    # HATI-HATI: Kita pake to_csv mode append
    new_data.to_csv(file_path, mode='a', header=False, index=False)
    
    return new_id

# --- SIDEBAR ---
with st.sidebar:
    st.title("🎛️ System Control")
    st.subheader("Mode Operasi")
    mode_aplikasi = st.radio("Pilih Mode:", ["User Diagnosis (Learning)", "Model Evaluation (Dosen)"])
    
    st.markdown("---")
    st.subheader("📂 Knowledge Base")
    pilihan_kasus = st.selectbox("Studi Kasus:", ["Laptop", "Tanaman Cabai"])
    
    # Load Data (Selalu fresh biar update)
    df_gejala, df_solusi, df_kasus = load_data(pilihan_kasus)
    
    if df_gejala is not None:
        st.success(f"✅ Data Loaded: {len(df_kasus)} Kasus")
        if mode_aplikasi == "User Diagnosis (Learning)":
             st.info("💡 Fitur Active Learning Aktif: Sistem dapat menerima pengetahuan baru dari user.")
    else:
        st.error("❌ Error: CSV tidak ditemukan!")

# --- HALAMAN UTAMA ---

if df_gejala is not None:
    
    # === MODE 1: USER DIAGNOSIS + LEARNING ===
    if mode_aplikasi == "User Diagnosis (Learning)":
        
        # Banner
        img_path = BANNER_PATHS.get(pilihan_kasus)
        img_base64 = get_img_as_base64(img_path)
        if img_base64:
            st.markdown(f"""
            <div class="banner-container">
                <img src="data:image/jpg;base64,{img_base64}" class="banner-image">
                <div class="banner-overlay">
                    <div>
                        <div class="banner-text">Diagnosis: {pilihan_kasus}</div>
                        <div class="banner-subtext">Expert System with Self-Learning Capability</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.title(f"Diagnosis: {pilihan_kasus}")

        # Form Input
        st.write("")
        st.subheader("📝 Observasi Gejala")
        opsi_tampilan = [f"{row['nama_gejala']} ({row['id_gejala']})" for i, row in df_gejala.iterrows()]
        mapping_gejala = {f"{row['nama_gejala']} ({row['id_gejala']})": row['id_gejala'] for i, row in df_gejala.iterrows()}
        
        input_pilihan = st.multiselect("Gejala yang ditemukan:", options=opsi_tampilan)
        
        st.write("")
        
        # Session State untuk nyimpen hasil sementara biar gak ilang pas refresh
        if 'hasil_diagnosis' not in st.session_state:
            st.session_state['hasil_diagnosis'] = None

        # --- UPDATE BAGIAN TOMBOL ANALISIS INI ---
        if st.button(f"🚀 ANALISIS & DIAGNOSIS", type="primary"):
            if not input_pilihan:
                st.warning("⚠️ Pilih gejala dulu bro.")
            else:
                user_gejala_ids = [mapping_gejala[x] for x in input_pilihan]
                
                with st.spinner('Menganalisis pola...'):
                    time.sleep(0.8)
                    hasil = hitung_similarity(user_gejala_ids, df_kasus, df_gejala)
                
                # --- PENGAMAN (SAFETY CHECK) ---
                if len(hasil) > 0:
                    # Kalau ada hasil, baru simpan
                    st.session_state['hasil_diagnosis'] = {
                        'top': hasil[0],
                        'gejala_input': user_gejala_ids,
                        'input_display': input_pilihan
                    }
                else:
                    # Kalau hasil kosong (Database 0), kasih peringatan JANGAN CRASH
                    st.error("❌ Database Kosong atau Rusak! Silakan cek file CSV Anda.")
                    st.session_state['hasil_diagnosis'] = None
        # TAMPILKAN HASIL (Jika ada di session state)
        if st.session_state['hasil_diagnosis']:
            data_hasil = st.session_state['hasil_diagnosis']
            top = data_hasil['top']
            user_gejala_ids = data_hasil['gejala_input']
            
            # --- UPDATE BAGIAN PENGAMBILAN SOLUSI (ANTI ERROR) ---
            try:
                # Coba cari nama solusinya
                solusi_row = df_solusi[df_solusi['id_solusi'] == top['solusi_id']]
                
                if not solusi_row.empty:
                    solusi_text = solusi_row['nama_solusi'].values[0]
                else:
                    # Kalau ID-nya gak ada di tabel solusi
                    solusi_text = f"⚠️ CRITICAL DATA ERROR: ID Solusi '{top['solusi_id']}' tidak ditemukan di database solusi_laptop.csv!"
            except Exception as e:
                solusi_text = f"Error System: {e}"
            score = top['similarity']

            st.markdown("---")
            col1, col2 = st.columns([1,4])
            with col1:
                if score >= 80: st.image("https://cdn-icons-png.flaticon.com/512/190/190411.png")
                elif score >= 50: st.image("https://cdn-icons-png.flaticon.com/512/190/190406.png")
                else: st.image("https://cdn-icons-png.flaticon.com/512/190/190407.png")
            
            with col2:
                st.subheader("Hasil Diagnosis Sistem")
                if score >= 80: st.success(f"### Solusi Ditemukan ({score:.1f}%)")
                elif score >= 50: st.warning(f"### Kemungkinan Solusi ({score:.1f}%)")
                else: st.error(f"### Kasus Tidak Dikenal ({score:.1f}%)")
                
                st.markdown(f"**Rekomendasi:** \n### {solusi_text}")
                st.caption(f"Mirip dengan Kasus Lama ID: **{top['id_kasus']}**")

            # === FITUR RETAIN (ACTIVE LEARNING) ===
            st.markdown("---")
            st.markdown("### 🧠 Feedback Loop (Active Learning)")
            
            with st.expander("⚠️ Jawaban Salah / Kurang Akurat? Ajari Saya! (Klik Disini)"):
                st.write("Jika diagnosis di atas salah, silakan beritahu solusi yang benar agar sistem bisa belajar.")
                
                # Dropdown pilih solusi yang benar
                list_solusi = [f"{row['nama_solusi']} ({row['id_solusi']})" for i, row in df_solusi.iterrows()]
                mapping_solusi = {f"{row['nama_solusi']} ({row['id_solusi']})": row['id_solusi'] for i, row in df_solusi.iterrows()}
                
                solusi_benar = st.selectbox("Pilih Solusi yang Seharusnya:", options=list_solusi)
                
                if st.button("💾 Simpan Pengetahuan Baru (Retain)"):
                    solusi_id_fix = mapping_solusi[solusi_benar]
                    
                    # PROSES PENYIMPANAN
                    try:
                        new_case_id = simpan_kasus_baru(pilihan_kasus, user_gejala_ids, solusi_id_fix, df_kasus)
                        st.success(f"🎉 Terima kasih! Pengetahuan baru telah disimpan dengan ID **{new_case_id}**.")
                        st.balloons()
                        time.sleep(2)
                        st.rerun() # Refresh halaman biar data update
                    except Exception as e:
                        st.error(f"Gagal menyimpan: {e}. Pastikan file CSV tidak sedang dibuka!")

            # Detail & Download
            st.write("")
            with st.expander("ℹ️ Lihat Detail Logika"):
                st.write(f"Gejala Input: `{user_gejala_ids}`")
                st.info("Metode: Weighted Nearest Neighbor Similarity")

    # === MODE 2: MODEL EVALUATION ===
    elif mode_aplikasi == "Model Evaluation (Dosen)":
        st.header("📊 Evaluation Dashboard")
        if st.button("▶️ JALANKAN SELF-TESTING"):
            benar = 0
            total = len(df_kasus)
            logs = []
            bar = st.progress(0)
            
            for i, row in df_kasus.iterrows():
                gejala_test = str(row['gejala_terkait']).split(',')
                real_solusi = row['solusi_final']
                
                hasil = hitung_similarity(gejala_test, df_kasus, df_gejala)
                prediksi = hasil[0]['solusi_id']
                
                if real_solusi == prediksi: benar += 1
                logs.append({"ID": row['id_kasus'], "Real": real_solusi, "Pred": prediksi, "Score": f"{hasil[0]['similarity']:.1f}%"})
                time.sleep(0.05)
                bar.progress((i+1)/total)
            
            akurasi = (benar/total)*100
            st.metric("Akurasi Sistem (Recall)", f"{akurasi:.1f}%")
            st.dataframe(pd.DataFrame(logs))