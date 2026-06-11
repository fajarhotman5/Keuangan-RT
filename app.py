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
