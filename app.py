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

st.markdown("""
    <style>
    .stApp a.element-header-anchor, a.element-header-anchor, .stMarkdown a,
    [data-testid="stMarkdownContainer"] a.element-header-anchor { display: none !important; }
    h1, h2, h3, h4, h5, h6 { pointer-events: none !important; }
    [data-testid="stAppDeployButton"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    footer { display: none !important; }
    header { display: none !important; }
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
    .stTabs [data-baseweb="tab"] { font-size: 12px !important; padding: 8px 12px !important; }
    label[data-testid="stWidgetLabel"] p { font-size: 12px !important; font-weight: bold; }
    @media (max-width: 768px) {
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfer (
                id_transfer INT AUTO_INCREMENT PRIMARY KEY,
                tanggal DATE NOT NULL,
                dari_wallet VARCHAR(30) NOT NULL,
                ke_wallet VARCHAR(30) NOT NULL,
                jumlah BIGINT NOT NULL DEFAULT 0,
                keterangan TEXT
            )
        """)
    conn.commit()
    conn.close()

init_db()

# --- LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown(
        "<div style='text-align:center; margin: 40px 0 20px 0;'>"
        "<p style='font-size:20px; font-weight:bold; color:#8B0000;'>Informasi Keuangan Kei</p>"
        "<p style='font-size:11px; color:#888; letter-spacing:1px;'>HARUS CATAT SETIAP SAAT</p>"
        "</div>",
        unsafe_allow_html=True
    )
    with st.form("form_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        masuk = st.form_submit_button("Masuk", use_container_width=True)
    if masuk:
        if username == st.secrets["login"]["username"] and password == st.secrets["login"]["password"]:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Upsss, anda bukan keluarga kami!")
    st.stop()

# --- VALID LISTS ---
LIST_WALLET = ['Cash', 'Dana', 'Gopay', 'Jago', 'Mandiri', 'OVO', 'ShopeePay']
KAT_PENGELUARAN = ['Makanan & Minuman', 'Jajan', 'Listrik, Air & Internet', 'Belanja Bulanan', 'Transportasi & Bensin', 'Hiburan', 'Bulanan Keluarga', 'Lain-lain']
KAT_PEMASUKAN = ['Gapok', 'Tukin', 'Uang Makan', 'Lainnya']

# --- JUDUL ---
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Amatic+SC:wght@700&display=swap" rel="stylesheet">
    <div style='text-align: center; margin-bottom: 15px;'>
        <div style='font-family: "Amatic SC", sans-serif; font-size: 34px; font-weight: bold; font-style: italic; color: var(--text-color); letter-spacing: 1px; margin: 0; padding: 0; line-height: 1.1;'>Informasi Keuangan Kei</div>
        <div style='font-size: 11px; color: var(--text-color); font-weight: 500; opacity: 0.6; letter-spacing: 1px; margin-top: 4px; padding: 0;'>HARUS CATAT SETIAP SAAT</div>
    </div>
""", unsafe_allow_html=True)

# --- DATA FETCHING ---
conn = get_connection()
df_trans = pd.read_sql("SELECT * FROM transaksi ORDER BY tanggal DESC, id_transaksi DESC", conn)
df_transfer = pd.read_sql("SELECT * FROM transfer ORDER BY tanggal DESC, id_transfer DESC", conn)
conn.close()

if not df_trans.empty:
    df_trans['tanggal'] = pd.to_datetime(df_trans['tanggal']).dt.date
    total_masuk = df_trans[df_trans['jenis'] == 'Pemasukan']['jumlah'].sum()
    total_keluar = df_trans[df_trans['jenis'] == 'Pengeluaran']['jumlah'].sum()
    sisa_saldo = total_masuk - total_keluar

    bulan_ini = datetime.now().month
    tahun_ini = datetime.now().year
    df_bulan_ini = df_trans[
        df_trans['tanggal'].apply(lambda x: x.month == bulan_ini and x.year == tahun_ini)
    ]
    total_keluar_bulan = df_bulan_ini[df_bulan_ini['jenis'] == 'Pengeluaran']['jumlah'].sum()

    if not df_transfer.empty:
        df_transfer['tanggal'] = pd.to_datetime(df_transfer['tanggal']).dt.date

    wallet_balances = {}
    for w in LIST_WALLET:
        w_masuk = df_trans[(df_trans['wallet'] == w) & (df_trans['jenis'] == 'Pemasukan')]['jumlah'].sum()
        w_keluar = df_trans[(df_trans['wallet'] == w) & (df_trans['jenis'] == 'Pengeluaran')]['jumlah'].sum()
        w_tf_masuk = df_transfer[df_transfer['ke_wallet'] == w]['jumlah'].sum() if not df_transfer.empty else 0
        w_tf_keluar = df_transfer[df_transfer['dari_wallet'] == w]['jumlah'].sum() if not df_transfer.empty else 0
        wallet_balances[w] = w_masuk - w_keluar + w_tf_masuk - w_tf_keluar
else:
    sisa_saldo = 0
    total_keluar_bulan = 0
    if not df_transfer.empty:
        df_transfer['tanggal'] = pd.to_datetime(df_transfer['tanggal']).dt.date
    wallet_balances = {w: 0 for w in LIST_WALLET}
    if not df_transfer.empty:
        for w in LIST_WALLET:
            w_tf_masuk = df_transfer[df_transfer['ke_wallet'] == w]['jumlah'].sum()
            w_tf_keluar = df_transfer[df_transfer['dari_wallet'] == w]['jumlah'].sum()
            wallet_balances[w] = w_tf_masuk - w_tf_keluar

# --- KARTU METRIK ---
st.markdown(f"""
    <div style='display: flex; gap: 8px; margin-bottom: 12px;'>
        <div style='flex: 1; padding: 8px 6px; border-radius: 12px; text-align: center; background-color: #8B0000; border: 1.5px solid #8B0000; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
            <p style='margin: 0; font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.9); letter-spacing: 0.3px;'>Sisa Saldo Berjalan</p>
            <h3 style='margin: 2px 0 0 0; font-size: 15px; font-weight: 800; color: #FFFFFF;'>Rp {sisa_saldo:,.0f}</h3>
        </div>
        <div style='flex: 1; padding: 8px 6px; border-radius: 12px; text-align: center; background-color: #8B0000; border: 1.5px solid #8B0000; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
            <p style='margin: 0; font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.9); letter-spacing: 0.3px;'>Pengeluaran Bulan Ini</p>
            <h3 style='margin: 2px 0 0 0; font-size: 15px; font-weight: 800; color: #FFFFFF;'>Rp {total_keluar_bulan:,.0f}</h3>
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
# MENU: TAMBAH
# ==========================================
if st.session_state.menu_aktif == 'tambah':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 5px;'>➕ Tambah Transaksi Baru</p>", unsafe_allow_html=True)
    jenis_tx = st.radio("Pilih Jenis:", ["Pengeluaran", "Pemasukan", "Transfer Wallet"], horizontal=True)

    if jenis_tx == "Transfer Wallet":
        with st.form("form_transfer", clear_on_submit=True):
            tgl_tf = st.date_input("Tanggal Transfer", datetime.now(), format="DD-MM-YYYY")
            col_tf1, col_tf2 = st.columns(2)
            with col_tf1:
                dari_wlt = st.selectbox("Dari Wallet", LIST_WALLET, key="dari_wlt")
            with col_tf2:
                ke_wlt = st.selectbox("Ke Wallet", LIST_WALLET, key="ke_wlt")
            jml_tf = st.number_input("Jumlah Transfer (Rp)", min_value=0, step=1000)
            ket_tf = st.text_input("Keterangan Transfer")
            simpan_tf = st.form_submit_button("Simpan Transfer")

            if simpan_tf:
                if dari_wlt == ke_wlt:
                    st.error("Wallet asal dan tujuan tidak boleh sama.")
                elif jml_tf <= 0:
                    st.error("Jumlah transfer harus lebih dari Rp 0.")
                else:
                    try:
                        conn = get_connection()
                        with conn.cursor() as cursor:
                            cursor.execute(
                                "INSERT INTO transfer (tanggal, dari_wallet, ke_wallet, jumlah, keterangan) VALUES (%s, %s, %s, %s, %s)",
                                (tgl_tf, dari_wlt, ke_wlt, jml_tf, ket_tf)
                            )
                        conn.commit()
                        conn.close()
                        st.toast("Transfer berhasil dicatat!", icon="💸")
                        st.success(f"Transfer Rp {jml_tf:,.0f} dari {dari_wlt} ke {ke_wlt} tersimpan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan transfer: {str(e)}")
    else:
        with st.form("form_transaksi", clear_on_submit=True):
            tgl = st.date_input("Tanggal Transaksi", datetime.now(), format="DD-MM-YYYY")
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
                    try:
                        conn = get_connection()
                        with conn.cursor() as cursor:
                            cursor.execute(
                                "INSERT INTO transaksi (jenis, tanggal, wallet, kategori, jumlah, reimburse, keterangan) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                (jenis_tx, tgl, wlt, kat, jml, remb, ket)
                            )
                        conn.commit()
                        conn.close()
                        st.toast("Transaksi baru berhasil disimpan!", icon="💰")
                        st.success("Data berhasil disimpan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan transaksi: {str(e)}")
                else:
                    st.error("Jumlah input harus lebih besar dari Rp 0!")

# ==========================================
# MENU: UNDUH
# ==========================================
elif st.session_state.menu_aktif == 'unduh':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 10px;'>📥 Ekspor Laporan Dokumen</p>", unsafe_allow_html=True)
    if df_trans.empty:
        st.info("Tidak ada data transaksi.")
    else:
        col_d1, col_d2 = st.columns(2)
        with col_d1: tgl_awal = st.date_input("Mulai Tanggal", df_trans['tanggal'].min(), key="eks_awal", format="DD-MM-YYYY")
        with col_d2: tgl_akhir = st.date_input("Sampai Tanggal", df_trans['tanggal'].max(), key="eks_akhir", format="DD-MM-YYYY")

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
                doc = SimpleDocTemplate(buffer_pdf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=40, bottomMargin=40)
                story = []

                title_style = ParagraphStyle(name='TitleStyle', fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#8B0000'), alignment=1, spaceAfter=4)
                meta_style = ParagraphStyle(name='MetaStyle', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor('#666666'), alignment=2)
                sub_style = ParagraphStyle(name='SubStyle', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#444444'), alignment=1, spaceAfter=12)
                header_style = ParagraphStyle(name='HeaderStyle', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, leading=10, alignment=1)
                cell_style = ParagraphStyle(name='CellStyle', fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor('#333333'))
                cell_center = ParagraphStyle(name='CellCenter', fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor('#333333'), alignment=1)
                cell_bold = ParagraphStyle(name='CellBold', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=colors.HexColor('#222222'))
                section_style = ParagraphStyle(name='SectionStyle', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#8B0000'), spaceAfter=6, spaceBefore=12)

                waktu_wib = datetime.now() + timedelta(hours=7)
                waktu_cetak = waktu_wib.strftime("%d-%m-%Y %H:%M WIB")

                story.append(Paragraph(f"Waktu Cetak: {waktu_cetak}", meta_style))
                story.append(Spacer(1, 8))
                story.append(Paragraph("LAPORAN MUTASI KEUANGAN KEI", title_style))
                story.append(Paragraph(f"Periode: {tgl_awal.strftime('%d-%m-%Y')} s/d {tgl_akhir.strftime('%d-%m-%Y')}", sub_style))

                # ── RINGKASAN UTAMA ──
                story.append(Paragraph("RINGKASAN", section_style))
                total_masuk_f = df_filter[df_filter['jenis'] == 'Pemasukan']['jumlah'].sum()
                total_keluar_f = df_filter[df_filter['jenis'] == 'Pengeluaran']['jumlah'].sum()
                net_f = total_masuk_f - total_keluar_f
                net_color = colors.HexColor('#2E7D32') if net_f >= 0 else colors.HexColor('#C62828')

                ringkasan_data = [
                    [Paragraph("Keterangan", header_style), Paragraph("Jumlah", header_style)],
                    [Paragraph("Total Pemasukan", cell_style), Paragraph(f"Rp {total_masuk_f:,.0f}", ParagraphStyle(name='Green', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#2E7D32')))],
                    [Paragraph("Total Pengeluaran", cell_style), Paragraph(f"Rp {total_keluar_f:,.0f}", ParagraphStyle(name='Red', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#C62828')))],
                    [Paragraph("Selisih (Net)", cell_bold), Paragraph(f"Rp {net_f:,.0f}", ParagraphStyle(name='Net', fontName='Helvetica-Bold', fontSize=9, textColor=net_color))],
                ]
                t_ringkasan = Table(ringkasan_data, colWidths=[300, 200])
                t_ringkasan.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8B0000')),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E5E5')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')]),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('LEFTPADDING', (0,0), (-1,-1), 8),
                    ('RIGHTPADDING', (0,0), (-1,-1), 8),
                    ('LINEBELOW', (0,2), (-1,2), 1.5, colors.HexColor('#8B0000')),
                ]))
                story.append(t_ringkasan)

                # ── SETUP PERIODE PERBANDINGAN ──
                from dateutil.relativedelta import relativedelta
                tgl_ref = datetime.now()
                bulan_ini_start = tgl_ref.replace(day=1)
                bulan_lalu_start = bulan_ini_start - relativedelta(months=1)
                bulan_lalu_end = bulan_ini_start - timedelta(days=1)
                tahun_lalu_start = bulan_ini_start - relativedelta(years=1)
                tahun_lalu_end = (tahun_lalu_start + relativedelta(months=1)) - timedelta(days=1)

                df_bln_ini = df_trans[df_trans['tanggal'].apply(lambda x: x >= bulan_ini_start.date())]
                df_bln_lalu = df_trans[df_trans['tanggal'].apply(lambda x: bulan_lalu_start.date() <= x <= bulan_lalu_end.date())]
                df_thn_lalu = df_trans[df_trans['tanggal'].apply(lambda x: tahun_lalu_start.date() <= x <= tahun_lalu_end.date())]

                nama_bln_ini = tgl_ref.strftime('%b %Y')
                nama_bln_lalu = bulan_lalu_start.strftime('%b %Y')
                nama_thn_lalu = tahun_lalu_start.strftime('%b %Y')

                def pct_change(now, prev):
                    if prev == 0: return "N/A"
                    pct = ((now - prev) / prev) * 100
                    return f"{'+'if pct>=0 else ''}{pct:.1f}%"

                def clr(val, invert=False):
                    if val == "N/A": return colors.HexColor('#888888')
                    num = float(val.replace('%','').replace('+',''))
                    if invert:
                        return colors.HexColor('#2E7D32') if num <= 0 else colors.HexColor('#C62828')
                    return colors.HexColor('#2E7D32') if num >= 0 else colors.HexColor('#C62828')

                def ps(name, val, color):
                    return Paragraph(val, ParagraphStyle(name=name, fontName='Helvetica-Bold', fontSize=8, textColor=color))

                def kat_sum(df, jenis, kat):
                    if df.empty: return 0
                    r = df[(df['jenis']==jenis) & (df['kategori']==kat)]['jumlah'].sum()
                    return int(r) if r else 0

                def build_kat_table(jenis, label_section):
                    story.append(Paragraph(label_section, section_style))
                    all_kat = set(
                        list(df_bln_ini[df_bln_ini['jenis']==jenis]['kategori'].unique()) +
                        list(df_bln_lalu[df_bln_lalu['jenis']==jenis]['kategori'].unique()) +
                        list(df_thn_lalu[df_thn_lalu['jenis']==jenis]['kategori'].unique())
                    )
                    if not all_kat:
                        story.append(Paragraph("Tidak ada data.", cell_style))
                        return

                    invert = (jenis == 'Pengeluaran')
                    cmp_header = [
                        Paragraph("Kategori", header_style),
                        Paragraph(nama_bln_ini, header_style),
                        Paragraph(nama_bln_lalu, header_style),
                        Paragraph(nama_thn_lalu, header_style),
                        Paragraph("vs Bln Lalu", header_style),
                        Paragraph("vs Thn Lalu", header_style),
                    ]
                    cmp_data = [cmp_header]

                    for kat in sorted(all_kat):
                        v_bi = kat_sum(df_bln_ini, jenis, kat)
                        v_bl = kat_sum(df_bln_lalu, jenis, kat)
                        v_tl = kat_sum(df_thn_lalu, jenis, kat)
                        pct_bl = pct_change(v_bi, v_bl)
                        pct_tl = pct_change(v_bi, v_tl)
                        cmp_data.append([
                            Paragraph(kat, cell_style),
                            Paragraph(f"Rp {v_bi:,.0f}" if v_bi else "-", cell_style),
                            Paragraph(f"Rp {v_bl:,.0f}" if v_bl else "-", cell_style),
                            Paragraph(f"Rp {v_tl:,.0f}" if v_tl else "-", cell_style),
                            ps(f'pbl_{kat}', pct_bl, clr(pct_bl, invert=invert)),
                            ps(f'ptl_{kat}', pct_tl, clr(pct_tl, invert=invert)),
                        ])

                    t_cmp = Table(cmp_data, colWidths=[110, 85, 85, 85, 75, 75])
                    t_cmp.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8B0000')),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E5E5')),
                        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')]),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('TOPPADDING', (0,0), (-1,-1), 5),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                        ('LEFTPADDING', (0,0), (-1,-1), 6),
                        ('RIGHTPADDING', (0,0), (-1,-1), 6),
                    ]))
                    story.append(t_cmp)

                build_kat_table('Pemasukan', "PEMASUKAN PER KATEGORI: BULAN INI vs BULAN LALU vs TAHUN LALU")
                build_kat_table('Pengeluaran', "PENGELUARAN PER KATEGORI: BULAN INI vs BULAN LALU vs TAHUN LALU")

                # ── REKAP PER WALLET ──
                story.append(Paragraph("REKAP PER WALLET", section_style))
                df_wlt_f = df_filter.groupby(['wallet', 'jenis'])['jumlah'].sum().unstack(fill_value=0).reset_index()
                wallet_data = [[Paragraph("Wallet", header_style), Paragraph("Pemasukan", header_style), Paragraph("Pengeluaran", header_style), Paragraph("Selisih", header_style)]]
                for _, r in df_wlt_f.iterrows():
                    masuk_w = r.get('Pemasukan', 0)
                    keluar_w = r.get('Pengeluaran', 0)
                    net_w = masuk_w - keluar_w
                    net_w_color = colors.HexColor('#2E7D32') if net_w >= 0 else colors.HexColor('#C62828')
                    wallet_data.append([
                        Paragraph(str(r['wallet']), cell_bold),
                        Paragraph(f"Rp {masuk_w:,.0f}", ParagraphStyle(name='WMasuk', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#2E7D32'))),
                        Paragraph(f"Rp {keluar_w:,.0f}", ParagraphStyle(name='WKeluar', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#C62828'))),
                        Paragraph(f"Rp {net_w:,.0f}", ParagraphStyle(name='WNet', fontName='Helvetica-Bold', fontSize=8, textColor=net_w_color)),
                    ])
                t_wallet = Table(wallet_data, colWidths=[120, 130, 130, 120])
                t_wallet.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8B0000')),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E5E5')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')]),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('LEFTPADDING', (0,0), (-1,-1), 8),
                    ('RIGHTPADDING', (0,0), (-1,-1), 8),
                ]))
                story.append(t_wallet)

                # ── REKAP PER KATEGORI ──
                story.append(Paragraph("REKAP PER KATEGORI", section_style))
                df_kat_f = df_filter.groupby(['kategori', 'jenis'])['jumlah'].sum().reset_index().sort_values('jumlah', ascending=False)
                kat_data = [[Paragraph("Kategori", header_style), Paragraph("Jenis", header_style), Paragraph("Jumlah", header_style)]]
                for _, r in df_kat_f.iterrows():
                    warna_kat = colors.HexColor('#2E7D32') if r['jenis'] == 'Pemasukan' else colors.HexColor('#C62828')
                    kat_data.append([
                        Paragraph(str(r['kategori']), cell_style),
                        Paragraph(str(r['jenis']), ParagraphStyle(name='KatJenis', fontName='Helvetica', fontSize=8, textColor=warna_kat)),
                        Paragraph(f"Rp {r['jumlah']:,.0f}", ParagraphStyle(name='KatJml', fontName='Helvetica-Bold', fontSize=8, textColor=warna_kat)),
                    ])
                t_kat = Table(kat_data, colWidths=[220, 120, 160])
                t_kat.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8B0000')),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E5E5')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')]),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('LEFTPADDING', (0,0), (-1,-1), 8),
                    ('RIGHTPADDING', (0,0), (-1,-1), 8),
                ]))
                story.append(t_kat)

                # ── REKAP REIMBURSE ──
                df_rmb_f = df_filter[df_filter['jenis'] == 'Pengeluaran'].groupby('reimburse')['jumlah'].sum().reset_index()
                if not df_rmb_f.empty:
                    story.append(Paragraph("REKAP REIMBURSE", section_style))
                    rmb_data = [[Paragraph("Status", header_style), Paragraph("Jumlah", header_style)]]
                    for _, r in df_rmb_f.iterrows():
                        rmb_data.append([
                            Paragraph(f"Reimburse: {r['reimburse']}", cell_style),
                            Paragraph(f"Rp {r['jumlah']:,.0f}", cell_bold),
                        ])
                    t_rmb = Table(rmb_data, colWidths=[300, 200])
                    t_rmb.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8B0000')),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E5E5')),
                        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')]),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('TOPPADDING', (0,0), (-1,-1), 6),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                        ('LEFTPADDING', (0,0), (-1,-1), 8),
                        ('RIGHTPADDING', (0,0), (-1,-1), 8),
                    ]))
                    story.append(t_rmb)

                # ── DETAIL MUTASI ──
                story.append(Paragraph("DETAIL MUTASI TRANSAKSI", section_style))
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
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('LEFTPADDING', (0,0), (-1,-1), 5),
                    ('RIGHTPADDING', (0,0), (-1,-1), 5),
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

