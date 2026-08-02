import streamlit as st
st.markdown("""
    <style>
    /* Paksa Background Utama Jadi Dark Gray/Hitam */
    .stApp {
        background-color: #0E1117 !important;
    }
    
    /* Paksa Semua Teks & Judul Jadi Putih Terang */
    h1, h2, h3, h4, h5, h6, p, span, label, div {
        color: #FAFAFA !important;
    }
    
    /* Perbaiki Teks Judul Utama */
    .stMarkdown h1, .stMarkdown h2 {
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)
import sqlite3
import json
import os
import uuid
from datetime import datetime, date
 
# ==========================================================
# KONFIGURASI DASAR
# ==========================================================
st.set_page_config(
    page_title="Filladent CS Tracker",
    page_icon="🦷",
    layout="wide",
)
 
DB_PATH = os.path.join(os.path.dirname(__file__), "cs_tracker.db")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
 
CUSTOM_STEP_LABELS = {
    1: "Discussion",
    2: "Konfirmasi Pesanan",
    3: "Memproses Pesanan Customer",
    4: "Production Process (Mbak Ajeng)",
    5: "ACC Design Sample",
    6: "Pengiriman Sample",
    7: "ACC Sample",
    8: "Produksi Keseluruhan",
    9: "Pelunasan Sisa DP",
    10: "Pengiriman Keseluruhan Model",
}
 
READY_STEP_LABELS = {
    1: "Diskusi Produk & Stok",
    2: "Konfirmasi Total & Invoice",
    3: "Pembayaran Full",
    4: "Handover Gudang",
    5: "Pengiriman Final",
}
 
DEFAULT_CUSTOM_CHECKLIST = {
    "step1": {"tnc": False, "form_order": False},
    "step2": {"order_summary": False, "dp_50": False},
    "step3": {"serahkan_admin": False, "spek_jelas": False},
    "step4": {"data_sheet": False, "info_ubai": False},
    "step5": {"acc_status": None},
    "step6": {"sudah_dikirim": False},
    "step7": {"acc_status": None},
    "step8": {"produksi_selesai": False},
    "step9": {"invoice_sent": False, "pelunasan_received": False},
    "step10": {"sudah_dikirim": False},
}
 
DEFAULT_READY_CHECKLIST = {
    "step1": {"diskusi": False},
    "step2": {"konfirmasi_invoice": False},
    "step3": {"pembayaran_full": False},
    "step4": {"handover_gudang": False},
    "step5": {"pengiriman_final": False},
}
 
# ==========================================================
# PASTEL THEME (CSS)
# ==========================================================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FDF6FB;
    }
    h1, h2, h3 {
        color: #6B5B95;
        font-family: 'Trebuchet MS', sans-serif;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 10px;
        box-shadow: 0px 2px 6px rgba(0,0,0,0.06);
    }
    .cs-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 18px 22px;
        margin-bottom: 12px;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.06);
        border: 1px solid #F1E4F3;
    }
    .detail-pesanan-box {
        background-color: #FBF3FE;
        border-radius: 14px;
        padding: 14px 18px 6px 18px;
        margin: 10px 0 14px 0;
        border: 1px solid #ECD9F3;
    }
    .stButton>button {
        border-radius: 10px;
        border: none;
        background-color: #C9A7EB;
        color: white;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #B58FE0;
        color: white;
    }
    .badge-custom {
        background-color: #FFD6E8;
        color: #A2447A;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-ready {
        background-color: #CDEFDC;
        color: #2E7D52;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-deadline {
        background-color: #FFE9C7;
        color: #96650B;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
 
# ==========================================================
# DATABASE HELPERS
# ==========================================================
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
 
 
def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            nama_customer TEXT,
            no_hp TEXT,
            jenis_pesanan TEXT,
            detail_kasus TEXT,
            discussion_log TEXT,
            current_step INTEGER DEFAULT 1,
            step_checklist_json TEXT,
            items_json TEXT DEFAULT '[]',
            deadline_sample TEXT,
            deadline_final TEXT,
            bukti_pengiriman_sample TEXT,
            bukti_pengiriman_final TEXT,
            status_pembayaran_dp BOOLEAN DEFAULT 0,
            status_pelunasan BOOLEAN DEFAULT 0,
            created_at TIMESTAMP
        )
        """
    )
    conn.commit()
 
    # Migrasi ringan: kalau database lama belum punya kolom-kolom baru, tambahkan
    # tanpa menghapus data yang sudah ada.
    cur.execute("PRAGMA table_info(orders)")
    existing_columns = [row["name"] for row in cur.fetchall()]
    if "items_json" not in existing_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN items_json TEXT DEFAULT '[]'")
        conn.commit()
    if "deadline_sample" not in existing_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN deadline_sample TEXT")
        conn.commit()
    if "deadline_final" not in existing_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN deadline_final TEXT")
        conn.commit()
 
    conn.close()
 
 
