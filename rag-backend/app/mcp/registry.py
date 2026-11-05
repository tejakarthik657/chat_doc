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
            "resolve_patient_identity": {
                "name": "resolve_patient_identity",
                "description": (
                    "Resolves patient identity across multi-tenant hospital namespaces (Apollo, Yashoda, KIMS). "
                    "Accepts an MRN (e.g. 'AP-104'), Trial Subject ID ('NB204-AP-0042'), or VeriDoc Patient ID ('VD-P-00104') "
                    "and resolves the authorized FHIR Patient resource reference."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "identifier": {
                            "type": "string",
                            "description": "Patient MRN, Subject ID, or VeriDoc internal ID (e.g. '104', 'AP-104', 'NB204-AP-0042')"
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Optional hospital tenant ID (e.g. 'apollo-001', 'yashoda-001')"
                        }
                    },
                    "required": ["identifier"]
                },
                "category": "clinical_fhir",
                "handler": self._handle_resolve_patient
            },
            "audit_patient_trial_eligibility": {
                "name": "audit_patient_trial_eligibility",
                "description": (
                    "Audits a patient's live FHIR lab observations against clinical trial protocol exclusion criteria "
                    "(e.g., ALT > 2.5x ULN, Creatinine > 1.5 mg/dL, Platelets < 100k, Chemo washout < 28 days)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "identifier": {
                            "type": "string",
                            "description": "Patient MRN, Subject ID, or VeriDoc ID (e.g. '104', 'AP-104')"
                        },
                        "protocol_id": {
                            "type": "string",
                            "description": "Trial Protocol Code (defaults to 'NB-204')"
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Hospital tenant ID (e.g. 'apollo-001', 'yashoda-001')"
                        }
                    },
                    "required": ["identifier"]
                },
                "category": "clinical_fhir",
                "handler": self._handle_audit_eligibility
            },
            "get_patient_fhir_observations": {
                "name": "get_patient_fhir_observations",
                "description": (
                    "Retrieves live, normalized FHIR observations and biomarker panels for a patient within "
                    "their authorized hospital tenant."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "identifier": {
                            "type": "string",
                            "description": "Patient MRN or ID (e.g. '104', 'AP-104')"
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Hospital tenant ID"
                        }
                    },
                    "required": ["identifier"]
                },
                "category": "clinical_fhir",
                "handler": self._handle_get_fhir_observations
            },
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
            },
            "send_slack_alert": {
                "name": "send_slack_alert",
                "description": (
                    "Dispatch an urgent clinical trial deviation or contradiction alert to a Slack channel "
                    "(e.g. #clinical-safety, #regulatory-ops)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Slack channel name (e.g. #clinical-safety)"
                        },
                        "message": {
                            "type": "string",
                            "description": "Detailed explanation of the protocol discrepancy or violation."
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                            "description": "Risk severity level"
                        },
                        "document_name": {
                            "type": "string",
                            "description": "Name of the protocol or filing document"
                        }
                    },
                    "required": ["message", "document_name"]
                },
                "category": "outbound_action",
                "handler": self._handle_send_slack_alert
            },
            "dispatch_edc_protocol_hold": {
                "name": "dispatch_edc_protocol_hold",
                "description": (
                    "Issue a recommended protocol screening or enrollment hold to the Electronic Data Capture (EDC) system."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "protocol_id": {
                            "type": "string",
                            "description": "Clinical trial protocol identifier (e.g. PROTOCOL-VX-409)"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for the recommended hold"
                        },
                        "affected_sites": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of clinical trial hospital trial sites"
                        }
                    },
                    "required": ["protocol_id", "reason"]
                },
                "category": "outbound_action",
                "handler": self._handle_edc_hold
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

    def _run_async(self, coro):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, coro).result()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    def _handle_resolve_patient(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.mcp.clinical_tools import clinical_mcp_tools
        return self._run_async(clinical_mcp_tools.resolve_patient(
            identifier=args.get("identifier"),
            tenant_id=args.get("tenant_id")
        ))

    def _handle_audit_eligibility(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.mcp.clinical_tools import clinical_mcp_tools
        return self._run_async(clinical_mcp_tools.audit_patient_eligibility(
            identifier=args.get("identifier"),
            protocol_id=args.get("protocol_id", "NB-204"),
            tenant_id=args.get("tenant_id")
        ))

    def _handle_get_fhir_observations(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.mcp.clinical_tools import clinical_mcp_tools
        return self._run_async(clinical_mcp_tools.get_patient_observations(
            identifier=args.get("identifier"),
            tenant_id=args.get("tenant_id")
        ))

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

    def _handle_send_slack_alert(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.mcp.actions import outbound_dispatcher
        return outbound_dispatcher.dispatch_slack_alert_sync(
            channel=args.get("channel"),
            message=args.get("message"),
            severity=args.get("severity", "HIGH"),
            document_name=args.get("document_name", "Clinical Protocol")
        )

    def _handle_edc_hold(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.mcp.actions import outbound_dispatcher
        return outbound_dispatcher.dispatch_edc_protocol_hold_sync(
            protocol_id=args.get("protocol_id", "PROTOCOL-GENERIC"),
            reason=args.get("reason", "Protocol discrepancy detected"),
            affected_sites=args.get("affected_sites")
        )


# Global singleton MCP registry
mcp_registry = MCPRegistry()

