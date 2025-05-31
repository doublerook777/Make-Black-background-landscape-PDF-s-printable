print("Launching TouchPDFs...")

import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# === STEP 1: Conditional admin relaunch only if needed ===
def is_admin():
    if os.name != 'nt':
        return True
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def relaunch_as_admin():
    import ctypes
    params = ' '.join([f'"{arg}"' for arg in sys.argv if arg != '--elevated']) + ' --elevated'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit()

# === STEP 2: Check and install packages ===
def check_and_install(package, pip_name):
    try:
        __import__(package)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
        except subprocess.CalledProcessError:
            if '--elevated' not in sys.argv:
                resp = messagebox.askyesno("Admin Required",
                    f"Missing package '{pip_name}' could not be installed.\n\nDo you want to relaunch this app as administrator to install it?")
                if resp:
                    relaunch_as_admin()
            messagebox.showerror("Permission Denied", f"Could not install '{pip_name}'.")
            sys.exit(1)

# Package list
for pkg, pipname in zip(
    ["fitz", "PIL", "fpdf", "PyPDF2"],
    ["pymupdf", "Pillow", "fpdf", "PyPDF2"]
):
    check_and_install(pkg, pipname)

# === STEP 3: Import the confirmed packages ===
import fitz
from PIL import Image, ImageOps
from fpdf import FPDF
from PyPDF2 import PdfMerger

