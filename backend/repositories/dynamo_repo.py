"""DynamoDB Repository for KhetSathi.

Implements single-table access patterns conforming to TRD Section 15:
Table: `khetsathi`
PK: Partition Key
SK: Sort Key
GSI1PK, GSI1SK: Secondary index for active plots query.

Includes local storage fallback for local development when boto3 DynamoDB is unavailable.
"""

from __future__ import annotations
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class KhetSathiRepository:
    """Repository handling persistence for Plots, States, Decisions, and Feedback."""

    def __init__(self, table_name: str = "khetsathi", db_path: Optional[str] = None):
        self.table_name = table_name
        self.use_aws = bool(os.environ.get("AWS_REGION") or os.environ.get("USE_AWS_DYNAMODB"))
        self.dynamodb = None
        self.table = None

        if self.use_aws:
            try:
                import boto3
                self.dynamodb = boto3.resource("dynamodb")
                self.table = self.dynamodb.Table(self.table_name)
            except Exception:
                self.use_aws = False

        # Local SQLite storage for zero-ops local development and testing
        if not self.use_aws:
            if db_path is None:
                default_dir = Path(__file__).resolve().parent.parent / "data"
                default_dir.mkdir(parents=True, exist_ok=True)
                db_path = str(default_dir / "local_khetsathi.db")
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self._init_sqlite()

    def _init_sqlite(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS khetsathi (
                    PK TEXT NOT NULL,
                    SK TEXT NOT NULL,
                    GSI1PK TEXT,
                    GSI1SK TEXT,
                    data_json TEXT NOT NULL,
                    PRIMARY KEY (PK, SK)
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_gsi1 ON khetsathi(GSI1PK, GSI1SK)")

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_plot(
        self,
        farmer_name: str,
        language: str,
        plot_name: str,
        latitude: float,
        longitude: float,
        area_ha: float,
        crop: str,
        sowing_date: str,
        soil_type: str,
        pump_flow_lpm: float,
        pump_power_kw: float,
        application_efficiency: float,
    ) -> Dict[str, Any]:
        """Create a farmer and plot record, generate access token, and initialize state."""
        farmer_id = f"frm_{uuid.uuid4().hex[:12]}"
        plot_id = f"plt_{uuid.uuid4().hex[:12]}"
        access_token = f"tok_{uuid.uuid4().hex}"
        token_hash = self.hash_token(access_token)
        now_iso = datetime.now(timezone.utc).isoformat()

        farmer_item = {
            "farmer_id": farmer_id,
            "display_name": farmer_name,
            "language": language,
            "access_token_hash": token_hash,
            "created_at": now_iso,
        }

        plot_item = {
            "plot_id": plot_id,
            "farmer_id": farmer_id,
            "name": plot_name,
            "latitude": round(latitude, 2),
            "longitude": round(longitude, 2),
            "area_ha": area_ha,
            "crop": crop.lower(),
            "sowing_date": sowing_date,
            "soil_type": soil_type.lower(),
            "pump_flow_lpm": pump_flow_lpm,
            "pump_power_kw": pump_power_kw,
            "application_efficiency": application_efficiency,
            "active": True,
            "config_version": "2026-10-08-demo-1",
            "created_at": now_iso,
        }

        state_item = {
            "plot_id": plot_id,
            "depletion_mm": 10.0,  # initial healthy moisture
            "crop_stage": "initial",
            "last_irrigation_date": None,
            "last_irrigation_depth_mm": None,
            "confidence_score": 0.95,
            "data_quality": "GOOD",
            "version": 1,
            "as_of": now_iso,
        }

        if self.use_aws and self.table:
            # DynamoDB TransactWrite or batch
            self.table.put_item(Item={"PK": f"FARMER#{farmer_id}", "SK": "META", **farmer_item})
            self.table.put_item(
                Item={
                    "PK": f"PLOT#{plot_id}",
                    "SK": "META",
                    "GSI1PK": "STATUS#ACTIVE",
                    "GSI1SK": f"PLOT#{plot_id}",
                    **plot_item,
                }
            )
            self.table.put_item(Item={"PK": f"PLOT#{plot_id}", "SK": "STATE", **state_item})
        else:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO khetsathi (PK, SK, data_json) VALUES (?, ?, ?)",
                    (f"FARMER#{farmer_id}", "META", json.dumps(farmer_item)),
                )
                self.conn.execute(
                    "INSERT OR REPLACE INTO khetsathi (PK, SK, GSI1PK, GSI1SK, data_json) VALUES (?, ?, ?, ?, ?)",
                    (f"PLOT#{plot_id}", "META", "STATUS#ACTIVE", f"PLOT#{plot_id}", json.dumps(plot_item)),
                )
                self.conn.execute(
                    "INSERT OR REPLACE INTO khetsathi (PK, SK, data_json) VALUES (?, ?, ?)",
                    (f"PLOT#{plot_id}", "STATE", json.dumps(state_item)),
                )

        return {
            "farmer_id": farmer_id,
            "plot_id": plot_id,
            "plot_access_token": access_token,
            "state_summary": {
                "crop": crop,
                "crop_stage": "initial",
                "depletion_mm": 10.0,
                "confidence": "HIGH",
            },
        }

    def get_plot(self, plot_id: str) -> Optional[Dict[str, Any]]:
        """Fetch plot metadata and state."""
        if self.use_aws and self.table:
            meta = self.table.get_item(Key={"PK": f"PLOT#{plot_id}", "SK": "META"}).get("Item")
            state = self.table.get_item(Key={"PK": f"PLOT#{plot_id}", "SK": "STATE"}).get("Item")
        else:
            cur = self.conn.cursor()
            cur.execute("SELECT data_json FROM khetsathi WHERE PK = ? AND SK = ?", (f"PLOT#{plot_id}", "META"))
            meta_row = cur.fetchone()
            cur.execute("SELECT data_json FROM khetsathi WHERE PK = ? AND SK = ?", (f"PLOT#{plot_id}", "STATE"))
            state_row = cur.fetchone()
            meta = json.loads(meta_row[0]) if meta_row else None
            state = json.loads(state_row[0]) if state_row else None

        if not meta:
            return None

        return {
            "plot_id": plot_id,
            "plot": meta,
            "state": state or {},
        }

    def list_active_plots(self) -> List[Dict[str, Any]]:
        """Retrieve all active plots for the daily decision runner."""
        plots = []
        if self.use_aws and self.table:
            resp = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :status",
                ExpressionAttributeValues={":status": "STATUS#ACTIVE"},
            )
            plots = resp.get("Items", [])
        else:
            cur = self.conn.cursor()
            cur.execute("SELECT data_json FROM khetsathi WHERE GSI1PK = ?", ("STATUS#ACTIVE",))
            for row in cur.fetchall():
                plots.append(json.loads(row[0]))
        return plots

    def get_today_decision(self, plot_id: str, decision_date: str) -> Optional[Dict[str, Any]]:
        """Fetch today's decision record."""
        sk = f"DEC#{decision_date}"
        if self.use_aws and self.table:
            item = self.table.get_item(Key={"PK": f"PLOT#{plot_id}", "SK": sk}).get("Item")
            return item
        else:
            cur = self.conn.cursor()
            cur.execute("SELECT data_json FROM khetsathi WHERE PK = ? AND SK = ?", (f"PLOT#{plot_id}", sk))
            row = cur.fetchone()
            return json.loads(row[0]) if row else None

    def save_decision(self, decision: Dict[str, Any]) -> None:
        """Persist a decision record idempotently."""
        plot_id = decision["plot_id"]
        decision_date = decision["decision_date"]
        pk = f"PLOT#{plot_id}"
        sk = f"DEC#{decision_date}"

        if self.use_aws and self.table:
            self.table.put_item(Item={"PK": pk, "SK": sk, **decision})
        else:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO khetsathi (PK, SK, data_json) VALUES (?, ?, ?)",
                    (pk, sk, json.dumps(decision)),
                )

    def get_decision_history(self, plot_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Fetch past decisions, newest first."""
        history = []
        if self.use_aws and self.table:
            resp = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={":pk": f"PLOT#{plot_id}", ":sk_prefix": "DEC#"},
                ScanIndexForward=False,
                Limit=limit,
            )
            history = resp.get("Items", [])
        else:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT data_json FROM khetsathi WHERE PK = ? AND SK LIKE 'DEC#%' ORDER BY SK DESC LIMIT ?",
                (f"PLOT#{plot_id}", limit),
            )
            for row in cur.fetchall():
                history.append(json.loads(row[0]))
        return history

    def save_feedback(
        self,
        plot_id: str,
        decision_id: str,
        status: str,  # "DONE" or "NOT_DONE"
        actual_duration_minutes: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save farmer feedback and update plot state accordingly."""
        feedback_id = f"fbk_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        feedback_item = {
            "feedback_id": feedback_id,
            "plot_id": plot_id,
            "decision_id": decision_id,
            "status": status.upper(),
            "actual_duration_minutes": actual_duration_minutes,
            "reason": reason,
            "recorded_at": now_iso,
        }

        pk = f"PLOT#{plot_id}"
        sk = f"FB#{decision_id}"

        if self.use_aws and self.table:
            self.table.put_item(Item={"PK": pk, "SK": sk, **feedback_item})
        else:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO khetsathi (PK, SK, data_json) VALUES (?, ?, ?)",
                    (pk, sk, json.dumps(feedback_item)),
                )

        # If DONE, update plot state with last irrigation date
        if status.upper() == "DONE":
            self._update_plot_state_on_irrigation(plot_id, now_iso)

        return feedback_item

    def _update_plot_state_on_irrigation(self, plot_id: str, timestamp_iso: str):
        plot_data = self.get_plot(plot_id)
        if not plot_data or not plot_data.get("state"):
            return
        state = plot_data["state"]
        state["last_irrigation_date"] = timestamp_iso[:10]
        state["depletion_mm"] = 5.0  # Refilled after irrigation
        state["as_of"] = timestamp_iso
        state["version"] = state.get("version", 1) + 1

        pk = f"PLOT#{plot_id}"
        sk = "STATE"
        if self.use_aws and self.table:
            self.table.put_item(Item={"PK": pk, "SK": sk, **state})
        else:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO khetsathi (PK, SK, data_json) VALUES (?, ?, ?)",
                    (pk, sk, json.dumps(state)),
                )
