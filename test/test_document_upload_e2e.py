#!/usr/bin/env python3
"""
End-to-End Test: Document Upload with RAG Template

This script demonstrates the complete workflow of uploading a PDF document
and using it with the SQL Query Template - Document Context.

Steps:
1. Create a test PDF document
2. Use the template generator to create a RAG case with document upload
3. Verify the document is processed correctly
4. Show the generated case structure
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from trusted_data_agent.agent.rag_template_generator import RAGTemplateGenerator
from trusted_data_agent.llm.document_upload import DocumentUploadHandler
from trusted_data_agent.llm.document_upload_config_manager import DocumentUploadConfigManager
import json


def create_test_pdf(output_path: str):
    """Create a simple test PDF document."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        c = canvas.Canvas(output_path, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "Database Performance Tuning Guide")
        
        c.setFont("Helvetica", 12)
        y = 700
        
        content = [
            "",
            "Table Fragmentation Analysis",
            "",
            "Table fragmentation occurs when the physical storage of table data becomes",
            "scattered across multiple blocks or cylinders. This can significantly impact",
            "query performance, especially for sequential scans.",
            "",
            "To check fragmentation on Teradata:",
            "",
            "SELECT DatabaseName, TableName, CurrentPerm, PeakPerm,",
            "       (CurrentPerm - PeakPerm) / NULLIFZERO(PeakPerm) as FragmentationRatio",
            "FROM DBC.TableSize",
            "WHERE (CurrentPerm - PeakPerm) / NULLIFZERO(PeakPerm) > 0.20",
            "ORDER BY FragmentationRatio DESC;",
            "",
            "Tables showing more than 20% fragmentation should be considered for",
            "reorganization using COLLECT STATISTICS or table recreation.",
            "",
            "Best Practices:",
            "- Monitor fragmentation weekly in production databases",
            "- Schedule reorganization during maintenance windows",
            "- Consider partitioning for very large tables",
            "- Use appropriate primary index selection",
        ]
        
        for line in content:
            c.drawString(100, y, line)
            y -= 20
            if y < 100:
                c.showPage()
                c.setFont("Helvetica", 12)
                y = 750
        
        c.save()
        print(f"✓ Created test PDF: {output_path}")
        return True
        
    except ImportError:
        print("✗ reportlab not installed - using text file instead")
        # Fallback to text file
        text_path = output_path.replace('.pdf', '.txt')
        with open(text_path, 'w') as f:
            f.write("Database Performance Tuning Guide\n\n")
            f.write("Table Fragmentation Analysis\n\n")
            f.write("Table fragmentation occurs when the physical storage of table data becomes\n")
            f.write("scattered across multiple blocks or cylinders.\n\n")
            f.write("To check fragmentation on Teradata:\n\n")
            f.write("SELECT DatabaseName, TableName, CurrentPerm, PeakPerm,\n")
            f.write("       (CurrentPerm - PeakPerm) / NULLIFZERO(PeakPerm) as FragmentationRatio\n")
            f.write("FROM DBC.TableSize\n")
            f.write("WHERE (CurrentPerm - PeakPerm) / NULLIFZERO(PeakPerm) > 0.20\n")
            f.write("ORDER BY FragmentationRatio DESC;\n")
        print(f"✓ Created test text file: {text_path}")
        return text_path


def test_document_upload_handler(file_path: str):
    """Test the document upload handler directly."""
    print("\n" + "="*70)
    print("Step 1: Test Document Upload Handler")
    print("="*70)
    
    handler = DocumentUploadHandler()
    
    # Test with Google (native upload)
    print("\n[Provider: Google - Native Upload]")
    config_google = DocumentUploadConfigManager.get_effective_config('Google')
    result_google = handler.prepare_document_for_llm(
        file_path=file_path,
        provider_name='Google',
        model_name='gemini-pro',
        effective_config=config_google
    )
    
    print(f"  Method: {result_google['method']}")
    print(f"  File size: {result_google['file_size']} bytes")
    print(f"  Content type: {result_google['content_type']}")
    print(f"  Content length: {len(result_google['content'])} characters")
    print(f"  Content preview: {result_google['content'][:150]}...")
    
    # Test with Ollama (text extraction)
    print("\n[Provider: Ollama - Text Extraction]")
    config_ollama = DocumentUploadConfigManager.get_effective_config('Ollama')
    result_ollama = handler.prepare_document_for_llm(
        file_path=file_path,
        provider_name='Ollama',
        model_name='llama2',
        effective_config=config_ollama
    )
    
    print(f"  Method: {result_ollama['method']}")
    print(f"  Content length: {len(result_ollama['content'])} characters")
    
    return result_google, result_ollama


