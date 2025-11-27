#!/usr/bin/env python3
"""Quick test: Create PDF and process with document upload handler"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from trusted_data_agent.llm.document_upload import DocumentUploadHandler
from trusted_data_agent.llm.document_upload_config_manager import DocumentUploadConfigManager

# Create PDF
pdf_path = Path(__file__).parent / "test_data" / "test.pdf"
pdf_path.parent.mkdir(exist_ok=True)

c = canvas.Canvas(str(pdf_path), pagesize=letter)
c.setFont("Helvetica-Bold", 16)
c.drawString(100, 750, "Database Performance Guide")
c.setFont("Helvetica", 12)
c.drawString(100, 700, "This is a test PDF document about database fragmentation.")
c.drawString(100, 680, "Tables should be reorganized when fragmentation exceeds 20%.")
c.save()

print(f"✓ Created PDF: {pdf_path}")
print(f"  File size: {pdf_path.stat().st_size} bytes")

# Test with document upload handler
handler = DocumentUploadHandler()
config = DocumentUploadConfigManager.get_effective_config('Google')

result = handler.prepare_document_for_llm(
    file_path=str(pdf_path),
    provider_name='Google',
    model_name='gemini-pro',
    effective_config=config
)

print(f"\n✓ Document processed:")
print(f"  Method: {result['method']}")
print(f"  Content type: {result['content_type']}")
print(f"  Content length: {len(result['content'])} characters")
print(f"  Content preview: {result['content'][:200]}...")

print("\n✓ PDF test successful!")
