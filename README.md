# PDF OCR Enhancement Tool

<div align="center">
  <img src="https://img.shields.io/badge/python-3.7+-blue.svg" alt="Python 3.7+"/>
  <img src="https://img.shields.io/badge/streamlit-1.0+-green.svg" alt="Streamlit 1.0+"/>
  <img src="https://img.shields.io/badge/license-MIT-orange.svg" alt="MIT License"/>
</div>

## 📑 Overview

PDF OCR Enhancement Tool is a powerful application that improves the readability and searchability of scanned PDFs. The tool applies advanced image preprocessing techniques and Optical Character Recognition (OCR) to transform scanned documents into searchable, machine-readable text while maintaining the original layout.

![PDF OCR Enhancement Tool Screenshot](https://example.com/screenshot.png)

## ✨ Features

- **Image Preprocessing**: Multiple levels of preprocessing to enhance image quality before OCR
- **Advanced OCR**: Extracts text from images using Tesseract OCR
- **Multiple Languages**: Support for English, French, German, Turkish, Russian
- **Customizable Settings**: Adjust DPI, preprocessing level, and other parameters
- **Parallel Processing**: Efficiently processes multiple pages concurrently
- **Interactive UI**: User-friendly interface with page previews and progress tracking
- **Before/After Comparison**: View original and processed images side by side
- **Downloadable Results**: Get both searchable PDF and extracted text

## 🔧 Installation

### Prerequisites

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed
- Required language data files for Tesseract

### Step 1: Clone the repository

```bash
git clone https://github.com/ChadSaglam/OCR.git
cd OCR
```

### Step 2: Create a virtual environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # For Linux/Mac
# OR
venv\Scripts\activate  # For Windows
```

### Step 3: Install required packages

```bash
pip install -r requirements.txt
```


### Step 4: Run the application

```bash
streamlit run app.py
```