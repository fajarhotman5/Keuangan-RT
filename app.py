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

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Keuangan Kei", page_icon="💰", layout="centered")

# Custom CSS Responsif & Pembersihan Elemen Pengganggu
st.markdown("""
    <style>
    /* 1. Pembersihan total simbol/lambang link */
    .stApp a.element-header-anchor, 
    a.element-header-anchor, 
    .stMarkdown a, 
    [data-testid="stMarkdownContainer"] a.element-header-anchor {
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
    footer { display: none !important; }
    header { display: none !important; }
    
    /* TOMBOL NAVIGASI MENU JADI LEBIH REPIH & COMPACT (KAPSUL MODERN) */
    div.stButton > button {
        background-color: #8B0000 !important;
        color: #FFFFFF !important;
        border: 1px solid #8B0000 !important;
        border-radius: 6px !important; /* Mengubah tombol jadi kapsul estetik */
        padding: 4px 6px !important; /* Lebih tipis */
        font-weight: bold !important;
        font-size: 11px !important; /* Huruf kompak khusus mobile */
        height: auto !important;
        min-height: unset !important;
    }
    div.stButton > button:hover {
        background-color: #000000 !important;
        color: #FFD700 !important;
        border-color: #FFD700 !important;
    }

    div[data-testid="stForm"] {
        border: 1px solid #8B0000 !important;
        border-radius: 10px;
        padding: 12px;
    }

    /* DESAIN TABEL MINIMALIS KRISPI (12px - 13px untuk HP) */
    .table-container {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        margin-top: 5px;
        margin-bottom: 15px;
    }
    .custom-table {
        width: 100%;
        min-width: 600px;
        border-collapse: collapse;
        font-size: 12px;
    }
    .custom-table th {
        background-color: transparent;
        color: #8B0000;
        font-weight: 700;
        padding: 8px 6px;
        border-bottom: 2px solid #8B0000;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.5px;
    }
    .custom-table td {
        padding: 8px 6px;
        border-bottom: 1px solid rgba(139, 0, 0, 0.15);
        color: inherit !important; 
    }
    .badge-masuk { color: #2e7d32; font-weight: bold; }
    .badge-keluar { color: #c62828; font-weight: bold; }

    /* Atur teks input dan caption bawaan agar lebih ringkas */
    .stTabs [data-baseweb="tab"] { font-size: 12px !important; padding: 8px 12px !important; }
    label[data-testid="stWidgetLabel"] p { font-size: 12px !important; font-weight: bold; }
    
    @media (max-width: 768px) {
        .header-title { font-size: 24px !important; }
        .header-subtitle { font-size: 11px !important; }
        div[data-testid="stForm"] { padding: 8px; }
    }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
def get_connection(db_name="keuangan_rt"):
    ca_data = st.secrets["db"]["ca_data"]
    return pymysql.connect(
        host=st.secrets["db"]["host"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database=db_name,
        port=4000,
        ssl={'cadata': ca_data}
    )

@st.cache_resource
def init_db():
    conn = get_connection(db_name="sys")
    with conn.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS keuangan_rt")
        cursor.execute("USE keuangan_rt")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaksi (
                id_transaksi INT AUTO_INCREMENT PRIMARY KEY,
                jenis ENUM('Pemasukan', 'Pengeluaran') NOT NULL,
                tanggal DATE NOT NULL,
                wallet VARCHAR(30) NOT NULL,
                kategori VARCHAR(50) NOT NULL,
                jumlah BIGINT NOT NULL DEFAULT 0,
                reimburse VARCHAR(10) NOT NULL DEFAULT 'Tidak',
                keterangan TEXT
            )
        """)
        cursor.execute("SHOW COLUMNS FROM transaksi LIKE 'reimburse'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE transaksi ADD COLUMN reimburse VARCHAR(10) NOT NULL DEFAULT 'Tidak' AFTER jumlah")
    conn.commit()
    conn.close()

init_db()

# --- VALID LISTS ---
LIST_WALLET = ['Cash', 'Dana', 'Gopay', 'Jago', 'Mandiri', 'OVO', 'ShopeePay']
KAT_PENGELUARAN = ['Makanan & Minuman', 'Jajan', 'Listrik, Air & Internet', 'Belanja Bulanan', 'Transportasi & Bensin', 'Hiburan', 'Lain-lain']
KAT_PEMASUKAN = ['Gapok', 'Tukin', 'Lainnya']
ALL_KATEGORI = list(set(KAT_PENGELUARAN + KAT_PEMASUKAN))

