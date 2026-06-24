import streamlit as st
import pymysql
import pandas as pd
import io
from datetime import datetime, timedelta
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# --- CONFIG & STYLING ---\nst.set_page_config(page_title="Keuangan Kei", page_icon="💰", layout="centered")

# Custom CSS Responsif & Pembersihan Elemen Pengganggu
st.markdown("""
    <style>
    /* 1. Pembersihan total simbol/lambang link */
    .stApp a.element-header-anchor, 
    a.element-header-anchor, \n    .stMarkdown a, \n    [data-testid="stMarkdownContainer"] a.element-header-anchor {
        display: none !important;
    }
    h1, h2, h3, h4, h5, h6 {
        pointer-events: none !important;
    }
    
    /* Sembunyikan elemen bawaan Streamlit yang mengganggu */
    [data-testid="stAppDeployButton"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    
    /* 2. Responsivitas Layar (Deteksi HP vs Laptop) */
    @media (max-width: 768px) {
        .desktop-only { display: none !important; }
        .mobile-only { display: block !important; }
    }
    @media (min-width: 769px) {
        .desktop-only { display: block !important; }
        .mobile-only { display: none !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
def get_connection():
    return pymysql.connect(
        host=st.secrets["mysql"]["host"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        port=int(st.secrets["mysql"].get("port", 3306)),
        autocommit=True
    )

# --- GLOBAL CONFIG & CONSTANTS ---
LIST_WALLET = ["BCA", "Jago", "Gopay", "Dana", "Ovo", "Cash", "Lainnya"]
LIST_KATEGORI = [
    "Makanan & Minuman", "Transportasi", "Belanja", "Hiburan", 
    "Tagihan & Utilitas", "Kesehatan", "Pendidikan", 
    "Investasi", "Gaji", "Bonus", "Lain-lain"
]

# --- APP INITIALIZATION & STATE ---
if 'menu_aktif' not in st.session_state:
    st.session_state.menu_aktif = 'riwayat'

# --- MENU UTAMA ATAS (TAMPILAN TOMBOL ELEGAN) ---
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Amatic+SC:wght@700&display=swap" rel="stylesheet">
    
    <div style='text-align: center; margin-bottom: 15px;'>
        <div style='font-family: "Amatic SC", sans-serif; font-size: 34px; font-weight: bold; font-style: italic; color: var(--text-color); letter-spacing: 1px; margin: 0; padding: 0; line-height: 1.1;'>Informasi Keuangan Kei</div>
        <div style='font-size: 11px; color: var(--text-color); font-weight: 500; opacity: 0.6; letter-spacing: 1px; margin-top: 4px; padding: 0;'>HARUS CATAT SETIAP SAAT</div>
    </div>
""", unsafe_allow_html=True)

col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
with col_m1: 
    if st.button("📝 Tambah", use_container_width=True, type="primary" if st.session_state.menu_aktif == 'tambah' else "secondary"):
        st.session_state.menu_aktif = 'tambah'
        st.rerun()
with col_m2: 
    if st.button("📜 Riwayat", use_container_width=True, type="primary" if st.session_state.menu_aktif == 'riwayat' else "secondary"):
        st.session_state.menu_aktif = 'riwayat'
        st.rerun()
with col_m3: 
    if st.button("📊 Rekap", use_container_width=True, type="primary" if st.session_state.menu_aktif == 'rekap' else "secondary"):
        st.session_state.menu_aktif = 'rekap'
        st.rerun()
with col_m4: 
    if st.button("📥 Unduh", use_container_width=True, type="primary" if st.session_state.menu_aktif == 'unduh' else "secondary"):
        st.session_state.menu_aktif = 'unduh'
        st.rerun()
with col_m5: 
    if st.button("💳 Wallet", use_container_width=True, type="primary" if st.session_state.menu_aktif == 'wallet' else "secondary"):
        st.session_state.menu_aktif = 'wallet'
        st.rerun()

st.markdown("---")

# --- DATA FETCHING ---
@st.cache_data(ttl=5)
def load_all_data():
    try:
        conn = get_connection()
        query = "SELECT id_transaksi, jenis, tanggal, wallet, kategori, jumlah, reimburse, keterangan FROM transaksi ORDER BY tanggal DESC, id_transaksi DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Koneksi Database Gagal: {e}")
        return pd.DataFrame()

