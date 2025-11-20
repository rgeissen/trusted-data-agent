"""
RAG Template Manager: Loads and manages RAG case generation templates.

This module provides functionality to load template definitions from JSON files,
validate them, and make them available for case generation at runtime.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger("rag_template_manager")


class RAGTemplateManager:
    """
    Manages RAG templates loaded from JSON files.
    
    Loads template definitions from the rag_templates directory and provides
    access to template metadata and configurations.
    """
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the template manager.
        
        Args:
            templates_dir: Path to the templates directory. If None, uses default location.
        """
        if templates_dir is None:
            # Default: rag_templates/ at project root
            script_dir = Path(__file__).resolve().parent
            project_root = script_dir.parent.parent.parent
            templates_dir = project_root / "rag_templates"
        
        self.templates_dir = templates_dir
        self.templates_subdir = templates_dir / "templates"
        self.registry_file = templates_dir / "template_registry.json"
        
        self.registry: Dict[str, Any] = {}
        self.templates: Dict[str, Dict[str, Any]] = {}
        
        # Ensure directories exist
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.templates_subdir.mkdir(parents=True, exist_ok=True)
        
        # Load templates
        self._load_registry()
        self._load_templates()
    
    def _load_registry(self):
        """Load the template registry from disk."""
        if not self.registry_file.exists():
            logger.warning(f"Template registry not found at {self.registry_file}. Creating empty registry.")
            self.registry = {
                "registry_version": "1.0.0",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "templates": []
            }
            return
        
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                self.registry = json.load(f)
            logger.info(f"Loaded template registry with {len(self.registry.get('templates', []))} template(s)")
        except Exception as e:
            logger.error(f"Failed to load template registry: {e}", exc_info=True)
            self.registry = {"registry_version": "1.0.0", "templates": []}
    
    def _load_templates(self):
        """Load all active templates from registry."""
        for template_entry in self.registry.get("templates", []):
            template_id = template_entry.get("template_id")
            template_file = template_entry.get("template_file")
            status = template_entry.get("status", "active")
            
            # Only load active templates
            if status != "active":
                logger.debug(f"Skipping template {template_id} with status: {status}")
                continue
            
            template_path = self.templates_subdir / template_file
            
            if not template_path.exists():
                logger.error(f"Template file not found: {template_path}")
                continue
            
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                # Validate required fields
                if not self._validate_template(template_data):
                    logger.error(f"Template {template_id} failed validation")
                    continue
                
                self.templates[template_id] = template_data
                logger.info(f"Loaded template: {template_id} ({template_data.get('template_name')})")
                
            except Exception as e:
                logger.error(f"Failed to load template {template_id}: {e}", exc_info=True)
    
    def _validate_template(self, template_data: Dict[str, Any]) -> bool:
        """Validate that a template has required fields."""
        required_fields = [
            "template_id",
            "template_name",
            "template_type",
            "input_variables",
            "output_configuration",
            "strategy_template"
        ]
        
        for field in required_fields:
            if field not in template_data:
                logger.error(f"Template missing required field: {field}")
                return False
        
        return True
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a template by ID.
        
        Args:
            template_id: The unique template identifier
            
        Returns:
            Template data dictionary or None if not found
        """
        return self.templates.get(template_id)
    
    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all loaded templates.
        
        Returns:
            Dictionary mapping template IDs to template data
        """
        return self.templates.copy()
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        Get a list of all templates with basic metadata.
        
        Returns:
            List of template metadata dictionaries
        """
        templates_list = []
        for template_id, template_data in self.templates.items():
            templates_list.append({
                "template_id": template_id,
                "template_name": template_data.get("template_name"),
                "template_type": template_data.get("template_type"),
                "description": template_data.get("description"),
                "status": template_data.get("status", "active"),
                "version": template_data.get("template_version")
            })
        
        return templates_list
    
    def get_template_config(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the editable configuration for a template.
        
        Args:
            template_id: The template identifier
            
        Returns:
            Dictionary of editable configuration values
        """
        template = self.get_template(template_id)
        if not template:
            return None
        
        output_config = template.get("output_configuration", {})
        editable_config = {}
        
        # Extract editable values
        for key, value in output_config.items():
            if isinstance(value, dict) and value.get("editable"):
                editable_config[key] = value.get("value")
            elif key == "estimated_tokens" and isinstance(value, dict):
                editable_config["estimated_input_tokens"] = value.get("input_tokens", {}).get("value", 150)
                editable_config["estimated_output_tokens"] = value.get("output_tokens", {}).get("value", 180)
        
        # Add default MCP tool if available
        input_vars = template.get("input_variables", {})
        if "mcp_tool_name" in input_vars:
            editable_config["default_mcp_tool"] = input_vars["mcp_tool_name"].get("default")
        
        if "mcp_context_prompt" in input_vars:
            editable_config["default_mcp_context_prompt"] = input_vars["mcp_context_prompt"].get("default")
        
        return editable_config
    
    def update_template_config(self, template_id: str, config: Dict[str, Any]):
        """
        Update editable configuration for a template (runtime only, not persisted).
        
        Args:
            template_id: The template identifier
            config: Dictionary of configuration values to update
        """
        template = self.get_template(template_id)
        if not template:
            logger.error(f"Template {template_id} not found")
            return
        
        output_config = template.get("output_configuration", {})
        
        # Update editable values
        if "estimated_input_tokens" in config and "estimated_tokens" in output_config:
            output_config["estimated_tokens"]["input_tokens"]["value"] = config["estimated_input_tokens"]
        
        if "estimated_output_tokens" in config and "estimated_tokens" in output_config:
            output_config["estimated_tokens"]["output_tokens"]["value"] = config["estimated_output_tokens"]
        
        if "default_mcp_tool" in config:
            input_vars = template.get("input_variables", {})
            if "mcp_tool_name" in input_vars:
                input_vars["mcp_tool_name"]["default"] = config["default_mcp_tool"]
        
        if "default_mcp_context_prompt" in config:
            input_vars = template.get("input_variables", {})
            if "mcp_context_prompt" in input_vars:
                input_vars["mcp_context_prompt"]["default"] = config["default_mcp_context_prompt"]
        
        logger.info(f"Updated runtime configuration for template {template_id}")
    
    def reload_templates(self):
        """Reload all templates from disk."""
        self.templates.clear()
        self._load_registry()
        self._load_templates()
        logger.info("Templates reloaded")


# Singleton instance
_template_manager_instance: Optional[RAGTemplateManager] = None


def get_template_manager() -> RAGTemplateManager:
    """Get or create the singleton template manager instance."""
    global _template_manager_instance
    if _template_manager_instance is None:
        _template_manager_instance = RAGTemplateManager()
    return _template_manager_instance
