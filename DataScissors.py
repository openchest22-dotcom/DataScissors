import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
import hashlib
import queue
import re  # Yeni: regex için eklendi

# ================== XP Stili ==================
def set_xp_style():
    style = ttk.Style()
    try:
        style.theme_use('winnative')
    except:
        pass
    xp_font = ("Tahoma", 8)
    xp_bold_font = ("Tahoma", 8, "bold")
    style.configure("TButton", font=xp_font, padding=3)
    style.configure("TLabel", font=xp_font)
    style.configure("TEntry", font=xp_font)
    style.configure("TRadiobutton", font=xp_font)
    return xp_font, xp_bold_font

# ================== Ana Uygulama ==================
class FileSplitterXP:
    def __init__(self, root, xp_font, xp_bold_font):
        self.root = root
        self.root.title("DataScissors v1.1")  # Sürüm yükseltildi
        self.root.geometry("500x520")  # Yeni elemanlar için biraz yükseklik arttı
        self.root.resizable(False, False)

        # Değişkenler
        self.xp_font = xp_font
        self.xp_bold_font = xp_bold_font
        self.split_thread = None
        self.merge_thread = None
        self.cancel_flag = False
        self.queue = queue.Queue()

        # Ana notebook (sekmeler)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Sekme 1: Dosya Bölme
        self.tab_split = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_split, text="Dosya Böl")
        self.setup_split_tab()

        # Sekme 2: Parçaları Birleştir
        self.tab_merge = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_merge, text="Parçaları Birleştir")
        self.setup_merge_tab()

        # İlerleme durumunu güncellemek için periyodik kontrol
        self.root.after(100, self.process_queue)

    # ========== Bölme Sekmesi ==========
    def setup_split_tab(self):
        tab = self.tab_split

        # Kaynak dosya
        ttk.Label(tab, text="Bölünecek Dosya:", font=self.xp_bold_font).grid(row=0, column=0, sticky="w", pady=5)
        self.src_entry = ttk.Entry(tab, width=40)
        self.src_entry.grid(row=1, column=0, columnspan=2, padx=5, sticky="ew")
        ttk.Button(tab, text="Gözat...", command=self.browse_source).grid(row=1, column=2, padx=5)

        # Bölme modu seçimi
        self.split_mode = tk.StringVar(value="parts")
        ttk.Radiobutton(tab, text="Parça sayısına göre", variable=self.split_mode, value="parts", command=self.toggle_split_mode).grid(row=2, column=0, sticky="w", pady=5)
        ttk.Radiobutton(tab, text="Parça boyutuna göre (MB)", variable=self.split_mode, value="size", command=self.toggle_split_mode).grid(row=2, column=1, sticky="w", pady=5)

        # Parça sayısı girişi
        self.parts_frame = ttk.Frame(tab)
        self.parts_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Label(self.parts_frame, text="Parça sayısı:").pack(side=tk.LEFT)
        self.parts_spinbox = ttk.Spinbox(self.parts_frame, from_=2, to=100, width=5)
        self.parts_spinbox.pack(side=tk.LEFT, padx=5)
        self.parts_spinbox.set(4)

        # Parça boyutu girişi (başlangıçta gizli)
        self.size_frame = ttk.Frame(tab)
        self.size_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Label(self.size_frame, text="Parça boyutu (MB):").pack(side=tk.LEFT)
        self.size_spinbox = ttk.Spinbox(self.size_frame, from_=1, to=1024, width=5)
        self.size_spinbox.pack(side=tk.LEFT, padx=5)
        self.size_spinbox.set(10)
        self.size_frame.grid_remove()  # başlangıçta gizle

        # Çıktı klasörü
        ttk.Label(tab, text="Çıktı klasörü:", font=self.xp_bold_font).grid(row=4, column=0, sticky="w", pady=5)
        self.out_folder_entry = ttk.Entry(tab, width=40)
        self.out_folder_entry.grid(row=5, column=0, columnspan=2, padx=5, sticky="ew")
        ttk.Button(tab, text="Gözat...", command=self.browse_output_folder).grid(row=5, column=2, padx=5)

        # Butonlar
        btn_frame = ttk.Frame(tab)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=10)
        self.split_btn = ttk.Button(btn_frame, text="Bölmeyi Başlat", command=self.start_split)
        self.split_btn.pack(side=tk.LEFT, padx=5)
        self.cancel_split_btn = ttk.Button(btn_frame, text="İptal", state=tk.DISABLED, command=self.cancel_split)
        self.cancel_split_btn.pack(side=tk.LEFT, padx=5)

        # İlerleme çubuğu ve durum
        self.split_progress = ttk.Progressbar(tab, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.split_progress.grid(row=7, column=0, columnspan=3, pady=5, padx=5)
        self.split_status = ttk.Label(tab, text="Hazır", font=self.xp_font)
        self.split_status.grid(row=8, column=0, columnspan=3, sticky="w", padx=5)

        # Ağırlıklandırma
        tab.columnconfigure(1, weight=1)

    def toggle_split_mode(self):
        if self.split_mode.get() == "parts":
            self.parts_frame.grid()
            self.size_frame.grid_remove()
        else:
            self.parts_frame.grid_remove()
            self.size_frame.grid()

    def browse_source(self):
        path = filedialog.askopenfilename()
        if path:
            self.src_entry.delete(0, tk.END)
            self.src_entry.insert(0, path)
            # Çıktı klasörü varsayılan olarak kaynak dosyanın klasörü
            if not self.out_folder_entry.get():
                self.out_folder_entry.delete(0, tk.END)
                self.out_folder_entry.insert(0, os.path.dirname(path))

    def browse_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.out_folder_entry.delete(0, tk.END)
            self.out_folder_entry.insert(0, folder)

    def start_split(self):
        src = self.src_entry.get().strip()
        if not src or not os.path.isfile(src):
            messagebox.showerror("Hata", "Geçerli bir dosya seçin.")
            return

        out_folder = self.out_folder_entry.get().strip()
        if not out_folder:
            out_folder = os.path.dirname(src)
            self.out_folder_entry.insert(0, out_folder)
        elif not os.path.isdir(out_folder):
            messagebox.showerror("Hata", "Çıktı klasörü geçerli değil.")
            return

        try:
            if self.split_mode.get() == "parts":
                num_parts = int(self.parts_spinbox.get())
                if num_parts < 2:
                    raise ValueError
                self.split_by_parts(src, out_folder, num_parts)
            else:
                part_size_mb = float(self.size_spinbox.get())
                if part_size_mb <= 0:
                    raise ValueError
                self.split_by_size(src, out_folder, part_size_mb)
        except ValueError:
            messagebox.showerror("Hata", "Parça sayısı/boyutu geçersiz.")
            return

    def split_by_parts(self, src, out_folder, num_parts):
        file_size = os.path.getsize(src)
        part_size = file_size // num_parts
        self._start_split_thread(src, out_folder, part_size, num_parts, by_parts=True)

    def split_by_size(self, src, out_folder, part_size_mb):
        part_size_bytes = int(part_size_mb * 1024 * 1024)
        file_size = os.path.getsize(src)
        num_parts = (file_size + part_size_bytes - 1) // part_size_bytes  # tavan bölme
        self._start_split_thread(src, out_folder, part_size_bytes, num_parts, by_parts=False)

    def _start_split_thread(self, src, out_folder, part_size, num_parts, by_parts):
        # UI hazırlığı
        self.cancel_flag = False
        self.split_btn.config(state=tk.DISABLED)
        self.cancel_split_btn.config(state=tk.NORMAL)
        self.split_progress['maximum'] = 100
        self.split_progress['value'] = 0
        self.split_status.config(text="Bölme başlıyor...")

        # Thread'i başlat
        self.split_thread = threading.Thread(target=self._split_worker,
                                             args=(src, out_folder, part_size, num_parts, by_parts),
                                             daemon=True)
        self.split_thread.start()

    def _split_worker(self, src, out_folder, part_size, num_parts, by_parts):
        try:
            base_name = os.path.basename(src)
            name_without_ext = os.path.splitext(base_name)[0]
            ext = os.path.splitext(base_name)[1]
            out_prefix = os.path.join(out_folder, name_without_ext)

            file_size = os.path.getsize(src)
            bytes_processed = 0
            part_num = 0

            with open(src, 'rb') as infile:
                while part_num < num_parts and not self.cancel_flag:
                    # Bu parçanın boyutunu belirle (son parça kalan tüm veri)
                    if part_num == num_parts - 1 and by_parts:
                        # Parça sayısına göre bölmede son parça kalan tüm veri
                        current_part_size = file_size - bytes_processed
                    else:
                        current_part_size = part_size

                    out_filename = f"{out_prefix}.part{part_num+1}{ext}"
                    bytes_written = 0
                    with open(out_filename, 'wb') as outfile:
                        while bytes_written < current_part_size and not self.cancel_flag:
                            chunk_size = min(1024*1024, current_part_size - bytes_written)  # 1 MB bloklar
                            chunk = infile.read(chunk_size)
                            if not chunk:
                                break
                            outfile.write(chunk)
                            bytes_written += len(chunk)
                            bytes_processed += len(chunk)
                            # İlerleme yüzdesi
                            progress = (bytes_processed / file_size) * 100
                            self.queue.put(('progress', progress))
                            self.queue.put(('status', f"Parça {part_num+1} yazılıyor... %{progress:.1f}"))
                    part_num += 1

            if self.cancel_flag:
                self.queue.put(('status', "İşlem iptal edildi."))
                # İptal edildiyse yazılan parçaları silmek isteyebiliriz (opsiyonel)
            else:
                self.queue.put(('done', "Bölme tamamlandı!", out_folder))
        except Exception as e:
            self.queue.put(('error', f"Hata: {str(e)}"))
        finally:
            self.queue.put(('split_finished',))

    # ========== Birleştirme Sekmesi ==========
    def setup_merge_tab(self):
        tab = self.tab_merge

        # Parça dosyaları seçimi (birden fazla seçilebilir)
        ttk.Label(tab, text="Parça Dosyaları (.partX):", font=self.xp_bold_font).grid(row=0, column=0, sticky="w", pady=5)
        self.parts_listbox = tk.Listbox(tab, height=5, selectmode=tk.EXTENDED)
        self.parts_listbox.grid(row=1, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.parts_listbox.yview)
        scrollbar.grid(row=1, column=2, sticky="ns")
        self.parts_listbox.config(yscrollcommand=scrollbar.set)
        ttk.Button(tab, text="Parçaları Ekle...", command=self.add_parts).grid(row=2, column=0, padx=5, pady=2, sticky="w")
        ttk.Button(tab, text="Temizle", command=self.clear_parts).grid(row=2, column=1, padx=5, pady=2, sticky="w")

        # Çıktı dosyası adı
        ttk.Label(tab, text="Birleştirilmiş dosya adı:", font=self.xp_bold_font).grid(row=3, column=0, sticky="w", pady=5)
        self.merged_name_entry = ttk.Entry(tab, width=40)
        self.merged_name_entry.grid(row=4, column=0, columnspan=2, padx=5, sticky="ew")
        ttk.Button(tab, text="Gözat...", command=self.browse_merged_output).grid(row=4, column=2, padx=5)

        # Hash doğrulama seçenekleri (geliştirilmiş)
        verify_frame = ttk.Frame(tab)
        verify_frame.grid(row=5, column=0, columnspan=3, sticky="w", pady=5)
        self.verify_var = tk.BooleanVar(value=True)
        self.verify_cb = ttk.Checkbutton(verify_frame, text="Birleştirme sonrası hash doğrulaması yap", variable=self.verify_var)
        self.verify_cb.pack(side=tk.LEFT)

        # Hash algoritması seçimi
        ttk.Label(verify_frame, text="Algoritma:").pack(side=tk.LEFT, padx=(10,2))
        self.hash_algo = tk.StringVar(value="MD5")
        self.hash_combo = ttk.Combobox(verify_frame, textvariable=self.hash_algo, values=["MD5", "SHA1", "SHA256"], state="readonly", width=8)
        self.hash_combo.pack(side=tk.LEFT)

        # Butonlar
        btn_frame = ttk.Frame(tab)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=10)
        self.merge_btn = ttk.Button(btn_frame, text="Birleştirmeyi Başlat", command=self.start_merge)
        self.merge_btn.pack(side=tk.LEFT, padx=5)
        self.cancel_merge_btn = ttk.Button(btn_frame, text="İptal", state=tk.DISABLED, command=self.cancel_merge)
        self.cancel_merge_btn.pack(side=tk.LEFT, padx=5)

        # İlerleme çubuğu ve durum
        self.merge_progress = ttk.Progressbar(tab, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.merge_progress.grid(row=7, column=0, columnspan=3, pady=5, padx=5)
        self.merge_status = ttk.Label(tab, text="Hazır", font=self.xp_font)
        self.merge_status.grid(row=8, column=0, columnspan=3, sticky="w", padx=5)

        tab.columnconfigure(1, weight=1)

    def add_parts(self):
        files = filedialog.askopenfilenames(title="Parça dosyalarını seçin")
        for f in files:
            self.parts_listbox.insert(tk.END, f)
        # Otomatik çıktı adı oluştur (ilk parçanın adından yola çıkarak)
        if self.parts_listbox.size() > 0 and not self.merged_name_entry.get():
            first = self.parts_listbox.get(0)
            # .partX ifadesini temizle (regex ile)
            base = re.sub(r'\.part\d+', '', first)  # Yeni: daha güvenli temizleme
            self.merged_name_entry.delete(0, tk.END)
            self.merged_name_entry.insert(0, base)

    def clear_parts(self):
        self.parts_listbox.delete(0, tk.END)

    def browse_merged_output(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".bin", filetypes=[("Tüm dosyalar", "*.*")])
        if file_path:
            self.merged_name_entry.delete(0, tk.END)
            self.merged_name_entry.insert(0, file_path)

    def start_merge(self):
        parts = list(self.parts_listbox.get(0, tk.END))
        if not parts:
            messagebox.showerror("Hata", "En az bir parça dosyası seçin.")
            return
        output = self.merged_name_entry.get().strip()
        if not output:
            messagebox.showerror("Hata", "Çıktı dosya adını belirtin.")
            return

        self.cancel_flag = False
        self.merge_btn.config(state=tk.DISABLED)
        self.cancel_merge_btn.config(state=tk.NORMAL)
        self.merge_progress['maximum'] = 100
        self.merge_progress['value'] = 0
        self.merge_status.config(text="Birleştirme başlıyor...")

        self.merge_thread = threading.Thread(target=self._merge_worker,
                                             args=(parts, output, self.verify_var.get(), self.hash_algo.get()),
                                             daemon=True)
        self.merge_thread.start()

    def _merge_worker(self, parts, output, verify, hash_algo):
        try:
            # 1. Parçaları sırala (dosya adındaki .partX'e göre)
            def part_sort_key(filename):
                match = re.search(r'\.part(\d+)', filename)
                if match:
                    return int(match.group(1))
                return filename  # sayı bulunamazsa alfabetik sırala
            parts_sorted = sorted(parts, key=part_sort_key)  # Yeni: sıralama eklendi

            total_size = 0
            for p in parts_sorted:
                total_size += os.path.getsize(p)

            # 2. Dinamik tampon boyutu belirle (dosya boyutuna göre)
            if total_size > 1024 * 1024 * 1024:  # 1 GB'den büyük
                buffer_size = 8 * 1024 * 1024
            elif total_size > 100 * 1024 * 1024:  # 100 MB - 1 GB
                buffer_size = 4 * 1024 * 1024
            else:  # 100 MB'den küçük
                buffer_size = 1024 * 1024  # 1 MB

            bytes_processed = 0
            with open(output, 'wb') as outfile:
                for i, part in enumerate(parts_sorted):
                    if self.cancel_flag:
                        break
                    with open(part, 'rb') as infile:
                        while True:
                            chunk = infile.read(buffer_size)  # Dinamik buffer kullanımı
                            if not chunk:
                                break
                            outfile.write(chunk)
                            bytes_processed += len(chunk)
                            progress = (bytes_processed / total_size) * 100
                            self.queue.put(('progress', progress))
                            self.queue.put(('status', f"Parça {i+1}/{len(parts_sorted)} birleştiriliyor... %{progress:.1f}"))
                            if self.cancel_flag:
                                break

            if self.cancel_flag:
                self.queue.put(('status', "Birleştirme iptal edildi."))
                if os.path.exists(output):
                    os.remove(output)
            else:
                if verify:
                    self.queue.put(('status', f"{hash_algo} doğrulaması yapılıyor..."))
                    # Seçilen algoritma ile hash hesapla
                    if hash_algo == "MD5":
                        hash_obj = hashlib.md5()
                    elif hash_algo == "SHA1":
                        hash_obj = hashlib.sha1()
                    elif hash_algo == "SHA256":
                        hash_obj = hashlib.sha256()
                    else:
                        hash_obj = hashlib.md5()  # varsayılan

                    with open(output, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_obj.update(chunk)
                    hash_digest = hash_obj.hexdigest()
                    self.queue.put(('status', f"Birleştirme tamamlandı. {hash_algo}: {hash_digest}"))
                else:
                    self.queue.put(('status', "Birleştirme tamamlandı."))
                self.queue.put(('done', "Birleştirme başarıyla tamamlandı!", os.path.dirname(output)))
        except Exception as e:
            self.queue.put(('error', f"Hata: {str(e)}"))
        finally:
            self.queue.put(('merge_finished',))

    # ========== Ortak Yardımcı Metotlar ==========
    def cancel_split(self):
        self.cancel_flag = True
        self.split_status.config(text="İptal ediliyor...")

    def cancel_merge(self):
        self.cancel_flag = True
        self.merge_status.config(text="İptal ediliyor...")

    def process_queue(self):
        """GUI güncellemelerini kuyruktan alır."""
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg[0] == 'progress':
                    if hasattr(self, 'split_progress') and self.split_progress.winfo_exists():
                        self.split_progress['value'] = msg[1]
                    if hasattr(self, 'merge_progress') and self.merge_progress.winfo_exists():
                        self.merge_progress['value'] = msg[1]
                elif msg[0] == 'status':
                    if hasattr(self, 'split_status') and self.split_status.winfo_exists():
                        self.split_status.config(text=msg[1])
                    if hasattr(self, 'merge_status') and self.merge_status.winfo_exists():
                        self.merge_status.config(text=msg[1])
                elif msg[0] == 'done':
                    messagebox.showinfo("Tamam", msg[1])
                    folder = msg[2]
                    if os.path.exists(folder) and os.name == 'nt':
                        os.startfile(folder)
                elif msg[0] == 'error':
                    messagebox.showerror("Hata", msg[1])
                elif msg[0] == 'split_finished':
                    self.split_btn.config(state=tk.NORMAL)
                    self.cancel_split_btn.config(state=tk.DISABLED)
                elif msg[0] == 'merge_finished':
                    self.merge_btn.config(state=tk.NORMAL)
                    self.cancel_merge_btn.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

# ================== Ana Program ==================
if __name__ == "__main__":
    root = tk.Tk()
    xp_f, xp_bf = set_xp_style()
    app = FileSplitterXP(root, xp_f, xp_bf)
    root.mainloop()
