import os
import cv2
import numpy as np
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import concurrent.futures
import gc

class PDFOCREnhancer:
    def __init__(self, tesseract_path=None, language='eng', dpi=300, preprocessing_level='medium'):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        self.language = language
        self.dpi = dpi
        self.preprocessing_level = preprocessing_level
        
    def preprocess_image(self, image):
        """Apply preprocessing based on selected level"""
        # Convert to grayscale if not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply preprocessing based on selected level
        if self.preprocessing_level == 'light':
            # Just basic grayscale conversion
            return gray
            
        elif self.preprocessing_level == 'medium':
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            return thresh
            
        elif self.preprocessing_level == 'heavy':
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Noise removal
            denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
            
            # Dilation to enhance text
            kernel = np.ones((1, 1), np.uint8)
            dilated = cv2.dilate(denoised, kernel, iterations=1)
            
            return dilated
    
    def process_single_page(self, args):
        """Process a single page (designed for parallel processing)"""
        image, page_num, temp_dir = args
        
        # Convert PIL image to OpenCV format
        cv_image = np.array(image)
        
        # Preprocess image
        processed_image = self.preprocess_image(cv_image)
        
        # Convert back to PIL for OCR
        pil_processed = Image.fromarray(processed_image)
        
        # Perform OCR
        text = pytesseract.image_to_string(pil_processed, lang=self.language)
        
        # Get OCR data including bounding boxes
        ocr_data = pytesseract.image_to_pdf_or_hocr(
            pil_processed, 
            extension='pdf',
            lang=self.language
        )
        
        # Save OCR'd page as PDF
        page_pdf_path = os.path.join(temp_dir, f"page_{page_num}.pdf")
        with open(page_pdf_path, "wb") as f:
            f.write(ocr_data)
        
        # Force garbage collection to free memory
        gc.collect()
        
        return page_num, text, page_pdf_path, image, pil_processed
    
    def process_pdf(self, input_pdf, temp_dir, start_page=1, end_page=None, progress_callback=None, max_workers=None):
        """Process a PDF file with parallel processing"""
        os.makedirs(temp_dir, exist_ok=True)
        
        # Determine optimal number of workers if not specified
        if max_workers is None:
            max_workers = max(1, os.cpu_count() - 1)  # Leave one CPU free
        
        # Extract base filename without extension
        base_name = os.path.basename(input_pdf).rsplit('.', 1)[0]
        
        # Convert PDF pages to images
        progress_callback(0.1, "Converting PDF to images...")
        images = convert_from_path(
            input_pdf, 
            dpi=self.dpi, 
            first_page=start_page,
            last_page=end_page
        )
        
        total_pages = len(images)
        progress_callback(0.2, f"Found {total_pages} pages to process")
        
        all_text = []
        searchable_pages = []
        original_pages = []
        processed_pages = []
        
        # Prepare arguments for parallel processing
        process_args = [(images[i], start_page + i, temp_dir) for i in range(total_pages)]
        
        # Process pages in parallel
        completed = 0
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.process_single_page, arg) for arg in process_args]
            
            # Collect results as they complete
            results = []
            for future in concurrent.futures.as_completed(futures):
                completed += 1
                progress = 0.2 + (0.7 * (completed / total_pages))
                progress_callback(progress, f"Processed {completed}/{total_pages} pages")
                results.append(future.result())
        
        # Sort results by page number
        results.sort(key=lambda x: x[0])
        
        # Extract results
        for page_num, text, page_pdf_path, original_image, processed_image in results:
            all_text.append(f"--- Page {page_num} ---\n{text}\n\n")
            searchable_pages.append(page_pdf_path)
            original_pages.append(original_image)
            processed_pages.append(processed_image)
        
        # Combine all pages into one PDF
        progress_callback(0.9, "Creating final searchable PDF...")
        output_pdf = os.path.join(temp_dir, f"{base_name}_searchable.pdf")
        self.merge_pdfs(searchable_pages, output_pdf)
        
        # Save extracted text
        text_output = os.path.join(temp_dir, f"{base_name}_text.txt")
        with open(text_output, "w", encoding="utf-8") as f:
            f.writelines(all_text)
            
        progress_callback(1.0, "Processing complete!")
        return output_pdf, text_output, all_text, original_pages, processed_pages
    
    def merge_pdfs(self, pdf_files, output_file):
        """Merge multiple PDF files into one"""
        result_pdf = fitz.open()
        
        for pdf_path in pdf_files:
            with fitz.open(pdf_path) as pdf:
                result_pdf.insert_pdf(pdf)
                
        result_pdf.save(output_file)
        result_pdf.close()