def generate_order_id():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM orders")
    count = cur.fetchone()["c"]
    conn.close()
    return f"CST-{count + 1:03d}"
 
 
def add_order(nama, no_hp, jenis, catatan_awal):
    conn = get_connection()
    cur = conn.cursor()
    checklist = DEFAULT_CUSTOM_CHECKLIST if jenis == "Custom" else DEFAULT_READY_CHECKLIST
    cur.execute(
        """
        INSERT INTO orders (order_id, nama_customer, no_hp, jenis_pesanan, detail_kasus,
                             discussion_log, current_step, step_checklist_json, items_json,
                             bukti_pengiriman_sample, bukti_pengiriman_final,
                             status_pembayaran_dp, status_pelunasan, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            generate_order_id(),
            nama,
            no_hp,
            jenis,
            catatan_awal,
            "",
            1,
            json.dumps(checklist),
            json.dumps([]),
            None,
            None,
            0,
            0,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()
 
 
def get_orders(filter_jenis="All", search_query=""):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM orders WHERE 1=1"
    params = []
    if filter_jenis != "All":
        query += " AND jenis_pesanan = ?"
        params.append(filter_jenis)
    if search_query:
        query += " AND (nama_customer LIKE ? OR no_hp LIKE ?)"
        like = f"%{search_query}%"
        params.extend([like, like])
    query += " ORDER BY id DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows
 
 
def get_order_by_id(order_pk):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE id = ?", (order_pk,))
    row = cur.fetchone()
    conn.close()
    return row
 
 
def update_order_field(order_pk, field, value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE orders SET {field} = ? WHERE id = ?", (value, order_pk))
    conn.commit()
    conn.close()
 
 
def update_order_fields(order_pk, fields: dict):
    """Update satu atau beberapa kolom sekaligus (termasuk items_json, deadline_sample,
    deadline_final, dan step_checklist_json) tanpa mengganggu kolom lain yang tidak disebutkan."""
    conn = get_connection()
    cur = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [order_pk]
    cur.execute(f"UPDATE orders SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
 
 
def delete_order(order_pk):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM orders WHERE id = ?", (order_pk,))
    conn.commit()
    conn.close()
 
 
def save_uploaded_file(uploaded_file, order_id, tag):
    if uploaded_file is None:
        return None
    ext = os.path.splitext(uploaded_file.name)[1]
    filename = f"{order_id}_{tag}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return filepath
 
 
# ==========================================================
# HELPER: VARIASI MODEL (ITEMS) & TANGGAL
# ==========================================================
def load_items(order):
    try:
        items = json.loads(order["items_json"] or "[]")
    except (TypeError, json.JSONDecodeError):
        items = []
    return items
 
 
def parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
 
 
def format_id_date(value):
    d = parse_iso_date(value) if isinstance(value, str) else value
    if d is None:
        return "-"
    bulan_id = [
        "", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
        "Jul", "Agu", "Sep", "Okt", "Nov", "Des",
    ]
    return f"{d.day:02d} {bulan_id[d.month]} {d.year}"
 
 
# ==========================================================
# SESSION STATE
# ==========================================================
if "selected_order_id" not in st.session_state:
    st.session_state.selected_order_id = None
if "show_add_form" not in st.session_state:
    st.session_state.show_add_form = False
 
init_db()
 
# ==========================================================
# KOMPONEN: FORM TAMBAH PESANAN BARU
# ==========================================================
def render_add_order_form():
    with st.sidebar:
        st.markdown("### ➕ Tambah Pesanan Baru")
        with st.form("form_tambah_pesanan", clear_on_submit=True):
            nama = st.text_input("Nama Customer")
            no_hp = st.text_input("No. HP")
            jenis = st.radio("Jenis Pesanan", ["Custom", "Ready Stock"], horizontal=True)
            catatan_awal = st.text_area("Catatan Kasus Awal (opsional)")
            submitted = st.form_submit_button("Simpan Pesanan")
            if submitted:
                if not nama or not no_hp:
                    st.warning("Nama dan No. HP wajib diisi.")
                else:
                    add_order(nama, no_hp, jenis, catatan_awal)
                    st.success(f"Pesanan untuk {nama} berhasil ditambahkan! Lanjutkan isi Detail Pesanan di halaman detail.")
                    st.session_state.show_add_form = False
                    st.rerun()
        if st.button("Tutup Form"):
            st.session_state.show_add_form = False
            st.rerun()
 
 
# ==========================================================
# KOMPONEN: MAIN TABLE (HOME VIEW)
# ==========================================================
def render_home_view():
    st.markdown("# 🦷 Filladent CS Tracker")
    st.caption("Pantau progres pesanan customer dari diskusi awal sampai pengiriman final.")
 
    col_a, col_b, col_c = st.columns([2, 3, 2])
    with col_a:
        filter_jenis = st.selectbox("Filter Jenis Pesanan", ["All", "Custom", "Ready Stock"])
    with col_b:
        search_query = st.text_input("🔍 Cari Nama Customer / No. HP")
    with col_c:
        st.write("")
        st.write("")
        if st.button("➕ Tambah Pesanan Baru", use_container_width=True):
            st.session_state.show_add_form = True
 
    if st.session_state.show_add_form:
        render_add_order_form()
 
    orders = get_orders(filter_jenis, search_query)
 
    st.markdown(f"### 📋 Daftar Pesanan ({len(orders)})")
 
    if not orders:
        st.info("Belum ada data pesanan yang cocok. Tambahkan pesanan baru lewat tombol di atas.")
        return
 
    header = st.columns([2, 1.8, 1.6, 2, 2, 2, 1.3])
    for col, title in zip(
        header,
        ["Nama", "No HP", "Jenis (Item)", "Progress", "Deadline Sample", "Deadline Final", "Aksi"],
    ):
        col.markdown(f"**{title}**")
 
    for order in orders:
        checklist = json.loads(order["step_checklist_json"] or "{}")
        items = load_items(order)
        total_steps = 10 if order["jenis_pesanan"] == "Custom" else 5
        current_step = order["current_step"] or 1
        step_text = f"Step {current_step}/{total_steps}"
 
        row = st.columns([2, 1.8, 1.6, 2, 2, 2, 1.3])
        row[0].write(order["nama_customer"])
        row[1].write(order["no_hp"])
 
        badge_class = "badge-custom" if order["jenis_pesanan"] == "Custom" else "badge-ready"
        row[2].markdown(
            f'<span class="{badge_class}">{order["jenis_pesanan"]} ({len(items)} Item)</span>',
            unsafe_allow_html=True,
        )
        row[3].progress(current_step / total_steps, text=step_text)
 
        if order["deadline_sample"]:
            row[4].markdown(f'<span class="badge-deadline">{format_id_date(order["deadline_sample"])}</span>', unsafe_allow_html=True)
        else:
            row[4].write("-")
 
        if order["deadline_final"]:
            row[5].markdown(f'<span class="badge-deadline">{format_id_date(order["deadline_final"])}</span>', unsafe_allow_html=True)
        else:
            row[5].write("-")
 
        if row[6].button("View Detail", key=f"detail_{order['id']}"):
            st.session_state.selected_order_id = order["id"]
            st.rerun()
 
 
# ==========================================================
# KOMPONEN: DETAIL VIEW - "DETAIL PESANAN" (VARIASI MODEL GAYA TIKTOK SHOP)
# ==========================================================
def variant_ids_key(order_pk):
    return f"variant_ids_{order_pk}"
 
 
def init_variant_state(order_pk, order):
    ids_key = variant_ids_key(order_pk)
    if ids_key not in st.session_state:
        items = load_items(order)
        ids = []
        for it in items:
            iid = it.get("item_id") or uuid.uuid4().hex[:8]
            ids.append(iid)
            st.session_state[f"variant_name_{order_pk}_{iid}"] = it.get("tipe_model", "")
            st.session_state[f"variant_qty_{order_pk}_{iid}"] = int(it.get("jumlah_pcs") or 1)
        st.session_state[ids_key] = ids
 
 
def render_detail_pesanan_section(order):
    order_pk = order["id"]
    init_variant_state(order_pk, order)
    ids_key = variant_ids_key(order_pk)
 
    st.markdown('<div class="detail-pesanan-box">', unsafe_allow_html=True)
    st.markdown("#### 📦 Detail Pesanan")
    st.caption("Tambahkan variasi model yang dipesan customer, mirip daftar varian produk toko online.")
 
    ids = st.session_state[ids_key]
 
    if ids:
        hcol1, hcol2, hcol3 = st.columns([3, 1.3, 0.7])
        hcol1.markdown("**Nama Model / Varian**")
        hcol2.markdown("**Jumlah (Pcs)**")
        hcol3.markdown("**Aksi**")
 
        for iid in list(ids):
            c1, c2, c3 = st.columns([3, 1.3, 0.7])
            name_key = f"variant_name_{order_pk}_{iid}"
            qty_key = f"variant_qty_{order_pk}_{iid}"
            c1.text_input(
                "Nama Model/Varian",
                key=name_key,
                label_visibility="collapsed",
                placeholder="contoh: Anterior bergusi / Dengan celah Diastema",
            )
            c2.number_input(
                "Jumlah", key=qty_key, min_value=1, step=1, label_visibility="collapsed"
            )
            if c3.button("🗑️", key=f"del_variant_{order_pk}_{iid}"):
                ids.remove(iid)
                st.session_state[ids_key] = ids
                del st.session_state[name_key]
                del st.session_state[qty_key]
                st.rerun()
    else:
        st.info("Belum ada variasi model. Klik tombol di bawah untuk menambah baris baru.")
 
    if st.button("➕ Tambah Variasi Model", key=f"add_variant_{order_pk}"):
        new_id = uuid.uuid4().hex[:8]
        st.session_state[ids_key].append(new_id)
        st.session_state[f"variant_name_{order_pk}_{new_id}"] = ""
        st.session_state[f"variant_qty_{order_pk}_{new_id}"] = 1
        st.rerun()
 
    st.markdown("<br>", unsafe_allow_html=True)
 
    catatan_khusus_baru = st.text_area(
        "Catatan Kasus / Spesifikasi Khusus",
        value=order["detail_kasus"] or "",
        key=f"catatan_khusus_{order_pk}",
        height=90,
        placeholder="Catatan klinis umum: preparasi, saluran akar, sulkus, dll.",
    )
 
    dcol1, dcol2 = st.columns(2)
    default_sample = parse_iso_date(order["deadline_sample"]) or date.today()
    default_final = parse_iso_date(order["deadline_final"]) or date.today()
    with dcol1:
        deadline_sample_baru = st.date_input(
            "Deadline Sample Kirim", value=default_sample, key=f"dl_sample_{order_pk}"
        )
    with dcol2:
        deadline_final_baru = st.date_input(
            "Deadline Keseluruhan (Final)", value=default_final, key=f"dl_final_{order_pk}"
        )
 
    if st.button("💾 Simpan Detail Pesanan", key=f"save_detail_pesanan_{order_pk}", use_container_width=True):
        new_items = []
        for iid in st.session_state[ids_key]:
            name_val = (st.session_state.get(f"variant_name_{order_pk}_{iid}", "") or "").strip()
            qty_val = st.session_state.get(f"variant_qty_{order_pk}_{iid}", 1)
            if name_val:
                new_items.append({"item_id": iid, "tipe_model": name_val, "jumlah_pcs": int(qty_val)})
 
        update_order_fields(
            order_pk,
            {
                "items_json": json.dumps(new_items),
                "detail_kasus": catatan_khusus_baru,
                "deadline_sample": deadline_sample_baru.isoformat() if deadline_sample_baru else None,
                "deadline_final": deadline_final_baru.isoformat() if deadline_final_baru else None,
            },
        )
        st.success("Detail Pesanan berhasil disimpan.")
        st.rerun()
 
    st.markdown("</div>", unsafe_allow_html=True)
 
 
# ==========================================================
# KOMPONEN: DETAIL VIEW - CUSTOM CHECKLIST
# ==========================================================
def render_custom_checklist(order, checklist):
    order_pk = order["id"]
 
    # STEP 1
    with st.expander("Step 1 — Discussion", expanded=(order["current_step"] == 1)):
        checklist["step1"]["tnc"] = st.checkbox(
            "Pengiriman T&C", value=checklist["step1"]["tnc"], key=f"s1_tnc_{order_pk}"
        )
        checklist["step1"]["form_order"] = st.checkbox(
            "Custom Form Order", value=checklist["step1"]["form_order"], key=f"s1_form_{order_pk}"
        )
 
    # STEP 2
    with st.expander("Step 2 — Konfirmasi Pesanan", expanded=(order["current_step"] == 2)):
        checklist["step2"]["order_summary"] = st.checkbox(
            "Order Summary", value=checklist["step2"]["order_summary"], key=f"s2_summary_{order_pk}"
        )
        checklist["step2"]["dp_50"] = st.checkbox(
            "DP 50%", value=checklist["step2"]["dp_50"], key=f"s2_dp_{order_pk}"
        )
        if not checklist["step2"]["dp_50"]:
            st.warning("⚠️ DP 50% belum dicentang. Pesanan tidak bisa lanjut ke step berikutnya.")
 
    # STEP 3
    with st.expander("Step 3 — Memproses Pesanan Customer", expanded=(order["current_step"] == 3)):
        disabled_step3 = not checklist["step2"]["dp_50"]
        checklist["step3"]["serahkan_admin"] = st.checkbox(
            "Serahkan Order Summary ke Admin",
            value=checklist["step3"]["serahkan_admin"],
            key=f"s3_admin_{order_pk}",
            disabled=disabled_step3,
        )
        checklist["step3"]["spek_jelas"] = st.checkbox(
            "Spesifikasi Kasus Jelas",
            value=checklist["step3"]["spek_jelas"],
            key=f"s3_spek_{order_pk}",
            disabled=disabled_step3,
        )
 
    # STEP 4
    with st.expander("Step 4 — Production Process (Mbak Ajeng)", expanded=(order["current_step"] == 4)):
        checklist["step4"]["data_sheet"] = st.checkbox(
            "Memasukkan Order Data Sheet", value=checklist["step4"]["data_sheet"], key=f"s4_sheet_{order_pk}"
        )
        checklist["step4"]["info_ubai"] = st.checkbox(
            "Info ke Pak Ubai", value=checklist["step4"]["info_ubai"], key=f"s4_ubai_{order_pk}"
        )
 
    # STEP 5
    with st.expander("Step 5 — ACC Design Sample", expanded=(order["current_step"] == 5)):
        options = ["Belum dipilih", "Sudah di-ACC", "Belum Sesuai/Revisi"]
        current_val = checklist["step5"]["acc_status"] or "Belum dipilih"
        chosen = st.radio(
            "Status ACC Design Sample", options, index=options.index(current_val), key=f"s5_acc_{order_pk}"
        )
        checklist["step5"]["acc_status"] = None if chosen == "Belum dipilih" else chosen
 
    # STEP 6
    with st.expander("Step 6 — Pengiriman Sample", expanded=(order["current_step"] == 6)):
        checklist["step6"]["sudah_dikirim"] = st.checkbox(
            "Sudah dikirim?", value=checklist["step6"]["sudah_dikirim"], key=f"s6_kirim_{order_pk}"
        )
        uploaded = st.file_uploader(
            "Upload Bukti Pengiriman Sample", key=f"s6_upload_{order_pk}", type=None
        )
        if uploaded is not None:
            path = save_uploaded_file(uploaded, order["order_id"], "sample")
            update_order_field(order_pk, "bukti_pengiriman_sample", path)
            st.success("Bukti pengiriman sample berhasil diupload.")
        if order["bukti_pengiriman_sample"]:
            st.caption(f"📎 File tersimpan: {os.path.basename(order['bukti_pengiriman_sample'])}")
 
    # STEP 7
    with st.expander("Step 7 — ACC Sample", expanded=(order["current_step"] == 7)):
        options7 = ["Belum dipilih", "Sesuai", "Belum Sesuai/Revisi"]
        current_val7 = checklist["step7"]["acc_status"] or "Belum dipilih"
        chosen7 = st.radio(
            "Status ACC Sample", options7, index=options7.index(current_val7), key=f"s7_acc_{order_pk}"
        )
        checklist["step7"]["acc_status"] = None if chosen7 == "Belum dipilih" else chosen7
 
    # STEP 8
    with st.expander("Step 8 — Produksi Keseluruhan", expanded=(order["current_step"] == 8)):
        checklist["step8"]["produksi_selesai"] = st.checkbox(
            "Produksi massal selesai", value=checklist["step8"]["produksi_selesai"], key=f"s8_produksi_{order_pk}"
        )
 
    # STEP 9
    with st.expander("Step 9 — Pelunasan Sisa DP", expanded=(order["current_step"] == 9)):
        checklist["step9"]["invoice_sent"] = st.checkbox(
            "Invoice Pelunasan Sent", value=checklist["step9"]["invoice_sent"], key=f"s9_invoice_{order_pk}"
        )
        checklist["step9"]["pelunasan_received"] = st.checkbox(
            "Pelunasan Received", value=checklist["step9"]["pelunasan_received"], key=f"s9_pelunasan_{order_pk}"
        )
        if not checklist["step9"]["pelunasan_received"]:
            st.warning("⚠️ Pelunasan belum diterima. Step 10 (Pengiriman Keseluruhan) masih terkunci.")
 
    # STEP 10
    with st.expander("Step 10 — Pengiriman Keseluruhan Model", expanded=(order["current_step"] == 10)):
        disabled_step10 = not checklist["step9"]["pelunasan_received"]
        checklist["step10"]["sudah_dikirim"] = st.checkbox(
            "Sudah dikirim?",
            value=checklist["step10"]["sudah_dikirim"],
            key=f"s10_kirim_{order_pk}",
            disabled=disabled_step10,
        )
        uploaded_final = st.file_uploader(
            "Upload Bukti Pengiriman Final",
            key=f"s10_upload_{order_pk}",
            type=None,
            disabled=disabled_step10,
        )
        if uploaded_final is not None:
            path = save_uploaded_file(uploaded_final, order["order_id"], "final")
            update_order_field(order_pk, "bukti_pengiriman_final", path)
            st.success("Bukti pengiriman final berhasil diupload.")
        if order["bukti_pengiriman_final"]:
            st.caption(f"📎 File tersimpan: {os.path.basename(order['bukti_pengiriman_final'])}")
 
    return checklist
 
 
def render_ready_checklist(order, checklist):
    order_pk = order["id"]
 
    with st.expander("Step 1 — Diskusi Produk & Stok", expanded=(order["current_step"] == 1)):
        checklist["step1"]["diskusi"] = st.checkbox(
            "Diskusi produk & stok selesai", value=checklist["step1"]["diskusi"], key=f"r1_{order_pk}"
        )
 
    with st.expander("Step 2 — Konfirmasi Total & Invoice", expanded=(order["current_step"] == 2)):
        checklist["step2"]["konfirmasi_invoice"] = st.checkbox(
            "Total & invoice dikonfirmasi", value=checklist["step2"]["konfirmasi_invoice"], key=f"r2_{order_pk}"
        )
 
    with st.expander("Step 3 — Pembayaran Full", expanded=(order["current_step"] == 3)):
        checklist["step3"]["pembayaran_full"] = st.checkbox(
            "Pembayaran full diterima", value=checklist["step3"]["pembayaran_full"], key=f"r3_{order_pk}"
        )
        if not checklist["step3"]["pembayaran_full"]:
            st.warning("⚠️ Pembayaran full belum diterima. Step selanjutnya masih terkunci.")
 
    with st.expander("Step 4 — Handover Gudang", expanded=(order["current_step"] == 4)):
        disabled_step4 = not checklist["step3"]["pembayaran_full"]
        checklist["step4"]["handover_gudang"] = st.checkbox(
            "Sudah handover ke gudang", value=checklist["step4"]["handover_gudang"],
            key=f"r4_{order_pk}", disabled=disabled_step4,
        )
 
    with st.expander("Step 5 — Pengiriman Final", expanded=(order["current_step"] == 5)):
        checklist["step5"]["pengiriman_final"] = st.checkbox(
            "Sudah dikirim?", value=checklist["step5"]["pengiriman_final"], key=f"r5_{order_pk}"
        )
        uploaded_final = st.file_uploader("Upload Bukti Pengiriman Final", key=f"r5_upload_{order_pk}")
        if uploaded_final is not None:
            path = save_uploaded_file(uploaded_final, order["order_id"], "final")
            update_order_field(order_pk, "bukti_pengiriman_final", path)
            st.success("Bukti pengiriman final berhasil diupload.")
        if order["bukti_pengiriman_final"]:
            st.caption(f"📎 File tersimpan: {os.path.basename(order['bukti_pengiriman_final'])}")
 
    return checklist
 
 
def compute_current_step(jenis, checklist):
    """Hitung current_step otomatis berdasarkan checklist yang sudah selesai,
    dengan menghormati gating (DP 50% dan Pelunasan)."""
    if jenis == "Custom":
        order_keys = [f"step{i}" for i in range(1, 11)]
 
        def step_done(key):
            data = checklist[key]
            if key == "step5":
                return data["acc_status"] == "Sudah di-ACC"
            if key == "step7":
                return data["acc_status"] == "Sesuai"
            return all(v is True for v in data.values() if isinstance(v, bool)) and len(
                [v for v in data.values() if isinstance(v, bool)]
            ) > 0
    else:
        order_keys = [f"step{i}" for i in range(1, 6)]
 
        def step_done(key):
            data = checklist[key]
            return all(v is True for v in data.values())
 
    current = 1
    for i, key in enumerate(order_keys, start=1):
        if step_done(key):
            current = min(i + 1, len(order_keys))
        else:
            current = i
            break
    else:
        current = len(order_keys)
    return current
 
 
def render_detail_view(order_pk):
    order = get_order_by_id(order_pk)
    if order is None:
        st.error("Data pesanan tidak ditemukan.")
        st.session_state.selected_order_id = None
        return
 
    if st.button("⬅️ Kembali ke Daftar Pesanan"):
        st.session_state.selected_order_id = None
        st.rerun()
 
    st.markdown(f"## 👤 Detail Customer — {order['nama_customer']}")
 
    col_left, col_right = st.columns([1, 1.4])
 
    checklist = json.loads(order["step_checklist_json"] or "{}")
 
    with col_left:
        st.markdown('<div class="cs-card">', unsafe_allow_html=True)
        st.markdown("#### Profil Customer")
        st.write(f"**Order ID:** {order['order_id']}")
        st.write(f"**Dibuat pada:** {order['created_at']}")
 
        nama_baru = st.text_input("Nama Customer", value=order["nama_customer"], key=f"nama_{order_pk}")
        no_hp_baru = st.text_input("No. HP", value=order["no_hp"], key=f"hp_{order_pk}")
 
        jenis_baru = st.radio(
            "Jenis Pesanan",
            ["Custom", "Ready Stock"],
            index=0 if order["jenis_pesanan"] == "Custom" else 1,
            horizontal=True,
            key=f"jenis_{order_pk}",
        )
 
        # ---- Section "Detail Pesanan" tepat di bawah Jenis Pesanan ----
        render_detail_pesanan_section(order)
 
        discussion_log_baru = st.text_area(
            "💬 Discussion Log (update progres obrolan CS)",
            value=order["discussion_log"] or "",
            key=f"log_{order_pk}",
            height=130,
        )
 
        if st.button("💾 Simpan Perubahan Profil", key=f"save_profile_{order_pk}"):
            update_fields = {
                "nama_customer": nama_baru,
                "no_hp": no_hp_baru,
                "jenis_pesanan": jenis_baru,
                "discussion_log": discussion_log_baru,
            }
            # reset checklist jika jenis pesanan berubah (Detail Pesanan tetap dipertahankan)
            if jenis_baru != order["jenis_pesanan"]:
                new_checklist = DEFAULT_CUSTOM_CHECKLIST if jenis_baru == "Custom" else DEFAULT_READY_CHECKLIST
                update_fields["step_checklist_json"] = json.dumps(new_checklist)
                update_fields["current_step"] = 1
                st.info("Jenis pesanan diubah, checklist progres direset sesuai alur baru.")
            update_order_fields(order_pk, update_fields)
            st.success("Profil customer berhasil diperbarui.")
            st.rerun()
 
        st.markdown("---")
        if st.button("🗑️ Hapus Pesanan Ini", key=f"delete_{order_pk}"):
            delete_order(order_pk)
            st.session_state.selected_order_id = None
            st.success("Pesanan dihapus.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
 
    with col_right:
        st.markdown('<div class="cs-card">', unsafe_allow_html=True)
        st.markdown("#### Interactive Checklist Progress")
 
        # re-fetch data terbaru (bisa berubah dari kolom kiri)
        current_order = get_order_by_id(order_pk)
        checklist = json.loads(current_order["step_checklist_json"] or "{}")
 
        if current_order["jenis_pesanan"] == "Custom":
            total_steps = 10
            checklist = render_custom_checklist(current_order, checklist)
        else:
            total_steps = 5
            checklist = render_ready_checklist(current_order, checklist)
 
        new_current_step = compute_current_step(current_order["jenis_pesanan"], checklist)
 
        step_labels = CUSTOM_STEP_LABELS if current_order["jenis_pesanan"] == "Custom" else READY_STEP_LABELS
        st.progress(
            new_current_step / total_steps,
            text=f"Step {new_current_step}/{total_steps}: {step_labels.get(new_current_step, '-')}",
        )
 
        if st.button("💾 Simpan Progress Checklist", key=f"save_checklist_{order_pk}"):
            status_dp = False
            status_pelunasan = False
            if current_order["jenis_pesanan"] == "Custom":
                status_dp = bool(checklist["step2"]["dp_50"])
                status_pelunasan = bool(checklist["step9"]["pelunasan_received"])
            else:
                status_dp = bool(checklist["step3"]["pembayaran_full"])
                status_pelunasan = bool(checklist["step3"]["pembayaran_full"])
 
            update_order_fields(
                order_pk,
                {
                    "step_checklist_json": json.dumps(checklist),
                    "current_step": new_current_step,
                    "status_pembayaran_dp": int(status_dp),
                    "status_pelunasan": int(status_pelunasan),
                },
            )
            st.success("Progress checklist berhasil disimpan.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
 
 
# ==========================================================
# ROUTER UTAMA
# ==========================================================
if st.session_state.selected_order_id is not None:
    render_detail_view(st.session_state.selected_order_id)
else:
    render_home_view()
 
