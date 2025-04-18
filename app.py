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
import math  # Import math for ceiling rounding

# Configure logging for debugging on Render
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
base_dir = os.path.abspath(os.path.dirname(__file__))
upload_folder = os.path.join(base_dir, "static", "Uploads")
pdf_output_folder = os.path.join(base_dir, "static")
images_folder = os.path.join(base_dir, "static", "images")

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

# Function to draw the header (logos and title) on the first page
def draw_header(c, width, height):
    logo_height = 50
    logo_width = 100
    small_logo_width = 80
    small_logo_height = 40
    payment_logo_width = 50
    payment_logo_height = 30

    try:
        if os.path.exists(logo_path):
            c.drawImage(logo_path, 40, height - 60, width=logo_width, height=logo_height, preserveAspectRatio=True)
        else:
            logging.error(f"Home Rail logo file not found at: {logo_path}")
    except Exception as e:
        logging.error(f"Could not load Home Rail logo: {e}")

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

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 120, "Home Rail – Quote Summary")

# Function to wrap text and calculate the number of lines
def wrap_text(c, text, max_width, font_name, font_size):
    c.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current_line = []
    current_width = 0

    for word in words:
        word_width = c.stringWidth(word + " ", font_name, font_size)
        if current_width + word_width <= max_width:
            current_line.append(word)
            current_width += word_width
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_width = c.stringWidth(word + " ", font_name, font_size)
    if current_line:
        lines.append(" ".join(current_line))

    return lines

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
            line_total = footage * price_per_ft
            products.append({
                "Product": product.get("Product", ""),
                "Color": product.get("Color", ""),
                "Footage": footage,
                "PricePerFt": price_per_ft,
                "LineTotal": line_total
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

    # Function to round up to 2 decimal places
    def round_up_to_2_decimals(value):
        return math.ceil(value * 100) / 100

    # Apply ceiling rounding to financial values
    subtotal_rounded = round_up_to_2_decimals(subtotal)
    gst_rounded = round_up_to_2_decimals(gst)
    total_rounded = round_up_to_2_decimals(total)
    deposit_rounded = round_up_to_2_decimals(deposit)

    # Round LineTotal for each product
    for product in products:
        product["LineTotalRounded"] = round_up_to_2_decimals(product["LineTotal"])

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
    extra_image3 = save_uploaded_image('extraImage3')
    extra_image4 = save_uploaded_image('extraImage4')
    extra_image5 = save_uploaded_image('extraImage5')

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

    # Draw the header for the first page
    draw_header(c, width, height)

    # Add contact information below the title
    y = height - 140  # Start below title (height - 120 - 20)
    c.setFont("Helvetica", 8)  # Smaller font, non-bold

    # Four sections side by side
    section1 = [
        "5520-4th Street SE",
        "Calgary, Alberta",
        "T2H 1K7"
    ]
    section2 = [
        "Our Regular Office Hours:",
        "Monday – Friday: 8:00 am to 4:30pm",
        "Closed: Saturdays & Sundays",
        "Pickups before 4:00"
    ]
    section3 = [
        "Web: www.home-rail.com",
        "Phone: (403) 202-5493",
        "Toll Free: 1-844-402-5493",
        "Warehouse: (587) 317-6052"
    ]
    section4 = [
        "Accounting: (587) 320-1116",
        "Scheduling: (587) 320-1117",
        "Sales: (587) 320-1118"
    ]

    # Define x-positions for each section (centered within their width)
    section_width = 125  # 500 points / 4 columns
    x_positions = [50, 175, 300, 425]  # x=50, 175, 300, 425

    # Draw section 1 (Address)
    y_temp = y
    for line in section1:
        line_width = c.stringWidth(line, "Helvetica", 8)
        c.drawString(x_positions[0] + (section_width - line_width) / 2, y_temp, line)
        y_temp -= 9  # Reduced from 10 to 9 for tighter spacing

    # Draw section 2 (Office Hours)
    y_temp = y
    for line in section2:
        line_width = c.stringWidth(line, "Helvetica", 8)
        c.drawString(x_positions[1] + (section_width - line_width) / 2, y_temp, line)
        y_temp -= 9

    # Draw section 3 (Website and first three phone numbers)
    y_temp = y
    for line in section3:
        line_width = c.stringWidth(line, "Helvetica", 8)
        c.drawString(x_positions[2] + (section_width - line_width) / 2, y_temp, line)
        y_temp -= 9

    # Draw section 4 (Remaining three phone numbers)
    y_temp = y
    for line in section4:
        line_width = c.stringWidth(line, "Helvetica", 8)
        c.drawString(x_positions[3] + (section_width - line_width) / 2, y_temp, line)
        y_temp -= 9

    # Move to Basic Information section
    y = height - 190  # Adjusted from height - 180 to account for new contact info height
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Basic Information")
    y -= 5
    c.line(50, y, 550, y)
    y -= 15

    info_fields = [
        ("Name", data.get("ClientName")),
        ("Phone", data.get("Phone")),
        ("Email", data.get("Email")),
        ("Address", data.get("Address")),
        ("Area", data.get("Area")),
        ("Date", data.get("QuoteDate")),
        ("Quoted By", data.get("QuotedBy")),
        ("Install Type", data.get("InstallType")),
        ("Lead Time", data.get("LeadTime")),
    ]

    for label, val in info_fields:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(55, y, f"{label}:")
        label_width = c.stringWidth(f"{label}:", "Helvetica-Bold", 10)
        c.setFont("Helvetica", 10)
        c.drawString(55 + label_width + 5, y, f"{val}")
        y -= 15

    install_notes = data.get("InstallNotes", "")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(55, y, "Install Notes:")
    label_width = c.stringWidth("Install Notes:", "Helvetica-Bold", 10)
    y -= 15

    if install_notes:
        c.setFont("Helvetica", 10)
        max_width = 490
        lines = wrap_text(c, install_notes, max_width, "Helvetica", 10)
        for line in lines:
            c.drawString(55, y, line)
            y -= 15
    else:
        c.drawString(55, y, "")
        y -= 15

    y -= 10
    remaining_space_needed = (
        20 +  # Space after products
        80 +  # Financial summary
        60    # Signatures
    )  # Total: 160 points

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Quote Details")
    y -= 5
    c.line(50, y, 550, y)
    y -= 20

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Product")
    c.drawString(250, y, "Color")
    c.drawString(350, y, "Footage")
    c.drawString(420, y, "Price/FT")
    c.drawString(490, y, "Line Total")
    y -= 20

    c.setFont("Helvetica", 10)
    first_page = True
    for product in products:
        space_needed = 20 + remaining_space_needed
        if y < space_needed:
            c.showPage()
            draw_header(c, width, height)
            y = height - 150
            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, y, "Quote Details (Continued)")
            y -= 5
            c.line(50, y, 550, y)
            y -= 20
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "Product")
            c.drawString(250, y, "Color")
            c.drawString(350, y, "Footage")
            c.drawString(420, y, "Price/FT")
            c.drawString(490, y, "Line Total")
            y -= 20
            c.setFont("Helvetica", 10)
            first_page = False

        c.drawString(50, y, product["Product"])
        c.drawString(250, y, product["Color"])
        c.drawString(350, y, str(product["Footage"]))
        c.drawString(420, y, f"${product['PricePerFt']:.2f}")
        c.drawString(490, y, f"${product['LineTotalRounded']:.2f}")
        y -= 20

    y -= 20
    c.setFont("Helvetica-Bold", 10)
    right_edge = 550
    financial_fields = [
        ("Subtotal:", f"${subtotal_rounded:.2f}"),
        ("GST (5%):", f"${gst_rounded:.2f}"),
        ("Total:", f"${total_rounded:.2f}"),
        ("Deposit:", f"${deposit_rounded:.2f}")
    ]

    for label, value in financial_fields:
        c.drawString(350, y, label)
        value_width = c.stringWidth(value, "Helvetica-Bold", 10)
        c.drawString(right_edge - value_width, y, value)
        y -= 15

    y -= 40
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Client Signature: __________________________")
    c.drawString(350, y, "Date: __________")
    y -= 20
    c.drawString(50, y, "Home Rail Rep Signature: __________________")
    c.drawString(350, y, "Date: __________")

    # Force a page break to move Reference Images to the second page
    c.showPage()
    y = height - 200  # Start position for images

    # Reference Images section (no title or line)
    img_width, img_height = 200, 150
    img_spacing_x, img_spacing_y = 10, 10
    img_positions = [
        (50, y),                    # Row 1, Col 1
        (50 + img_width + img_spacing_x, y),  # Row 1, Col 2
        (50, y - img_height - img_spacing_y),  # Row 2, Col 1
        (50 + img_width + img_spacing_x, y - img_height - img_spacing_y),  # Row 2, Col 2
        (50, y - 2 * (img_height + img_spacing_y)),  # Row 3, Col 1
        (50 + img_width + img_spacing_x, y - 2 * (img_height + img_spacing_y))  # Row 3, Col 2
    ]

    images = [
        (primary_image, "Primary Image"),
        (extra_image1, "Extra Image 1"),
        (extra_image2, "Extra Image 2"),
        (extra_image3, "Extra Image 3"),
        (extra_image4, "Extra Image 4"),
        (extra_image5, "Extra Image 5")
    ]

    for i, (img_path, img_name) in enumerate(images):
        x_pos, y_pos = img_positions[i]
        # Draw a placeholder rectangle
        c.setLineWidth(1)
        c.setStrokeColor(colors.grey)
        c.rect(x_pos, y_pos, img_width, img_height)
        if img_path and os.path.exists(img_path):
            try:
                c.drawImage(img_path, x_pos, y_pos, width=img_width, height=img_height, preserveAspectRatio=True)
            except Exception as e:
                logging.error(f"Could not load {img_name}: {e}")

    # Footer on the second page
    footer_y = y - 3 * (img_height + img_spacing_y) - 30
    c.setFont("Helvetica-Oblique", 8)
    quoted_by = data.get("QuotedBy") or "System"
    c.drawString(50, footer_y, f"Home-Rail Ltd. | www.homerailltd.com | Quote Generated by {quoted_by}")

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