// Simple static finance manager using localStorage
const STORAGE_KEY = 'pfm_transactions_v1'

function loadTransactions(){
  const raw = localStorage.getItem(STORAGE_KEY)
  return raw ? JSON.parse(raw) : []
}

function saveTransactions(tx){
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tx))
}

function formatIDR(n){
  return 'Rp ' + Number(n).toLocaleString('id-ID')
}

function renderTransactions(){
  const txs = loadTransactions().slice().reverse()
  const container = document.getElementById('transactions')
  container.innerHTML = ''
  txs.forEach(t=>{
    const el = document.createElement('div')
    el.className = 'tx-item ' + (t.type==='income' ? 'income' : 'expense')
    el.innerHTML = `
      <div class="d-flex justify-content-between">
        <div>
          <strong>${t.description}</strong><br><small class="text-muted">${t.date}</small>
        </div>
        <div class="text-end">
          <div class="tx-amount ${t.type==='income' ? 'text-success' : 'text-danger'}">${t.type==='income' ? '+' : '-'} ${formatIDR(t.amount)}</div>
          <div><small class="text-muted">${t.category || ''}</small></div>
          <div><button class="btn btn-sm btn-outline-danger mt-1" onclick="deleteTransaction(${t.id})">Hapus</button></div>
        </div>
      </div>
    `
    container.appendChild(el)
  })
  renderSummary()
}

function renderSummary(){
  const txs = loadTransactions()
  let income = 0, expense = 0
  const byCat = {}
  const byDay = {}
  txs.forEach(t=>{
    if(t.type==='income') income += Number(t.amount)
    else expense += Number(t.amount)
    const c = t.category || 'Lain-lain'
    byCat[c] = (byCat[c]||0) + Number(t.amount)
    const day = (new Date(t.date)).toLocaleDateString('id-ID')
    byDay[day] = (byDay[day]||0) + (t.type==='income' ? Number(t.amount) : -Number(t.amount))
  })
  document.getElementById('balance').innerText = formatIDR(income - expense)
  document.getElementById('totalIncome').innerText = formatIDR(income)
  document.getElementById('totalExpense').innerText = formatIDR(expense)
  renderPie(Object.entries(byCat))
  renderLine(Object.entries(byDay).sort((a,b)=> new Date(a[0]) - new Date(b[0])))
}

function renderPie(data){
  const ctx = document.getElementById('pieChart').getContext('2d')
  if(window._pie) window._pie.destroy()
  window._pie = new Chart(ctx,{type:'doughnut',data:{labels:data.map(d=>d[0]),datasets:[{data:data.map(d=>d[1]),backgroundColor:['#ff6384','#36a2eb','#ffcd56','#4bc0c0','#9966ff','#28a745','#dc3545','#888']}]},options:{plugins:{legend:{position:'right'}}}})
}

function renderLine(data){
  const labels = data.map(d=>d[0])
  const vals = data.map(d=>d[1])
  const ctx = document.getElementById('lineChart').getContext('2d')
  if(window._line) window._line.destroy()
  window._line = new Chart(ctx,{type:'bar',data:{labels, datasets:[{label:'Saldo per hari',data:vals,backgroundColor:'#667eea'}]},options:{scales:{y:{beginAtZero:true}}}})
}

function addTransaction(e){
  e && e.preventDefault()
  const desc = document.getElementById('description').value.trim()
  const amount = Number(document.getElementById('amount').value)
  const type = document.getElementById('type').value
  const category = document.getElementById('category').value
  if(!desc || !amount) return alert('Isi deskripsi dan jumlah')
  const tx = loadTransactions()
  const id = tx.length ? Math.max(...tx.map(t=>t.id))+1 : 1
  tx.push({id, description:desc, amount, type, category, date: new Date().toISOString()})
  saveTransactions(tx)
  document.getElementById('txForm').reset()
  renderTransactions()
}

function deleteTransaction(id){
  const tx = loadTransactions().filter(t=>t.id!==id)
  saveTransactions(tx)
  renderTransactions()
}