df_trans = load_all_data()

if not df_trans.empty:
    df_trans['tanggal'] = pd.to_datetime(df_trans['tanggal']).dt.date
    
    # Hitung Saldo & Pengeluaran Berjalan
    saldo_berjalan = df_trans[df_trans['jenis'] == 'Pemasukan']['jumlah'].sum() - df_trans[df_trans['jenis'] == 'Pengeluaran']['jumlah'].sum()
    total_pengeluaran = df_trans[df_trans['jenis'] == 'Pengeluaran']['jumlah'].sum()
    
    # Hitung per wallet dinamis
    wallet_balances = {}
    for w in LIST_WALLET:
        df_w = df_trans[df_trans['wallet'] == w]
        masuk = df_w[df_w['jenis'] == 'Pemasukan']['jumlah'].sum()
        keluar = df_w[df_w['jenis'] == 'Pengeluaran']['jumlah'].sum()
        wallet_balances[w] = masuk - keluar
else:
    saldo_berjalan = 0
    total_pengeluaran = 0
    wallet_balances = {w: 0 for w in LIST_WALLET}

# Tampilkan Ringkasan Metrik (Rata Tengah)
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
        <div style="background-color: var(--background-color); border: 1px solid #B8860B; padding: 12px; border-radius: 8px; text-align: center;">
            <p style="margin: 0; font-size: 11px; color: var(--text-color); opacity: 0.7; font-weight: 500;">💰 Sisa Saldo Berjalan</p>
            <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: 800; color: #B8860B;">Rp {saldo_berjalan:,.0f}</p>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div style="background-color: var(--background-color); border: 1px solid #8B0000; padding: 12px; border-radius: 8px; text-align: center;">
            <p style="margin: 0; font-size: 11px; color: var(--text-color); opacity: 0.7; font-weight: 500;">📉 Total Pengeluaran</p>
            <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: 800; color: #8B0000;">Rp {total_pengeluaran:,.0f}</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 1. MENU: TAMBAH TRANSAKSI
# ==========================================
if st.session_state.menu_aktif == 'tambah':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 8px;'>📝 Tambah Transaksi Baru</p>", unsafe_allow_html=True)
    
    with st.form("form_transaksi", clear_on_submit=True):
        jenis_tx = st.radio("Aliran Dana", ["Pengeluaran", "Pemasukan"], horizontal=True)
        tgl = st.date_input("Tanggal Transaksi", datetime.now(), format="DD-MM-YYYY")
        wlt = st.selectbox("Wallet", LIST_WALLET)
        kat = st.selectbox("Kategori", LIST_KATEGORI)
        jml = st.number_input("Nominal (Rp)", min_value=0, step=1000, format="%d")
        remb = st.radio("Reimburse?", ["Tidak", "Ya"], horizontal=True)
        ket = st.text_input("Keterangan Tambahan (Opsional)")
        
        simpan = st.form_submit_button("Simpan Transaksi", use_container_width=True)
        if simpan:
            if jml > 0:
                try:
                    conn = get_connection()
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO transaksi (jenis, tanggal, wallet, kategori, jumlah, reimburse, keterangan) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (jenis_tx, tgl, wlt, kat, jml, remb, ket)
                        )
                    conn.commit()
                    conn.close()
                    st.toast("✅ Transaksi baru berhasil disimpan!", icon="💰")
                    st.success("Data berhasil disimpan!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal menyimpan transaksi: {str(e)}")
            else:
                st.error("Jumlah input harus lebih besar dari Rp 0!")

