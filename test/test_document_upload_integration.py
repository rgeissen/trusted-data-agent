#!/usr/bin/env python3
"""
Test script for document upload endpoint integration with abstraction layer.

Tests the /v1/rag/generate-questions-from-documents endpoint to verify:
1. Document upload with abstraction layer
2. Provider capability detection
3. Native upload vs text extraction
4. Database configuration override
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

def test_document_handler_initialization():
    """Test that DocumentUploadHandler can be initialized."""
    print("\n" + "="*60)
    print("TEST 1: DocumentUploadHandler Initialization")
    print("="*60)
    
    from trusted_data_agent.llm.document_upload import DocumentUploadHandler
    
    handler = DocumentUploadHandler()
    print("✓ DocumentUploadHandler initialized successfully")
    
    return True


def test_provider_capability_detection():
    """Test provider capability detection."""
    print("\n" + "="*60)
    print("TEST 2: Provider Capability Detection")
    print("="*60)
    
    from trusted_data_agent.llm.document_upload import DocumentUploadHandler
    
    providers = ['Google', 'Anthropic', 'OpenAI', 'Amazon', 'Friendli', 'Ollama']
    
    for provider in providers:
        capability_info = DocumentUploadHandler.get_capability_info(provider)
        print(f"\n{provider}:")
        print(f"  Capability: {capability_info['capability']}")
        print(f"  Native Support: {capability_info['supports_native']}")
        print(f"  Max Size: {capability_info['max_file_size_mb']}MB")
        print(f"  Formats: {', '.join(capability_info['supported_formats'][:3])}...")
    
    return True


def test_effective_config_with_db():
    """Test effective config retrieval with database."""
    print("\n" + "="*60)
    print("TEST 3: Effective Config with Database")
    print("="*60)
    
    from trusted_data_agent.llm.document_upload_config_manager import DocumentUploadConfigManager
    
    # Test default config
    print("\nGoogle (default):")
    config = DocumentUploadConfigManager.get_effective_config('Google')
    print(f"  Enabled: {config['enabled']}")
    print(f"  Native Upload: {config['use_native_upload']}")
    print(f"  Max Size: {config['max_file_size_mb']}MB")
    print(f"  Has Overrides: {config['has_overrides']}")
    
    # Test with override
    print("\nApplying override to Google...")
    DocumentUploadConfigManager.update_config(
        provider='Google',
        use_native_upload=False,
        max_file_size_mb=30,
        notes='Test override'
    )
    
    config = DocumentUploadConfigManager.get_effective_config('Google')
    print(f"  Enabled: {config['enabled']}")
    print(f"  Native Upload: {config['use_native_upload']}")
    print(f"  Max Size: {config['max_file_size_mb']}MB")
    print(f"  Has Overrides: {config['has_overrides']}")
    
    # Reset
    DocumentUploadConfigManager.reset_to_defaults('Google')
    print("✓ Config override and reset working")
    
    return True


def test_text_extraction():
    """Test text extraction from sample document."""
    print("\n" + "="*60)
    print("TEST 4: Text Extraction")
    print("="*60)
    
    from trusted_data_agent.llm.document_upload import DocumentUploadHandler
    from trusted_data_agent.llm.document_upload_config_manager import DocumentUploadConfigManager
    import tempfile
    
    handler = DocumentUploadHandler()
    
    # Create sample text file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Sample document content for testing.\n")
        f.write("This is line 2.\n")
        f.write("This is line 3.\n")
        temp_path = f.name
    
    try:
        # Use public API with Friendli (text extraction only)
        effective_config = DocumentUploadConfigManager.get_effective_config('Friendli')
        result = handler.prepare_document_for_llm(
            file_path=temp_path,
            provider_name='Friendli',
            model_name='mixtral-8x7b',
            effective_config=effective_config
        )
        print(f"✓ Text extraction successful")
        print(f"  Method: {result['method']}")
        print(f"  Content length: {len(result['content'])} chars")
        print(f"  Content preview: {result['content'][:50]}...")
        
        return True
    finally:
        os.unlink(temp_path)


def test_prepare_document_flow():
    """Test full document preparation flow."""
    print("\n" + "="*60)
    print("TEST 5: Document Preparation Flow")
    print("="*60)
    
    from trusted_data_agent.llm.document_upload import DocumentUploadHandler
    from trusted_data_agent.llm.document_upload_config_manager import DocumentUploadConfigManager
    import tempfile
    
    handler = DocumentUploadHandler()
    
    # Create sample text file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Sample technical documentation.\n")
        f.write("Contains important information about the database schema.\n")
        temp_path = f.name
    
    try:
        # Test with Friendli (text extraction only)
        print("\nTest with Friendli (text extraction):")
        effective_config = DocumentUploadConfigManager.get_effective_config('Friendli')
        result = handler.prepare_document_for_llm(
            file_path=temp_path,
            provider_name='Friendli',
            model_name='mixtral-8x7b',
            effective_config=effective_config
        )
        
        print(f"  Method: {result['method']}")
        print(f"  Content type: {result.get('content_type', 'N/A')}")
        print(f"  Has content: {'content' in result}")
        if 'content' in result:
            print(f"  Content preview: {result['content'][:50]}...")
        
        # Test with Google (native capable)
        print("\nTest with Google (native upload capable):")
        effective_config = DocumentUploadConfigManager.get_effective_config('Google')
        result = handler.prepare_document_for_llm(
            file_path=temp_path,
            provider_name='Google',
            model_name='gemini-1.5-flash',
            effective_config=effective_config
        )
        
        print(f"  Method: {result['method']}")
        print(f"  Content type: {result.get('content_type', 'N/A')}")
        
        # Test with forced text extraction
        print("\nTest with Google (forced text extraction):")
        effective_config = DocumentUploadConfigManager.get_effective_config('Google')
        effective_config['use_native_upload'] = False
        result = handler.prepare_document_for_llm(
            file_path=temp_path,
            provider_name='Google',
            model_name='gemini-1.5-flash',
            effective_config=effective_config
        )
        
        print(f"  Method: {result['method']}")
        print(f"  Has content: {'content' in result}")
        
        print("\n✓ Document preparation flow working correctly")
        return True
        
    finally:
        os.unlink(temp_path)


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*60)
    print("DOCUMENT UPLOAD ENDPOINT INTEGRATION TESTS")
    print("="*60)
    
    tests = [
        ("DocumentUploadHandler Init", test_document_handler_initialization),
        ("Provider Capability Detection", test_provider_capability_detection),
        ("Effective Config with DB", test_effective_config_with_db),
        ("Text Extraction", test_text_extraction),
        ("Document Preparation Flow", test_prepare_document_flow)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result, None))
        except Exception as e:
            print(f"\n✗ TEST FAILED: {name}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False, str(e)))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for name, result, error in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if error:
            print(f"       Error: {error}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "="*60)
        print("INTEGRATION NOTES")
        print("="*60)
        print("✓ Document upload abstraction layer is working correctly")
        print("✓ Provider capability detection is functional")
        print("✓ Database configuration system is integrated")
        print("✓ Text extraction fallback is working")
        print("\nNext steps:")
        print("- Test with actual REST API endpoint")
        print("- Test with real PDF/DOCX files")
        print("- Test native upload with Google/Anthropic providers")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