# --- JUDUL UTAMA & SUB-JUDUL TEMA BARU (SINKRON, MEPET & ANTI TUMPANG TINDIH) ---
st.markdown("""
    <div style='text-align: center; margin-bottom: 15px;'>
        <div style='font-size: 20px; font-weight: 800; color: #8B0000; letter-spacing: 0.5px; margin: 0; padding: 0; line-height: 1.2;'>Informasi Keuangan Kei</div>
        <div style='font-size: 13px; color: var(--text-color); font-weight: 500; opacity: 0.75; letter-spacing: 0.3px; margin-top: 2px; padding: 0;'>HARUS CATAT SETIAP SAAT</div>
    </div>
""", unsafe_allow_html=True)

# --- DATA FETCHING ---
conn = get_connection()
df_trans = pd.read_sql("SELECT * FROM transaksi ORDER BY tanggal DESC, id_transaksi DESC", conn)
conn.close()

if not df_trans.empty:
    df_trans['tanggal'] = pd.to_datetime(df_trans['tanggal']).dt.date
    total_masuk = df_trans[df_trans['jenis'] == 'Pemasukan']['jumlah'].sum()
    total_keluar = df_trans[df_trans['jenis'] == 'Pengeluaran']['jumlah'].sum()
    sisa_saldo = total_masuk - total_keluar
    
    wallet_balances = {}
    for w in LIST_WALLET:
        w_masuk = df_trans[(df_trans['wallet'] == w) & (df_trans['jenis'] == 'Pemasukan')]['jumlah'].sum()
        w_keluar = df_trans[(df_trans['wallet'] == w) & (df_trans['jenis'] == 'Pengeluaran')]['jumlah'].sum()
        wallet_balances[w] = w_masuk - w_keluar
else:
    sisa_saldo = 0
    total_keluar = 0
    wallet_balances = {w: 0 for w in LIST_WALLET}