# ==========================================
# MENU: RIWAYAT
# ==========================================
elif st.session_state.menu_aktif == 'riwayat':
    st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 14px; margin-bottom: 5px;'>📋 Riwayat Buku Kas</p>", unsafe_allow_html=True)

    tab_tx, tab_tf = st.tabs(["💸 Transaksi", "🔄 Transfer Wallet"])

    with tab_tx:
        if df_trans.empty:
            st.info("Belum ada mutasi transaksi.")
        else:
            cari = st.text_input("🔍 Cari Kategori / Keterangan:", key="cari_riwayat")
            df_tampil = df_trans.copy()
            if cari:
                df_tampil = df_tampil[
                    df_tampil['kategori'].str.contains(cari, case=False, na=False) |
                    df_tampil['keterangan'].str.contains(cari, case=False, na=False)
                ]

            st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 12px; margin-top: 10px; margin-bottom: 2px;'>⚡ Aksi Cepat Transaksi</p>", unsafe_allow_html=True)
            opsi_pilih = {row['id_transaksi']: f"#{row['id_transaksi']} - {row['kategori']} (Rp {row['jumlah']:,.0f})" for _, row in df_tampil.iterrows()}

            if opsi_pilih:
                col_action1, col_action2 = st.columns([3, 2])
                with col_action1:
                    id_terpilih = st.selectbox("Pilih ID:", options=list(opsi_pilih.keys()), format_func=lambda x: opsi_pilih[x], label_visibility="collapsed")
                with col_action2:
                    mode_aksi = st.selectbox("Tindakan:", ["Pilih...", "📝 Edit", "🗑️ Hapus"], label_visibility="collapsed")

                if id_terpilih and mode_aksi != "Pilih...":
                    data_row = df_trans[df_trans['id_transaksi'] == id_terpilih].iloc[0]

                    if mode_aksi == "📝 Edit":
                        with st.form("form_cepat_edit_universal"):
                            st.markdown(f"<p style='color: #B8860B; font-weight: bold; font-size: 12px;'>📝 Edit Data #{id_terpilih}</p>", unsafe_allow_html=True)
                            new_tgl = st.date_input("Tanggal", data_row['tanggal'])
                            new_jenis = st.selectbox("Jenis", ["Pemasukan", "Pengeluaran"], index=["Pemasukan", "Pengeluaran"].index(data_row['jenis']))
                            new_wallet = st.selectbox("Wallet", LIST_WALLET, index=LIST_WALLET.index(data_row['wallet']))
                            list_kat_opsi = KAT_PEMASUKAN if new_jenis == "Pemasukan" else KAT_PENGELUARAN
                            if data_row['kategori'] not in list_kat_opsi:
                                list_kat_opsi = list_kat_opsi + [data_row['kategori']]
                            new_kat = st.selectbox("Kategori", list_kat_opsi, index=list_kat_opsi.index(data_row['kategori']))
                            new_jml = st.number_input("Nominal (Rp)", min_value=0, value=int(data_row['jumlah']), step=1000)
                            new_remb = st.radio("Reimburse:", ["Tidak", "Ya"], index=["Tidak", "Ya"].index(data_row.get('reimburse', 'Tidak')), horizontal=True)
                            new_ket = st.text_input("Keterangan", value=data_row['keterangan'] if data_row['keterangan'] else "")
                            col_ef1, col_ef2 = st.columns(2)
                            with col_ef1:
                                if st.form_submit_button("Simpan", use_container_width=True):
                                    try:
                                        conn = get_connection()
                                        with conn.cursor() as cursor:
                                            cursor.execute(
                                                "UPDATE transaksi SET tanggal=%s, jenis=%s, wallet=%s, kategori=%s, jumlah=%s, reimburse=%s, keterangan=%s WHERE id_transaksi=%s",
                                                (new_tgl, new_jenis, new_wallet, new_kat, new_jml, new_remb, new_ket, id_terpilih)
                                            )
                                        conn.commit()
                                        conn.close()
                                        st.toast("Data berhasil diperbarui!", icon="🎉")
                                        st.success("Berhasil diubah!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Gagal mengubah data: {str(e)}")

                    elif mode_aksi == "🗑️ Hapus":
                        st.markdown(f"<div style='background-color:rgba(198,40,40,0.1); padding:8px; border-radius:6px; border:1px solid #c62828; margin-bottom:8px; font-size:11px; color:#c62828;'>Hapus data <b>{data_row['kategori']} (Rp {data_row['jumlah']:,.0f})</b>?</div>", unsafe_allow_html=True)
                        col_del1, col_del2 = st.columns(2)
                        with col_del1:
                            if st.button("🔴 Ya, Hapus", key="confirm_del_universal", use_container_width=True):
                                try:
                                    conn = get_connection()
                                    with conn.cursor() as cursor:
                                        cursor.execute("DELETE FROM transaksi WHERE id_transaksi=%s", (id_terpilih,))
                                    conn.commit()
                                    conn.close()
                                    st.toast("Data transaksi telah dihapus!", icon="ℹ️")
                                    st.success("Terhapus!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal menghapus data: {str(e)}")

            st.markdown("<hr style='border-top: 1px solid rgba(139, 0, 0, 0.15); margin: 12px 0;'>", unsafe_allow_html=True)

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

            html_desktop_rows = ""
            for _, row in df_tampil.iterrows():
                tgl_str = row['tanggal'].strftime('%d-%m-%Y')
                color_p = "#2e7d32" if row['jenis'] == "Pemasukan" else "#c62828"
                sign_p = "+" if row['jenis'] == "Pemasukan" else "-"
                ket_str = row['keterangan'] if row['keterangan'] else "-"
                html_desktop_rows += f"<tr><td>{tgl_str}</td><td>{row['wallet']}</td><td>{row['kategori']}</td><td style='color:{color_p}; font-weight:700;'>{sign_p}Rp {row['jumlah']:,.0f}</td><td>{row.get('reimburse', 'Tidak')}</td><td>{ket_str}</td><td style='font-weight:bold; color:#B8860B;'>#{row['id_transaksi']}</td></tr>"

            desktop_html = f"<div class='desktop-table-container'><table class='custom-table-v2'><thead><tr><th>Tanggal</th><th>Wallet</th><th>Kategori</th><th>Nominal</th><th>Reimburse</th><th>Keterangan</th><th>ID</th></tr></thead><tbody>{html_desktop_rows}</tbody></table></div>"
            st.markdown(desktop_html, unsafe_allow_html=True)

            html_mobile_cards = ""
            for _, row in df_tampil.iterrows():
                tgl_mini = row['tanggal'].strftime('%d-%m')
                color_p = "#2e7d32" if row['jenis'] == "Pemasukan" else "#c62828"
                sign_p = "+" if row['jenis'] == "Pemasukan" else "-"
                rmb_badge = " [Rmb]" if row.get('reimburse', 'Tidak') == "Ya" else ""
                html_mobile_cards += f"<div class='tx-card'><div class='tx-card-row'><span class='tx-card-title'>{row['kategori']}<span style='color:#c62828; font-size:10px;'>{rmb_badge}</span></span><span class='tx-card-price' style='color:{color_p};'>{sign_p}Rp {row['jumlah']:,.0f}</span></div><div class='tx-card-row' style='margin-bottom:0;'><span class='tx-card-meta'>📅 {tgl_mini} | 💳 {row['wallet']}</span><span class='tx-card-meta' style='font-weight:bold; color:#B8860B;'>#{row['id_transaksi']}</span></div></div>"
            st.markdown(f"<div class='mobile-card-container'>{html_mobile_cards}</div>", unsafe_allow_html=True)

    with tab_tf:
        if df_transfer.empty:
            st.info("Belum ada riwayat transfer antar wallet.")
        else:
            html_tf_rows = ""
            for _, row in df_transfer.iterrows():
                tgl_str = row['tanggal'].strftime('%d-%m-%Y')
                ket_str = row['keterangan'] if row['keterangan'] else "-"
                html_tf_rows += f"<tr><td>{tgl_str}</td><td style='color:#c62828; font-weight:bold;'>{row['dari_wallet']}</td><td style='color:#2e7d32; font-weight:bold;'>{row['ke_wallet']}</td><td style='font-weight:700;'>Rp {row['jumlah']:,.0f}</td><td>{ket_str}</td><td style='font-weight:bold; color:#B8860B;'>#{row['id_transfer']}</td></tr>"

            tf_html = f"<div style='overflow-x:auto;'><table class='custom-table-v2'><thead><tr><th>Tanggal</th><th>Dari</th><th>Ke</th><th>Jumlah</th><th>Keterangan</th><th>ID</th></tr></thead><tbody>{html_tf_rows}</tbody></table></div>"
            st.markdown(tf_html, unsafe_allow_html=True)

            st.markdown("<p style='color: #8B0000; font-weight: bold; font-size: 12px; margin-top: 10px; margin-bottom: 2px;'>⚡ Hapus Transfer</p>", unsafe_allow_html=True)
            opsi_tf = {row['id_transfer']: f"#{row['id_transfer']} - {row['dari_wallet']} ke {row['ke_wallet']} (Rp {row['jumlah']:,.0f})" for _, row in df_transfer.iterrows()}
            id_tf_pilih = st.selectbox("Pilih transfer:", options=list(opsi_tf.keys()), format_func=lambda x: opsi_tf[x], label_visibility="collapsed")
            if st.button("🔴 Hapus Transfer Ini", use_container_width=True):
                try:
                    conn = get_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("DELETE FROM transfer WHERE id_transfer=%s", (id_tf_pilih,))
                    conn.commit()
                    conn.close()
                    st.success("Transfer dihapus!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal: {str(e)}")

