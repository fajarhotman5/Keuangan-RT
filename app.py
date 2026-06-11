import streamlit as st
import pymysql
import pandas as pd
from datetime import datetime

def get_connection():
    ca_data = st.secrets["db"]["ca_data"]  # pindah ke secrets
    return pymysql.connect(
        host=st.secrets["db"]["host"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database="keuangan_rt",
        port=4000,
        ssl={'cadata': ca_data}
    )

def init_db():
    conn = pymysql.connect(
        host=st.secrets["db"]["host"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database="sys",
        port=4000,
        ssl={'cadata': st.secrets["db"]["ca_data"]}
    )
    with conn.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS keuangan_rt")
        cursor.execute("USE keuangan_rt")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kategori (
                id_kategori INT AUTO_INCREMENT PRIMARY KEY,
                nama_kategori VARCHAR(50) NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pengeluaran (
                id_pengeluaran INT AUTO_INCREMENT PRIMARY KEY,
                tanggal DATE NOT NULL,
                keterangan TEXT,
                jumlah BIGINT DEFAULT 0,
                id_kategori INT,
                FOREIGN KEY (id_kategori) REFERENCES kategori(id_kategori)
            )
        """)
        cursor.execute("""
            ALTER TABLE pengeluaran 
            ADD COLUMN IF NOT EXISTS jumlah BIGINT DEFAULT 0
        """)
        cursor.execute("SELECT COUNT(*) FROM kategori")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO kategori (nama_kategori) VALUES (%s)",
                [('Makanan & Minuman',), ('Listrik, Air & Internet',),
                 ('Belanja Bulanan',), ('Transportasi & Bensin',),
                 ('Hiburan',), ('Lain-lain',)]
            )
            conn.commit()
    conn.close()

# --- INIT ---
init_db()

st.header("💰 Informasi Keuangan Kei")
st.caption("Catat pengeluaran harian setiap hari.")

# --- Ambil kategori SEBELUM form ---
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT id_kategori, nama_kategori FROM kategori")
daftar_kategori = cursor.fetchall()
cursor.close()
conn.close()
opsi_kategori = {item[1]: item[0] for item in daftar_kategori}

# --- FORM (bersih, tanpa duplikat) ---
st.subheader("✍️ Input Pengeluaran Baru Disini!")
with st.form("form_pengeluaran", clear_on_submit=True):
    tanggal = st.date_input("Tanggal", datetime.now())
    kategori_terpilih = st.selectbox("Kategori", list(opsi_kategori.keys()))
    jumlah = st.number_input("Jumlah Pengeluaran (Rp)", min_value=0, step=1000)
    keterangan = st.text_input("Keterangan (Contoh: Beli bakso, bayar wifi)")
    tombol_simpan = st.form_submit_button("Simpan Pengeluaran")

if tombol_simpan:
    if jumlah > 0:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pengeluaran (tanggal, id_kategori, jumlah, keterangan) VALUES (%s, %s, %s, %s)",
            (tanggal, opsi_kategori[kategori_terpilih], jumlah, keterangan)
        )
        conn.commit()
        cursor.close()
        conn.close()
        st.success(f"Berhasil mencatat pengeluaran Rp {jumlah:,.0f}!")
    else:
        st.error("Jumlah pengeluaran harus lebih dari Rp 0!")

# --- RIWAYAT ---
st.write("---")
st.subheader("📊 Riwayat Pengeluaran")
conn = get_connection()
df = pd.read_sql("""
    SELECT p.tanggal, k.nama_kategori, p.jumlah, p.keterangan 
    FROM pengeluaran p
    JOIN kategori k ON p.id_kategori = k.id_kategori
    ORDER BY p.tanggal DESC
""", conn)
conn.close()

if not df.empty:
    total = df['jumlah'].sum()
    df_tampil = df.copy()
    df_tampil['jumlah'] = df_tampil['jumlah'].apply(lambda x: f"Rp {x:,.0f}")
    st.dataframe(df_tampil, use_container_width=True, hide_index=True)
    st.metric("Total Pengeluaran", f"Rp {total:,.0f}")

    # --- Tombol Download Excel ---
    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Pengeluaran')
    
    st.download_button(
        label="⬇️ Download sebagai Excel",
        data=buffer.getvalue(),
        file_name=f"riwayat_pengeluaran_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Belum ada data pengeluaran.")
