from flask import Flask, request, send_file, abort
from bson import ObjectId
from gridfs import GridFS
from io import BytesIO
from datetime import datetime
from PIL import Image
from pypdf import PdfReader, PdfWriter
import fitz  # PyMuPDF
import os

from db import db, quotes_col

app = Flask(__name__)

@app.get("/health")
def health():
	return {"ok": True}

@app.get("/sign-form")
def sign_form():
	"""Minimal HTML form to upload a signature image for a quote and role."""
	quote_id = request.args.get("quote_id", "")
	role = request.args.get("role", "")
	return (
		f"""
		<!doctype html>
		<html><head><meta charset='utf-8'><title>Sign Quote</title></head>
		<body style='font-family: Arial; max-width: 600px; margin: auto;'>
			<h2>Sign Quote</h2>
			<form action='/sign' method='post' enctype='multipart/form-data'>
				<label>Quote ID</label><br/>
				<input name='quote_id' value='{quote_id}' style='width: 100%;' /><br/><br/>
				<label>Role</label><br/>
				<select name='role'>
					<option value='seller' {'selected' if role=='seller' else ''}>Seller</option>
					<option value='buyer' {'selected' if role=='buyer' else ''}>Buyer</option>
				</select><br/><br/>
				<label>Signature (PNG/JPG)</label><br/>
				<input type='file' name='signature' accept='image/*' /><br/><br/>
				<label>Page</label>
				<input type='number' name='page' value='0' min='0' style='width: 80px;' />
				<label style='margin-left:10px;'>X</label>
				<input type='number' name='x' value='50' style='width: 80px;' />
				<label style='margin-left:10px;'>Y</label>
				<input type='number' name='y' value='50' style='width: 80px;' />
				<br/><br/>
				<button type='submit'>Submit Signature</button>
			</form>
		</body></html>
		""",
		200,
		{"Content-Type": "text/html"},
	)


def _overlay_signature(pdf_bytes: bytes, signature_bytes: bytes, x: int, y: int, page_index: int = 0, w: int = 150) -> bytes:
    """Overlay a signature image onto the given PDF page using PyMuPDF and return bytes.
    x,y in points (72 per inch), origin top-left in PyMuPDF; we convert from bottom-left by page rect.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_index]
    sig_img = fitz.open(stream=signature_bytes, filetype="png")
    rect = page.rect
    # Convert y from bottom-left to top-left
    y_top = rect.height - y
    # Keep aspect ratio
    iw = sig_img[0].rect.width
    ih = sig_img[0].rect.height
    if iw == 0:
        iw = 1
    scale = w / iw
    h = ih * scale
    bbox = fitz.Rect(x, y_top - h, x + w, y_top)
    page.insert_image(bbox, stream=signature_bytes)
    out = BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()


@app.post("/sign")
def sign_pdf():
	"""Signer posts: quote_id, role (seller|buyer), signature image (PNG), optional page/x/y.
	Returns updated PDF.
	"""
	quote_id = request.form.get("quote_id")
	role = request.form.get("role")
	if role not in {"seller", "buyer"}:
		return abort(400, "role must be seller or buyer")
    try:
        page_index = int(request.form.get("page", 0))
        x = int(request.form.get("x", 50))
        y = int(request.form.get("y", 50))
        w = int(request.form.get("w", 150))
    except Exception:
		return abort(400, "invalid placement")
	file = request.files.get("signature")
	if not quote_id or not file:
		return abort(400, "missing quote_id or signature")

	fs = GridFS(db)
	# Expect original PDF stored previously as {type: 'quote_original', quote_id}
	doc = fs.find_one({"metadata.type": "quote_original", "metadata.quote_id": quote_id})
	if not doc:
		return abort(404, "original pdf not found")

	pdf_bytes = doc.read()
	sig_bytes = file.read()

    new_pdf = _overlay_signature(pdf_bytes, sig_bytes, x=x, y=y, page_index=page_index, w=w)
	# Save signed variant
	status_field = f"{role}_signed"
	fs_id = fs.put(new_pdf, filename=f"{quote_id}-{role}-signed.pdf", metadata={"type": "quote_signed", "quote_id": quote_id, "role": role})

	# Update quote signing status
	update = {"$set": {status_field: True, f"{role}_signed_at": datetime.utcnow(), f"{role}_signed_file_id": fs_id}}
	# Determine overall status
	q = quotes_col.find_one({"_id": ObjectId(quote_id)}) if ObjectId.is_valid(quote_id) else None
	# If quote_id here is not ObjectId but our generated string, we store by quote_id string instead
	filter_by = {"quote_id": quote_id} if not q else {"_id": ObjectId(quote_id)}
	quotes_col.update_one(filter_by, update, upsert=True)

	return send_file(BytesIO(new_pdf), mimetype="application/pdf", as_attachment=True, download_name=f"{quote_id}-{role}-signed.pdf")


if __name__ == "__main__":
	port = int(os.environ.get("SIGN_PORT", "5001"))
	app.run(host="0.0.0.0", port=port)


