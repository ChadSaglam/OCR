import os
import cv2
import numpy as np
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import concurrent.futures
import gc
import tempfile
import traceback
import logging
from functools import partial

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFOCREnhancer:
    def __init__(self, tesseract_path=None, language='eng', dpi=300, preprocessing_level='medium'):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        self.language = language.lower()  # Ensure language is lowercase for tesseract
        self.dpi = dpi
        self.preprocessing_level = preprocessing_level
    
    def verify_tesseract(self):
        """Verify that tesseract is installed and working"""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception as e:
            raise RuntimeError(f"Tesseract OCR not properly configured: {str(e)}")
    
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
    
    @staticmethod
    def _process_single_page_static(image_path, page_num, temp_dir, language, preprocessing_level, tesseract_cmd=None):
        """Static method for multiprocessing compatibility"""
        try:
            # Set tesseract command if provided
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            
            # Load image
            image = Image.open(image_path)
            
            # Convert PIL image to OpenCV format
            cv_image = np.array(image)
            
            # Create enhancer instance for preprocessing
            enhancer = PDFOCREnhancer(language=language, preprocessing_level=preprocessing_level)
            
            # Preprocess image
            processed_image = enhancer.preprocess_image(cv_image)
            
            # Convert back to PIL for OCR
            pil_processed = Image.fromarray(processed_image)
            
            # Perform OCR
            text = pytesseract.image_to_string(pil_processed, lang=language)
            
            # Get OCR data including bounding boxes
            ocr_data = pytesseract.image_to_pdf_or_hocr(
                pil_processed, 
                extension='pdf',
                lang=language
            )
            
            # Save OCR'd page as PDF
            page_pdf_path = os.path.join(temp_dir, f"page_{page_num}.pdf")
            with open(page_pdf_path, "wb") as f:
                f.write(ocr_data)
            
            # Save images for comparison
            original_img_path = os.path.join(temp_dir, f"original_{page_num}.jpg")
            processed_img_path = os.path.join(temp_dir, f"processed_{page_num}.jpg")
            
            image.save(original_img_path, "JPEG")
            pil_processed.save(processed_img_path, "JPEG")
            
            # Force garbage collection to free memory
            gc.collect()
            
            return page_num, text, page_pdf_path, original_img_path, processed_img_path
        except Exception as e:
            # Log the error and return it
            error_msg = f"Error processing page {page_num}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return page_num, f"ERROR: {str(e)}", None, None, None
    
    def process_pdf(self, input_pdf, temp_dir, start_page=1, end_page=None, progress_callback=None, max_workers=None):
        """Process a PDF file with parallel processing"""
        os.makedirs(temp_dir, exist_ok=True)
        
        # Determine optimal number of workers if not specified
        if max_workers is None:
            max_workers = max(1, os.cpu_count() - 1)  # Leave one CPU free
        
        # Extract base filename without extension
        base_name = os.path.basename(input_pdf).rsplit('.', 1)[0]
        
        # Create a temp directory for page images
        page_images_dir = tempfile.mkdtemp(dir=temp_dir)
        
        # Convert PDF pages to images
        if progress_callback:
            progress_callback(0.1, "Converting PDF to images...")
        
        images = convert_from_path(
            input_pdf, 
            dpi=self.dpi, 
            first_page=start_page,
            last_page=end_page,
            output_folder=page_images_dir,  # Save images to disk instead of memory
            fmt="jpg",
            paths_only=True  # Return paths instead of PIL objects
        )
        
        total_pages = len(images)
        if progress_callback:
            progress_callback(0.2, f"Found {total_pages} pages to process")
        
        all_text = []
        searchable_pages = []
        original_pages = []
        processed_pages = []
        
        # Get tesseract path for the worker processes
        tesseract_cmd = pytesseract.pytesseract.tesseract_cmd
        
        # Create a partial function with our static method and fixed parameters
        process_func = partial(
            self._process_single_page_static,
            temp_dir=page_images_dir,
            language=self.language,
            preprocessing_level=self.preprocessing_level,
            tesseract_cmd=tesseract_cmd
        )
        
        # Prepare arguments for parallel processing
        process_args = [(images[i], start_page + i) for i in range(total_pages)]
        
        # Process pages in parallel
        completed = 0
        results = []
        
        # Note: Using ThreadPoolExecutor instead of ProcessPoolExecutor to avoid pickling issues
        # This is still effective because the CPU-intensive work will be done by Tesseract in a separate process
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_func, img_path, page_num) 
                      for img_path, page_num in process_args]
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                completed += 1
                if progress_callback:
                    progress = 0.2 + (0.7 * (completed / total_pages))
                    progress_callback(progress, f"Processed {completed}/{total_pages} pages")
                results.append(future.result())
        
        # Sort results by page number
        results.sort(key=lambda x: x[0])
        
        # Check for errors
        errors = [r for r in results if r[2] is None]  # r[2] is page_pdf_path
        if errors:
            error_pages = [r[0] for r in errors]
            raise RuntimeError(f"Failed to process pages: {error_pages}")
        
        # Extract results
        for page_num, text, page_pdf_path, original_img_path, processed_img_path in results:
            all_text.append(f"--- Page {page_num} ---\n{text}\n\n")
            searchable_pages.append(page_pdf_path)
            
            # Load images for display
            original_pages.append(Image.open(original_img_path))
            processed_pages.append(Image.open(processed_img_path))
        
        # Combine all pages into one PDF
        if progress_callback:
            progress_callback(0.9, "Creating final searchable PDF...")
        output_pdf = os.path.join(temp_dir, f"{base_name}_searchable.pdf")
        self.merge_pdfs(searchable_pages, output_pdf)
        
        # Save extracted text
        text_output = os.path.join(temp_dir, f"{base_name}_text.txt")
        with open(text_output, "w", encoding="utf-8") as f:
            f.writelines(all_text)
        
        if progress_callback:
            progress_callback(1.0, "Processing complete!")
        
        return output_pdf, text_output, all_text, original_pages, processed_pages
    
    def merge_pdfs(self, pdf_files, output_file):
        """Merge multiple PDF files into one"""
        result_pdf = fitz.open()
        
        for pdf_path in pdf_files:
            try:
                with fitz.open(pdf_path) as pdf:
                    result_pdf.insert_pdf(pdf)
            except Exception as e:
                logger.error(f"Error merging PDF {pdf_path}: {str(e)}")
                # Continue with other PDFs
        
        result_pdf.save(output_file)
        result_pdf.close()