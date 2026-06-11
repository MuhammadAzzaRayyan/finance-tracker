# Personal Finance Manager

Aplikasi web pengelola keuangan pribadi sederhana berbasis Python Flask.

## Fitur Utama
✅ Tambah transaksi (pemasukan/pengeluaran)
✅ Lihat daftar transaksi
✅ Hitung saldo otomatis
✅ Hapus transaksi
✅ API endpoint untuk data transaksi

## Struktur Folder

## Perubahan (MVP yang ditambahkan)

- Dukungan `wallets` (dompet) dengan saldo awal dan transfer antar dompet.
- `categories` dan `subcategories` untuk mengkategorikan transaksi.
- Form input cepat: pilih dompet, kategori, tipe, jumlah, deskripsi.
- Endpoint ekspor CSV (`/export`) untuk men-download semua transaksi.
- Perhitungan saldo sekarang berdasarkan dompet + transaksi.
- Tombol tambah dompet dan form transfer di UI.

Catatan: fitur recurring, budgeting, notifikasi, grafik, dan keamanan PIN akan ditambahkan bertahap sesuai rencana.