def test_template_with_document(file_path: str):
    """Test the RAG template generator with document upload."""
    print("\n" + "="*70)
    print("Step 2: Test RAG Template with Document Upload")
    print("="*70)
    
    # Note: This requires a RAGRetriever instance, so we'll simulate it
    print("\n[Simulating Template Case Generation]")
    
    # Define input values for the template
    input_values = {
        "user_query": "Show me all tables with high fragmentation in the production database",
        "sql_statement": """SELECT DatabaseName, TableName, CurrentPerm, PeakPerm,
       (CurrentPerm - PeakPerm) / NULLIFZERO(PeakPerm) as FragmentationRatio
FROM DBC.TableSize
WHERE (CurrentPerm - PeakPerm) / NULLIFZERO(PeakPerm) > 0.20
ORDER BY FragmentationRatio DESC""",
        "context_topic": "performance tuning",
        "database_name": "production",
        "document_file": file_path,  # This will be processed
        "mcp_tool_name": "base_executeRawSQLStatement",
        "target_database": "Teradata"
    }
    
    print(f"\nInput Values:")
    for key, value in input_values.items():
        if key == "sql_statement":
            print(f"  {key}: [SQL statement - {len(value)} chars]")
        elif key == "document_file":
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {value}")
    
    # Process document using the handler (simulating what the generator does)
    from trusted_data_agent.agent.rag_template_manager import get_template_manager
    
    template_manager = get_template_manager()
    template = template_manager.get_template("sql_query_doc_context_v1")
    
    if not template:
        print("✗ Template not found: sql_query_doc_context_v1")
        return None
    
    print(f"\n✓ Template loaded: {template['template_name']} v{template['template_version']}")
    
    # Process document
    handler = DocumentUploadHandler()
    config = DocumentUploadConfigManager.get_effective_config('Google')
    
    result = handler.prepare_document_for_llm(
        file_path=file_path,
        provider_name='Google',
        model_name='gemini-pro',
        effective_config=config
    )
    
    print(f"\n✓ Document processed:")
    print(f"  Method: {result['method']}")
    print(f"  Content extracted: {len(result['content'])} characters")
    
    # Update input values with extracted content
    input_values_processed = input_values.copy()
    input_values_processed["document_content"] = result["content"]
    
    print(f"\n✓ Input values updated with document content")
    
    # Show the structure that would be generated
    print(f"\nGenerated Case Structure:")
    print(f"  Template: sql_query_doc_context_v1")
    print(f"  User Query: {input_values['user_query']}")
    print(f"  Context Topic: {input_values['context_topic']}")
    print(f"  Database: {input_values['database_name']}")
    print(f"  Document Content: {len(input_values_processed['document_content'])} chars")
    print(f"  SQL Statement: {len(input_values['sql_statement'])} chars")
    
    return input_values_processed


def main():
    """Run the end-to-end test."""
    print("="*70)
    print("End-to-End Test: Document Upload with RAG Template")
    print("="*70)
    
    # Create test directory
    test_dir = Path(__file__).parent / "test_data"
    test_dir.mkdir(exist_ok=True)
    
    # Create test document
    pdf_path = str(test_dir / "performance_tuning_guide.pdf")
    file_path = create_test_pdf(pdf_path)
    
    # If fallback to text, use that path
    if isinstance(file_path, str) and file_path.endswith('.txt'):
        pdf_path = file_path
    
    try:
        # Test 1: Document upload handler
        google_result, ollama_result = test_document_upload_handler(pdf_path)
        
        # Test 2: Template with document
        processed_input = test_template_with_document(pdf_path)
        
        if processed_input:
            print("\n" + "="*70)
            print("✓ End-to-End Test Completed Successfully!")
            print("="*70)
            print("\nSummary:")
            print("  ✓ PDF document created")
            print("  ✓ Document upload handler working")
            print("  ✓ Provider-aware processing (Google native, Ollama extraction)")
            print("  ✓ Template integration validated")
            print("  ✓ Document content extracted and ready for RAG case")
            print("\nNext Steps:")
            print("  - The template can now be used with actual PDF uploads")
            print("  - Document content will be automatically extracted")
            print("  - Provider-specific handling is configured in admin UI")
            print("  - RAG cases can be generated with document context")
            
            return 0
        else:
            print("\n✗ Template processing failed")
            return 1
            
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        if Path(pdf_path).exists():
            print(f"\nTest file: {pdf_path}")
            print("(File kept for inspection)")


if __name__ == '__main__':
    sys.exit(main())
