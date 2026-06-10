# Personal Finance Manager — Static Web

Versi statis dari Personal Finance Manager. Menyimpan data transaksi di `localStorage` browser, menyediakan grafik, dan fitur pemindaian struk menggunakan `Tesseract.js`.

Cara pakai (direkomendasikan menjalankan server sederhana agar Tesseract.js bekerja baik):

Windows / macOS / Linux:
```bash
# Jalankan dari folder static_site
python -m http.server 8000
# lalu buka http://localhost:8000 di browser
```

Fitur:
- Tambah/hapus transaksi
- Kategori dasar
- Dashboard saldo dan grafik (Chart.js)
- Scan struk dengan OCR (Tesseract.js) — membutuhkan koneksi dan waktu proses
- Ekspor CSV

Catatan: OCR dijalankan di sisi klien sehingga akurasi bergantung pada kualitas gambar dan bahasa.