function exportCSV(){
  const tx = loadTransactions()
  if(!tx.length) return alert('Belum ada data')
  const rows = [['id','description','amount','type','category','date']].concat(tx.map(t=>[t.id,t.description,t.amount,t.type,t.category,t.date]))
  const csv = rows.map(r=>r.map(c=>`"${String(c).replace(/"/g,'""')}"`).join(',')).join('\n')
  const blob = new Blob([csv],{type:'text/csv;charset=utf-8;'})
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'transactions.csv'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)
}

function clearAll(){
  if(!confirm('Hapus semua data transaksi?')) return
  localStorage.removeItem(STORAGE_KEY)
  renderTransactions()
}

async function scanReceipt(){
  const file = document.getElementById('receiptFile').files[0]
  if(!file) return alert('Pilih gambar terlebih dahulu')
  document.getElementById('ocrResult').style.display='block'
  document.getElementById('ocrResult').innerText = 'Memproses OCR...'
  try{
    const { data: { text } } = await Tesseract.recognize(file, 'ind')
    document.getElementById('ocrResult').innerText = text
    // basic extraction
    const nums = text.match(/[\d\.,]+/g) || []
    const cleaned = nums.map(n=>Number(n.replace(/[^\d]/g,''))).filter(Boolean)
    const total = cleaned.length ? Math.max(...cleaned) : 0
    const lines = text.split('\n').map(s=>s.trim()).filter(Boolean)
    const merchant = lines.length ? lines[0] : ''
    // prefill form
    document.getElementById('description').value = merchant
    document.getElementById('amount').value = total
  }catch(err){
    document.getElementById('ocrResult').innerText = 'OCR error: '+err.message
  }
}

// Camera capture + OCR flow
let _stream = null
const video = document.getElementById('video')
const canvas = document.getElementById('captureCanvas')

async function startCamera(){
  try{
    _stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
    video.srcObject = _stream
    document.getElementById('cameraArea').style.display = 'block'
    document.getElementById('openCamera').style.display = 'none'
    document.getElementById('stopCamera').style.display = 'inline-block'
  }catch(e){
    alert('Gagal membuka kamera: '+e.message)
  }
}

function stopCamera(){
  if(_stream){
    _stream.getTracks().forEach(t=>t.stop())
    _stream = null
  }
  video.srcObject = null
  document.getElementById('cameraArea').style.display = 'none'
  document.getElementById('openCamera').style.display = 'inline-block'
  document.getElementById('stopCamera').style.display = 'none'
}

async function captureImage(){
  const w = video.videoWidth
  const h = video.videoHeight
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video,0,0,w,h)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.9)
  document.getElementById('retakeBtn').style.display = 'inline-block'
  document.getElementById('captureBtn').style.display = 'none'
  document.getElementById('ocrResult').style.display='block'
  document.getElementById('ocrResult').innerText = 'Memproses OCR...'
  try{
    const blob = await (await fetch(dataUrl)).blob()
    const { data: { text } } = await Tesseract.recognize(blob, 'ind')
    document.getElementById('ocrResult').innerText = text
    const nums = text.match(/[\d\.,]+/g) || []
    const cleaned = nums.map(n=>Number(n.replace(/[^\d]/g,''))).filter(Boolean)
    const total = cleaned.length ? Math.max(...cleaned) : 0
    const lines = text.split('\n').map(s=>s.trim()).filter(Boolean)
    const merchant = lines.length ? lines[0] : ''
    document.getElementById('description').value = merchant
    document.getElementById('amount').value = total
    // stop camera automatically
    stopCamera()
  }catch(err){
    document.getElementById('ocrResult').innerText = 'OCR error: '+err.message
  }
}

function retake(){
  document.getElementById('retakeBtn').style.display = 'none'
  document.getElementById('captureBtn').style.display = 'inline-block'
  document.getElementById('ocrResult').style.display='none'
  startCamera()
}

// Wire camera buttons
document.getElementById('openCamera').addEventListener('click', startCamera)
document.getElementById('stopCamera').addEventListener('click', stopCamera)
document.getElementById('captureBtn').addEventListener('click', captureImage)
document.getElementById('retakeBtn').addEventListener('click', retake)

// Event bindings
document.getElementById('txForm').addEventListener('submit', addTransaction)
document.getElementById('exportCsv').addEventListener('click', exportCSV)
document.getElementById('clearAll').addEventListener('click', clearAll)
document.getElementById('scanBtn').addEventListener('click', scanReceipt)

// Initialize
renderTransactions()
