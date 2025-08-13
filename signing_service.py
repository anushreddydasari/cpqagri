from flask import Flask, request, send_file, abort, render_template_string
from bson import ObjectId
from gridfs import GridFS
from io import BytesIO
from datetime import datetime
from PIL import Image
from pypdf import PdfReader, PdfWriter
import fitz  # PyMuPDF
import os

from db import db, quotes_col
import hashlib, hmac, os

app = Flask(__name__)

@app.get("/health")
def health():
	return {"ok": True}

SIGN_FORM = """
<!doctype html><html><head><meta charset='utf-8'><title>Sign Quote</title></head>
<body style='font-family: Arial; max-width: 600px; margin: auto;'>
  <h2>Sign Quote {{quote_id}} ({{role}})</h2>
  {% if msg %}<p style='color:green'>{{msg}}</p>{% endif %}
  <form method='post' enctype='multipart/form-data'>
    <label>Signature (PNG/JPG)</label><br/>
    <input type='file' name='signature' accept='image/*' required/><br/><br/>
    <button type='submit'>Submit Signature</button>
  </form>
</body></html>
"""

def _hash_token(t: str) -> str:
    secret = os.environ.get("SIGN_SECRET", "change-me")
    return hmac.new(secret.encode(), t.encode(), hashlib.sha256).hexdigest()

def _find_by_token(token: str):
    th = _hash_token(token)
    q = quotes_col.find_one({"$or": [{"buyer.token_hash": th}, {"seller.token_hash": th}]})
    if not q:
        return None, None
    role = "buyer" if q.get("buyer", {}).get("token_hash") == th else "seller"
    return q, role

@app.get("/sign/<token>")
def sign_form_token(token):
    q, role = _find_by_token(token)
    if not q:
        return abort(404)
    if q.get(role, {}).get("signed"):
        return render_template_string(SIGN_FORM, quote_id=q.get("quote_id", str(q.get("_id"))), role=role, msg="Already signed.")
    return render_template_string(SIGN_FORM, quote_id=q.get("quote_id", str(q.get("_id"))), role=role, msg=None)

@app.post("/sign/<token>")
def sign_post_token(token):
    q, role = _find_by_token(token)
    if not q:
        return abort(404)
    file = request.files.get("signature")
    if not file:
        return abort(400, "signature required")
    sig_bytes = file.read()
    fs = GridFS(db)
    orig_id = q.get("original_file_id") or q.get("original_file_id") or q.get("original_file_id")
    orig_id = q.get("original_file_id") or q.get("original_file_id")
    orig_id = q.get("original_file_id") or q.get("original_file_id")
    orig_id = q.get("original_file_id") or q.get("original_file_id")
    orig_id = q.get("original_file_id") or q.get("original_file_id")
    orig_id = q.get("original_file_id") or q.get("original_file_id")
    orig_id = q.get("original_file_id") or q.get("original_file_id")
    orig_id = q.get("original_file_id")
    if not orig_id:
        return abort(400, "original pdf missing")
    pdf_bytes = fs.get(orig_id).read()
    new_pdf = _overlay_signature(pdf_bytes, sig_bytes, x=380 if role=="seller" else 120, y=120, page_index=0, w=180)
    fid = fs.put(new_pdf, filename=f"{q.get('quote_id','')}-{role}-signed.pdf", metadata={"type": "quote_signed", "quote_id": q.get('quote_id',''), "role": role})
    quotes_col.update_one({"_id": q["_id"]}, {"$set": {f"{role}.signed": True, f"{role}.signed_at": datetime.utcnow(), f"{role}.file_id": fid, "status": ("fully_signed" if (role=="buyer" and q.get("seller",{}).get("signed")) or (role=="seller" and q.get("buyer",{}).get("signed")) else f"{role}_signed")}})
    return send_file(BytesIO(new_pdf), mimetype="application/pdf", as_attachment=True, download_name=f"{q.get('quote_id','')}-{role}-signed.pdf")


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
    doc = fs.find_one({"metadata.type": "quote_original", "metadata.quote_id": quote_id})
    if not doc:
        return abort(404, "original pdf not found")

    pdf_bytes = doc.read()
    sig_bytes = file.read()

    new_pdf = _overlay_signature(pdf_bytes, sig_bytes, x=x, y=y, page_index=page_index, w=w)
    fs_id = fs.put(new_pdf, filename=f"{quote_id}-{role}-signed.pdf", metadata={"type": "quote_signed", "quote_id": quote_id, "role": role})

    # Update signing status on quote document by quote_id string
    update = {"$set": {f"{role}_signed": True, f"{role}_signed_at": datetime.utcnow(), f"{role}_signed_file_id": fs_id}}
    quotes_col.update_one({"quote_id": quote_id}, update, upsert=True)

    return send_file(BytesIO(new_pdf), mimetype="application/pdf", as_attachment=True, download_name=f"{quote_id}-{role}-signed.pdf")


if __name__ == "__main__":
	port = int(os.environ.get("SIGN_PORT", "5001"))
	app.run(host="0.0.0.0", port=port)


