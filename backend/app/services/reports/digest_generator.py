import os
import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from app.core.logging import log

# WeasyPrint requires system GTK binaries which notoriously crash on raw Windows setups.
# The user explicitly mandated: "run WeasyPrint inside Docker only — no local GTK installation on Windows"
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    log.warning("weasyprint_missing_or_failed_falling_back_to_html_only")

REPORTS_DIR = Path("data/reports")
TEMPLATE_DIR = Path(__file__).parent

def generate_weekly_digest() -> str:
    """
    Simulates fetching DB metrics, binds them to Jinja, and exports a PDF.
    If WeasyPrint is unavailable (e.g. running locally on Windows), exports raw HTML
    as a fallback.
    Returns the absolute path to the generated file.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Normally this data comes from Postgres/Redis endpoints!
    context = {
        "current_date": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "savings_estimate": "$2.4M",
        "model_accuracy": "93.4%",
        "anomalies_detected": 14,
        "top_risks": [
            {"severity": "CRITICAL", "asset": "Suez Canal / SKU-014", "summary": "Chokepoint congestion index > 0.85; 14 vessels stranded."},
            {"severity": "HIGH", "asset": "Supplier: TSM-Asia-1", "summary": "Financial sentiment plummeted; default risk suspected."},
            {"severity": "HIGH", "asset": "Strait of Malacca", "summary": "Piracy/Geo-political events surging in local feeds."},
            {"severity": "MEDIUM", "asset": "SKU-007 (GPUs)", "summary": "Demand spiking past 1.8x supply threshold natively."},
            {"severity": "MEDIUM", "asset": "Supplier: EuroMotor", "summary": "Inventory depletion flagged by internal agent."}
        ],
        "seasonal_alerts": [
            {"event": "Lunar New Year", "impact": "Tier 2 Asian suppliers closing for 14 days next month. Requires pre-emptive inventory padding."},
            {"event": "Hurricane Season", "impact": "Panama Canal vessel throughput historically drops 18% during this quadrant."}
        ],
        "recommended_strategy": "Execute autonomous POs for Top 3 Critical/High Tier assets. Divert shipments from Suez to Cape of Good Hope if margin loss < $400k."
    }

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("template.html")
    rendered_html = template.render(context)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if WEASYPRINT_AVAILABLE:
        pdf_path = REPORTS_DIR / f"weekly_digest_{timestamp}.pdf"
        try:
            HTML(string=rendered_html).write_pdf(target=str(pdf_path))
            log.info("weekly_pdf_generated", path=str(pdf_path))
            return str(pdf_path.absolute())
        except Exception as e:
            log.error("weasyprint_pdf_crash", error=str(e))
            # Fall through to HTML dump below
    
    # Fallback if WeasyPrint is missing (running natively on Windows) or crashed
    html_path = REPORTS_DIR / f"weekly_digest_{timestamp}.html"
    html_path.write_text(rendered_html, encoding='utf-8')
    log.info("weekly_html_fallback_generated", path=str(html_path))
    return str(html_path.absolute())
