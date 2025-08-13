# utils.py

def parse_discount_rules(discount_str):
    """
    Parse discount string like "2:5,3:10" into list of dicts:
    [{"min_crops": 2, "discount_percent": 5}, {"min_crops": 3, "discount_percent": 10}]
    """
    rules = []
    if discount_str:
        parts = discount_str.split(',')
        for part in parts:
            try:
                min_crops, disc = part.split(':')
                rules.append({"min_crops": int(min_crops), "discount_percent": float(disc)})
            except Exception:
                # You can log or print warning here if you want
                pass
    return rules


def format_currency(amount):
    """Format float as currency string with ₹ symbol."""
    return f"₹{amount:,.2f}"


def render_lease_to_pdf(context: dict, output_pdf_path: str) -> str:
    """
    Render the lease agreement HTML template with the provided context and
    generate a PDF at output_pdf_path using WeasyPrint.

    Returns the path to the generated PDF.
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    import os

    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('lease.html')
    html_content = template.render(**context)

    return _render_html_to_pdf(html_content, output_pdf_path)


def render_quote_to_pdf(context: dict, output_pdf_path: str) -> str:
    """Generate a simple quote PDF using FPDF (no external system deps)."""
    from fpdf import FPDF

    pdf = FPDF(format='A4', unit='mm')
    pdf.add_page()
    # Load a Unicode font if available for ₹, otherwise use 'INR '
    currency_symbol = '₹'
    unicode_font_loaded = False
    try:
        font_candidates = [
            r'C:\\Windows\\Fonts\\Nirmala.ttf',
            r'C:\\Windows\\Fonts\\seguisym.ttf',
            r'C:\\Windows\\Fonts\\arialuni.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
        import os
        for font_path in font_candidates:
            if os.path.exists(font_path):
                pdf.add_font('UNI', '', font_path, uni=True)
                pdf.add_font('UNI', 'B', font_path, uni=True)
                unicode_font_loaded = True
                break
    except Exception:
        unicode_font_loaded = False
    if unicode_font_loaded:
        pdf.set_font('UNI', 'B', 16)
    else:
        pdf.set_font('Arial', 'B', 16)
        currency_symbol = 'INR '
    pdf.cell(0, 10, 'AGRI-CPQ QUOTE', ln=1, align='C')

    pdf.set_font('UNI' if unicode_font_loaded else 'Arial', '', 11)
    pdf.cell(0, 8, f"Quote ID: {context.get('quote_id','')}", ln=1)
    pdf.cell(0, 8, f"Date: {context.get('date','')}", ln=1)
    pdf.cell(0, 8, f"Farmer: {context.get('farmer','')}  |  Buyer: {context.get('buyer','')}", ln=1)
    pdf.ln(2)

    pdf.set_font('UNI' if unicode_font_loaded else 'Arial', 'B', 11)
    col_widths = [60, 20, 30, 30, 30]
    headers = ['Crop', 'Qty', 'Base', 'Discount', 'Final']
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 8, h, border=1, align='C')
    pdf.ln(8)

    pdf.set_font('UNI' if unicode_font_loaded else 'Arial', '', 11)
    for it in context.get('breakdown', []):
        pdf.cell(col_widths[0], 8, str(it.get('name','')), border=1)
        pdf.cell(col_widths[1], 8, str(it.get('quantity','')), border=1, align='C')
        pdf.cell(col_widths[2], 8, f"{currency_symbol}{float(it.get('base',0)):.2f}", border=1, align='R')
        disc = float(it.get('discount_percent',0))
        damt = float(it.get('discount_amount',0))
        pdf.cell(col_widths[3], 8, f"{disc:.0f}% ({currency_symbol}{damt:.2f})", border=1, align='R')
        pdf.cell(col_widths[4], 8, f"{currency_symbol}{float(it.get('final',0)):.2f}", border=1, align='R')
        pdf.ln(8)

    pdf.ln(2)
    pdf.set_font('UNI' if unicode_font_loaded else 'Arial', 'B', 12)
    pdf.cell(0, 8, f"Total Base: {currency_symbol}{context.get('total_base','')}", ln=1, align='R')
    pdf.cell(0, 8, f"Total Discount: {currency_symbol}{context.get('total_discount','')}", ln=1, align='R')
    pdf.cell(0, 8, f"Final Price: {currency_symbol}{context.get('total_final','')}", ln=1, align='R')
    pdf.set_font('UNI' if unicode_font_loaded else 'Arial', '', 10)
    pdf.cell(0, 6, f"Valid until: {context.get('valid_until','')}", ln=1, align='R')

    pdf.output(output_pdf_path)
    return output_pdf_path


def _render_html_to_pdf(html_content: str, output_pdf_path: str) -> str:
    """Prefer pdfkit (wkhtmltopdf); if unavailable, fall back to WeasyPrint."""
    # First try pdfkit, which works well on Windows with wkhtmltopdf
    try:
        import pdfkit  # type: ignore
        import os
        wkhtml_cmd = os.environ.get('WKHTMLTOPDF_CMD')
        config = pdfkit.configuration(wkhtmltopdf=wkhtml_cmd) if wkhtml_cmd else None
        options = {
            'page-size': 'A4',
            'margin-top': '15mm',
            'margin-right': '12mm',
            'margin-bottom': '15mm',
            'margin-left': '12mm',
            'encoding': 'UTF-8',
        }
        if config:
            pdfkit.from_string(html_content, output_pdf_path, options=options, configuration=config)
        else:
            pdfkit.from_string(html_content, output_pdf_path, options=options)
        return output_pdf_path
    except Exception:
        # Fallback to WeasyPrint
        try:
            from weasyprint import HTML  # type: ignore
            HTML(string=html_content).write_pdf(output_pdf_path)
            return output_pdf_path
        except Exception as fallback_error:
            raise RuntimeError(
                "PDF generation failed. Install wkhtmltopdf (recommended) or WeasyPrint dependencies."
            ) from fallback_error


def render_template_to_html(template_name: str, context: dict) -> str:
    """Render a Jinja2 template from the local templates folder to an HTML string."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    import os

    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template(template_name)
    return template.render(**context)
