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
    [data-testid="stHeader"] { background: transparent !important; }
    
    /* 2. Navigasi Grid Tombol Atas */
    .nav-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 4px;
        margin-bottom: 15px;
    }
    
    /* TOMBOL NAVIGASI MENU JADI LEBIH KOTAK MODERN (SEMI-SQUARE) */
    div.stButton > button {
        background-color: #8B0000 !important;
        color: #FFFFFF !important;
        border: 1px solid #8B0000 !important;
        border-radius: 6px !important;
        padding: 4px 6px !important; 
        font-weight: bold !important;
        font-size: 11px !important; 
        height: auto !important;
        min-height: unset !important;
    }
    
    /* Gaps Form Spacing */
    [data-testid="stForm"] {
        padding: 10px !important;
        border-radius: 12px !important;
    }
    .stSlider, .stSelectbox, .stNumberInput, .stTextInput, .stDateInput {
        margin-bottom: -10px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
def get_connection():
    db = st.secrets["mysql"]
    return pymysql.connect(
        host=db["host"],
        user=db["user"],
        password=db["password"],
        database=db["database"],
        port=int(db["port"]),
        autocommit=True
    )

# --- MASTER DATA CONFIG ---
LIST_WALLET = ["Cash", "Mandiri", "Jago", "Dana", "Gopay", "OVO", "ShopeePay"]
KAT_PEMASUKAN = ["Gaji Utama", "Tukin", "Bonus & Insentif", "Investasi", "Lainnya"]
KAT_PENGELUARAN = [
    "Makanan & Minuman", "Transportasi & Bensin", "Belanja Bulanan", 
    "Listrik, Air & Internet", "Hiburan & Healing", "Kesehatan & Obat", 
    "Pakaian & Edukasi", "Sedekah & Hadiah", "Cicilan & Hutang", "Lainnya"
]

# --- SESSION STATE FOR NAVIGATION ---
if 'menu_aktif' not in st.session_state:
    st.session_state.menu_aktif = 'tambah'

# --- LOAD REALTIME DATA FROM DB ---
try:
    conn = get_connection()
    df_trans = pd.read_sql("SELECT * FROM transaksi ORDER BY tanggal DESC, id_transaksi DESC", conn)
    conn.close()
    
    # Pastikan tipe data tanggal dibaca dengan benar
    df_trans['tanggal'] = pd.to_datetime(df_trans['tanggal']).dt.date
except Exception as e:
    st.error(f"Gagal memuat database: {e}")
    df_trans = pd.DataFrame()

# --- REALTIME CALCULATION ---
wallet_balances = {w: 0.0 for w in LIST_WALLET}
total_keluar = 0.0

if not df_trans.empty:
    for _, row in df_trans.iterrows():
        amt = float(row['jumlah'])
        if row['jenis'] == 'Pemasukan':
            wallet_balances[row['wallet']] += amt
        else:
            wallet_balances[row['wallet']] -= amt
            total_keluar += amt

sisa_saldo = sum(wallet_balances.values())

# ==========================================
# HEADER: JUDUL UTAMA & METRIK KEMBAR MAROON
# ==========================================
st.markdown("""
    <div style='text-align: center; margin-bottom: 15px;'>
        <div style='font-size: 20px; font-weight: 800; color: #8B0000; letter-spacing: 0.5px; margin: 0; padding: 0; line-height: 1.2;'>Informasi Keuangan Kei</div>
        <div style='font-size: 13px; color: var(--text-color); font-weight: 500; opacity: 0.75; letter-spacing: 0.3px; margin-top: 2px; padding: 0;'>HARUS CATAT SETIAP SAAT</div>
    </div>
""", unsafe_allow_html=True)

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

# ==========================================
# GRID NAVIGASI UTAMA
# ==========================================
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

st.markdown("<hr style='border-top: 1px dashed rgba(139,0,0,0.2); margin: 5px 0 12px 0;'>", unsafe_allow_html=True)

# ==========================================
# ACTIONS: LOGIC TIAP MENU NAVIGASI
# ==========================================

# 1. MENU: TAMBAH TRANSAKSI
if st.session_state.menu_aktif == 'tambah':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 5px;'>➕ Catat Transaksi Baru</p>", unsafe_allow_html=True)
    
    # Fitur Salin Transaksi Terakhir dengan Format Tanggal Indonesia
    id_salin = None
    if not df_trans.empty:
        st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 11px; margin-top: 10px; margin-bottom: 2px;'>📋 Salin dari Transaksi Terakhir (Opsional)</p>", unsafe_allow_html=True)
        opsi_terakhir = {
            row['id_transaksi']: f"{row['tanggal'].strftime('%d-%m-%Y')} | {row['kategori']} (Rp {row['jumlah']:,.0f})" 
            for _, row in df_trans.head(5).iterrows()
        }
        opsi_pilihan = ["Pilih transaksi..."] + list(opsi_terakhir.keys())
        id_salin = st.selectbox("Salin data:", options=opsi_pilihan, format_func=lambda x: opsi_terakhir[x] if x in opsi_terakhir else x, label_visibility="collapsed")

    # Inisialisasi Default Values
    val_tgl = datetime.now().date()
    val_jenis = "Pengeluaran"
    val_wallet = "Cash"
    val_kat = KAT_PENGELUARAN[0]
    val_jml = 0
    val_remb = "Tidak"
    val_ket = ""

    if id_salin and id_salin != "Pilih transaksi...":
        row_salin = df_trans[df_trans['id_transaksi'] == id_salin].iloc[0]
        val_tgl = row_salin['tanggal']
        val_jenis = row_salin['jenis']
        val_wallet = row_salin['wallet']
        val_kat = row_salin['kategori']
        val_jml = int(row_salin['jumlah'])
        val_remb = row_salin.get('reimburse', 'Tidak')
        val_ket = row_salin['keterangan'] if row_salin['keterangan'] else ""

    with st.form("form_tambah_transaksi"):
        c1, c2 = st.columns(2)
        with c1:
            tgl = st.date_input("Tanggal", value=val_tgl)
            jenis = st.selectbox("Jenis", ["Pengeluaran", "Pemasukan"], index=0 if val_jenis == "Pengeluaran" else 1)
        with c2:
            wallet = st.selectbox("Wallet", LIST_WALLET, index=LIST_WALLET.index(val_wallet) if val_wallet in LIST_WALLET else 0)
            list_kat = KAT_PENGELUARAN if jenis == "Pengeluaran" else KAT_PEMASUKAN
            kat = st.selectbox("Kategori", list_kat, index=list_kat.index(val_kat) if val_kat in list_kat else 0)
            
        jumlah = st.number_input("Nominal (Rp)", min_value=0, step=1000, value=val_jml)
        reimburse = st.radio("Reimburse / Tagihan Balik?", ["Tidak", "Ya"], index=0 if val_remb == "Tidak" else 1, horizontal=True)
        keterangan = st.text_input("Keterangan Tambahan", placeholder="Contoh: Makan siang nasi padang", value=val_ket)
        
        if st.form_submit_button("Simpan Transaksi Kas", use_container_width=True):
            if jumlah <= 0:
                st.error("Nominal jumlah transaksi harus lebih besar dari Rp 0!")
            else:
                try:
                    conn = get_connection()
                    with conn.cursor() as cursor:
                        sql = "INSERT INTO transaksi (tanggal, jenis, wallet, kategori, jumlah, reimburse, keterangan) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                        cursor.execute(sql, (tgl, jenis, wallet, kat, jumlah, reimburse, keterangan))
                    conn.commit()
                    conn.close()
                    st.success("Transaksi kas berhasil disimpan ke database!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan ke database: {e}")

# 2. MENU: UNDUH DATA (PDF / EXCEL)
elif st.session_state.menu_aktif == 'unduh':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 5px;'>📥 Unduh Laporan Keuangan</p>", unsafe_allow_html=True)
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        u_tgl_mulai = st.date_input("Mulai Tanggal:", datetime.now().date() - timedelta(days=30))
    with col_u2:
        u_tgl_akhir = st.date_input("Sampai Tanggal:", datetime.now().date())
        
    df_unduh = df_trans[(df_trans['tanggal'] >= u_tgl_mulai) & (df_trans['tanggal'] <= u_tgl_akhir)]
    
    if df_unduh.empty:
        st.warning("Tidak ditemukan transaksi pada rentang tanggal tersebut.")
    else:
        # Preview Tabel dengan Format Tanggal Indonesia
        html_rows = ""
        for index, row in df_unduh.iterrows():
            tgl_preview_str = row['tanggal'].strftime('%d-%m-%Y') if isinstance(row['tanggal'], (datetime, pd.Timestamp, datetime.date)) else str(row['tanggal'])
            color_p = "#2e7d32" if row['jenis'] == "Pemasukan" else "#c62828"
            sign_p = "+" if row['jenis'] == "Pemasukan" else "-"
            ket_p = row['keterangan'] if row['keterangan'] else "-"
            
            html_rows += f"<tr><td>{tgl_preview_str}</td><td>{row['wallet']}</td><td>{row['kategori']}</td><td style='color:{color_p}; font-weight:bold;'>{sign_p}Rp {row['jumlah']:,.0f}</td><td>{row.get('reimburse', 'Tidak')}</td><td>{ket_p}</td></tr>"
            
        st.markdown(f"<div style='max-height:200px; overflow-y:auto; border:1px solid rgba(139,0,0,0.2); border-radius:8px; margin-bottom:12px;'><table style='width:100%; border-collapse:collapse; font-size:11px;'><thead><tr style='background-color:rgba(139,0,0,0.05); color:#8B0000;'><th>Tanggal</th><th>Wallet</th><th>Kategori</th><th>Nominal</th><th>Rmb</th><th>Ket</th></tr></thead><tbody>{html_rows}</tbody></table></div>", unsafe_allow_html=True)
        
        # Tombol Unduh Laporan
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            buffer_excel = io.BytesIO()
            with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                df_unduh.to_excel(writer, index=False, sheet_name='Mutasi Keuangan')
            st.download_button(label="🟢 Download Excel (.xlsx)", data=buffer_excel.getvalue(), file_name=f"Laporan_Keuangan_{u_tgl_mulai}_to_{u_tgl_akhir}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
        with col_btn2:
            buffer_pdf = io.BytesIO()
            doc = SimpleDocTemplate(buffer_pdf, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            story = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#8B0000'), alignment=1, spaceAfter=5)
            meta_style = ParagraphStyle('MetaStyle', parent=styles['Normal'], fontSize=10, leading=14, alignment=1, spaceAfter=15)
            th_style = ParagraphStyle('THStyle', parent=styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Bold', textColor=colors.white)
            td_style = ParagraphStyle('TDStyle', parent=styles['Normal'], fontSize=8, leading=10)
            
            story.append(Paragraph("LAPORAN MUTASI BUKU KAS KEI", title_style))
            story.append(Paragraph(f"Periode: {u_tgl_mulai.strftime('%d-%m-%Y')} s/d {u_tgl_akhir.strftime('%d-%m-%Y')}", meta_style))
            
            pdf_data = [[Paragraph("Tanggal", th_style), Paragraph("Jenis", th_style), Paragraph("Wallet", th_style), Paragraph("Kategori", th_style), Paragraph("Nominal", th_style), Paragraph("Reimburse", th_style)]]
            
            for _, r in df_unduh.iterrows():
                tgl_f = r['tanggal'].strftime('%d-%m-%Y') if isinstance(r['tanggal'], (datetime, pd.Timestamp, datetime.date)) else str(r['tanggal'])
                sign = "+" if r['jenis'] == "Pemasukan" else "-"
                pdf_data.append([
                    Paragraph(tgl_f, td_style),
                    Paragraph(r['jenis'], td_style),
                    Paragraph(r['wallet'], td_style),
                    Paragraph(r['kategori'], td_style),
                    Paragraph(f"{sign}Rp {r['jumlah']:,.0f}", td_style),
                    Paragraph(r.get('reimburse', 'Tidak'), td_style)
                ])
                
            t_style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8B0000')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('TOPPADDING', (0,0), (-1,0), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E0E0E0')),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ])
            
            for idx in range(1, len(pdf_data)):
                bg_color = colors.HexColor('#F9F9F9') if idx % 2 == 0 else colors.white
                t_style.add('BACKGROUND', (0, idx), (-1, idx), bg_color)
                
            col_widths = [60, 65, 65, 110, 85, 60]
            table = Table(pdf_data, colWidths=col_widths)
            table.setStyle(t_style)
            story.append(table)
            
            doc.build(story)
            st.download_button(label="🔴 Download PDF (.pdf)", data=buffer_pdf.getvalue(), file_name=f"Laporan_Keuangan_{u_tgl_mulai}_to_{u_tgl_akhir}.pdf", mime="application/pdf", use_container_width=True)