# ==========================================
# MENU: REKAP
# ==========================================
elif st.session_state.menu_aktif == 'rekap':
    st.markdown("<p style='color: #8B0000; font-weight: bold; margin-bottom: 5px; font-size: 14px;'>📊 Rekap Pemasukan Pengeluaran</p>", unsafe_allow_html=True)
    if df_trans.empty:
        st.info("Belum ada data transaksi.")
    else:
        col_r1, col_r2 = st.columns(2)
        with col_r1: rekap_awal = st.date_input("Dari", df_trans['tanggal'].min(), key="rk_awal", format="DD-MM-YYYY")
        with col_r2: rekap_akhir = st.date_input("Sampai", df_trans['tanggal'].max(), key="rk_akhir", format="DD-MM-YYYY")

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
                df_chart_rk = df_chart_rk.sort_values(by='jumlah', ascending=False)

                def trim_text(text):
                    return text[:10] + "..." if len(text) > 12 else text

                df_chart_rk['kategori_mini'] = df_chart_rk['kategori'].apply(trim_text)
                fig = px.bar(
                    df_chart_rk, x='kategori_mini', y='jumlah', text='jumlah',
                    color='kategori', color_discrete_sequence=px.colors.qualitative.Dark24
                )
                fig.update_layout(
                    xaxis_title=None, yaxis_title=None,
                    margin=dict(t=5, b=25, l=5, r=5), height=220,
                    showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=10),
                    xaxis=dict(tickangle=-30, tickfont=dict(size=9), automargin=True)
                )
                fig.update_traces(
                    texttemplate='Rp %{text:,.0f}', textposition='inside',
                    insidetextanchor='middle', textfont=dict(size=9, color='white', weight='bold')
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# MENU: WALLET
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
        wallet_html += f"""<div style='border: 1px solid {border_c}; background-color: {bg_c}; padding: 4px 10px; border-radius: 20px; font-size: 12px; display: inline-block;'><span style='font-weight: bold; color: {border_c};'>{w_name}:</span> <span style='color: {text_c}; font-weight: 700;'>Rp {w_bal:,.0f}</span></div>"""
    wallet_html += "</div>"
    st.markdown(wallet_html, unsafe_allow_html=True)
