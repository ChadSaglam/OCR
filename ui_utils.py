import os
import base64
import psutil
import streamlit as st
from pdf2image import convert_from_path

def display_pdf(pdf_file):
    """Display a PDF with proper permissions"""
    with open(pdf_file, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    
    # Fix: Use only allow="fullscreen" attribute
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

def preview_pdf_page(pdf_path, page_number, dpi=100):
    """Generate a preview of a specific PDF page at lower resolution"""
    try:
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=page_number,
            last_page=page_number
        )
        if images:
            return images[0]
        return None
    except Exception as e:
        st.warning(f"Couldn't generate preview: {str(e)}")
        return None

def get_memory_usage():
    """Get current memory usage"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024**2  # MB