import datetime
from pathlib import Path

import pdfkit

from base import settings


def get_pdf(statistics, html_content, report_name_prefix):
    if settings.ENVIRONMENT == 'DEVELOPMENT':
        wkhtmltopdf_path = "/usr/local/bin/wkhtmltopdf"  # For testing 5 items  for economy
    else:
        wkhtmltopdf_path = "/usr/bin/wkhtmltopdf"

    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    # Define the directory and file path with the date
    reports_dir = Path("chat_bot/pdfs")
    reports_dir.mkdir(parents=True, exist_ok=True)
    # Get the current date in dd.mm.yyyy format
    current_date = datetime.datetime.now().strftime("%d.%m.%Y")
    pdf_path = reports_dir / f"{report_name_prefix}_{current_date}.pdf"
    pdfkit.from_string(html_content, pdf_path, configuration=config)
    return pdf_path
