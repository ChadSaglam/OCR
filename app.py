import os
import tempfile
import streamlit as st
from enhancer import PDFOCREnhancer
from ui_utils import display_pdf, preview_pdf_page, get_memory_usage
import fitz  # PyMuPDF
import time

def main():
    # Page config must be the FIRST Streamlit command
    st.set_page_config(page_title="PDF OCR Enhancer", page_icon="📄", layout="wide")
    
    # Custom CSS - simpler approach for scrollable container
    st.markdown("""
    <style>
    /* Make the preview container scrollable */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
        overflow-y: auto;
        max-height: 500px; 
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        background-color: #f9f9f9;
    }
    
    /* Card styling */
    .preview-card {
        padding: 10px;
        border-radius: 8px;
        background-color: white;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    /* Better button */
    .stButton > button {
        width: 100%;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📄 PDF OCR Enhancement Tool")
    st.write("Enhance the readability of scanned PDFs by applying image preprocessing and OCR.")
    
    # Initialize session state variables
    if 'preview_dpi' not in st.session_state:
        st.session_state.preview_dpi = 100  # Lower DPI for previews
    if 'temp_dir' not in st.session_state:
        st.session_state.temp_dir = tempfile.mkdtemp()
    if 'temp_pdf_path' not in st.session_state:
        st.session_state.temp_pdf_path = None
    if 'total_pages' not in st.session_state:
        st.session_state.total_pages = 0
    
    # Sidebar for settings
    st.sidebar.header("Settings")
    
    language = st.sidebar.selectbox(
        "OCR Language", 
        ["ENG", "FRA", "DEU", "TUR", "RUS"],
        index=0
    )
    
    dpi = st.sidebar.slider("Image DPI", min_value=100, max_value=600, value=300, step=50,
                          help="Higher DPI gives better quality but slower processing")
    
    preprocessing = st.sidebar.select_slider(
        "Preprocessing Level",
        options=["light", "medium", "heavy"],
        value="medium",
        help="Light=fastest, Heavy=best quality but slowest"
    )
    
    cpu_cores = os.cpu_count()
    max_workers = st.sidebar.slider("CPU Cores to Use", min_value=1, max_value=cpu_cores, 
                                   value=max(1, cpu_cores-1))
    
    tesseract_path = st.sidebar.text_input(
        "Tesseract Path (optional)",
        "",
        help="Path to Tesseract executable if not in system PATH"
    )
    
    # Memory usage monitor
    memory_placeholder = st.sidebar.empty()
    memory_usage = get_memory_usage()
    memory_placeholder.info(f"Memory usage: {memory_usage:.1f} MB")
    
    # Main area for PDF upload and processing
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", label_visibility="visible")
    
    if uploaded_file is not None:
        # Save the uploaded file to the temp directory if it's new
        if st.session_state.temp_pdf_path is None:
            temp_pdf = os.path.join(st.session_state.temp_dir, uploaded_file.name)
            with open(temp_pdf, "wb") as f:
                f.write(uploaded_file.getvalue())
            st.session_state.temp_pdf_path = temp_pdf
            
            # Get total pages
            pdf_document = fitz.open(temp_pdf)
            st.session_state.total_pages = len(pdf_document)
        
        # Display total pages
        st.write(f"PDF has {st.session_state.total_pages} pages")
        
        # Page range selection
        col1, col2 = st.columns(2)
        with col1:
            start_page = st.number_input("Start Page", 
                                       min_value=1, 
                                       max_value=st.session_state.total_pages, 
                                       value=1, 
                                       step=1)
        with col2:
            end_page = st.number_input("End Page", 
                                     min_value=1, 
                                     max_value=st.session_state.total_pages, 
                                     value=min(5, st.session_state.total_pages),
                                     step=1)
        
        # Preview section with native Streamlit container
        st.subheader("Page Preview")
        st.write(f"Previews of pages {start_page} to {end_page} (scroll to see all):")
        
        # Create a native Streamlit container that we'll style with CSS to be scrollable
        with st.container():
            # Use a spinner while generating previews
            with st.spinner("Loading page previews..."):
                # Calculate number of columns and total pages
                num_cols = 3
                total_preview_pages = end_page - start_page + 1
                
                # Process pages in batches of 3 (for 3 columns)
                for i in range(0, total_preview_pages, num_cols):
                    cols = st.columns(num_cols)
                    
                    # Add preview for each column
                    for j in range(num_cols):
                        if i + j < total_preview_pages:
                            page_num = start_page + i + j
                            with cols[j]:
                                st.markdown(f"<div class='preview-card'><h4>Page {page_num}</h4></div>", unsafe_allow_html=True)
                                
                                # Generate the preview image
                                preview_image = preview_pdf_page(
                                    st.session_state.temp_pdf_path, 
                                    page_num, 
                                    dpi=st.session_state.preview_dpi
                                )
                                if preview_image:
                                    st.image(preview_image, use_container_width=True)
        
        # Process button with improved styling
        process_button = st.button("Process PDF", use_container_width=True)
        
        if process_button:
            # Initialize the enhancer
            enhancer = PDFOCREnhancer(
                tesseract_path=tesseract_path if tesseract_path else None,
                language=language,
                dpi=dpi,
                preprocessing_level=preprocessing
            )
            
            # Progress bar and status
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(progress, text):
                progress_bar.progress(progress)
                status_text.text(text)
            
            start_time = time.time()
            
            try:
                # Process the PDF
                output_pdf, text_output, all_text, original_pages, processed_pages = enhancer.process_pdf(
                    st.session_state.temp_pdf_path, 
                    st.session_state.temp_dir, 
                    start_page=start_page, 
                    end_page=end_page,
                    progress_callback=update_progress,
                    max_workers=max_workers
                )
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                st.success(f"✅ Processing completed in {processing_time:.2f} seconds!")
                
                # Create tabs for results
                tab1, tab2, tab3 = st.tabs(["Text", "Before/After Images", "Download Results"])
                
                with tab1:
                    st.write("Extracted Text:")
                    text_area = st.text_area("Extracted text content", value="".join(all_text), height=400)
                
                with tab2:
                    # Let user select which page to view
                    total_processed = len(original_pages)
                    if total_processed > 0:
                        page_to_view = st.slider("Select page to view", 
                                                min_value=1, 
                                                max_value=total_processed,
                                                value=1)
                        
                        # Adjust for 0-based indexing
                        page_index = page_to_view - 1
                        
                        st.subheader(f"Page {start_page + page_index}")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("Original Image")
                            st.image(original_pages[page_index], use_container_width=True)
                        with col2:
                            st.write("Processed Image")
                            st.image(processed_pages[page_index], use_container_width=True)
                
                with tab3:
                    col1, col2 = st.columns(2)
                    
                    # Use native Streamlit download buttons
                    with open(output_pdf, "rb") as pdf_file:
                        col1.download_button(
                            label="Download Searchable PDF",
                            data=pdf_file,
                            file_name=os.path.basename(output_pdf),
                            mime="application/pdf"
                        )
                    
                    with open(text_output, "rb") as text_file:
                        col2.download_button(
                            label="Download Extracted Text",
                            data=text_file,
                            file_name=os.path.basename(text_output),
                            mime="text/plain"
                        )
                    
                    # Display PDF preview
                    st.write("PDF Preview:")
                    display_pdf(output_pdf)
            
            except Exception as e:
                st.error(f"Error processing PDF: {str(e)}")
                st.exception(e)
    else:
        # Reset session variables when no file is uploaded
        st.session_state.temp_pdf_path = None
        st.session_state.total_pages = 0

    # Help information
    with st.expander("How to use this tool"):
        st.markdown("""
        ### Instructions:
        1. Upload a PDF file
        2. Preview pages and select your page range
        3. Select language and adjust settings
        4. Click "Process PDF"
        5. View and download results
        
        ### Performance Tips:
        - For faster processing: Lower DPI, "light" preprocessing, fewer pages
        - For better quality: Higher DPI, "heavy" preprocessing
        """)
    
    st.sidebar.markdown("---")
    st.sidebar.info("This application processes PDFs locally and does not upload your files to any server.")
    
    # Credits
    st.sidebar.markdown("### About")
    st.sidebar.markdown(
        "PDF OCR Enhancement Tool v1.8\n\n"
        "Created for improving readability of scanned documents."
    )

if __name__ == "__main__":
    main()