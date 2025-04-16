from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import os
import datetime
import json

app = Flask(__name__)
base_dir = os.path.abspath(os.path.dirname(__file__))
upload_folder = os.path.join(base_dir, "static", "uploads")
pdf_output_folder = os.path.join(base_dir, "static")
logo_path = os.path.join(base_dir, "static", "logo_home_rail.png")
quote_store_path = os.path.join(base_dir, "quote_data.json")

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
    if not client_name:
        return "Client name is required.", 400

    try:
        footage = float(data.get("Footage", 0))
        price_per_ft = float(data.get("PricePerFt", 0))
    except ValueError:
        return "Footage and Price must be valid numbers.", 400

    gst_rate = 0.05
    subtotal = footage * price_per_ft
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

    save_quote_version(data)

    safe_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '_')).rstrip()
    pdf_filename = f"quote_{safe_name.replace(' ', '_')}.pdf"
    pdf_path = os.path.join(pdf_output_folder, pdf_filename)

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    try:
        if os.path.exists(logo_path):
            c.drawImage(logo_path, 40, height - 50, width=100, preserveAspectRatio=True)
    except Exception as e:
        print(f"[LOGO ERROR] Could not load logo: {e}")

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 60, "Home Rail – Quote Summary")

    y = height - 90
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
    c.drawString(50, y, data.get("Product"))
    c.drawString(220, y, str(footage))
    c.drawString(320, y, f"${price_per_ft:.2f}")
    c.drawString(420, y, f"${footage * price_per_ft:.2f}")

    y -= 40
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

    y -= 60
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Reference Images:")
    y -= 10

    image_y = y
    img_width, img_height = 180, 120
    if primary_image and os.path.exists(primary_image):
        c.drawImage(primary_image, 50, image_y - img_height, width=img_width, height=img_height)
    if extra_image1 and os.path.exists(extra_image1):
        c.drawImage(extra_image1, 250, image_y - img_height, width=img_width, height=img_height)
    if extra_image2 and os.path.exists(extra_image2):
        c.drawImage(extra_image2, 400, image_y - img_height, width=img_width, height=img_height)

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 40, "Home-Rail Ltd. | www.homerailltd.com | Quote Generated by System")
    c.save()

    if not os.path.exists(pdf_path):
        return "Failed to generate PDF.", 500

    return send_file(pdf_path, as_attachment=True)

@app.route('/delete/<quote_id>', methods=['DELETE'])
def delete_quote(quote_id):
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
