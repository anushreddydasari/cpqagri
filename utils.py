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
    """
    Render the quote HTML template with the provided context and
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
    template = env.get_template('quote.html')
    html_content = template.render(**context)

    return _render_html_to_pdf(html_content, output_pdf_path)


def _render_html_to_pdf(html_content: str, output_pdf_path: str) -> str:
    """Try WeasyPrint first; if missing system libs on Windows, fall back to pdfkit (wkhtmltopdf)."""
    try:
        from weasyprint import HTML  # type: ignore
        HTML(string=html_content).write_pdf(output_pdf_path)
        return output_pdf_path
    except Exception:
        # Fallback to pdfkit (requires wkhtmltopdf installed and on PATH)
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
        except Exception as fallback_error:
            raise RuntimeError(
                "PDF generation failed. Install WeasyPrint dependencies or wkhtmltopdf. "
                "On Windows, easiest: install wkhtmltopdf and add to PATH."
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