# === STEP 4: GUI Class ===
class PDFToolApp:
    def __init__(self, root):
        self.root = root
        root.title("TouchPDFs Utility")
        root.geometry("600x440")
        self.apply_dark_theme()
        self.create_widgets()

    def apply_dark_theme(self):
        style = ttk.Style(self.root)
        self.root.configure(bg="#2b2b2b")
        style.theme_use("clam")

        style.configure("TLabel", background="#2b2b2b", foreground="white")
        style.configure("TButton", background="#3c3f41", foreground="white")
        style.configure("TEntry", fieldbackground="#3c3f41", foreground="white")
        style.configure("TCombobox", fieldbackground="#3c3f41", background="#3c3f41", foreground="white")
        style.configure("Horizontal.TProgressbar", troughcolor="#444", background="#6a9fb5", bordercolor="#444")

        style.map("TCombobox",
            fieldbackground=[('readonly', '#3c3f41')],
            background=[('readonly', '#3c3f41')],
            foreground=[('readonly', 'white')]
        )

    def create_widgets(self):
        ttk.Label(self.root, text="Select Operation:").pack(pady=(10, 0))
        self.operation_var = tk.StringVar()
        self.operation_box = ttk.Combobox(self.root, textvariable=self.operation_var, state="readonly", width=55)
        self.operation_box['values'] = [
            "1. Process PDFs (Invert colors and arrange into A4 format)",
            "2. Merge PDFs",
            "3. Convert to color-inverted PNGs",
            "4. Arrange PDFs into A4 (No Invert)"
        ]
        self.operation_box.current(0)
        self.operation_box.pack(pady=5)

        ttk.Label(self.root, text="Input Directory:").pack()
        self.input_entry = ttk.Entry(self.root, width=50)
        self.input_entry.pack()
        ttk.Button(self.root, text="Browse", command=self.browse_input).pack(pady=(0, 10))

        ttk.Label(self.root, text="Output Path:").pack()
        self.output_entry = ttk.Entry(self.root, width=50)
        self.output_entry.pack()
        ttk.Button(self.root, text="Browse", command=self.browse_output).pack(pady=(0, 10))

        ttk.Button(self.root, text="Run", command=self.run_operation).pack()
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="indeterminate")
        self.progress.pack(pady=10)

    def browse_input(self):
        path = filedialog.askdirectory()
        if path:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, path)

    def browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, path)

    def disable_ui(self):
        self.operation_box.config(state="disabled")
        self.input_entry.config(state="disabled")
        self.output_entry.config(state="disabled")

    def enable_ui(self):
        self.operation_box.config(state="readonly")
        self.input_entry.config(state="normal")
        self.output_entry.config(state="normal")

    def run_operation(self):
        self.progress.start()
        self.disable_ui()
        thread = threading.Thread(target=self._run_operation_safe)
        thread.start()

    def _run_operation_safe(self):
        op = self.operation_box.get()
        input_path = self.input_entry.get()
        output_path = self.output_entry.get()

        if not os.path.isdir(input_path):
            messagebox.showerror("Error", "Invalid input directory.")
            self.progress.stop()
            self.enable_ui()
            return

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        try:
            if op.startswith("1"):
                self.process_pdfs(input_path, output_path)
            elif op.startswith("2"):
                output_pdf = os.path.join(output_path, "merged_output.pdf")
                files = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.endswith(".pdf")]
                self.merge_pdfs(files, output_pdf)
            elif op.startswith("3"):
                self.process_directory(input_path, output_path)
            elif op.startswith("4"):
                self.arrange_pdfs(input_path, output_path)

            messagebox.showinfo("Success", "Operation completed successfully.")

        except Exception as e:
            messagebox.showerror("Error", str(e))

        self.progress.stop()
        self.enable_ui()

    # === PDF logic (same as before) ===

    def process_pdfs(self, input_dir, output_dir):
        for filename in os.listdir(input_dir):
            if filename.endswith(".pdf"):
                input_path = os.path.join(input_dir, filename)
                output_pdf_path = os.path.join(output_dir, f"{filename[:-4]}_arranged.pdf")
                os.makedirs(output_dir, exist_ok=True)
                image_paths = self.invert_colors_and_convert_to_images(input_path, output_dir)
                self.arrange_images_on_a4(image_paths, output_pdf_path)
                for img_path in image_paths:
                    os.remove(img_path)

    def merge_pdfs(self, pdf_list, output_path):
        merger = PdfMerger()
        for pdf in pdf_list:
            merger.append(pdf)
        merger.write(output_path)
        merger.close()

    def process_directory(self, input_dir, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        for filename in os.listdir(input_dir):
            if filename.endswith(".pdf"):
                input_pdf_path = os.path.join(input_dir, filename)
                individual_output_folder = os.path.join(output_dir, os.path.splitext(filename)[0])
                self.invert_colors_and_save_as_png(input_pdf_path, individual_output_folder)

    def arrange_pdfs(self, input_dir, output_dir):
        for filename in os.listdir(input_dir):
            if filename.endswith(".pdf"):
                input_path = os.path.join(input_dir, filename)
                output_pdf_path = os.path.join(output_dir, f"{filename[:-4]}_arranged.pdf")
                os.makedirs(output_dir, exist_ok=True)
                image_paths = self.convert_pdf_to_images(input_path, output_dir)
                self.arrange_images_on_a4(image_paths, output_pdf_path)
                for img_path in image_paths:
                    os.remove(img_path)

    def invert_colors_and_convert_to_images(self, pdf_path, output_dir):
        doc = fitz.open(pdf_path)
        image_paths = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            for x in range(pix.width):
                for y in range(pix.height):
                    pixel = pix.pixel(x, y)
                    if len(pixel) == 4:
                        r, g, b, a = pixel
                        pix.set_pixel(x, y, (255 - r, 255 - g, 255 - b, a))
                    else:
                        r, g, b = pixel
                        pix.set_pixel(x, y, (255 - r, 255 - g, 255 - b))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
            img.save(image_path)
            image_paths.append(image_path)
        return image_paths

    def convert_pdf_to_images(self, pdf_path, output_dir):
        doc = fitz.open(pdf_path)
        image_paths = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
            img.save(image_path)
            image_paths.append(image_path)
        return image_paths

    def arrange_images_on_a4(self, images, output_pdf_path):
        a4_width, a4_height = (2480, 3508)
        image_height = a4_height // 3
        pages = []
        for i in range(0, len(images), 3):
            page_images = images[i:i+3]
            page = Image.new('RGB', (a4_width, a4_height), 'white')
            for j, img_path in enumerate(page_images):
                img = Image.open(img_path)
                img = img.resize((a4_width, image_height))
                page.paste(img, (0, j * image_height))
            pages.append(page)
        if pages:
            pages[0].save(output_pdf_path, save_all=True, append_images=pages[1:])

    def invert_colors_and_save_as_png(self, input_pdf_path, output_folder):
        pdf_document = fitz.open(input_pdf_path)
        os.makedirs(output_folder, exist_ok=True)
        for page_number in range(len(pdf_document)):
            page = pdf_document.load_page(page_number)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            inverted_img = ImageOps.invert(img)
            output_path = os.path.join(output_folder, f"{os.path.basename(input_pdf_path).split('.')[0]}_page_{page_number + 1}.png")
            inverted_img.save(output_path)

# === Launch GUI ===
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = PDFToolApp(root)
        root.mainloop()
    except Exception as e:
        print("GUI failed:", e)
        input("Press Enter to exit...")
