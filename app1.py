from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
base_dir = os.path.abspath(os.path.dirname(__file__))

# Define paths
UPLOAD_FOLDER = os.path.join(base_dir, "uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logging.debug(f"Upload folder: {UPLOAD_FOLDER}, exists: {os.path.exists(UPLOAD_FOLDER)}")

# Specify the path to Poppler's bin directory
POPPLER_PATH = r"C:\poppler\1\poppler-24.08.0\Library\bin"  # Updated to match your Poppler installation

def allowed_pdf(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

@app.route('/pdf_converter')
def pdf_converter():
    return render_template('pdf_converter.html')

@app.route('/convert_pdf', methods=['POST'])
def convert_pdf():
    if 'pdfUpload' not in request.files:
        logging.error("No pdfUpload part in the request")
        return jsonify({"error": "No PDF file uploaded."}), 400

    file = request.files['pdfUpload']
    if file.filename == '':
        logging.error("No selected file")
        return jsonify({"error": "No file selected."}), 400

    if not allowed_pdf(file.filename):
        logging.error(f"File {file.filename} is not a valid PDF")
        return jsonify({"error": "Invalid file type. Please upload a PDF."}), 400

    # Generate a unique filename
    base_filename = secure_filename(file.filename).rsplit('.', 1)[0]
    pdf_filename = f"{base_filename}_{os.urandom(8).hex()}.pdf"
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)

    # Save the PDF
    try:
        file.save(pdf_path)
        if not os.path.exists(pdf_path):
            logging.error(f"Failed to save PDF: {pdf_path} does not exist after save")
            return jsonify({"error": "Failed to save PDF."}), 500
        logging.debug(f"Successfully saved PDF: {pdf_path}")
    except Exception as e:
        logging.error(f"Error saving PDF: {str(e)}")
        return jsonify({"error": f"Error saving PDF: {str(e)}"}), 500

    # Convert PDF to image
    image_filename = f"{base_filename}_{os.urandom(8).hex()}.png"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)

    try:
        # Pass the Poppler path explicitly
        images = convert_from_path(pdf_path, dpi=200, fmt='png', poppler_path=POPPLER_PATH)
        if not images:
            logging.error("No images extracted from PDF")
            return jsonify({"error": "Failed to convert PDF to image."}), 500
        images[0].save(image_path, 'PNG')
        if not os.path.exists(image_path):
            logging.error(f"Converted image not found at: {image_path}")
            return jsonify({"error": "Failed to save converted image."}), 500
        logging.debug(f"Successfully converted PDF to image: {image_path}")
    except Exception as e:
        logging.error(f"PDF conversion failed: {str(e)}")
        return jsonify({"error": f"PDF conversion failed: {str(e)}"}), 500

    return jsonify({"image_path": image_filename})

@app.route('/download_image/<filename>', methods=['GET'])
def download_image(filename):
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(image_path):
        return send_file(image_path, as_attachment=True)
    else:
        logging.error(f"Image not found for download: {image_path}")
        return jsonify({"error": "Image not found."}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Run on a different port to avoid conflict with app.py