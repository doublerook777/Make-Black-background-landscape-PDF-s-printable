import os
import subprocess
import sys

# Function to check if a package is installed, and install it if not present
def check_and_install(package, pip_name):
    try:
        __import__(package)
    except ImportError:
        while True:
            choice = input(f"'{pip_name}' is not installed. Would you like to install it? (yes/no): ").strip().lower()
            if choice == 'yes':
                subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
                break
            elif choice == 'no':
                print(f"Please install '{pip_name}' manually to continue.")
                sys.exit(1)
            else:
                print("Invalid input. Please enter 'yes' or 'no'.")

# Check for the required packages and install if necessary
required_packages = ['fitz', 'PIL', 'fpdf', 'PyPDF2']
package_names_for_install = ['pymupdf', 'Pillow', 'fpdf', 'PyPDF2']

for package, pip_name in zip(required_packages, package_names_for_install):
    check_and_install(package, pip_name)

# Now include your other functions and logic for processing PDFs below
# ----------------------------------

import fitz  # PyMuPDF
from PIL import Image, ImageOps
from fpdf import FPDF
from PyPDF2 import PdfMerger

# 1. Process PDFs: Invert colors and arrange into A4
def invert_colors_and_convert_to_images(pdf_path, output_dir):
    doc = fitz.open(pdf_path)
    image_paths = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        
        # Invert colors
        for x in range(pix.width):
            for y in range(pix.height):
                pixel = pix.pixel(x, y)
                if len(pixel) == 4:  # RGBA
                    r, g, b, a = pixel
                    pix.set_pixel(x, y, (255-r, 255-g, 255-b, a))
                else:  # RGB
                    r, g, b = pixel
                    pix.set_pixel(x, y, (255-r, 255-g, 255-b))
        
        # Convert pixmap to image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image_path = os.path.join(output_dir, f"page_{page_num+1}.png")
        img.save(image_path)
        image_paths.append(image_path)
    
    return image_paths

def arrange_images_on_a4(images, output_pdf_path):
    a4_width, a4_height = (2480, 3508)  # A4 size in pixels at 300 DPI
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

    # Save all pages to a PDF
    if pages:
        pages[0].save(output_pdf_path, save_all=True, append_images=pages[1:])

# 2. Merge PDFs
def merge_pdfs(pdf_list, output_path):
    merger = PdfMerger()

    for pdf in pdf_list:
        merger.append(pdf)
    
    merger.write(output_path)
    merger.close()

# 3. Invert PNG (Convert slides into color inverted PNGs)
def invert_colors_and_save_as_png(input_pdf_path, output_folder):
    pdf_document = fitz.open(input_pdf_path)
    os.makedirs(output_folder, exist_ok=True)

    for page_number in range(len(pdf_document)):
        page = pdf_document.load_page(page_number)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        inverted_img = ImageOps.invert(img)
        output_path = os.path.join(output_folder, f"{os.path.basename(input_pdf_path).split('.')[0]}_page_{page_number + 1}.png")
        inverted_img.save(output_path)

def process_directory(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.endswith(".pdf"):
            input_pdf_path = os.path.join(input_dir, filename)
            individual_output_folder = os.path.join(output_dir, os.path.splitext(filename)[0])
            invert_colors_and_save_as_png(input_pdf_path, individual_output_folder)

# 4. Arrange PDFs into A4 without inverting colors
def convert_pdf_to_images(pdf_path, output_dir):
    doc = fitz.open(pdf_path)
    image_paths = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        
        # Convert pixmap to image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image_path = os.path.join(output_dir, f"page_{page_num+1}.png")
        img.save(image_path)
        image_paths.append(image_path)
    
    return image_paths

def arrange_pdfs(pdf_dir, output_dir):
    for filename in os.listdir(pdf_dir):
        if filename.endswith(".pdf"):
            input_path = os.path.join(pdf_dir, filename)
            output_pdf_path = os.path.join(output_dir, f"{filename[:-4]}_arranged.pdf")

            # Convert to images
            image_paths = convert_pdf_to_images(input_path, output_dir)

            # Arrange images on A4 pages and save as PDF
            arrange_images_on_a4(image_paths, output_pdf_path)

            # Clean up image files
            for img_path in image_paths:
                os.remove(img_path)

# Main function for the utility
def main():
    print("PDF Utility Menu:")
    print("1. Process PDFs: Invert color and arrange into A4 format")
    print("2. Merge PDFs")
    print("3. Convert slides into color inverted PNGs")
    print("4. Arrange PDFs into A4 format without inverting colors")

    choice = input("Enter the number corresponding to the operation you want to perform: ").strip()

    if choice == '1':
        pdf_dir = input("Enter the path to your PDF directory: ").strip()
        output_dir = input("Enter the path to your output directory: ").strip()
        for filename in os.listdir(pdf_dir):
            if filename.endswith(".pdf"):
                input_path = os.path.join(pdf_dir, filename)
                output_pdf_path = os.path.join(output_dir, f"{filename[:-4]}_arranged.pdf")
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                image_paths = invert_colors_and_convert_to_images(input_path, output_dir)
                arrange_images_on_a4(image_paths, output_pdf_path)
                for img_path in image_paths:
                    os.remove(img_path)
        print("PDF processing complete.")

    elif choice == '2':
        pdf_dir = input("Enter the path to your PDF directory: ").strip()
        output_pdf_path = input("Enter the desired output path for the merged PDF: ").strip()
        pdf_files = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
        merge_pdfs(pdf_files, output_pdf_path)
        print(f"Merged PDF saved at: {output_pdf_path}")

    elif choice == '3':
        input_dir = input("Enter the path to your input PDF directory: ").strip()
        output_dir = input("Enter the path to your output PNG directory: ").strip()
        process_directory(input_dir, output_dir)
        print(f"Inverted PNG images saved in: {output_dir}")

    elif choice == '4':
        pdf_dir = input("Enter the path to your PDF directory: ").strip()
        output_dir = input("Enter the path to your output directory: ").strip()
        arrange_pdfs(pdf_dir, output_dir)
        print("PDF arrangement complete.")

    else:
        print("Invalid choice. Please select a valid operation number.")

# Run the script
if __name__ == "__main__":
    main()
