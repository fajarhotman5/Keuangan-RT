import streamlit as st
import pymysql
import pandas as pd
import io
from datetime import datetime
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Keuangan Kei", page_icon="💰", layout="centered")

# Custom CSS untuk menjaga keterbacaan tinggi (High Contrast) di Mode Dark maupun Light
st.markdown("""
    <style>
    /* Sembunyikan elemen bawaan Streamlit yang mengganggu */
    [data-testid="stAppDeployButton"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    footer { display: none !important; }
    header { display: none !important; }
    
    /* GAYA TOMBOL UTAMA (Merah Tua dengan Teks Putih Bersih) */
    div.stButton > button {
        background-color: #8B0000 !important;
        color: #FFFFFF !important;
        border: 2px solid #8B0000 !important;
        border-radius: 8px !important;
        padding: 6px 12px !important;
        font-weight: bold !important;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #000000 !important;
        color: #FFD700 !important; /* Kuning Emas saat di-hover */
        border-color: #FFD700 !important;
    }

    /* Memaksa teks form & dropdown bawaan agar mengikuti skema bawaan Streamlit secara aman */
    div[data-testid="stForm"] {
        border: 1px solid #8B0000 !important;
        border-radius: 10px;
        padding: 20px;
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
                keterangan TEXT
            )
        """)
    conn.commit()
    conn.close()

init_db()

# --- VALID LISTS ---
LIST_WALLET = ['Cash', 'Dana', 'Gopay', 'Jago', 'Mandiri', 'OVO', 'ShopeePay']
KAT_PENGELUARAN = ['Makanan & Minuman', 'Listrik, Air & Internet', 'Belanja Bulanan', 'Transportasi & Bensin', 'Hiburan', 'Lain-lain']
KAT_PEMASUKAN = ['Gapok', 'Tukin', 'Lainnya']

# --- APP HEADER (Lambang Uang & Lambang Link Sudah Dihilangkan) ---
st.markdown("""
    <div style='text-align: center; margin-bottom: 25px;'>
        <p style='font-size: 32px; font-weight: 800; color: #8B0000; margin-bottom: 0px; line-height: 1.2;'>Informasi Keuangan Kei</p>
        <p style='color: #B8860B; font-size: 14px; font-style: italic; font-weight: bold; margin-top: 5px;'>Harus catat setiap saat</p>
    </div>
""", unsafe_allow_html=True)

# --- DATA FETCHING & CALCULATIONS ---
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

# --- BARIS PERTAMA: KARTU METRIK KONTRAST TINGGI ---
col_s1, col_s2 = st.columns(2)
with col_s1:
    st.markdown(f"""
        <div style='background-color: #000000; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #B8860B;'>
            <p style='margin: 0; font-size: 14px; color: #FFFFFF !important; font-weight: bold;'>Sisa Saldo Berjalan</p>
            <p style='margin: 5px 0 0 0; font-size: 22px; font-weight: 900; color: #FFD700 !important;'>Rp {sisa_saldo:,.0f}</p>
        </div>
    """, unsafe_allow_html=True)
