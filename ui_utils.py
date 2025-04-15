import os
import base64
import psutil
import streamlit as st
from pdf2image import convert_from_path
import io

def display_pdf(pdf_file):
    """Display a PDF with proper permissions"""
    try:
        with open(pdf_file, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        # Use only allow="fullscreen" attribute for security
        pdf_display = f'''
        <div style="display: flex; justify-content: center;">
            <iframe 
                src="data:application/pdf;base64,{base64_pdf}" 
                width="100%" 
                height="600" 
                type="application/pdf"
                frameborder="0"
                allow="fullscreen"
                style="border: 1px solid #ddd; border-radius: 5px;"
            ></iframe>
        </div>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error displaying PDF: {str(e)}")

def preview_pdf_page(pdf_path, page_number, dpi=100, cache=None):
    """Generate a preview of a specific PDF page at lower resolution with caching"""
    try:
        # Use cache if available
        cache_key = f"{pdf_path}_{page_number}_{dpi}"
        if cache is not None and cache_key in cache:
            return cache[cache_key]
            
        # Convert the page to an image
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=page_number,
            last_page=page_number
        )
        
        if images:
            # Convert PIL image to bytes for better memory management
            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Cache the image bytes
            if cache is not None:
                # Limit cache size to avoid memory issues
                if len(cache) > 20:  # Keep only 20 previews in memory
                    # Remove oldest item (assuming first added)
                    oldest_key = next(iter(cache))
                    del cache[oldest_key]
                
                # Store in cache
                cache[cache_key] = img_byte_arr
                
            return img_byte_arr
        
        return None
    except Exception as e:
        st.warning(f"Couldn't generate preview for page {page_number}: {str(e)}")
        return None

def get_memory_usage():
    """Get current memory usage"""
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024**2  # MB
    except Exception:
        return 0  # Return 0 if we can't get memory info