# --- KARTU METRIK UTAMA (KEMBAR MAROON PREMIUM) ---
st.markdown(f"""
    <div style='display: flex; gap: 8px; margin-bottom: 12px;'>
        <div style='flex: 1; padding: 8px 6px; border-radius: 12px; text-align: center; background-color: #8B0000; border: 1.5px solid #8B0000; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
            <p style='margin: 0; font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.9); letter-spacing: 0.3px;'>Sisa Saldo Berjalan</p>
            <h3 style='margin: 2px 0 0 0; font-size: 15px; font-weight: 800; color: #FFFFFF;'>Rp {sisa_saldo:,.0f}</h3>
        </div>
        <div style='flex: 1; padding: 8px 6px; border-radius: 12px; text-align: center; background-color: #8B0000; border: 1.5px solid #8B0000; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
            <p style='margin: 0; font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.9); letter-spacing: 0.3px;'>Total Pengeluaran</p>
            <h3 style='margin: 2px 0 0 0; font-size: 15px; font-weight: 800; color: #FFFFFF;'>Rp {total_keluar:,.0f}</h3>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- NAVIGASI MENU ---
if 'menu_aktif' not in st.session_state:
    st.session_state.menu_aktif = None

col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
with col_m1:
    if st.button("➕ Tambah", use_container_width=True): st.session_state.menu_aktif = 'tambah'
with col_m2:
    if st.button("📥 Unduh", use_container_width=True): st.session_state.menu_aktif = 'unduh'
with col_m3:
    if st.button("📋 Riwayat", use_container_width=True): st.session_state.menu_aktif = 'riwayat'
with col_m4:
    if st.button("📊 Rekap", use_container_width=True): st.session_state.menu_aktif = 'rekap'
with col_m5:
    if st.button("💳 Wallet", use_container_width=True): st.session_state.menu_aktif = 'wallet'

st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px; border-color: #8B0000;'>", unsafe_allow_html=True)

# ==========================================
# LOGIKA KONTEN MENU APPLICATION
# ==========================================

# 1. MENU: TAMBAH
if st.session_state.menu_aktif == 'tambah':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 5px;'>➕ Tambah Transaksi Baru</p>", unsafe_allow_html=True)
    jenis_tx = st.radio("Pilih Jenis Aliran Dana:", ["Pengeluaran", "Pemasukan"], horizontal=True)
    
    with st.form("form_transaksi", clear_on_submit=True):
        tgl = st.date_input("Tanggal Transaksi", datetime.now())
        wlt = st.selectbox("Pilih Wallet / Dompet", LIST_WALLET)
        kat = st.selectbox("Kategori", KAT_PENGELUARAN if jenis_tx == "Pengeluaran" else KAT_PEMASUKAN)
        jml = st.number_input("Jumlah Nominal (Rp)", min_value=0, step=1000)
        
        if jenis_tx == "Pengeluaran":
            remb = st.radio("Reimburse:", ["Tidak", "Ya"], horizontal=True)
        else:
            remb = "Tidak"
            
        ket = st.text_input("Keterangan Tambahan")
        simpan = st.form_submit_button("Simpan Catatan")
        
        if simpan:
            if jml > 0:
                conn = get_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO transaksi (jenis, tanggal, wallet, kategori, jumlah, reimburse, keterangan) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (jenis_tx, tgl, wlt, kat, jml, remb, ket)
                    )
                conn.commit()
                conn.close()
                st.success("Data berhasil disimpan!")
                st.rerun()
            else:
                st.error("Jumlah input harus lebih besar dari Rp 0!")

# 2. MENU: UNDUH
elif st.session_state.menu_aktif == 'unduh':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 10px;'>📥 Ekspor Laporan Dokumen</p>", unsafe_allow_html=True)
    if df_trans.empty:
        st.info("Tidak ada data transaksi.")
    else:
        col_d1, col_d2 = st.columns(2)
        with col_d1: tgl_awal = st.date_input("Mulai Tanggal", df_trans['tanggal'].min(), key="eks_awal")
        with col_d2: tgl_akhir = st.date_input("Sampai Tanggal", df_trans['tanggal'].max(), key="eks_akhir")
            
        df_filter = df_trans[(df_trans['tanggal'] >= tgl_awal) & (df_trans['tanggal'] <= tgl_akhir)].copy()
        
        if df_filter.empty:
            st.warning("Data kosong untuk rentang tanggal tersebut.")
        else:
            waktu_wib = datetime.now() + timedelta(hours=7)
            waktu_cetak = waktu_wib.strftime("%d-%m-%Y %H:%M WIB")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                df_excel = df_filter.copy()
                df_excel['tanggal'] = pd.to_datetime(df_excel['tanggal']).dt.strftime('%d-%m-%Y')
                
                buffer_xl = io.BytesIO()
                with pd.ExcelWriter(buffer_xl, engine='openpyxl') as writer:
                    df_excel.to_excel(writer, index=False, sheet_name='Laporan Keuangan')
                st.download_button(
                    label="🟢 Unduh File Excel",
                    data=buffer_xl.getvalue(),
                    file_name=f"Laporan_Keuangan_{tgl_awal.strftime('%d-%m-%Y')}_{tgl_akhir.strftime('%d-%m-%Y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with col_b2:
                buffer_pdf = io.BytesIO()
                doc = SimpleDocTemplate(buffer_pdf, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=35, bottomMargin=35)
                story = []
                
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(name='TitleStyle', fontName='Helvetica-Bold', fontSize=15, textColor=colors.HexColor('#8B0000'), spaceAfter=2)
                meta_style = ParagraphStyle(name='MetaStyle', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor('#666666'), alignment=2)
                sub_style = ParagraphStyle(name='SubStyle', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#333333'), spaceAfter=15)
                
                header_style = ParagraphStyle(name='HeaderStyle', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, leading=10)
                cell_style = ParagraphStyle(name='CellStyle', fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor('#222222'))
                cell_style_bold = ParagraphStyle(name='CellStyleBold', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=colors.HexColor('#222222'))
                
                story.append(Paragraph(f"Waktu Cetak: {waktu_cetak}", meta_style))
                story.append(Paragraph("LAPORAN MUTASI KEUANGAN KEI", title_style))
                story.append(Paragraph(f"Periode Laporan: {tgl_awal.strftime('%d-%m-%Y')} s/d {tgl_akhir.strftime('%d-%m-%Y')}", sub_style))
                
                table_data = [[
                    Paragraph("TANGGAL", header_style), Paragraph("ALIRAN", header_style), Paragraph("WALLET", header_style), 
                    Paragraph("KATEGORI", header_style), Paragraph("NOMINAL", header_style), Paragraph("REIMBURSE", header_style), 
                    Paragraph("KETERANGAN", header_style)
                ]]
                
                for _, row in df_filter.iterrows():
                    txt_jenis = "Masuk" if row['jenis'] == "Pemasukan" else "Keluar"
                    tgl_str = row['tanggal'].strftime('%d-%m-%Y')
                    
                    table_data.append([
                        Paragraph(tgl_str, cell_style),
                        Paragraph(txt_jenis, cell_style),
                        Paragraph(str(row['wallet']), cell_style),
                        Paragraph(str(row['kategori']), cell_style),
                        Paragraph(f"Rp {row['jumlah']:,.0f}", cell_style_bold),
                        Paragraph(str(row.get('reimburse', 'Tidak')), cell_style),
                        Paragraph(str(row['keterangan'] or '-'), cell_style)
                    ])
                
                col_widths = [62, 48, 65, 95, 75, 60, 147]
                t = Table(table_data, colWidths=col_widths, repeatRows=1)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8B0000')),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E5E5')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#FAFAFA')]),
                    ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)
                ]))
                story.append(t)
                doc.build(story, canvasmaker=canvas.Canvas)
                st.download_button(
                    label="🔴 Unduh File PDF", 
                    data=buffer_pdf.getvalue(), 
                    file_name=f"Laporan_Keuangan_{tgl_awal.strftime('%d-%m-%Y')}_{tgl_akhir.strftime('%d-%m-%Y')}.pdf", 
                    mime="application/pdf", 
                    use_container_width=True
                )

# 3. MENU: RIWAYAT (AKSI CEPAT DI ATAS - SEMPURNA DI LAPTOP & HP)
elif st.session_state.menu_aktif == 'riwayat':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 5px;'>📋 Riwayat Buku Kas</p>", unsafe_allow_html=True)
    if df_trans.empty:
        st.info("Belum ada mutasi transaksi.")
    else:
        # 1. KOLOM PENCARIAN (TETAP DI ATAS)
        cari = st.text_input("🔍 Cari Kategori / Keterangan:", key="cari_riwayat")
        df_tampil = df_trans.copy()
        if cari:
            df_tampil = df_tampil[df_tampil['kategori'].str.contains(cari, case=False, na=False) | df_tampil['keterangan'].str.contains(cari, case=False, na=False)]
        
        # ==========================================
        # 2. PANEL UTALITAS AKSI (PINDAH KE ATAS - ANTI SCROLL JAUH)
        # ==========================================
        st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 12px; margin-top: 10px; margin-bottom: 2px;'>⚡ Aksi Cepat Transaksi</p>", unsafe_allow_html=True)
        opsi_pilih = {row['id_transaksi']: f"#{row['id_transaksi']} - {row['kategori']} (Rp {row['jumlah']:,.0f})" for _, row in df_tampil.iterrows()}
        
        if opsi_pilih:
            col_action1, col_action2 = st.columns([3, 2])
            with col_action1:
                id_terpilih = st.selectbox("Pilih ID Transaksi:", options=list(opsi_pilih.keys()), format_func=lambda x: opsi_pilih[x], label_visibility="collapsed")
            with col_action2:
                mode_aksi = st.selectbox("Pilih Tindakan:", ["Pilih...", "📝 Edit", "🗑️ Hapus"], label_visibility="collapsed")
            
            if id_terpilih and mode_aksi != "Pilih...":
                data_row = df_trans[df_trans['id_transaksi'] == id_terpilih].iloc[0]
                
                if mode_aksi == "📝 Edit":
                    with st.form("form_cepat_edit_universal"):
                        st.markdown(f"<p style='color: #B8860B; font-weight: bold; font-size: 12px;'>📝 Edit Data #{id_terpilih}</p>", unsafe_allow_html=True)
                        new_tgl = st.date_input("Tanggal", data_row['tanggal'])
                        new_jenis = st.selectbox("Jenis", ["Pemasukan", "Pengeluaran"], index=["Pemasukan", "Pengeluaran"].index(data_row['jenis']))
                        new_wallet = st.selectbox("Wallet", LIST_WALLET, index=LIST_WALLET.index(data_row['wallet']))
                        list_kat_opsi = KAT_PEMASUKAN if new_jenis == "Pemasukan" else KAT_PENGELUARAN
                        if data_row['kategori'] not in list_kat_opsi: list_kat_opsi = list_kat_opsi + [data_row['kategori']]
                        new_kat = st.selectbox("Kategori", list_kat_opsi, index=list_kat_opsi.index(data_row['kategori']))
                        new_jml = st.number_input("Nominal (Rp)", min_value=0, value=int(data_row['jumlah']), step=1000)
                        new_remb = st.radio("Reimburse:", ["Tidak", "Ya"], index=["Tidak", "Ya"].index(data_row.get('reimburse', 'Tidak')), horizontal=True)
                        new_ket = st.text_input("Keterangan", value=data_row['keterangan'] if data_row['keterangan'] else "")
                        
                        col_ef1, col_ef2 = st.columns(2)
                        with col_ef1:
                            if st.form_submit_button("Simpan", use_container_width=True):
                                conn = get_connection()
                                with conn.cursor() as cursor:
                                    cursor.execute("UPDATE transaksi SET tanggal=%s, jenis=%s, wallet=%s, kategori=%s, jumlah=%s, reimburse=%s, keterangan=%s WHERE id_transaksi=%s",
                                                   (new_tgl, new_jenis, new_wallet, new_kat, new_jml, new_remb, new_ket, id_terpilih))
                                conn.commit(); conn.close()
                                st.success("Berhasil diubah!"); st.rerun()
                        with col_ef2:
                            if st.form_submit_button("Batal", use_container_width=True):
                                st.rerun()
                                
                elif mode_aksi == "🗑️ Hapus":
                    st.markdown(f"<div style='background-color:rgba(198,40,40,0.1); padding:8px; border-radius:6px; border:1px solid #c62828; margin-bottom:8px; font-size:11px; color:#c62828;'>Hapus data <b>{data_row['kategori']} (Rp {data_row['jumlah']:,.0f})</b>?</div>", unsafe_allow_html=True)
                    col_del1, col_del2 = st.columns(2)
                    with col_del1:
                        if st.button("🔴 Ya, Hapus", key="confirm_del_universal", use_container_width=True):
                            conn = get_connection()
                            with conn.cursor() as cursor: cursor.execute("DELETE FROM transaksi WHERE id_transaksi=%s", (id_terpilih,))
                            conn.commit(); conn.close()
                            st.success("Terhapus!"); st.rerun()
                    with col_del2:
                        if st.button("Batal", key="cancel_del_universal", use_container_width=True):
                            st.rerun()

        st.markdown("<hr style='border-top: 1px solid rgba(139, 0, 0, 0.15); margin: 12px 0;'>", unsafe_allow_html=True)

        # Inject CSS khusus untuk tabel & kartu (Rapat Kiri & Anti Rewel)
        st.markdown("""
            <style>
            /* Tampilan Desktop (Laptop) */
            .desktop-table-container { display: block; width: 100%; margin-bottom: 15px; }
            .mobile-card-container { display: none; }
            
            .custom-table-v2 { width: 100%; border-collapse: collapse; font-size: 12px; }
            .custom-table-v2 th { color: #8B0000; font-weight: 700; padding: 8px; border-bottom: 2px solid #8B0000; text-align: left; }
            .custom-table-v2 td { padding: 8px; border-bottom: 1px solid rgba(139, 0, 0, 0.15); }
            
            /* Tampilan Khusus Mobile (HP) */
            @media (max-width: 768px) {
                .desktop-table-container { display: none !important; }
                .mobile-card-container { display: block; }
                
                .tx-card {
                    background: transparent;
                    border: 1px solid rgba(139, 0, 0, 0.2);
                    border-radius: 8px;
                    padding: 10px;
                    margin-bottom: 8px;
                }
                .tx-card-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
                .tx-card-title { font-weight: 700; font-size: 13px; color: inherit; }
                .tx-card-meta { font-size: 11px; color: #666; }
                .tx-card-price { font-weight: 800; font-size: 13px; }
            }
            </style>
        """, unsafe_allow_html=True)

        # ==========================================
        # LAYOUT 1: TAMPILAN LAPTOP (TABEL ELEGAN)
        # ==========================================
        html_desktop_rows = ""
        for index, row in df_tampil.iterrows():
            tgl_str = row['tanggal'].strftime('%d-%m-%Y')
            color_p = "#2e7d32" if row['jenis'] == "Pemasukan" else "#c62828"
            sign_p = "+" if row['jenis'] == "Pemasukan" else "-"
            ket_str = row['keterangan'] if row['keterangan'] else "-"
            
            html_desktop_rows += f"<tr><td>{tgl_str}</td><td>{row['wallet']}</td><td>{row['kategori']}</td><td style='color:{color_p}; font-weight:700;'>{sign_p}Rp {row['jumlah']:,.0f}</td><td>{row.get('reimburse', 'Tidak')}</td><td>{ket_str}</td><td style='font-weight:bold; color:#B8860B;'>#{row['id_transaksi']}</td></tr>"
            
        desktop_html = f"<div class='desktop-table-container'><table class='custom-table-v2'><thead><tr><th>Tanggal</th><th>Wallet</th><th>Kategori</th><th>Nominal</th><th>Reimburse</th><th>Keterangan</th><th>ID</th></tr></thead><tbody>{html_desktop_rows}</tbody></table></div>"
        st.markdown(desktop_html, unsafe_allow_html=True)

        # ==========================================
        # LAYOUT 2: TAMPILAN HP (KARTU COMPACT ANTI PECAH)
        # ==========================================
        html_mobile_cards = ""
        for index, row in df_tampil.iterrows():
            tgl_mini = row['tanggal'].strftime('%d-%m-%Y')
            color_p = "#2e7d32" if row['jenis'] == "Pemasukan" else "#c62828"
            sign_p = "+" if row['jenis'] == "Pemasukan" else "-"
            rmb_badge = " [Rmb]" if row.get('reimburse', 'Tidak') == "Ya" else ""
            
            html_mobile_cards += f"<div class='tx-card'><div class='tx-card-row'><span class='tx-card-title'>{row['kategori']}<span style='color:#c62828; font-size:10px;'>{rmb_badge}</span></span><span class='tx-card-price' style='color:{color_p};'>{sign_p}Rp {row['jumlah']:,.0f}</span></div><div class='tx-card-row' style='margin-bottom:0;'><span class='tx-card-meta'>📅 {tgl_mini} | 💳 {row['wallet']}</span><span class='tx-card-meta' style='font-weight:bold; color:#B8860B;'>#{row['id_transaksi']}</span></div></div>"
            
        st.markdown(f"<div class='mobile-card-container'>{html_mobile_cards}</div>", unsafe_allow_html=True)
# 4. MENU: REKAP
elif st.session_state.menu_aktif == 'rekap':
    st.markdown("<p style='color: #8B0000; font-weight: bold; margin-bottom: 5px; font-size: 14px;'>📊 Rekap Ringkas Data</p>", unsafe_allow_html=True)
    if df_trans.empty:
        st.info("Belum ada data transaksi.")
    else:
        col_r1, col_r2 = st.columns(2)
        with col_r1: rekap_awal = st.date_input("Dari", df_trans['tanggal'].min(), key="rk_awal")
        with col_r2: rekap_akhir = st.date_input("Sampai", df_trans['tanggal'].max(), key="rk_akhir")
            
        df_rk = df_trans[(df_trans['tanggal'] >= rekap_awal) & (df_trans['tanggal'] <= rekap_akhir)].copy()
        if df_rk.empty:
            st.warning("Data kosong pada periode ini.")
        else:
            rk_masuk = df_rk[df_rk['jenis'] == 'Pemasukan']['jumlah'].sum()
            rk_keluar = df_rk[df_rk['jenis'] == 'Pengeluaran']['jumlah'].sum()
            
            st.markdown(f"""
                <div style='padding: 5px 0; font-size: 12px; border-bottom: 1px solid #EEE; margin-bottom: 10px;'>
                    🟢 <b>Masuk:</b> <span style='color:#2e7d32;'>Rp {rk_masuk:,.0f}</span> | 
                    🔴 <b>Keluar:</b> <span style='color:#c62828;'>Rp {rk_keluar:,.0f}</span>
                </div>
            """, unsafe_allow_html=True)
                
            tab_wlt, tab_kat, tab_rmb = st.tabs(["💳 Wallet", "🗂️ Kategori", "🔄 Reimburse"])
            with tab_wlt:
                df_wlt = df_rk.groupby(['wallet', 'jenis'])['jumlah'].sum().unstack(fill_value=0).reset_index()
                for _, r in df_wlt.iterrows():
                    st.markdown(f"<p style='margin:0; font-size:12px;'>• <b>{r['wallet']}</b>: <span style='color:#2e7d32;'>+{r.get('Pemasukan',0):,.0f}</span> | <span style='color:#c62828;'>-{r.get('Pengeluaran',0):,.0f}</span></p>", unsafe_allow_html=True)
            with tab_kat:
                df_kat = df_rk.groupby(['kategori', 'jenis'])['jumlah'].sum().reset_index()
                for _, r in df_kat.sort_values(by='jumlah', ascending=False).iterrows():
                    warna_k = "#2e7d32" if r['jenis'] == 'Pemasukan' else "#c62828"
                    st.markdown(f"<p style='margin:0; font-size:12px;'>• [{r['jenis'][:3]}] {r['kategori']}: <span style='color:{warna_k}; font-weight:bold;'>Rp {r['jumlah']:,.0f}</span></p>", unsafe_allow_html=True)
            with tab_rmb:
                df_rmb = df_rk[df_rk['jenis'] == 'Pengeluaran'].groupby('reimburse')['jumlah'].sum().reset_index()
                st.markdown(f"<p style='margin:0; font-size:12px;'>• <b>Reimburse (Ya):</b> <span style='color:#c62828; font-weight:bold;'>Rp {df_rmb[df_rmb['reimburse']=='Ya']['jumlah'].sum():,.0f}</span></p>", unsafe_allow_html=True)
                st.markdown(f"<p style='margin:0; font-size:12px;'>• <b>Pribadi (Tidak):</b> Rp {df_rmb[df_rmb['reimburse']=='Tidak']['jumlah'].sum():,.0f}</p>", unsafe_allow_html=True)

            st.markdown("<p style='font-size: 12px; font-weight: bold; color: #8B0000; margin-top: 15px; margin-bottom: 2px;'>📊 Tren Pengeluaran</p>", unsafe_allow_html=True)
            df_chart_rk = df_rk[df_rk['jenis'] == 'Pengeluaran'].groupby('kategori')['jumlah'].sum().reset_index()
            if df_chart_rk.empty:
                st.caption("Tidak ada grafik pengeluaran.")
            else:
                # Urut dari yang terbesar
                df_chart_rk = df_chart_rk.sort_values(by='jumlah', ascending=False)
                
                # FUNGSI PANGKAS TEKS KATEGORI KHUSUS MOBILE (MAKS 12 CHAR)
                def trim_text(text):
                    if len(text) > 12:
                        return text[:10] + "..."
                    return text
                
                # Buat kolom baru khusus untuk label sumbu X
                df_chart_rk['kategori_mini'] = df_chart_rk['kategori'].apply(trim_text)
                
                # --- UPDATE GRAFIK (PALET GELAP & LABEL KRISPI) ---
                fig = px.bar(
                    df_chart_rk, 
                    x='kategori_mini',  # Gunakan label teks yang sudah dipangkas
                    y='jumlah', 
                    text='jumlah',
                    color='kategori', 
                    # Ganti ke palet warna-warni yang tone-nya agak gelap dikit (elegan)
                    color_discrete_sequence=px.colors.qualitative.Dark24
                )
                
                fig.update_layout(
                    xaxis_title=None, 
                    yaxis_title=None, 
                    margin=dict(t=5, b=25, l=5, r=5), # Beri sedikit ruang bawah untuk label miring
                    height=220, # Tinggi dinaikkan dikit biar tulisan miring muat
                    showlegend=False, # Sembunyikan legenda agar pas di HP
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=10),
                    # --- FIX LABEL TULISAN KATEGORI DI HP ---
                    xaxis=dict(
                        tickangle=-30, # Putar teks kategori agar miring ke bawah
                        tickfont=dict(size=9), # Ukuran font tulisan kategori diperkecil dikit
                        automargin=True # Biar Plotly otomatis ngatur jarak margin bawah
                    )
                )
                fig.update_traces(
                    texttemplate='Rp %{text:,.0f}', 
                    textposition='inside',
                    insidetextanchor='middle',
                    textfont=dict(size=9, color='white', weight='bold')
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# 5. MENU: WALLET (RAPAT KIRI - ANTI MARKDOWN CODE BLOCKS)
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
            
        # PENTING: String ini wajib rapat kiri agar tidak memicu deteksi Markdown otomatis
        wallet_html += f"""<div style='border: 1px solid {border_c}; background-color: {bg_c}; padding: 4px 10px; border-radius: 20px; font-size: 12px; display: inline-block;'><span style='font-weight: bold; color: {border_c};'>{w_name}:</span> <span style='color: {text_c}; font-weight: 700;'>Rp {w_bal:,.0f}</span></div>"""
        
    wallet_html += "</div>"
    st.markdown(wallet_html, unsafe_allow_html=True)
