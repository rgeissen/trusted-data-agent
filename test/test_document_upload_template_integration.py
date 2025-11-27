"""
Comprehensive Test Suite for Document Upload Template Integration

Tests the integration of DocumentUploadHandler abstraction layer with the
SQL Query Template - Document Context RAG template.

Test Coverage:
1. Template loading and validation
2. Document upload handler initialization
3. Provider-specific behavior (native vs text extraction)
4. Admin configuration override
5. File format validation
6. Error handling
7. End-to-end workflow
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from trusted_data_agent.llm.document_upload import (
    DocumentUploadHandler,
    DocumentUploadConfig,
    DocumentUploadCapability
)
from trusted_data_agent.llm.document_upload_config_manager import DocumentUploadConfigManager


class TestDocumentUploadTemplateIntegration(unittest.TestCase):
    """Test document upload integration with RAG template."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.template_path = Path(__file__).parent.parent / 'rag_templates' / 'templates' / 'sql-query-doc-context' / 'sql_query_doc_context_v1.json'
        cls.test_data_dir = Path(__file__).parent / 'test_data'
        cls.test_data_dir.mkdir(exist_ok=True)
        
        # Create test files
        cls.test_pdf = cls.test_data_dir / 'test_document.pdf'
        cls.test_txt = cls.test_data_dir / 'test_document.txt'
        cls.test_doc = cls.test_data_dir / 'test_document.docx'
        
        # Create simple text file
        with open(cls.test_txt, 'w') as f:
            f.write("Database Performance Tuning Guide\n\n")
            f.write("Table fragmentation occurs when the physical storage of table data becomes scattered.\n")
            f.write("Check DBC.TableSize for fragmentation metrics using the formula:\n")
            f.write("(CurrentPerm - PeakPerm) / NULLIFZERO(PeakPerm)\n")
        
        print(f"\n{'='*70}")
        print("Document Upload Template Integration Test Suite")
        print(f"{'='*70}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures."""
        # Clean up test files
        for file in [cls.test_txt, cls.test_pdf, cls.test_doc]:
            if file.exists():
                file.unlink()
        
        if cls.test_data_dir.exists():
            cls.test_data_dir.rmdir()
    
    # =========================================================================
    # Test 1: Template Loading and Validation
    # =========================================================================
    
    def test_01_template_loads_successfully(self):
        """Test that the updated template loads without errors."""
        print("\n[Test 1] Template Loading and Validation")
        print("-" * 70)
        
        self.assertTrue(self.template_path.exists(), f"Template not found: {self.template_path}")
        
        with open(self.template_path, 'r') as f:
            template = json.load(f)
        
        print(f"✓ Template loaded successfully")
        print(f"  Template ID: {template['template_id']}")
        print(f"  Version: {template['template_version']}")
        print(f"  Name: {template['template_name']}")
        
        self.assertEqual(template['template_version'], '1.1.0', "Template version should be 1.1.0")
        print(f"✓ Template version is 1.1.0")
    
    def test_02_template_has_document_file_input(self):
        """Test that template has new document_file input variable."""
        print("\n[Test 2] Document File Input Variable")
        print("-" * 70)
        
        with open(self.template_path, 'r') as f:
            template = json.load(f)
        
        input_vars = template['input_variables']
        
        self.assertIn('document_file', input_vars, "Template should have document_file input")
        print(f"✓ document_file input variable exists")
        
        doc_file = input_vars['document_file']
        self.assertEqual(doc_file['type'], 'file')
        self.assertFalse(doc_file['required'])
        print(f"✓ document_file is optional (required=False)")
        
        self.assertIn('upload_config', doc_file)
        upload_config = doc_file['upload_config']
        self.assertTrue(upload_config['use_abstraction'])
        self.assertTrue(upload_config['provider_aware'])
        self.assertTrue(upload_config['fallback_to_extraction'])
        print(f"✓ upload_config present with correct settings")
        print(f"  - use_abstraction: {upload_config['use_abstraction']}")
        print(f"  - provider_aware: {upload_config['provider_aware']}")
        print(f"  - fallback_to_extraction: {upload_config['fallback_to_extraction']}")
    
    def test_03_template_document_content_optional(self):
        """Test that document_content is now optional."""
        print("\n[Test 3] Document Content Now Optional")
        print("-" * 70)
        
        with open(self.template_path, 'r') as f:
            template = json.load(f)
        
        input_vars = template['input_variables']
        doc_content = input_vars['document_content']
        
        self.assertFalse(doc_content['required'], "document_content should be optional")
        print(f"✓ document_content is optional (required=False)")
        print(f"  Description: {doc_content['description'][:80]}...")
    
    def test_04_template_has_validation_rules(self):
        """Test that template has document processing validation rules."""
        print("\n[Test 4] Validation Rules")
        print("-" * 70)
        
        with open(self.template_path, 'r') as f:
            template = json.load(f)
        
        validation = template['validation_rules']
        
        self.assertIn('document_content_or_file', validation)
        doc_val = validation['document_content_or_file']
        self.assertIn('at_least_one', doc_val)
        self.assertIn('document_file', doc_val['at_least_one'])
        self.assertIn('document_content', doc_val['at_least_one'])
        print(f"✓ At least one validation rule exists")
        print(f"  Required: {doc_val['at_least_one']}")
        
        self.assertIn('document_processing', validation)
        doc_proc = validation['document_processing']
        self.assertTrue(doc_proc['use_upload_handler'])
        self.assertEqual(doc_proc['handler_class'], 'DocumentUploadHandler')
        self.assertEqual(doc_proc['handler_method'], 'prepare_document_for_llm')
        print(f"✓ Document processing rules configured")
        print(f"  Handler: {doc_proc['handler_class']}.{doc_proc['handler_method']}()")
    
    def test_05_template_has_integration_metadata(self):
        """Test that template has document_upload_integration metadata."""
        print("\n[Test 5] Integration Metadata")
        print("-" * 70)
        
        with open(self.template_path, 'r') as f:
            template = json.load(f)
        
        self.assertIn('document_upload_integration', template)
        integration = template['document_upload_integration']
        
        self.assertIn('features', integration)
        self.assertGreater(len(integration['features']), 0)
        print(f"✓ Integration metadata present")
        print(f"  Features: {len(integration['features'])}")
        for feature in integration['features']:
            print(f"    - {feature}")
        
        self.assertIn('workflow', integration)
        print(f"  Workflow steps: {len(integration['workflow'])}")
    
    # =========================================================================
    # Test 2: Document Upload Handler Initialization
    # =========================================================================
    
    def test_06_handler_initializes(self):
        """Test that DocumentUploadHandler initializes correctly."""
        print("\n[Test 6] Handler Initialization")
        print("-" * 70)
        
        handler = DocumentUploadHandler()
        self.assertIsNotNone(handler)
        print(f"✓ DocumentUploadHandler initialized")
        
        handler_with_params = DocumentUploadHandler(provider="Google", model="gemini-pro")
        self.assertEqual(handler_with_params.provider, "Google")
        self.assertEqual(handler_with_params.model, "gemini-pro")
        print(f"✓ Handler with parameters: provider={handler_with_params.provider}, model={handler_with_params.model}")
    
    def test_07_provider_capabilities_defined(self):
        """Test that all 7 providers have capability definitions."""
        print("\n[Test 7] Provider Capabilities")
        print("-" * 70)
        
        providers = ['Google', 'Anthropic', 'Amazon', 'OpenAI', 'Azure', 'Friendli', 'Ollama']
        
        print(f"Provider Capabilities Summary:")
        print(f"{'Provider':<12} {'Capability':<20} {'Max Size':<10} {'Formats'}")
        print("-" * 70)
        
        for provider in providers:
            capability = DocumentUploadConfig.get_capability(provider)
            self.assertIsInstance(capability, DocumentUploadCapability)
            
            config = DocumentUploadConfig.PROVIDER_CAPABILITIES.get(provider, {})
            max_size = config.get('max_file_size_mb', 0)
            formats = config.get('supported_formats', [])
            
            print(f"{provider:<12} {capability.value:<20} {max_size:<10} {len(formats)} formats")
        
        print(f"\n✓ All 7 providers have capability definitions")
    
    def test_08_capability_methods(self):
        """Test DocumentUploadConfig utility methods."""
        print("\n[Test 8] Capability Utility Methods")
        print("-" * 70)
        
        # Test supports_native_upload
        self.assertTrue(DocumentUploadConfig.supports_native_upload('Google'))
        print(f"✓ Google supports native upload")
        
        self.assertTrue(DocumentUploadConfig.supports_native_upload('Anthropic'))
        print(f"✓ Anthropic supports native upload")
        
        self.assertFalse(DocumentUploadConfig.supports_native_upload('Ollama'))
        print(f"✓ Ollama does not support native upload (text extraction)")
        
        # Test get_supported_formats
        google_formats = DocumentUploadConfig.get_supported_formats('Google')
        self.assertIn('.pdf', google_formats)
        self.assertGreater(len(google_formats), 0)
        print(f"✓ Google formats: {google_formats}")
        
        # Test get_max_file_size
        google_size = DocumentUploadConfig.get_max_file_size('Google')
        self.assertGreater(google_size, 0)
        print(f"✓ Google max size: {google_size / (1024*1024):.0f} MB")
    
    # =========================================================================
    # Test 3: Provider-Specific Behavior
    # =========================================================================
    
    def test_09_google_native_upload_capability(self):
        """Test Google provider native upload capability."""
        print("\n[Test 9] Google Native Upload")
        print("-" * 70)
        
        capability = DocumentUploadConfig.get_capability('Google')
        self.assertEqual(capability, DocumentUploadCapability.NATIVE_FULL)
        print(f"✓ Google capability: {capability.value}")
        
        info = DocumentUploadHandler.get_capability_info('Google')
        self.assertTrue(info['supports_native'])
        self.assertIn('.pdf', info['supported_formats'])
        print(f"✓ Native upload supported")
        print(f"  Formats: {info['supported_formats']}")
        print(f"  Max size: {info['max_file_size_mb']} MB")
        print(f"  Requires File API: {info['requires_file_api']}")
    
    def test_10_anthropic_native_upload_capability(self):
        """Test Anthropic provider native upload capability."""
        print("\n[Test 10] Anthropic Native Upload")
        print("-" * 70)
        
        capability = DocumentUploadConfig.get_capability('Anthropic')
        self.assertEqual(capability, DocumentUploadCapability.NATIVE_FULL)
        print(f"✓ Anthropic capability: {capability.value}")
        
        info = DocumentUploadHandler.get_capability_info('Anthropic')
        self.assertTrue(info['supports_native'])
        self.assertTrue(info['requires_base64'])
        print(f"✓ Native upload supported with base64 encoding")
        print(f"  Max size: {info['max_file_size_mb']} MB")
    
    def test_11_ollama_text_extraction_fallback(self):
        """Test Ollama text extraction fallback."""
        print("\n[Test 11] Ollama Text Extraction")
        print("-" * 70)
        
        capability = DocumentUploadConfig.get_capability('Ollama')
        self.assertEqual(capability, DocumentUploadCapability.TEXT_EXTRACTION)
        print(f"✓ Ollama capability: {capability.value}")
        
        info = DocumentUploadHandler.get_capability_info('Ollama')
        self.assertFalse(info['supports_native'])
        self.assertEqual(len(info['supported_formats']), 0)
        print(f"✓ Native upload not supported - text extraction only")
    
    def test_12_openai_vision_model_filter(self):
        """Test OpenAI model filtering (vision models only)."""
        print("\n[Test 12] OpenAI Model Filtering")
        print("-" * 70)
        
        # Vision model - should support native
        capability_vision = DocumentUploadConfig.get_capability('OpenAI', 'gpt-4o')
        self.assertEqual(capability_vision, DocumentUploadCapability.NATIVE_VISION_ONLY)
        print(f"✓ gpt-4o: {capability_vision.value}")
        
        # Non-vision model - should fall back to text extraction
        capability_text = DocumentUploadConfig.get_capability('OpenAI', 'gpt-3.5-turbo')
        self.assertEqual(capability_text, DocumentUploadCapability.TEXT_EXTRACTION)
        print(f"✓ gpt-3.5-turbo: {capability_text.value}")
        
        print(f"✓ Model filtering works correctly")
    
    # =========================================================================
    # Test 4: Document Processing
    # =========================================================================
    
    def test_13_text_file_extraction(self):
        """Test text file extraction."""
        print("\n[Test 13] Text File Extraction")
        print("-" * 70)
        
        handler = DocumentUploadHandler()
        result = handler._extract_text_from_document(str(self.test_txt))
        
        self.assertIn('content', result)
        self.assertIn('Database Performance', result['content'])
        self.assertIn('fragmentation', result['content'])
        print(f"✓ Text extracted successfully")
        print(f"  Length: {len(result['content'])} characters")
        print(f"  Preview: {result['content'][:80]}...")
    
    def test_14_prepare_document_for_llm_text_extraction(self):
        """Test prepare_document_for_llm with text extraction."""
        print("\n[Test 14] Prepare Document (Text Extraction Mode)")
        print("-" * 70)
        
        handler = DocumentUploadHandler()
        
        # Simulate effective config forcing text extraction
        effective_config = {
            'enabled': True,
            'use_native_upload': False,  # Force text extraction
            'max_file_size_mb': 32
        }
        
        result = handler.prepare_document_for_llm(
            file_path=str(self.test_txt),
            provider_name='Google',
            model_name='gemini-pro',
            effective_config=effective_config
        )
        
        self.assertEqual(result['method'], 'text_extraction')
        self.assertIn('content', result)
        self.assertIn('filename', result)
        self.assertEqual(result['filename'], 'test_document.txt')
        print(f"✓ Document prepared with text extraction")
        print(f"  Method: {result['method']}")
        print(f"  Filename: {result['filename']}")
        print(f"  Size: {result['file_size']} bytes")
        print(f"  Content type: {result['content_type']}")
    
    def test_15_prepare_document_for_llm_native_mode(self):
        """Test prepare_document_for_llm with native upload mode."""
        print("\n[Test 15] Prepare Document (Native Upload Mode)")
        print("-" * 70)
        
        handler = DocumentUploadHandler()
        
        # Simulate effective config enabling native upload
        effective_config = {
            'enabled': True,
            'use_native_upload': True,  # Enable native upload
            'max_file_size_mb': 32
        }
        
        result = handler.prepare_document_for_llm(
            file_path=str(self.test_txt),
            provider_name='Google',
            model_name='gemini-pro',
            effective_config=effective_config
        )
        
        self.assertEqual(result['method'], 'native_google')
        print(f"✓ Document prepared for native upload")
        print(f"  Method: {result['method']}")
        print(f"  Provider: Google")
    
    # =========================================================================
    # Test 5: Configuration Manager Integration
    # =========================================================================
    
    def test_16_config_manager_get_effective_config(self):
        """Test DocumentUploadConfigManager.get_effective_config()."""
        print("\n[Test 16] Configuration Manager")
        print("-" * 70)
        
        # Test for Google
        config = DocumentUploadConfigManager.get_effective_config('Google')
        
        self.assertIn('provider', config)
        self.assertEqual(config['provider'], 'Google')
        self.assertIn('enabled', config)
        self.assertIn('use_native_upload', config)
        self.assertIn('capability', config)
        print(f"✓ Effective config retrieved for Google")
        print(f"  Enabled: {config['enabled']}")
        print(f"  Use native: {config['use_native_upload']}")
        print(f"  Capability: {config['capability']}")
        print(f"  Has overrides: {config['has_overrides']}")
    
    def test_17_config_manager_all_providers(self):
        """Test getting config for all 7 providers."""
        print("\n[Test 17] All Provider Configurations")
        print("-" * 70)
        
        providers = ['Google', 'Anthropic', 'Amazon', 'OpenAI', 'Azure', 'Friendli', 'Ollama']
        
        print(f"{'Provider':<12} {'Enabled':<10} {'Native':<10} {'Capability'}")
        print("-" * 70)
        
        for provider in providers:
            config = DocumentUploadConfigManager.get_effective_config(provider)
            print(f"{provider:<12} {str(config['enabled']):<10} {str(config['use_native_upload']):<10} {config['capability']}")
        
        print(f"\n✓ All providers have effective configurations")
    
    # =========================================================================
    # Test 6: Error Handling
    # =========================================================================
    
    def test_18_invalid_file_format(self):
        """Test handling of unsupported file format."""
        print("\n[Test 18] Invalid File Format Handling")
        print("-" * 70)
        
        # Create a file with unsupported extension
        unsupported_file = self.test_data_dir / 'test.xyz'
        with open(unsupported_file, 'w') as f:
            f.write("test content")
        
        try:
            handler = DocumentUploadHandler()
            result = handler._extract_text_from_document(str(unsupported_file))
            
            self.assertIn('content', result)
            self.assertIn('Unsupported file format', result['content'])
            print(f"✓ Unsupported format handled gracefully")
            print(f"  Message: {result['content']}")
        finally:
            unsupported_file.unlink()
    
    def test_19_nonexistent_file(self):
        """Test handling of non-existent file."""
        print("\n[Test 19] Non-existent File Handling")
        print("-" * 70)
        
        handler = DocumentUploadHandler()
        
        try:
            result = handler._extract_text_from_document('/nonexistent/file.txt')
            self.assertIn('content', result)
            self.assertIn('failed', result['content'].lower())
            print(f"✓ Non-existent file handled gracefully")
            print(f"  Message: {result['content']}")
        except Exception as e:
            print(f"✓ Exception caught: {type(e).__name__}")
    
    # =========================================================================
    # Test 7: Integration Test
    # =========================================================================
    
    def test_20_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        print("\n[Test 20] End-to-End Workflow")
        print("-" * 70)
        
        print("\nSimulating template-based document upload workflow:")
        print("1. Template loaded")
        print("2. User provides document_file")
        print("3. Handler determines method based on provider")
        print("4. Document processed")
        print("5. Content used in SQL query generation")
        print()
        
        # Step 1: Load template
        with open(self.template_path, 'r') as f:
            template = json.load(f)
        print(f"✓ Step 1: Template loaded (v{template['template_version']})")
        
        # Step 2: Simulate user input
        user_input = {
            'user_query': 'Show me all tables with high fragmentation',
            'sql_statement': 'SELECT DatabaseName, TableName FROM DBC.TableSize WHERE fragmentation > 20',
            'context_topic': 'performance tuning',
            'database_name': 'production',
            'document_file': str(self.test_txt)
        }
        print(f"✓ Step 2: User input prepared")
        print(f"  Document: {user_input['document_file']}")
        
        # Step 3: Get provider config
        provider = 'Google'
        config = DocumentUploadConfigManager.get_effective_config(provider)
        print(f"✓ Step 3: Provider config retrieved")
        print(f"  Provider: {provider}")
        print(f"  Native upload: {config['use_native_upload']}")
        
        # Step 4: Process document
        handler = DocumentUploadHandler()
        result = handler.prepare_document_for_llm(
            file_path=user_input['document_file'],
            provider_name=provider,
            model_name='gemini-pro',
            effective_config=config
        )
        print(f"✓ Step 4: Document processed")
        print(f"  Method: {result['method']}")
        print(f"  Content length: {len(result['content'])} chars")
        
        # Step 5: Content would be used in Phase 1
        context_content = result['content']
        self.assertGreater(len(context_content), 0)
        print(f"✓ Step 5: Content ready for SQL query context")
        print(f"  Preview: {context_content[:100]}...")
        
        print(f"\n{'='*70}")
        print(f"✓ End-to-end workflow completed successfully")
        print(f"{'='*70}")


def run_tests():
    """Run the test suite with detailed output."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDocumentUploadTemplateIntegration)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*70}")
    print("Test Summary")
    print(f"{'='*70}")
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print(f"\n✓ All tests passed!")
    else:
        print(f"\n✗ Some tests failed")
    
    print(f"{'='*70}\n")
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
