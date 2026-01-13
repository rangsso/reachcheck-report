import os
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from models import ReportData

# Try importing WeasyPrint, if fails from missing libs, fallback
try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except OSError:
    HAS_WEASYPRINT = False
    print("[!] WeasyPrint system dependencies missing. Falling back...")

# Try checking for xhtml2pdf
try:
    from xhtml2pdf import pisa
    HAS_XHTML2PDF = True
except ImportError:
    HAS_XHTML2PDF = False

class ReportGenerator:
    def __init__(self, template_dir=None, output_dir=None):
        base_dir = Path(__file__).resolve().parent.parent # reachcheck_mvp root
        
        if not template_dir:
            template_dir = base_dir / "templates"
        
        if not output_dir:
            output_dir = base_dir / "output"
            
        self.template_dir = str(template_dir)
        self.output_dir = str(output_dir)
        
        # Ensure output dir exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

    def generate(self, data: ReportData, filename: str = "report.pdf"):
        template = self.env.get_template("report.html")
        html_string = template.render(data=data)
        
        # Save HTML for debugging/fallback
        html_filename = filename.replace(".pdf", ".html")
        html_path = os.path.join(self.output_dir, html_filename)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_string)
            
        pdf_path = os.path.join(self.output_dir, filename)

        if HAS_WEASYPRINT:
            print("[*] Using WeasyPrint for PDF generation...")
            try:
                HTML(string=html_string, base_url=self.template_dir).write_pdf(pdf_path)
                return pdf_path
            except Exception as e:
                print(f"[!] WeasyPrint failed: {e}")
        
        if HAS_XHTML2PDF:
            print("[*] Using xhtml2pdf for PDF generation...")
            with open(pdf_path, "wb") as pdf_file:
                pisa_status = pisa.CreatePDF(html_string, dest=pdf_file)
            
            if not pisa_status.err:
                return pdf_path
            else:
                print(f"[!] xhtml2pdf error: {pisa_status.err}")
        
        print("[!] Could not generate PDF. Please open the HTML file instead.")
        return html_path
