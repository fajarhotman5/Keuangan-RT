import streamlit as st
import pymysql
import pandas as pd
import io
from datetime import datetime

def get_connection():
    ca_data = st.secrets["db"]["ca_data"]
    return pymysql.connect(
        host=st.secrets["db"]["host"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database="keuangan_rt",
        port=4000,
        ssl={'cadata': ca_data}
    )

@st.cache_resource
def init_and_connect():
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
        cursor.execute("ALTER TABLE pengeluaran ADD COLUMN IF NOT EXISTS jumlah BIGINT DEFAULT 0")
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
init_and_connect()

st.header("💰 Informasi Keuangan Kei")
st.caption("Catat pengeluaran harian setiap hari.")

# --- Ambil kategori ---
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT id_kategori, nama_kategori FROM kategori")
daftar_kategori = cursor.fetchall()
cursor.close()
conn.close()
opsi_kategori = {item[1]: item[0] for item in daftar_kategori}

# --- SESSION STATE ---
if 'show_riwayat' not in st.session_state:
    st.session_state.show_riwayat = False
if 'show_diagram' not in st.session_state:
    st.session_state.show_diagram = False
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None
if 'hapus_id' not in st.session_state:
    st.session_state.hapus_id = None

# --- FORM INPUT ---
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

# --- RIWAYAT & DIAGRAM ---
st.write("---")

col1, col2 = st.columns(2)
with col1:
    if st.button("📋 Riwayat Pengeluaran"):
        st.session_state.show_riwayat = not st.session_state.show_riwayat
        st.session_state.show_diagram = False
        st.session_state.edit_id = None
with col2:
    if st.button("📊 Diagram Pengeluaran"):
        st.session_state.show_diagram = not st.session_state.show_diagram
        st.session_state.show_riwayat = False
        st.session_state.edit_id = None

# --- RIWAYAT ---
if st.session_state.show_riwayat:
    conn = get_connection()
    df = pd.read_sql("""
        SELECT p.id_pengeluaran, p.tanggal, k.nama_kategori, p.jumlah, p.keterangan 
        FROM pengeluaran p
        JOIN kategori k ON p.id_kategori = k.id_kategori
        ORDER BY p.tanggal DESC
    """, conn)
    conn.close()

    if not df.empty:
        total = df['jumlah'].sum()
        st.metric("Total Pengeluaran", f"Rp {total:,.0f}")

        st.write("##### Daftar Pengeluaran")
df_tampil = df.copy()
df_tampil['jumlah'] = df_tampil['jumlah'].apply(lambda x: f"Rp {x:,.0f}")
df_tampil['Edit'] = '✏️'
df_tampil['Hapus'] = '🗑️'
st.dataframe(df_tampil.drop(columns=['id_pengeluaran']), use_container_width=True, hide_index=True)

st.write("**Edit atau Hapus — masukkan nomor urut data:**")
col_edit_input, col_hapus_input = st.columns(2)
with col_edit_input:
    edit_index = st.number_input("Nomor urut untuk diedit", min_value=1, max_value=len(df), step=1, value=1)
    if st.button("✏️ Edit"):
        st.session_state.edit_id = int(df.iloc[edit_index - 1]['id_pengeluaran'])
with col_hapus_input:
    hapus_index = st.number_input("Nomor urut untuk dihapus", min_value=1, max_value=len(df), step=1, value=1)
    if st.button("🗑️ Hapus"):
        st.session_state.hapus_id = int(df.iloc[hapus_index - 1]['id_pengeluaran'])

        # --- KONFIRMASI HAPUS ---
        if st.session_state.hapus_id:
            st.warning(f"Yakin ingin menghapus data ini?")
            col_ya, col_batal = st.columns(2)
            with col_ya:
                if st.button("✅ Ya, Hapus"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM pengeluaran WHERE id_pengeluaran = %s", (st.session_state.hapus_id,))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.session_state.hapus_id = None
                    st.success("Data berhasil dihapus!")
                    st.rerun()
            with col_batal:
                if st.button("❌ Batal"):
                    st.session_state.hapus_id = None
                    st.rerun()

        # --- FORM EDIT ---
        if st.session_state.edit_id:
            data_edit = df[df['id_pengeluaran'] == st.session_state.edit_id].iloc[0]
            st.write("---")
            st.subheader("✏️ Edit Pengeluaran")
            with st.form("form_edit"):
                tanggal_edit = st.date_input("Tanggal", value=data_edit['tanggal'])
                kategori_edit = st.selectbox(
                    "Kategori",
                    list(opsi_kategori.keys()),
                    index=list(opsi_kategori.keys()).index(data_edit['nama_kategori'])
                )
                jumlah_edit = st.number_input("Jumlah (Rp)", min_value=0, step=1000, value=int(data_edit['jumlah']))
                keterangan_edit = st.text_input("Keterangan", value=data_edit['keterangan'] or "")
                col_simpan, col_batal = st.columns(2)
                with col_simpan:
                    tombol_update = st.form_submit_button("💾 Simpan Perubahan")
                with col_batal:
                    tombol_batal = st.form_submit_button("❌ Batal")

            if tombol_update:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE pengeluaran SET tanggal=%s, id_kategori=%s, jumlah=%s, keterangan=%s WHERE id_pengeluaran=%s",
                    (tanggal_edit, opsi_kategori[kategori_edit], jumlah_edit, keterangan_edit, st.session_state.edit_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                st.session_state.edit_id = None
                st.success("Data berhasil diupdate!")
                st.rerun()

            if tombol_batal:
                st.session_state.edit_id = None
                st.rerun()

        # --- DOWNLOAD EXCEL ---
        buffer = io.BytesIO()
        df_download = df.drop(columns=['id_pengeluaran'])
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_download.to_excel(writer, index=False, sheet_name='Pengeluaran')
        st.download_button(
            label="⬇️ Download sebagai Excel",
            data=buffer.getvalue(),
            file_name=f"riwayat_pengeluaran_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Belum ada data pengeluaran.")

# --- DIAGRAM ---
if st.session_state.show_diagram:
    conn = get_connection()
    df = pd.read_sql("""
        SELECT k.nama_kategori, p.jumlah
        FROM pengeluaran p
        JOIN kategori k ON p.id_kategori = k.id_kategori
    """, conn)
    conn.close()

    if not df.empty:
        df_chart = df.groupby('nama_kategori')['jumlah'].sum().reset_index()
        df_chart = df_chart.sort_values('jumlah', ascending=False)
        st.bar_chart(df_chart.set_index('nama_kategori')['jumlah'])
    else:
        st.info("Belum ada data pengeluaran.")
