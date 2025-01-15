"""
===========================================
MILESTONE 3

Nama  : Nisrina Tsany Sulthanah
Batch : FTDS RMT038

This Airflow pipeline fetches data from a PostgreSQL database, cleans the data, 
and uploads it to Elasticsearch for further processing. The pipeline is scheduled 
to run every Saturday at 09:10, 09:20, and 09:30.

Steps:
1. Fetches data from a PostgreSQL database.
2. Cleans the raw data by handling missing values, duplicates, and formatting issues.
3. Uploads the cleaned data to an Elasticsearch index for further analysis.

Modules Required:
- airflow
- pandas
- psycopg2
- elasticsearch
- time
===========================================
"""


from airflow import DAG
from airflow.decorators import task
from datetime import datetime, timedelta
import pandas as pd
import psycopg2
from elasticsearch import Elasticsearch
import time

# --- Default Arguments ---
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Define DAG
with DAG(
    "P2M3_Nisrina_DAG",
    default_args=default_args,
    description="Pipeline with PythonOperator scheduled every Saturday 09:10-09:30",
    start_date=datetime(2024, 11, 1, 9, 10),
    schedule_interval="10,20,30 9 * * 6",  # Setiap Sabtu pukul 09:10, 09:20, 09:30
    catchup=False,
) as dag:
    
    @task
    def fetch_data():
        """
        Fetches data from a PostgreSQL database and saves it as a raw CSV file.
        
        This task connects to the PostgreSQL database, retrieves the data from 
        the specified table, and saves it to a CSV file for further processing.
        
        Parameters: 
        None
        
        Returns:
        None
        
        Example usage:
        fetch_data()  # This will fetch the data and save it as 'P2M3_Nisrina_data_raw.csv'
        """
        time.sleep(10)  # Tunggu 10 detik
        conn = psycopg2.connect(
            dbname="airflow",
            user="airflow",
            password="airflow",
            host="postgres",
            port="5432",
            connect_timeout=10  # Timeout 10 detik
        )
        query = "SELECT * FROM table_m3;"  # Nama tabel di PostgreSQL
        df = pd.read_sql(query, conn)
        raw_path = '/opt/airflow/dags/P2M3_Nisrina_data_raw.csv'
        df.to_csv(raw_path, index=False)
        conn.close()
        print(f"Data mentah berhasil disimpan ke '{raw_path}'.")

    @task
    def clean_data():
        """
        Cleans the raw data and saves it as a cleaned CSV file.
        
        This task processes the raw data by handling missing values, removing 
        duplicates, normalizing column names, and correcting formatting issues. 
        It then saves the cleaned data to a new CSV file.
        
        Parameters:
        None
        
        Returns:
        None
        
        Example usage:
        clean_data()  # This will clean the raw data and save it as 'P2M3_Nisrina_data_clean.csv'
        """
        raw_path = '/opt/airflow/dags/P2M3_Nisrina_data_raw.csv'
        clean_path = '/opt/airflow/dags/P2M3_Nisrina_data_clean.csv'

        # Load raw data
        df = pd.read_csv(raw_path)

        # Hapus data duplikat
        df.drop_duplicates(inplace=True)

        # Normalisasi nama kolom
        df.columns = df.columns.str.lower().str.replace(" ", "_").str.replace(r"[^\w]", "", regex=True)

        # Tangani missing values
        # Kolom numerik
        df['publishing_year'] = df['publishing_year'].fillna(df['publishing_year'].median())
        df['book_average_rating'] = df['book_average_rating'].fillna(df['book_average_rating'].mean())
        df['gross_sales'] = df['gross_sales'].fillna(df['gross_sales'].median())

        # Kolom kategorikal
        df['author'] = df['author'].fillna(df['author'].mode()[0])
        df['genre'] = df['genre'].fillna(df['genre'].mode()[0])
        df['language_code'] = df['language_code'].fillna(df['language_code'].mode()[0])

        # Kolom dengan nilai default
        df['book_name'] = df['book_name'].fillna("No Title")
        df['publisher'] = df['publisher'].fillna("No Publisher")

        # Identifikasi baris yang memiliki nilai negatif
        rows_to_drop = df[df['publishing_year'] < 0].index
        # Hapus baris yang diidentifikasi
        df.drop(rows_to_drop, inplace=True)

        # Mengubah tipe data kolom 'publishing_year' menjadi int
        df['publishing_year'] = df['publishing_year'].astype(int)

        # Hapus kata "genre" di kolom genre jika ada
        df['genre'] = df['genre'].str.replace(r'\bgenre\b', '', regex=True).str.strip()

        # Simpan data bersih
        df.to_csv(clean_path, index=False)
        print(f"Data bersih berhasil disimpan ke '{clean_path}'.")


    @task
    def post_to_elasticsearch():
        """
        Posts the cleaned data to an Elasticsearch index.
        
        This task uploads the cleaned data from the CSV file to the specified 
        Elasticsearch index for future querying and analysis.
        
        Parameters:
        None
        
        Returns:
        None
        
        Example usage:
        post_to_elasticsearch()  # This will upload the cleaned data to Elasticsearch
        """
        # Kirim data ke Elasticsearch
        es = Elasticsearch(hosts=["http://elasticsearch:9200"])
        index_name = "p2m3_nisrina_data"
        
        # Baca data dari CSV
        df = pd.read_csv('/opt/airflow/dags/P2M3_Nisrina_data_clean.csv')
        
        # Kirim data ke Elasticsearch
        for i, row in df.iterrows():
            es.index(index=index_name, id=i, body=row.to_dict())  # Gunakan 'body'

        print(f"Data berhasil diunggah ke Elasticsearch dengan index '{index_name}'.")

    # Task dependencies
    fetch_data() >> clean_data() >> post_to_elasticsearch()