import streamlit as st
import mysql.connector as mysql
import pandas as pd
from datetime import datetime

# --- UPDATE KONEKSI DATABASE KE CLOUD ---
def get_connection():
    return mysql.connect(
        host="gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com",
        user="3rHamxEYY6WE1cR.root",
        password="eycB9zCN73Mug2nP",
        database="keuangan_rt",
        port=4000
        ssl_disabled=True
    )

# --- TRIK CSS: Mengecilkan Ukuran Semua Tulisan di Aplikasi ---
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-size: 14px !important; /* Ukuran teks default disusutkan ke 14px */
    }
    h1 {
        font-size: 24px !important; /* Mengecilkan Judul Utama */
    }
    h2 {
        font-size: 18px !important; /* Mengecilkan Sub-Judul */
    }
    </style>
    """, unsafe_allow_html=True) # <--- Sekarang sudah bersih dari parameter siluman

# Judul Utama (Menggunakan st.header agar lebih kecil dibanding st.title)
st.header("💰 Aplikasi Keuangan Rumah Tangga")
st.caption("Catat pengeluaran harian Anda dengan mudah di sini.")

# --- FORM INPUT PENGELUARAN ---
st.subheader("✍️ Input Pengeluaran Baru")

with st.form("form_pengeluaran", clear_on_submit=True):
    tanggal = st.date_input("Tanggal", datetime.now())
    # ... input lainnya ...
    keterangan = st.text_input("Keterangan")

    # PASTIKAN BARIS INI MASUK DI DALAM BLOK INDENTASI 'WITH':
    tombol_simpan = st.form_submit_button("Simpan Pengeluaran")
    
    # Ambil data kategori dari database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_kategori, nama_kategori FROM kategori")
    daftar_kategori = cursor.fetchall()
    cursor.close()
    conn.close()
    
    opsi_kategori = {item[1]: item[0] for item in daftar_kategori}
    kategori_terpilih = st.selectbox("Kategori", list(opsi_kategori.keys()))
    
    jumlah = st.number_input("Jumlah Pengeluaran (Rp)", min_value=0, step=1000)
    keterangan = st.text_input("Keterangan (Contoh: Beli bakso, bayar wifi)")
    
    tombol_simpan = st.form_submit_button("Simpan Pengeluaran")

if tombol_simpan:
    if jumlah > 0:
        id_kat = opsi_kategori[kategori_terpilih]
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "INSERT INTO pengeluaran (tanggal, id_kategori, jumlah, keterangan) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (tanggal, id_kat, jumlah, keterangan))
        
        conn.commit()
        cursor.close()
        conn.close()
        st.success(f"Berhasil mencatat pengeluaran Rp {jumlah:,.0f}!")
    else:
        st.error("Jumlah pengeluaran harus lebih dari Rp 0!")

# --- TAMPILKAN RIWAYAT PENGELUARAN ---
st.write("---")
st.subheader("📊 Riwayat Pengeluaran Bulan Ini")

conn = get_connection()
query_tampil = """
    SELECT p.tanggal, k.nama_kategori, p.jumlah, p.keterangan 
    FROM pengeluaran p
    INNER JOIN kategori k ON p.id_kategori = k.id_kategori
    ORDER BY p.tanggal DESC
"""
df = pd.read_sql(query_tampil, conn)
conn.close()

if not df.empty:
    df['jumlah'] = df['jumlah'].apply(lambda x: f"Rp {x:,.0f}")
    st.dataframe(df, use_container_width=True)
    
    # Total Pengeluaran Keseluruhan
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(jumlah) FROM pengeluaran")
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    # Menggunakan st.metric dengan label yang rapi
    st.metric(label="Total Pengeluaran Terbuku", value=f"Rp {total:,.0f}")
else:
    st.info("Belum ada data pengeluaran yang dicatat.")