# 3. MENU: RIWAYAT (AKSI CEPAT DI ATAS & DUAL RESPONSIVE LAYOUT)
elif st.session_state.menu_aktif == 'riwayat':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 5px;'>📋 Riwayat Buku Kas</p>", unsafe_allow_html=True)
    if df_trans.empty:
        st.info("Belum ada mutasi transaksi.")
    else:
        # 1. KOLOM PENCARIAN
        cari = st.text_input("🔍 Cari Kategori / Keterangan:", key="cari_riwayat")
        df_tampil = df_trans.copy()
        if cari:
            df_tampil = df_tampil[df_tampil['kategori'].str.contains(cari, case=False, na=False) | df_tampil['keterangan'].str.contains(cari, case=False, na=False)]
        
        # ==========================================
        # 2. PANEL UTALITAS AKSI DI ATAS
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
            .desktop-table-container { display: block; width: 100%; margin-bottom: 15px; }
            .mobile-card-container { display: none; }
            .custom-table-v2 { width: 100%; border-collapse: collapse; font-size: 12px; }
            .custom-table-v2 th { color: #8B0000; font-weight: 700; padding: 8px; border-bottom: 2px solid #8B0000; text-align: left; }
            .custom-table-v2 td { padding: 8px; border-bottom: 1px solid rgba(139, 0, 0, 0.15); }
            @media (max-width: 768px) {
                .desktop-table-container { display: none !important; }
                .mobile-card-container { display: block; }
                .tx-card { background: transparent; border: 1px solid rgba(139, 0, 0, 0.2); border-radius: 8px; padding: 10px; margin-bottom: 8px; }
                .tx-card-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
                .tx-card-title { font-weight: 700; font-size: 13px; color: inherit; }
                .tx-card-meta { font-size: 11px; color: #666; }
                .tx-card-price { font-weight: 800; font-size: 13px; }
            }
            </style>
        """, unsafe_allow_html=True)

        # LAYOUT 1: DESKTOP TABLE (dd-mm-yyyy)
        html_desktop_rows = ""
        for index, row in df_tampil.iterrows():
            tgl_str = row['tanggal'].strftime('%d-%m-%Y') if isinstance(row['tanggal'], (datetime, pd.Timestamp, datetime.date)) else str(row['tanggal'])
            color_p = "#2e7d32" if row['jenis'] == "Pemasukan" else "#c62828"
            sign_p = "+" if row['jenis'] == "Pemasukan" else "-"
            ket_str = row['keterangan'] if row['keterangan'] else "-"
            html_desktop_rows += f"<tr><td>{tgl_str}</td><td>{row['wallet']}</td><td>{row['kategori']}</td><td style='color:{color_p}; font-weight:700;'>{sign_p}Rp {row['jumlah']:,.0f}</td><td>{row.get('reimburse', 'Tidak')}</td><td>{ket_str}</td><td style='font-weight:bold; color:#B8860B;'>#{row['id_transaksi']}</td></tr>"
            
        desktop_html = f"<div class='desktop-table-container'><table class='custom-table-v2'><thead><tr><th>Tanggal</th><th>Wallet</th><th>Kategori</th><th>Nominal</th><th>Reimburse</th><th>Keterangan</th><th>ID</th></tr></thead><tbody>{html_desktop_rows}</tbody></table></div>"
        st.markdown(desktop_html, unsafe_allow_html=True)

        # LAYOUT 2: MOBILE CARDS (dd-mm-yyyy)
        html_mobile_cards = ""
        for index, row in df_tampil.iterrows():
            tgl_mini = row['tanggal'].strftime('%d-%m') if isinstance(row['tanggal'], (datetime, pd.Timestamp, datetime.date)) else str(row['tanggal'])
            color_p = "#2e7d32" if row['jenis'] == "Pemasukan" else "#c62828"
            sign_p = "+" if row['jenis'] == "Pemasukan" else "-"
            rmb_badge = " [Rmb]" if row.get('reimburse', 'Tidak') == "Ya" else ""
            html_mobile_cards += f"<div class='tx-card'><div class='tx-card-row'><span class='tx-card-title'>{row['kategori']}<span style='color:#c62828; font-size:10px;'>{rmb_badge}</span></span><span class='tx-card-price' style='color:{color_p};'>{sign_p}Rp {row['jumlah']:,.0f}</span></div><div class='tx-card-row' style='margin-bottom:0;'><span class='tx-card-meta'>📅 {tgl_mini} | 💳 {row['wallet']}</span><span class='tx-card-meta' style='font-weight:bold; color:#B8860B;'>#{row['id_transaksi']}</span></div></div>"
            
        st.markdown(f"<div class='mobile-card-container'>{html_mobile_cards}</div>", unsafe_allow_html=True)

# 4. MENU: REKAP MUTASI & GRAFIK PREMIUM (WARNA-WARNI EMAS GELAP & ADAPTIF HP)
elif st.session_state.menu_aktif == 'rekap':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 5px;'>📊 Rekap Keuangan Berkala</p>", unsafe_allow_html=True)
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        tgl_mulai = st.date_input("Mulai:", datetime.now().date() - timedelta(days=7), key="rk_mulai")
    with col_r2:
        tgl_akhir = st.date_input("Sampai:", datetime.now().date(), key="rk_akhir")
        
    df_rk = df_trans[(df_trans['tanggal'] >= tgl_mulai) & (df_trans['tanggal'] <= tgl_akhir)]
    
    if df_rk.empty:
        st.warning("Tidak ada mutasi pada periode ini.")
    else:
        # Kalkulasi subtotal rekap
        rk_masuk = df_rk[df_rk['jenis'] == 'Pemasukan']['jumlah'].sum()
        rk_keluar = df_rk[df_rk['jenis'] == 'Pengeluaran']['jumlah'].sum()
        rk_selisih = rk_masuk - rk_keluar
        
        st.markdown(f"""
            <div style='background-color:rgba(139,0,0,0.03); border:1px solid rgba(139,0,0,0.15); padding:8px; border-radius:10px; font-size:11px; margin-bottom:10px;'>
                🟢 Total Pemasukan: <b>Rp {rk_masuk:,.0f}</b><br>
                🔴 Total Pengeluaran: <b>Rp {rk_keluar:,.0f}</b><br>
                ⚖️ Selisih Arus Kas: <b style='color:{"#2e7d32" if rk_selisih >= 0 else "#c62828"};'>Rp {rk_selisih:,.0f}</b>
            </div>
        """, unsafe_allow_html=True)
        
        # --- TAB RINCIAN LIST MUTASI (dd-mm-yyyy) ---
        tab_kat, tab_wal = st.tabs(["🗂️ Per Kategori", "💳 Per Wallet"])
        
        with tab_kat:
            df_kat = df_rk.groupby(['kategori', 'jenis', 'tanggal'])['jumlah'].sum().reset_index()
            for _, r in df_kat.sort_values(by='tanggal', ascending=False).iterrows():
                tgl_rekap_str = r['tanggal'].strftime('%d-%m-%Y') if isinstance(r['tanggal'], (datetime, pd.Timestamp, datetime.date)) else str(r['tanggal'])
                warna_k = "#2e7d32" if r['jenis'] == 'Pemasukan' else "#c62828"
                st.markdown(f"<p style='margin:0; font-size:12px;'>• <b>{tgl_rekap_str}</b> | [{r['jenis'][:3]}] {r['kategori']}: <span style='color:{warna_k}; font-weight:bold;'>Rp {r['jumlah']:,.0f}</span></p>", unsafe_allow_html=True)
                
        with tab_wal:
            df_wal = df_rk.groupby(['wallet', 'jenis', 'tanggal'])['jumlah'].sum().reset_index()
            for _, r in df_wal.sort_values(by='tanggal', ascending=False).iterrows():
                tgl_rekap_str = r['tanggal'].strftime('%d-%m-%Y') if isinstance(r['tanggal'], (datetime, pd.Timestamp, datetime.date)) else str(r['tanggal'])
                warna_w = "#2e7d32" if r['jenis'] == 'Pemasukan' else "#c62828"
                st.markdown(f"<p style='margin:0; font-size:12px;'>• <b>{tgl_rekap_str}</b> | 💳 {r['wallet']} [{r['jenis'][:3]}]: <span style='color:{warna_w}; font-weight:bold;'>Rp {r['jumlah']:,.0f}</span></p>", unsafe_allow_html=True)
                
        # --- GRAFIK BATANG TREN PENGELUARAN (WARNA-WARNI GELAP & ANTI PECAH HP) ---
        st.markdown("<p style='font-size: 12px; font-weight: bold; color: #8B0000; margin-top: 15px; margin-bottom: 2px;'>📊 Tren Pengeluaran per Kategori</p>", unsafe_allow_html=True)
        df_chart_rk = df_rk[df_rk['jenis'] == 'Pengeluaran'].groupby('kategori')['jumlah'].sum().reset_index()
        if df_chart_rk.empty:
            st.caption("Tidak ada grafik pengeluaran.")
        else:
            df_chart_rk = df_chart_rk.sort_values(by='jumlah', ascending=False)
            
            # Pangkas teks kategori kepanjangan khusus HP
            def trim_text(text):
                return text[:10] + "..." if len(text) > 12 else text
            df_chart_rk['kategori_mini'] = df_chart_rk['kategori'].apply(trim_text)
            
            fig = px.bar(
                df_chart_rk, 
                x='kategori_mini', 
                y='jumlah', 
                text='jumlah',
                color='kategori', 
                color_discrete_sequence=px.colors.qualitative.Dark24
            )
            fig.update_layout(
                xaxis_title=None, 
                yaxis_title=None, 
                margin=dict(t=5, b=25, l=5, r=5), 
                height=220, 
                showlegend=False, 
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=10),
                xaxis=dict(tickangle=-30, tickfont=dict(size=9), automargin=True)
            )
            fig.update_traces(
                texttemplate='Rp %{text:,.0f}', 
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(size=9, color='white', weight='bold')
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# 5. MENU: WALLET STATUS
elif st.session_state.menu_aktif == 'wallet':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 8px;'>💳 Sisa Saldo per Wallet</p>", unsafe_allow_html=True)
    
    wallet_html = "<div style='display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-start;'>"
    for w_name in LIST_WALLET:
        w_bal = wallet_balances.get(w_name, 0)
        if w_bal < 0:
            border_c = "#c62828"; bg_c = "rgba(198, 40, 40, 0.1)"; text_c = "#c62828"
        else:
            border_c = "#B8860B"; bg_c = "rgba(184, 134, 11, 0.08)"; text_c = "inherit"
            
        wallet_html += f"<div style='flex: 1; min-width: 90px; max-width: 110px; background:{bg_c}; border: 1px solid {border_c}; padding: 6px; border-radius: 8px; text-align: center;'><p style='margin: 0; font-size: 10px; font-weight: bold; color: #8B0000;'>{w_name}</p><h4 style='margin: 2px 0 0 0; font-size: 11px; font-weight: 800; color:{text_c};'>Rp {w_bal:,.0f}</h4></div>"
        
    wallet_html += "</div>"
    st.markdown(wallet_html, unsafe_allow_html=True)
