"""
DSpace MCP Server — Export Tools

Provides CSV export of DSpace collections via the Scripts API.

The export flow is asynchronous:
  1. POST /api/system/scripts/metadata-export/processes  → launches a background process
  2. Poll GET /api/system/processes/{id}                 → wait for COMPLETED / FAILED
  3. GET /api/system/processes/{id}/files                → find the exportCSV bitstream
  4. GET /api/core/bitstreams/{uuid}/content             → download the CSV bytes
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from dspace_client import DSpaceClient

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 2
_POLL_TIMEOUT_SECONDS = 120


def register(mcp: "FastMCP", client: "DSpaceClient") -> None:

    @mcp.tool()
    def get_process_status(process_id: str) -> dict[str, Any]:
        """
        Check the status of an asynchronous DSpace script process.

        Args:
            process_id: The numeric process ID returned when a script was started.

        Returns:
            A dict with 'process_id', 'script_name', 'status' (SCHEDULED/RUNNING/COMPLETED/FAILED),
            'start_time', 'end_time', and 'parameters'.
        """
        try:
            data = client.get(f"/api/system/processes/{process_id}")
        except requests.HTTPError as exc:
            return {"error": f"DSpace API error: {exc.response.status_code} — {exc.response.text}"}

        return {
            "process_id": data.get("processId"),
            "script_name": data.get("scriptName"),
            "status": data.get("processStatus"),
            "start_time": data.get("startTime"),
            "end_time": data.get("endTime"),
            "creation_time": data.get("creationTime"),
            "parameters": data.get("parameters", []),
        }

    @mcp.tool()
    def export_collection_csv(collection_uuid: str, timeout_seconds: int = 120) -> dict[str, Any]:
        """
        Export all item metadata from a collection as a CSV file.

        This operation is asynchronous: it launches a DSpace background process,
        polls until it completes (or times out), then returns the CSV content as a string.

        The CSV uses DSpace's standard metadata-export format, with one row per item
        and one column per Dublin Core field.

        Args:
            collection_uuid: UUID of the collection to export.
            timeout_seconds: Maximum seconds to wait for the export to finish (default 120).

        Returns:
            A dict with 'process_id', 'status', and 'csv_content' (string) on success,
            or 'error' on failure.
        """
        # Step 1: Launch the metadata-export script
        # The script accepts -i <collection-uuid> as the collection identifier.
        # Parameters are sent as multipart/form-data fields.
        try:
            csrf = client._csrf()
            url = f"{client.base_url}/api/system/scripts/metadata-export/processes"
            resp = client.session.post(
                url,
                data={"-i": collection_uuid},
                headers={"X-XSRF-TOKEN": csrf},
            )
            if resp.status_code == 401:
                client._relogin()
                csrf = client._csrf()
                resp = client.session.post(
                    url,
                    data={"-i": collection_uuid},
                    headers={"X-XSRF-TOKEN": csrf},
                )
            resp.raise_for_status()
        except requests.HTTPError as exc:
            return {
                "error": f"Failed to start export process: {exc.response.status_code} — {exc.response.text}"
            }

        process_data = resp.json()
        process_id = str(process_data.get("processId", ""))
        if not process_id:
            return {"error": "Export process started but no processId returned.", "raw": process_data}

        logger.info("Export process started with id=%s for collection=%s", process_id, collection_uuid)

        # Step 2: Poll until COMPLETED or FAILED
        effective_timeout = min(timeout_seconds, _POLL_TIMEOUT_SECONDS)
        deadline = time.time() + effective_timeout
        status = process_data.get("processStatus", "RUNNING")

        while status in ("SCHEDULED", "RUNNING"):
            if time.time() > deadline:
                return {
                    "error": f"Export timed out after {effective_timeout}s. "
                             f"Process {process_id} is still {status}. "
                             "Use get_process_status() to check later.",
                    "process_id": process_id,
                    "status": status,
                }
            time.sleep(_POLL_INTERVAL_SECONDS)
            try:
                proc = client.get(f"/api/system/processes/{process_id}")
                status = proc.get("processStatus", "RUNNING")
            except requests.HTTPError as exc:
                return {"error": f"Failed to poll process status: {exc}"}

        if status == "FAILED":
            return {
                "error": f"Export process {process_id} failed.",
                "process_id": process_id,
                "status": "FAILED",
            }

        # Step 3: Find the exportCSV bitstream in the process files
        try:
            files_data = client.get(f"/api/system/processes/{process_id}/files")
        except requests.HTTPError as exc:
            return {"error": f"Could not retrieve process files: {exc}"}

        bitstreams = files_data.get("_embedded", {}).get("bitstreams", [])
        csv_bitstream_uuid = None
        for bs in bitstreams:
            file_type_values = bs.get("metadata", {}).get("dspace.process.filetype", [])
            for ftv in file_type_values:
                if ftv.get("value") == "exportCSV":
                    csv_bitstream_uuid = bs.get("uuid")
                    break
            if csv_bitstream_uuid:
                break

        if not csv_bitstream_uuid:
            return {
                "error": "Export completed but no exportCSV bitstream was found.",
                "process_id": process_id,
                "status": status,
                "files_found": [bs.get("name") for bs in bitstreams],
            }

        # Step 4: Download the CSV content
        try:
            csv_bytes = client.get_content(f"/api/core/bitstreams/{csv_bitstream_uuid}/content")
            csv_text = csv_bytes.decode("utf-8", errors="replace")
        except requests.HTTPError as exc:
            return {"error": f"Failed to download CSV content: {exc}"}

        return {
            "process_id": process_id,
            "status": "COMPLETED",
            "collection_uuid": collection_uuid,
            "csv_content": csv_text,
        }
