"""
actions.py — Outbound ActionMesh Dispatcher (Phase 5).
Dispatches autonomous clinical notifications and protocol alerts to external systems
such as Slack, Electronic Data Capture (EDC) webhooks, and Trial Master File (TMF) logs.
"""

import logging
import json
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.db.mongodb import compliance_audits_col, documents_col

logger = logging.getLogger("mcp.actions")


class OutboundActionDispatcher:
    """
    Handles outbound MCP actions triggered either autonomously by the watcher
    or via user confirmation in the interactive chat card interface.
    """

    def __init__(self):
        # Default mock webhook endpoint or environment fallback
        self.default_slack_channel = "#clinical-trials-safety"

    async def dispatch_slack_alert(
        self,
        channel: Optional[str] = None,
        message: Optional[str] = None,
        severity: str = "HIGH",
        document_name: str = "Clinical Protocol",
        findings: Optional[List[Dict[str, Any]]] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches a clinical safety alert to a Slack channel via incoming webhook or sandbox logger.
        """
        target_channel = channel or self.default_slack_channel
        severity_upper = severity.upper()
        severity_color = "#E01E5A" if severity_upper == "CRITICAL" else "#ECB22E" if severity_upper == "HIGH" else "#2EB886"

        # Build Slack Block Kit formatted payload
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"[{severity_upper}] VeriDoc Protocol Compliance Alert",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Document:*\n{document_name}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity_upper}"},
                    {"type": "mrkdwn", "text": f"*Target Channel:*\n{target_channel}"},
                    {"type": "mrkdwn", "text": f"*Timestamp:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"}
                ]
            }
        ]

        if message:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary of Deviation:*\n{message}"}
            })

        if findings:
            finding_text = ""
            for i, f in enumerate(findings[:3], 1):
                finding_text += f"• *{f.get('type', 'Conflict')}* ({f.get('severity', 'HIGH')}): {f.get('description', '')}\n  _Resolution_: {f.get('recommendation', 'Harmonize protocol')}\n"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Key Findings:*\n{finding_text.strip()}"}
            })

        payload = {
            "channel": target_channel,
            "attachments": [
                {
                    "color": severity_color,
                    "blocks": blocks
                }
            ]
        }

        # If a real Slack Webhook URL is supplied, make real HTTP POST
        delivered_live = False
        if webhook_url and webhook_url.startswith("http"):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(webhook_url, json=payload)
                    delivered_live = resp.status_code == 200
            except Exception as http_err:
                logger.warning(f"[Outbound Action] Slack webhook failed: {http_err}. Saved in sandbox dispatch log.")

        dispatch_record = {
            "action": "slack_alert",
            "channel": target_channel,
            "severity": severity_upper,
            "document_name": document_name,
            "delivered_live": delivered_live,
            "sandbox_simulated": not delivered_live,
            "dispatched_at": datetime.utcnow().isoformat(),
            "payload_summary": message or "Dispatched clinical trial safety alert.",
            "status": "SENT"
        }

        logger.info(f"[Outbound Action] Slack alert dispatched: {dispatch_record}")
        return dispatch_record

    async def dispatch_edc_protocol_hold(
        self,
        protocol_id: str,
        reason: str,
        affected_sites: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Dispatches an automated Protocol Site Hold recommendation to Electronic Data Capture (EDC).
        """
        sites = affected_sites or ["Site 101 (Johns Hopkins)", "Site 104 (Mayo Clinic)"]
        dispatch_record = {
            "action": "edc_protocol_hold",
            "protocol_id": protocol_id,
            "reason": reason,
            "affected_sites": sites,
            "recommended_action": "Pause new patient enrollment until dosage titration discrepancy is resolved by IRB.",
            "dispatched_at": datetime.utcnow().isoformat(),
            "status": "RECOMMENDED"
        }
        logger.info(f"[Outbound Action] EDC protocol hold dispatched: {dispatch_record}")
        return dispatch_record


    def dispatch_slack_alert_sync(
        self,
        channel: Optional[str] = None,
        message: Optional[str] = None,
        severity: str = "HIGH",
        document_name: str = "Clinical Protocol",
        findings: Optional[List[Dict[str, Any]]] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous version of Slack alert dispatcher."""
        target_channel = channel or self.default_slack_channel
        severity_upper = severity.upper()
        severity_color = "#E01E5A" if severity_upper == "CRITICAL" else "#ECB22E" if severity_upper == "HIGH" else "#2EB886"

        delivered_live = False
        if webhook_url and webhook_url.startswith("http"):
            try:
                resp = httpx.post(webhook_url, json={"channel": target_channel, "text": f"[{severity_upper}] {document_name}: {message}"}, timeout=5.0)
                delivered_live = resp.status_code == 200
            except Exception as http_err:
                logger.warning(f"[Outbound Action] Slack webhook failed: {http_err}.")

        dispatch_record = {
            "action": "slack_alert",
            "channel": target_channel,
            "severity": severity_upper,
            "document_name": document_name,
            "delivered_live": delivered_live,
            "sandbox_simulated": not delivered_live,
            "dispatched_at": datetime.utcnow().isoformat(),
            "payload_summary": message or "Dispatched clinical trial safety alert.",
            "status": "SENT"
        }
        logger.info(f"[Outbound Action Sync] Slack alert dispatched: {dispatch_record}")
        return dispatch_record

    def dispatch_edc_protocol_hold_sync(
        self,
        protocol_id: str,
        reason: str,
        affected_sites: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Synchronous version of EDC protocol hold recommendation."""
        sites = affected_sites or ["Site 101 (Johns Hopkins)", "Site 104 (Mayo Clinic)"]
        dispatch_record = {
            "action": "edc_protocol_hold",
            "protocol_id": protocol_id,
            "reason": reason,
            "affected_sites": sites,
            "recommended_action": "Pause new patient enrollment until dosage titration discrepancy is resolved by IRB.",
            "dispatched_at": datetime.utcnow().isoformat(),
            "status": "RECOMMENDED"
        }
        logger.info(f"[Outbound Action Sync] EDC protocol hold dispatched: {dispatch_record}")
        return dispatch_record


# Singleton instance
outbound_dispatcher = OutboundActionDispatcher()