with col_s2:
    st.markdown(f"""
        <div style='background-color: #8B0000; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #8B0000;'>
            <p style='margin: 0; font-size: 14px; color: #FFFFFF !important; font-weight: bold;'>Total Pengeluaran</p>
            <p style='margin: 5px 0 0 0; font-size: 22px; font-weight: 900; color: #FFFFFF !important;'>Rp {total_keluar:,.0f}</p>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# --- BARIS KEDUA: NAVIGASI MENU ---
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

st.markdown("<hr style='margin-top: 10px; margin-bottom: 20px; border-color: #8B0000;'>", unsafe_allow_html=True)

# --- FUNGSI CANVAS UNTUK PDF ---
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#000000"))
        self.setStrokeColor(colors.HexColor("#8B0000"))
        self.setLineWidth(1)
        self.line(54, 750, 558, 750)
        self.drawString(54, 755, "LAPORAN KEUANGAN KEI")
        
        self.line(54, 50, 558, 50)
        page_text = f"Halaman {self._pageNumber} dari {page_count}"
        self.drawRightString(558, 38, page_text)
        self.drawString(54, 38, f"Dicetak pada: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        self.restoreState()

# --- LOGIKA KONTEN MENU ---

# 1. MENU: TAMBAH
if st.session_state.menu_aktif == 'tambah':
    st.markdown("<h4 style='color: #8B0000;'>➕ Tambah Transaksi Baru</h4>", unsafe_allow_html=True)
    jenis_tx = st.radio("Pilih Jenis Aliran Dana:", ["Pengeluaran", "Pemasukan"], horizontal=True)
    
    with st.form("form_transaksi", clear_on_submit=True):
        tgl = st.date_input("Tanggal Transaksi", datetime.now())
        wlt = st.selectbox("Pilih Wallet / Dompet", LIST_WALLET)
        kat = st.selectbox("Kategori", KAT_PENGELUARAN if jenis_tx == "Pengeluaran" else KAT_PEMASUKAN)
        jml = st.number_input("Jumlah Nominal (Rp)", min_value=0, step=1000)
        ket = st.text_input("Keterangan Tambahan")
        
        simpan = st.form_submit_button("Simpan Catatan")
        if simpan:
            if jml > 0:
                conn = get_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO transaksi (jenis, tanggal, wallet, kategori, jumlah, keterangan) VALUES (%s, %s, %s, %s, %s, %s)",
                        (jenis_tx, tgl, wlt, kat, jml, ket)
                    )
                conn.commit()
                conn.close()
                st.success(f"Berhasil menyimpan {jenis_tx} sebesar Rp {jml:,.0f}")
                st.rerun()
            else:
                st.error("Jumlah input harus lebih besar dari Rp 0!")

# 2. MENU: UNDUH
elif st.session_state.menu_aktif == 'unduh':
    st.markdown("<h4 style='color: #8B0000;'>📥 Ekspor Laporan</h4>", unsafe_allow_html=True)
    if df_trans.empty:
        st.info("Tidak ada data transaksi yang dapat diekspor.")
    else:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            tgl_awal = st.date_input("Mulai Tanggal", df_trans['tanggal'].min())
        with col_d2:
            tgl_akhir = st.date_input("Sampai Tanggal", df_trans['tanggal'].max())
            
        df_filter = df_trans[(df_trans['tanggal'] >= tgl_awal) & (df_trans['tanggal'] <= tgl_akhir)].copy()
        
        if df_filter.empty:
            st.warning("Data kosong untuk rentang tanggal tersebut.")
        else:
            col_b1, col_b2 = st.columns(2)
            
            with col_b1:
                buffer_xl = io.BytesIO()
                with pd.ExcelWriter(buffer_xl, engine='openpyxl') as writer:
                    df_filter.to_excel(writer, index=False, sheet_name='Laporan')
                
                st.download_button(
                    label="🟢 Unduh File Excel",
                    data=buffer_xl.getvalue(),
                    file_name=f"Laporan_Keuangan_{tgl_awal}_{tgl_akhir}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
            with col_b2:
                buffer_pdf = io.BytesIO()
                doc = SimpleDocTemplate(buffer_pdf, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=72, bottomMargin=72)
                story = []
                
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(name='TitleStyle', fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#8B0000'), alignment=1, spaceAfter=20)
                sub_style = ParagraphStyle(name='SubStyle', fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#000000'), alignment=1, spaceAfter=20)
                cell_style = ParagraphStyle(name='CellStyle', fontName='Helvetica', fontSize=9, leading=11)
                header_style = ParagraphStyle(name='HeaderStyle', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, leading=11)
                
                story.append(Paragraph("LAPORAN PERINCIAN KEUANGAN", title_style))
                story.append(Paragraph(f"Periode: {tgl_awal.strftime('%d/%m/%Y')} s/d {tgl_akhir.strftime('%d/%m/%Y')}", sub_style))
                story.append(Spacer(1, 10))
                
                table_data = [[Paragraph("Jenis", header_style), Paragraph("Tanggal", header_style), Paragraph("Wallet", header_style), Paragraph("Kategori", header_style), Paragraph("Jumlah (Rp)", header_style), Paragraph("Keterangan", header_style)]]
                
                for _, row in df_filter.iterrows():
                    table_data.append([
                        Paragraph(str(row['jenis']), cell_style),
                        Paragraph(row['tanggal'].strftime('%d/%m/%Y'), cell_style),
                        Paragraph(str(row['wallet']), cell_style),
                        Paragraph(str(row['kategori']), cell_style),
                        Paragraph(f"{row['jumlah']:,.0f}", cell_style),
                        Paragraph(str(row['keterangan'] or '-'), cell_style)
                    ])
                
                col_widths = [65, 60, 60, 95, 74, 150] 
                t = Table(table_data, colWidths=col_widths, repeatRows=1)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8B0000')),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0,0), (-1,0), 6),
                    ('TOPPADDING', (0,0), (-1,0), 6),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')])
                ]))
                story.append(t)
                doc.build(story, canvasmaker=NumberedCanvas)
                
                st.download_button(
                    label="🔴 Unduh File PDF",
                    data=buffer_pdf.getvalue(),
                    file_name=f"Laporan_Keuangan_{tgl_awal}_{tgl_akhir}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

# 3. MENU: RIWAYAT
elif st.session_state.menu_aktif == 'riwayat':
    st.markdown("<h4 style='color: #8B0000;'>📋 Riwayat Transaksi Buku</h4>", unsafe_allow_html=True)
    if df_trans.empty:
        st.info("Belum ada mutasi/transaksi tercatat.")
    else:
        cari = st.text_input("🔍 Filter Pencarian (Kategori / Keterangan):")
        df_show = df_trans.copy()
        if cari:
            df_show = df_show[
                df_show['kategori'].str.contains(cari, case=False, na=False) | 
                df_show['keterangan'].str.contains(cari, case=False, na=False)
            ]
        
        df_show['tanggal'] = df_show['tanggal'].apply(lambda x: x.strftime('%d-%m-%Y'))
        df_show['jumlah'] = df_show['jumlah'].apply(lambda x: f"Rp {x:,.0f}")
        df_show = df_show.drop(columns=['id_transaksi']).reset_index(drop=True)
        df_show.index += 1
        
        st.dataframe(df_show, use_container_width=True)

# 4. MENU: REKAP
elif st.session_state.menu_aktif == 'rekap':
    st.markdown("<h4 style='color: #8B0000;'>📊 Distribusi Pengeluaran</h4>", unsafe_allow_html=True)
    df_keluar = df_trans[df_trans['jenis'] == 'Pengeluaran']
    
    if df_keluar.empty:
        st.info("Data pengeluaran kosong, grafik tidak dapat dibuat.")
    else:
        df_chart = df_keluar.groupby('kategori')['jumlah'].sum().reset_index()
        tema_warna_grafik = ['#8B0000', '#B8860B', '#000000', '#555555', '#D3D3D3', '#CD5C5C']
        
        fig = px.pie(
            df_chart, 
            values='jumlah', 
            names='kategori', 
            hole=0.4,
            color_discrete_sequence=tema_warna_grafik
        )
        fig.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            hovertemplate='%{label}<br>Rp %{value:,.0f}<extra></extra>'
        )
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3),
            margin=dict(t=10, b=10, l=10, r=10)
        )
        st.plotly_chart(fig, use_container_width=True)

# 5. MENU: WALLET
elif st.session_state.menu_aktif == 'wallet':
    st.markdown("<h4 style='color: #8B0000;'>💳 Saldo Berjalan per Wallet</h4>", unsafe_allow_html=True)
    
    for i in range(0, len(LIST_WALLET), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(LIST_WALLET):
                w_name = LIST_WALLET[i + j]
                w_bal = wallet_balances[w_name]
                
                if w_bal < 0:
                    bg_color = "#8B0000"
                    border_color = "#8B0000"
                    text_amount_color = "#FFFFFF"
                else:
                    bg_color = "#000000"
                    border_color = "#B8860B"
                    text_amount_color = "#FFD700"
                
                cols[j].markdown(f"""
                    <div style='background-color: {bg_color}; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 2px solid {border_color};'>
                        <p style='margin:0; font-size:13px; font-weight:bold; color: #FFFFFF !important;'>{w_name}</p>
                        <p style='margin:5px 0 0 0; font-size:18px; font-weight:900; color: {text_amount_color} !important;'>Rp {w_bal:,.0f}</p>
                    </div>
                """, unsafe_allow_html=True)
