"""
registry.py — MCP (Model Context Protocol) Tool & Connector Registry.

Conforms to Anthropic Model Context Protocol specification for tool discovery (tools/list)
and tool invocation (tools/call). Exposes live database and search tools to VeriDoc agents.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from app.mcp.db_connector import clinical_db_connector

logger = logging.getLogger(__name__)


class MCPRegistry:
    """Registry managing available Inbound and Outbound MCP Tools."""

    def __init__(self):
        self.tools = {
            "query_clinical_database": {
                "name": "query_clinical_database",
                "description": (
                    "Execute a sandboxed, read-only SQL SELECT query against the live clinical/hospital database. "
                    "Use this to query patient lab records, medication histories, or inventory quantities."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "A valid SQL SELECT statement (e.g. 'SELECT * FROM patients WHERE patient_id = 104;')"
                        }
                    },
                    "required": ["sql_query"]
                },
                "category": "inbound_db",
                "handler": self._handle_query_database
            },
            "get_patient_lab_record": {
                "name": "get_patient_lab_record",
                "description": (
                    "Retrieve the complete biomarker and lab screening panel for a specific patient by ID. "
                    "Returns serum creatinine, ALT liver enzymes, platelet count, and concurrent medications."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "integer",
                            "description": "The unique patient identification number (e.g., 104, 105, 106)"
                        }
                    },
                    "required": ["patient_id"]
                },
                "category": "inbound_db",
                "handler": self._handle_get_patient
            },
            "inspect_database_schema": {
                "name": "inspect_database_schema",
                "description": "Inspect the table schema, column definitions, and data types of the connected clinical database.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                },
                "category": "inbound_db",
                "handler": self._handle_inspect_schema
            }
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns MCP-compliant tool descriptors (tools/list)."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["parameters"],
                "category": t["category"]
            }
            for t in self.tools.values()
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an MCP tool call (tools/call) to its corresponding handler."""
        tool = self.tools.get(tool_name)
        if not tool:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error: MCP tool '{tool_name}' not found."}]
            }

        try:
            handler = tool["handler"]
            result = handler(arguments)
            return {
                "isError": False,
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
                    }
                ],
                "data": result
            }
        except Exception as e:
            logger.error(f"[MCPRegistry] Error executing tool '{tool_name}': {e}")
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Execution Error: {str(e)}"}]
            }

    # ── Tool Handlers ──────────────────────────────────────────────────────────

    def _handle_query_database(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("sql_query", "")
        return clinical_db_connector.execute_query(query)

    def _handle_get_patient(self, args: Dict[str, Any]) -> Dict[str, Any]:
        patient_id = args.get("patient_id")
        patient = clinical_db_connector.get_patient(patient_id)
        if patient:
            return {"found": True, "patient": patient}
        return {"found": False, "message": f"Patient with ID {patient_id} was not found in the live database."}

    def _handle_inspect_schema(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return clinical_db_connector.get_schema()


# Global singleton MCP registry
mcp_registry = MCPRegistry()
