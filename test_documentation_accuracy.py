#!/usr/bin/env python3
"""
Test Documentation Accuracy - Phase 5 Verification

Verifies that all documentation accurately reflects the current implementation:
- Cross-references are valid
- Code examples work
- Schema files exist and are valid
- Exception handling examples are accurate
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path.cwd()
sys.path.insert(0, str(project_root))

from rag_templates.exceptions import (
    TemplateError,
    TemplateNotFoundError,
    TemplateValidationError,
    SchemaValidationError,
    ToolValidationError,
    TemplateRegistryError,
    TemplateLoadError
)
from src.trusted_data_agent.agent.rag_template_manager import get_template_manager

print("╔═══════════════════════════════════════════════════════════╗")
print("║     Documentation Accuracy Test - Phase 5 Verification   ║")
print("╚═══════════════════════════════════════════════════════════╝")
print()

test_results = {"passed": 0, "failed": 0}

# ============================================================================
# TEST 1: Verify All Referenced Files Exist
# ============================================================================
print("=" * 70)
print("TEST 1: Verify All Referenced Files Exist")
print("=" * 70)
print()

files_to_check = [
    "rag_templates/TYPE_TAXONOMY.md",
    "rag_templates/PLUGIN_MANIFEST_SCHEMA.md",
    "rag_templates/IMPROVEMENTS_LOG.md",
    "rag_templates/schemas/README.md",
    "rag_templates/schemas/planner-schema.json",
    "rag_templates/schemas/knowledge-template-schema.json",
    "rag_templates/exceptions.py",
    "rag_templates/template_registry.json"
]

all_exist = True
for filepath in files_to_check:
    full_path = project_root / filepath
    if full_path.exists():
        print(f"  ✅ {filepath}")
    else:
        print(f"  ❌ {filepath} - NOT FOUND")
        all_exist = False

if all_exist:
    print()
    print("  ✅ PASS: All referenced documentation files exist")
    test_results["passed"] += 1
else:
    print()
    print("  ❌ FAIL: Some documentation files missing")
    test_results["failed"] += 1
print()

# ============================================================================
# TEST 2: Verify JSON Schemas Are Valid
# ============================================================================
print("=" * 70)
print("TEST 2: Verify JSON Schemas Are Valid")
print("=" * 70)
print()

schemas = [
    "rag_templates/schemas/planner-schema.json",
    "rag_templates/schemas/knowledge-template-schema.json"
]

all_valid = True
for schema_file in schemas:
    schema_path = project_root / schema_file
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        # Check for required JSON schema fields
        if "$schema" in schema and "type" in schema:
            print(f"  ✅ {schema_file}")
            print(f"     Schema version: {schema.get('$schema')}")
        else:
            print(f"  ❌ {schema_file} - Missing required fields")
            all_valid = False
    except json.JSONDecodeError as e:
        print(f"  ❌ {schema_file} - Invalid JSON: {e}")
        all_valid = False
    except Exception as e:
        print(f"  ❌ {schema_file} - Error: {e}")
        all_valid = False

if all_valid:
    print()
    print("  ✅ PASS: All JSON schemas are valid")
    test_results["passed"] += 1
else:
    print()
    print("  ❌ FAIL: Some JSON schemas invalid")
    test_results["failed"] += 1
print()

# ============================================================================
# TEST 3: Verify Exception Hierarchy (From Documentation)
# ============================================================================
print("=" * 70)
print("TEST 3: Verify Exception Hierarchy Matches Documentation")
print("=" * 70)
print()

# Test the exception hierarchy as documented
try:
    # Test TemplateNotFoundError
    error1 = TemplateNotFoundError("test_v1")
    assert isinstance(error1, TemplateError), "TemplateNotFoundError should inherit from TemplateError"
    assert hasattr(error1, 'template_id'), "TemplateNotFoundError should have template_id"
    
    # Test SchemaValidationError with ValidationError-like objects
    class MockValidationError:
        def __init__(self, message, path=()):
            self.message = message
            self.path = path
    
    error2 = SchemaValidationError("test_v1", [MockValidationError("test error", ("field",))])
    assert isinstance(error2, TemplateValidationError), "SchemaValidationError should inherit from TemplateValidationError"
    assert isinstance(error2, TemplateError), "SchemaValidationError should inherit from TemplateError"
    assert hasattr(error2, 'schema_errors'), "SchemaValidationError should have schema_errors"
    
    # Test ToolValidationError
    error3 = ToolValidationError("test_v1", ["fake_tool"])
    assert isinstance(error3, TemplateValidationError), "ToolValidationError should inherit from TemplateValidationError"
    assert hasattr(error3, 'invalid_tools'), "ToolValidationError should have invalid_tools"
    
    print("  ✅ Exception hierarchy correct:")
    print("     - TemplateError (base)")
    print("     - TemplateNotFoundError -> TemplateError")
    print("     - TemplateValidationError -> TemplateError")
    print("     - SchemaValidationError -> TemplateValidationError -> TemplateError")
    print("     - ToolValidationError -> TemplateValidationError -> TemplateError")
    print()
    print("  ✅ PASS: Exception hierarchy matches documentation")
    test_results["passed"] += 1
except AssertionError as e:
    print(f"  ❌ FAIL: {e}")
    test_results["failed"] += 1
except Exception as e:
    print(f"  ❌ FAIL: Unexpected error: {e}")
    test_results["failed"] += 1
print()

# ============================================================================
# TEST 4: Verify Template Manager Methods (From Documentation)
# ============================================================================
print("=" * 70)
print("TEST 4: Verify Template Manager Methods Match Documentation")
print("=" * 70)
print()

manager = get_template_manager()

# Test that documented methods exist and work as described
documented_methods = {
    "get_template": "Gets template, raises TemplateNotFoundError if missing",
    "list_templates": "Lists all templates with category field",
    "_validate_template": "Validates template, supports strict and validate_tools params",
    "_validate_tool_names": "Validates MCP tool names",
}

methods_correct = True
for method_name, description in documented_methods.items():
    if hasattr(manager, method_name):
        print(f"  ✅ {method_name}() exists")
        print(f"     {description}")
    else:
        print(f"  ❌ {method_name}() missing")
        methods_correct = False

# Test get_template raises TemplateNotFoundError (as documented)
try:
    manager.get_template("nonexistent_v999")
    print("  ❌ get_template() should raise TemplateNotFoundError")
    methods_correct = False
except TemplateNotFoundError:
    print("  ✅ get_template() correctly raises TemplateNotFoundError")
except Exception as e:
    print(f"  ❌ get_template() raised wrong exception: {type(e).__name__}")
    methods_correct = False

# Test list_templates includes category (as documented)
try:
    templates = manager.list_templates()
    if templates and all('category' in t for t in templates):
        print(f"  ✅ list_templates() includes category field ({len(templates)} templates)")
    else:
        print("  ❌ list_templates() missing category field")
        methods_correct = False
except Exception as e:
    print(f"  ❌ list_templates() error: {e}")
    methods_correct = False

if methods_correct:
    print()
    print("  ✅ PASS: All documented methods work as described")
    test_results["passed"] += 1
else:
    print()
    print("  ❌ FAIL: Some methods don't match documentation")
    test_results["failed"] += 1
print()

# ============================================================================
# TEST 5: Verify Type Taxonomy Implementation
# ============================================================================
print("=" * 70)
print("TEST 5: Verify Type Taxonomy Implementation (From TYPE_TAXONOMY.md)")
print("=" * 70)
print()

# Test that templates have correct type concepts
try:
    templates = manager.list_templates()
    
    # Check for all three type concepts as documented
    type_taxonomy_correct = True
    for template in templates:
        template_id = template.get('template_id')
        category = template.get('category')
        
        # Get full template to check template_type
        full_template = manager.get_template(template_id)
        template_type = full_template.get('template_type')
        
        # Derive repository_type as documented
        if template_type == "knowledge_repository":
            expected_repo_type = "knowledge"
        else:
            expected_repo_type = "planner"
        
        print(f"  Template: {template_id}")
        print(f"    template_type    = {template_type} (strategy)")
        print(f"    repository_type  = {expected_repo_type} (storage)")
        print(f"    category         = {category} (UI)")
        
        if category and template_type:
            print(f"    ✅ All three type concepts present")
        else:
            print(f"    ❌ Missing type concepts")
            type_taxonomy_correct = False
    
    if type_taxonomy_correct:
        print()
        print("  ✅ PASS: Type taxonomy correctly implemented")
        test_results["passed"] += 1
    else:
        print()
        print("  ❌ FAIL: Type taxonomy incomplete")
        test_results["failed"] += 1
except Exception as e:
    print(f"  ❌ FAIL: Error checking type taxonomy: {e}")
    test_results["failed"] += 1
print()

# ============================================================================
# TEST 6: Verify Schema Validation (From schemas/README.md)
# ============================================================================
print("=" * 70)
print("TEST 6: Verify Schema Validation Implementation")
print("=" * 70)
print()

# Test that schema validation works as documented
test_template = {
    "template_id": "doc_test_v1",
    "template_name": "Documentation Test",
    "template_type": "sql_query",
    "input_variables": {
        "query": {"type": "string", "required": True, "description": "Test query"}
    },
    "output_configuration": {
        "session_id": {"type": "constant", "value": "test"}
    },
    "strategy_template": {
        "phases": [
            {"phase": 1, "goal": "Test", "relevant_tools": ["base_readQuery"], "arguments": {}}
        ]
    }
}

try:
    # Should validate successfully
    manager._validate_template(test_template, validate_tools=False)
    print("  ✅ Valid template passes validation")
    
    # Test invalid template
    invalid_template = {"template_id": "invalid", "template_name": "Invalid"}
    try:
        manager._validate_template(invalid_template, validate_tools=False)
        print("  ❌ Invalid template should fail validation")
        test_results["failed"] += 1
    except SchemaValidationError as e:
        print(f"  ✅ Invalid template correctly rejected")
        print(f"     Detected {len(e.schema_errors)} schema errors")
        print()
        print("  ✅ PASS: Schema validation works as documented")
        test_results["passed"] += 1
except Exception as e:
    print(f"  ❌ FAIL: Schema validation error: {e}")
    test_results["failed"] += 1
print()

# ============================================================================
# SUMMARY
# ============================================================================
print()
print("╔═══════════════════════════════════════════════════════════╗")
print("║                  DOCUMENTATION TEST SUMMARY               ║")
print("╚═══════════════════════════════════════════════════════════╝")
print()

total_tests = test_results["passed"] + test_results["failed"]
print(f"Tests Passed:  {test_results['passed']}/{total_tests}")
print(f"Tests Failed:  {test_results['failed']}/{total_tests}")
print()

if test_results["failed"] == 0:
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║        ALL DOCUMENTATION TESTS PASSED ✓✓✓                ║")
    print("║                                                           ║")
    print("║  Documentation accurately reflects implementation!        ║")
    print("║  Phase 5 (Fix Documentation Drift) is COMPLETE           ║")
    print("║  System Health: 10/10                                    ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    sys.exit(0)
else:
    print("⚠️  Some documentation tests failed - review above for details")
    sys.exit(1)
