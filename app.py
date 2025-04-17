from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import os
import datetime
import json
import re
import logging

# Configure logging for debugging on Render
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
base_dir = os.path.abspath(os.path.dirname(__file__))
upload_folder = os.path.join(base_dir, "static", "uploads")
pdf_output_folder = os.path.join(base_dir, "static")
images_folder = os.path.join(base_dir, "static", "images")

# Define paths to images
# Define paths to images
logo_path = os.path.join(images_folder, "logo.png")
chba_logo_path = os.path.join(images_folder, "CHB.png")
wcb_logo_path = os.path.join(images_folder, "wcb.png")
visa_logo_path = os.path.join(images_folder, "visa.png")
amex_logo_path = os.path.join(images_folder, "amex_logo.png")
mastercard_logo_path = os.path.join(images_folder, "mastercard_logo.png")

app.config['UPLOAD_FOLDER'] = upload_folder
app.config['SECRET_KEY'] = 'secret'

os.makedirs(upload_folder, exist_ok=True)
os.makedirs(pdf_output_folder, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['png', 'jpg', 'jpeg', 'gif']

def save_quote_version(quote_data):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    quote_id = f"{quote_data['ClientName'].replace(' ', '_')}_{timestamp}"
    entry = {"id": quote_id, "timestamp": timestamp, "data": quote_data}

    existing = []
    quote_store_path = os.path.join(base_dir, "quote_data.json")
    if os.path.exists(quote_store_path):
        with open(quote_store_path, "r") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    existing.append(entry)
    with open(quote_store_path, "w") as f:
        json.dump(existing, f, indent=2)

    return quote_id

@app.route('/')
def index():
    quotes = []
    quote_store_path = os.path.join(base_dir, "quote_data.json")
    if os.path.exists(quote_store_path):
        with open(quote_store_path, "r") as f:
            try:
                quotes = json.load(f)
            except json.JSONDecodeError:
                pass
    return render_template('index.html', quotes=quotes)

@app.route('/submit', methods=['POST'])
def submit_quote():
    data = {k: request.form.get(k, '').strip() for k in request.form}
    client_name = data.get("ClientName")
    client_address = data.get("Address")
    
    if not client_name:
        return "Client name is required.", 400

    # Process multiple products
    products = []
    product_pattern = re.compile(r'Products\[(\d+)\]\[(\w+)\]')
    product_dict = {}
    
    for key, value in request.form.items():
        match = product_pattern.match(key)
        if match:
            index, field = match.groups()
            if index not in product_dict:
                product_dict[index] = {}
            product_dict[index][field] = value.strip()

    for index in sorted(product_dict.keys()):
        product = product_dict[index]
        try:
            footage = float(product.get("Footage", 0))
            price_per_ft = float(product.get("PricePerFt", 0))
            products.append({
                "Product": product.get("Product", ""),
                "Footage": footage,
                "PricePerFt": price_per_ft,
                "LineTotal": footage * price_per_ft
            })
        except ValueError:
            return f"Footage and Price for product {index} must be valid numbers.", 400

    if not products:
        return "At least one product is required.", 400

    gst_rate = 0.05
    subtotal = sum(product["LineTotal"] for product in products)
    gst = subtotal * gst_rate
    total = subtotal + gst
    deposit = total / 2

    def save_uploaded_image(field_name):
        file = request.files.get(field_name)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(upload_folder, filename)
            file.save(path)
            return path
        return None

    primary_image = save_uploaded_image('fileUpload')
    extra_image1 = save_uploaded_image('extraImage1')
    extra_image2 = save_uploaded_image('extraImage2')

    # Save the quote with products
    data["Products"] = products
    quote_store_path = os.path.join(base_dir, "quote_data.json")
    save_quote_version(data)

    # Create a safe filename using both name and address
    safe_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
    safe_address = ""
    if client_address:
        address_parts = client_address.split(',')[0].split()
        if address_parts:
            safe_address = "".join(c for c in address_parts[0] if c.isalnum()).rstrip()
    
    pdf_filename = f"quote_{safe_name}"
    if safe_address:
        pdf_filename += f"_{safe_address}"
    pdf_filename += ".pdf"
    
    pdf_path = os.path.join(pdf_output_folder, pdf_filename)

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # Log image paths for debugging on Render
    logging.debug(f"Base directory: {base_dir}")
    logging.debug(f"Images folder: {images_folder}")
    logging.debug(f"Home Rail Logo path: {logo_path}, exists: {os.path.exists(logo_path)}")
    logging.debug(f"CHBA Logo path: {chba_logo_path}, exists: {os.path.exists(chba_logo_path)}")
    logging.debug(f"WCB Logo path: {wcb_logo_path}, exists: {os.path.exists(wcb_logo_path)}")
    logging.debug(f"Visa Logo path: {visa_logo_path}, exists: {os.path.exists(visa_logo_path)}")
    logging.debug(f"Amex Logo path: {amex_logo_path}, exists: {os.path.exists(amex_logo_path)}")
    logging.debug(f"MasterCard Logo path: {mastercard_logo_path}, exists: {os.path.exists(mastercard_logo_path)}")

    # Add logos at the top of the page
    logo_height = 50
    logo_width = 100
    small_logo_width = 80
    small_logo_height = 40
    payment_logo_width = 50
    payment_logo_height = 30

    # Home Rail logo (left)
    try:
        if os.path.exists(logo_path):
            c.drawImage(logo_path, 40, height - 60, width=logo_width, height=logo_height, preserveAspectRatio=True)
        else:
            logging.error(f"Home Rail logo file not found at: {logo_path}")
    except Exception as e:
        logging.error(f"Could not load Home Rail logo: {e}")

    # CHBA and WCB logos (center)
    try:
        if os.path.exists(chba_logo_path):
            c.drawImage(chba_logo_path, 220, height - 60, width=small_logo_width, height=small_logo_height, preserveAspectRatio=True)
        else:
            logging.error(f"CHBA logo file not found at: {chba_logo_path}")
    except Exception as e:
        logging.error(f"Could not load CHBA logo: {e}")

    try:
        if os.path.exists(wcb_logo_path):
            c.drawImage(wcb_logo_path, 310, height - 60, width=small_logo_width, height=small_logo_height, preserveAspectRatio=True)
        else:
            logging.error(f"WCB logo file not found at: {wcb_logo_path}")
    except Exception as e:
        logging.error(f"Could not load WCB logo: {e}")

    # Payment logos (right)
    try:
        if os.path.exists(visa_logo_path):
            c.drawImage(visa_logo_path, 430, height - 50, width=payment_logo_width, height=payment_logo_height, preserveAspectRatio=True)
        else:
            logging.error(f"Visa logo file not found at: {visa_logo_path}")
    except Exception as e:
        logging.error(f"Could not load Visa logo: {e}")

    try:
        if os.path.exists(amex_logo_path):
            c.drawImage(amex_logo_path, 490, height - 50, width=payment_logo_width, height=payment_logo_height, preserveAspectRatio=True)
        else:
            logging.error(f"Amex logo file not found at: {amex_logo_path}")
    except Exception as e:
        logging.error(f"Could not load Amex logo: {e}")

    try:
        if os.path.exists(mastercard_logo_path):
            c.drawImage(mastercard_logo_path, 550, height - 50, width=payment_logo_width, height=payment_logo_height, preserveAspectRatio=True)
        else:
            logging.error(f"MasterCard logo file not found at: {mastercard_logo_path}")
    except Exception as e:
        logging.error(f"Could not load MasterCard logo: {e}")

    # Adjust the title position to be below the logos
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 120, "Home Rail – Quote Summary")

    y = height - 150
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Basic Information")
    y -= 5
    c.line(50, y, 550, y)
    y -= 15

    c.setFont("Helvetica", 10)
    info_fields = [
        ("Name", data.get("ClientName")),
        ("Phone", data.get("Phone")),
        ("Email", data.get("Email")),
        ("Address", data.get("Address")),
        ("Area", data.get("Area")),
        ("Date", data.get("QuoteDate")),
        ("Quoted By", data.get("QuotedBy")),
        ("Rail Color", data.get("RailColor")),
        ("Vinyl Color", data.get("VinylColor")),
        ("Install Type", data.get("InstallType")),
        ("Lead Time", data.get("LeadTime")),
        ("Install Notes", data.get("InstallNotes"))
    ]

    for label, val in info_fields:
        c.drawString(55, y, f"{label}: {val}")
        y -= 15

    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Quote Details")
    y -= 5
    c.line(50, y, 550, y)
    y -= 20

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Product")
    c.drawString(220, y, "Footage")
    c.drawString(320, y, "Price/FT")
    c.drawString(420, y, "Line Total")
    y -= 20

    c.setFont("Helvetica", 10)
    for product in products:
        c.drawString(50, y, product["Product"])
        c.drawString(220, y, str(product["Footage"]))
        c.drawString(320, y, f"${product['PricePerFt']:.2f}")
        c.drawString(420, y, f"${product['LineTotal']:.2f}")
        y -= 20

    y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(350, y, f"Subtotal: ${subtotal:.2f}")
    y -= 15
    c.drawString(350, y, f"GST (5%): ${gst:.2f}")
    y -= 15
    c.drawString(350, y, f"Total: ${total:.2f}")
    y -= 15
    c.drawString(350, y, f"Deposit: ${deposit:.2f}")

    y -= 40
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Client Signature: __________________________")
    c.drawString(350, y, "Date: __________")
    y -= 20
    c.drawString(50, y, "Home Rail Rep Signature: __________________")
    c.drawString(350, y, "Date: __________")

    # Define the box for reference images
    y -= 40
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Reference Images:")
    y -= 10

    # Define the box dimensions
    box_x = 50
    box_y = y - 130  # Adjust height to fit images (130 points tall)
    box_width = 500  # Width of the box (fits within page margins)
    box_height = 130  # Height of the box

    # Draw the box
    c.setLineWidth(1)
    c.setStrokeColor(colors.black)
    c.rect(box_x, box_y, box_width, box_height)

    # Place images inside the box
    img_width, img_height = 150, 110  # Adjusted to fit within the box
    img_spacing = 10  # Space between images
    img_y = box_y + 10  # Start 10 points above the bottom of the box
    img_positions = [
        (box_x + 10, img_y),  # First image position
        (box_x + 10 + img_width + img_spacing, img_y),  # Second image position
        (box_x + 10 + (img_width + img_spacing) * 2, img_y)  # Third image position
    ]

    images = [
        (primary_image, "Primary Image"),
        (extra_image1, "Extra Image 1"),
        (extra_image2, "Extra Image 2")
    ]

    for i, (img_path, img_name) in enumerate(images):
        if img_path and os.path.exists(img_path):
            try:
                x_pos, y_pos = img_positions[i]
                c.drawImage(img_path, x_pos, y_pos, width=img_width, height=img_height, preserveAspectRatio=True)
            except Exception as e:
                logging.error(f"Could not load {img_name}: {e}")

    # Adjust the footer position to be below the box
    footer_y = box_y - 30  # Place the footer 30 points below the box
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, footer_y, "Home-Rail Ltd. | www.homerailltd.com | Quote Generated by System")

    c.save()

    if not os.path.exists(pdf_path):
        return "Failed to generate PDF.", 500

    return send_file(pdf_path, as_attachment=True)

@app.route('/delete/<quote_id>', methods=['DELETE'])
def delete_quote(quote_id):
    quote_store_path = os.path.join(base_dir, "quote_data.json")
    if not os.path.exists(quote_store_path):
        return jsonify({"error": "No quotes stored."}), 404

    with open(quote_store_path, "r") as f:
        quotes = json.load(f)

    updated_quotes = [q for q in quotes if q["id"] != quote_id]

    with open(quote_store_path, "w") as f:
        json.dump(updated_quotes, f, indent=2)

    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)