# ==========================================
# 2. MENU: RIWAYAT (TAP / SELEKSI LANGSUNG UNTUK EDIT/HAPUS)
# ==========================================
elif st.session_state.menu_aktif == 'riwayat':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 8px;'>📜 Riwayat Transaksi</p>", unsafe_allow_html=True)
    
    if df_trans.empty:
        st.info("Belum ada riwayat transaksi.")
    else:
        # Filter Cari (Kategori / Keterangan tetap dipertahankan)
        cari = st.text_input("🔍 Cari Kategori / Keterangan", "").strip().lower()
        if cari:
            df_tampil = df_trans[
                df_trans['kategori'].str.lower().str.contains(cari) | 
                df_trans['keterangan'].str.lower().str.contains(cari)
            ]
        else:
            df_tampil = df_trans.copy()
            
        id_terpilih = None
        
        # --- MODE DESKTOP / LAPTOP (Menggunakan st.dataframe Interaktif untuk Pilih & Klik) ---
        st.markdown('<div class="desktop-only">', unsafe_allow_html=True)
        if not df_tampil.empty:
            df_laptop = df_tampil.copy()
            df_laptop['tanggal'] = df_laptop['tanggal'].apply(lambda x: x.strftime('%d-%m-%Y'))
            df_laptop['jumlah'] = df_laptop['jumlah'].apply(lambda x: f"Rp {x:,.0f}")
            
            # Ubah nama kolom agar cantik di layar
            df_laptop.columns = ['ID', 'Aliran', 'Tanggal', 'Wallet', 'Kategori', 'Nominal', 'Reimburse', 'Keterangan']
            
            st.caption("💡 *Klik/Centang lingkaran di sebelah kiri baris tabel untuk Memilih Transaksi yang ingin di-Edit atau Hapus.*")
            
            # Fitur Seleksi Baris Otomatis bawaan Streamlit
            event = st.dataframe(
                df_laptop,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # Jika user memilih salah satu baris di tabel laptop
            if event and event.get("selection") and event["selection"].get("rows"):
                idx_terpilih_laptop = event["selection"]["rows"][0]
                id_terpilih = int(df_tampil.iloc[idx_terpilih_laptop]['id_transaksi'])
        else:
            st.write("Data tidak ditemukan.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- MODE MOBILE / HP (Interaksi Tap Langsung lewat Tombol Dinamis) ---
        st.markdown('<div class="mobile-only">', unsafe_allow_html=True)
        if not df_tampil.empty:
            st.caption("💡 *Ketuk tombol '⚙️ Aksi' di bawah masing-masing kartu riwayat untuk Edit/Hapus.*")
            for index, row in df_tampil.iterrows():
                tgl_mini = row['tanggal'].strftime('%d-%m-%Y')
                txt_jenis = "Masuk" if row['jenis'] == "Pemasukan" else "Keluar"
                badge_color = "#2E7D32" if row['jenis'] == "Pemasukan" else "#C62828"
                
                # Render visual kartu estetik asli bawaan tanpa diubah sedikit pun
                st.markdown(f"""
                    <div style='background-color: var(--background-color); border: 1px solid rgba(139,0,0,0.2); padding: 10px; border-radius: 8px; margin-bottom: 6px; position: relative;'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <span style='font-size: 10px; font-weight: bold; color: var(--text-color); opacity: 0.6;'>{tgl_mini} &bull; {row['wallet']}</span>
                            <span style='background-color: {badge_color}; color: white; font-size: 9px; font-weight: bold; padding: 2px 6px; border-radius: 10px;'>{txt_jenis}</span>
                        </div>
                        <div style='font-size: 13px; font-weight: bold; margin-top: 4px; color: var(--text-color);'>{row['kategori']}</div>
                        <div style='font-size: 11px; color: var(--text-color); opacity: 0.8; margin-top: 1px;'>{row['keterangan'] or '-'}</div>
                        <div style='font-size: 14px; font-weight: 800; text-align: right; color: {badge_color}; margin-top: -15px;'>Rp {row['jumlah']:,.0f}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Tombol Tap Terbuka Ringan di bawah kartu (Interaksi Tap Pengganti Aksi Cepat)
                if st.button(f"⚙️ Aksi untuk {row['kategori']} ({tgl_mini})", key=f"tap_{row['id_transaksi']}", use_container_width=True):
                    st.session_state.id_aktif_hp = row['id_transaksi']
            
            # Cek jika ada id aktif yang terpilih dari ketukan layar HP
            if 'id_aktif_hp' in st.session_state and st.session_state.id_aktif_hp in df_tampil['id_transaksi'].values:
                id_terpilih = st.session_state.id_aktif_hp
        else:
            st.write("Data tidak ditemukan.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- BLOK FORM MODAL EDIT / HAPUS (Otomatis Muncul saat Baris/Kartu Ditekan) ---
        if id_terpilih:
            data_row = df_trans[df_trans['id_transaksi'] == id_terpilih].iloc[0]
            
            st.markdown("---")
            st.markdown(f"<p style='color: #B8860B; font-weight: bold; font-size: 13px; margin-bottom: 4px;'>🛠️ Pengaturan Transaksi Terpilih (ID: {id_terpilih})</p>", unsafe_allow_html=True)
            
            mode_aksi = st.radio("Pilih Operasi Aksi:", ["📝 Edit Data", "🗑️ Hapus Data"], horizontal=True)
            
            if "📝 Edit Data" in mode_aksi:
                with st.form(f"form_edit_{id_terpilih}"):
                    new_jenis = st.radio("Aliran Dana", ["Pengeluaran", "Pemasukan"], index=0 if data_row['jenis'] == "Pengeluaran" else 1, horizontal=True)
                    new_tgl = st.date_input("Tanggal", data_row['tanggal'], format="DD-MM-YYYY")
                    new_wallet = st.selectbox("Wallet", LIST_WALLET, index=LIST_WALLET.index(data_row['wallet']) if data_row['wallet'] in LIST_WALLET else 0)
                    new_kat = st.selectbox("Kategori", LIST_KATEGORI, index=LIST_KATEGORI.index(data_row['kategori']) if data_row['kategori'] in LIST_KATEGORI else 0)
                    new_jml = st.number_input("Nominal (Rp)", min_value=0, value=int(data_row['jumlah']), step=1000, format="%d")
                    new_remb = st.radio("Reimburse?", ["Tidak", "Ya"], index=0 if data_row['reimburse'] == "Tidak" else 1, horizontal=True)
                    new_ket = st.text_input("Keterangan", value=str(data_row['keterangan'] or ''))
                    
                    col_ef1, col_ef2 = st.columns(2)
                    with col_ef1:
                        if st.form_submit_button("Simpan Perubahan", use_container_width=True):
                            try:
                                conn = get_connection()
                                with conn.cursor() as cursor:
                                    cursor.execute(
                                        "UPDATE transaksi SET tanggal=%s, jenis=%s, wallet=%s, kategori=%s, jumlah=%s, reimburse=%s, keterangan=%s WHERE id_transaksi=%s",
                                        (new_tgl, new_jenis, new_wallet, new_kat, new_jml, new_remb, new_ket, id_terpilih)
                                    )
                                conn.commit()
                                conn.close()
                                if 'id_aktif_hp' in st.session_state: del st.session_state.id_aktif_hp
                                st.toast("✅ Data berhasil diperbarui!", icon="🎉")
                                st.success("Berhasil diubah!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Gagal mengubah data: {str(e)}")
                    with col_ef2:
                        if st.form_submit_button("Batal", use_container_width=True):
                            if 'id_aktif_hp' in st.session_state: del st.session_state.id_aktif_hp
                            st.rerun()
                            
            elif "🗑️ Hapus Data" in mode_aksi:
                st.markdown(f"<div style='background-color:rgba(198,40,40,0.1); padding:8px; border-radius:6px; border:1px solid #c62828; margin-bottom:8px; font-size:11px; color:#c62828;'>Hapus data <b>{data_row['kategori']} (Rp {data_row['jumlah']:,.0f})</b>? Tindakan ini permanen.</div>", unsafe_allow_html=True)
                col_del1, col_del2 = st.columns(2)
                with col_del1:
                    if st.button("🔴 Ya, Hapus", key="confirm_del_univ", use_container_width=True):
                        try:
                            conn = get_connection()
                            with conn.cursor() as cursor:
                                cursor.execute("DELETE FROM transaksi WHERE id_transaksi=%s", (id_terpilih,))
                            conn.commit()
                            conn.close()
                            if 'id_aktif_hp' in st.session_state: del st.session_state.id_aktif_hp
                            st.toast("🗑️ Data transaksi telah dihapus!", icon="ℹ️")
                            st.success("Terhapus!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Gagal menghapus data: {str(e)}")
                with col_del2:
                    if st.button("Batal", key="cancel_del_univ", use_container_width=True):
                        if 'id_aktif_hp' in st.session_state: del st.session_state.id_aktif_hp
                        st.rerun()

# ==========================================
# 3. MENU: REKAP & GRAFIK
# ==========================================
elif st.session_state.menu_aktif == 'rekap':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 8px;'>📊 Rekap Keuangan & Grafik</p>", unsafe_allow_html=True)
    
    if df_trans.empty:
        st.info("Belum ada data untuk direkap.")
    else:
        col_r1, col_r2 = st.columns(2)
        with col_r1: rekap_awal = st.date_input("Dari", df_trans['tanggal'].min(), key="rk_awal", format="DD-MM-YYYY")
        with col_r2: rekap_akhir = st.date_input("Sampai", df_trans['tanggal'].max(), key="rk_akhir", format="DD-MM-YYYY")
        
        df_rekap = df_trans[(df_trans['tanggal'] >= rekap_awal) & (df_trans['tanggal'] <= rekap_akhir)]
        
        if df_rekap.empty:
            st.warning("Tidak ada transaksi pada rentang tanggal tersebut.")
        else:
            df_pie = df_rekap[df_rekap['jenis'] == 'Pengeluaran'].groupby('kategori')['jumlah'].sum().reset_index()
            
            if df_pie.empty:
                st.info("Tidak ada data pengeluaran pada rentang waktu ini.")
            else:
                fig = px.pie(
                    df_pie, 
                    values='jumlah', 
                    names='kategori', 
                    title="Proporsi Pengeluaran",
                    color_discrete_sequence=px.colors.sequential.OrRd_r
                )
                fig.update_layout(
                    margin=dict(l=20, r=20, t=40, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                fig.update_traces(
                    textposition='inside',
                    insidetextanchor='middle',
                    textfont=dict(size=9, color='white', weight='bold')
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# 4. MENU: UNDUH LAPORAN (PDF)
# ==========================================
elif st.session_state.menu_aktif == 'unduh':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 8px;'>📥 Unduh Laporan PDF</p>", unsafe_allow_html=True)
    
    if df_trans.empty:
        st.info("Belum ada data transaksi yang bisa diunduh.")
    else:
        col_d1, col_d2 = st.columns(2)
        with col_d1: tgl_awal = st.date_input("Mulai Tanggal", df_trans['tanggal'].min(), key="eks_awal", format="DD-MM-YYYY")
        with col_d2: tgl_akhir = st.date_input("Sampai Tanggal", df_trans['tanggal'].max(), key="eks_akhir", format="DD-MM-YYYY")
        
        df_filter = df_trans[(df_trans['tanggal'] >= tgl_awal) & (df_trans['tanggal'] <= tgl_akhir)].sort_values('tanggal', ascending=True)
        
        st.markdown(f"<div style='font-size:11px; opacity:0.8; margin-bottom:10px;'>Ditemukan <b>{len(df_filter)}</b> transaksi dalam periode cetak.</div>", unsafe_allow_html=True)
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            waktu_cetak = datetime.now().strftime("%d-%m-%Y %H:%M")
            
            with col_b2:
                buffer_pdf = io.BytesIO()
                doc = SimpleDocTemplate(buffer_pdf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=40, bottomMargin=40)
                story = []
                
                styles = getSampleStyleSheet()
                
                title_style = ParagraphStyle(
                    name='TitleStyle', 
                    fontName='Helvetica-Bold', 
                    fontSize=16, 
                    textColor=colors.HexColor('#8B0000'), 
                    alignment=1, 
                    spaceAfter=4
                )
                
                meta_style = ParagraphStyle(name='MetaStyle', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor('#666666'), alignment=2)
                sub_style = ParagraphStyle(name='SubStyle', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#444444'), alignment=1, spaceAfter=20)
                header_style = ParagraphStyle(name='HeaderStyle', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, leading=10, alignment=1)
                
                cell_style = ParagraphStyle(name='CellStyle', fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor('#333333'))
                cell_center = ParagraphStyle(name='CellCenter', fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor('#333333'), alignment=1)
                
                story.append(Paragraph(f"Waktu Cetak: {waktu_cetak}", meta_style))
                story.append(Spacer(1, 10))
                
                story.append(Paragraph("LAPORAN MUTASI KEUANGAN KEI", title_style))
                story.append(Paragraph(f"Periode Laporan: {tgl_awal.strftime('%d-%m-%Y')} s/d {tgl_akhir.strftime('%d-%m-%Y')}", sub_style))
                
                table_data = [[
                    Paragraph("TANGGAL", header_style), 
                    Paragraph("ALIRAN", header_style), 
                    Paragraph("WALLET", header_style), 
                    Paragraph("KATEGORI", header_style), 
                    Paragraph("NOMINAL", header_style), 
                    Paragraph("REIMBURSE", header_style), 
                    Paragraph("KETERANGAN", header_style)
                ]]
                
                for _, row in df_filter.iterrows():
                    txt_jenis = "Masuk" if row['jenis'] == "Pemasukan" else "Keluar"
                    tgl_str = row['tanggal'].strftime('%d-%m-%Y')
                    
                    color_nominal = colors.HexColor('#2E7D32') if row['jenis'] == "Pemasukan" else colors.HexColor('#C62828')
                    cell_nominal_style = ParagraphStyle(name='CellNominal', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=color_nominal)
                    
                    table_data.append([
                        Paragraph(tgl_str, cell_center),
                        Paragraph(txt_jenis, cell_center),
                        Paragraph(str(row['wallet']), cell_style),
                        Paragraph(str(row['kategori']), cell_style),
                        Paragraph(f"Rp {row['jumlah']:,.0f}", cell_nominal_style),
                        Paragraph(str(row.get('reimburse', 'Tidak')), cell_center),
                        Paragraph(str(row['keterangan'] or '-'), cell_style)
                    ])
                
                col_widths = [60, 45, 65, 95, 75, 60, 140]
                t = Table(table_data, colWidths=col_widths, repeatRows=1)
                
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8B0000')),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN', (0,0), (-1,0), 'CENTER'),
                    ('LINEBELOW', (0,0), (-1,0), 1.5, colors.HexColor('#5A0000')),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E5E5')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')]),
                    ('TOPPADDING', (0,0), (-1,-1), 7),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 7),
                    ('LEFTPADDING', (0,0), (-1,-1), 5),
                    ('RIGHTPADDING', (0,0), (-1,-1), 5),
                ]))
                story.append(t)
                doc.build(story, canvasmaker=canvas.Canvas)
                
            st.download_button(
                label="📥 Unduh PDF Sekarang",
                data=buffer_pdf.getvalue(),
                file_name=f"Laporan_Keuangan_Kei_{tgl_awal.strftime('%d%m%Y')}_{tgl_akhir.strftime('%d%m%Y')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# ==========================================
# 5. MENU: WALLET
# ==========================================
elif st.session_state.menu_aktif == 'wallet':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 8px;'>💳 Sisa Saldo per Wallet</p>", unsafe_allow_html=True)
    
    wallet_html = "<div style='display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-start;'>"
    for w_name in LIST_WALLET:
        w_bal = wallet_balances.get(w_name, 0)
        
        if w_bal < 0:
            border_c = "#c62828"
            bg_c = "rgba(198, 40, 40, 0.1)"
            text_c = "#c62828"
        else:
            border_c = "#B8860B"
            bg_c = "rgba(184, 134, 11, 0.08)"
            text_c = "inherit"
            
        wallet_html += f"""
            <div style='flex: 1; min-width: 90px; max-width: 110px; border: 1px solid {border_c}; background-color: {bg_c}; padding: 6px; border-radius: 6px; text-align: center;'>
                <p style='margin: 0; font-size: 9px; font-weight: bold; opacity: 0.7; color: var(--text-color);'>{w_name}</p>
                <p style='margin: 2px 0 0 0; font-size: 11px; font-weight: 800; color: {text_c if w_bal < 0 else "#B8860B"};'>Rp {w_bal:,.0f}</p>
            </div>
        """
    wallet_html += "</div>"
    st.markdown(wallet_html, unsafe_allow_html=True)
