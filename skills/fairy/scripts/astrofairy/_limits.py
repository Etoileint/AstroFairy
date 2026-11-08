from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

MiB = 1024 * 1024
KiB = 1024


def _limit(value: float, budget: str, unit: str, consumer: str) -> Any:
    return field(default=value, metadata={"budget": budget, "unit": unit, "consumer": consumer})


@dataclass(frozen=True)
class Limits:
    work_call_limit: int = _limit(1024, "B03", "registered calls", "task final work-call ceiling")
    work_call_warning: int = _limit(128, "B03", "registered calls", "task work-call warning")
    command_json_bytes: int = _limit(16 * MiB, "B07", "bytes", "CLI command and asset-import JSON input")
    content_bytes: int = _limit(256 * MiB, "B06", "bytes", "one captured content")
    task_capture_bytes: int = _limit(2 * 1024 * MiB, "B06", "bytes", "one task's unique captured content")
    stream_chunk_bytes: int = _limit(1 * MiB, "B06", "bytes", "streaming capture, hashing and export chunk")
    blob_bytes: int = _limit(16 * MiB, "B19", "bytes", "one in-memory blob or asset package")
    text_field_bytes: int = _limit(1 * MiB, "B08", "UTF-8 bytes", "ordinary semantic text fields")
    response_bytes: int = _limit(24 * KiB, "B09", "bytes", "CLI JSON response envelope")
    content_read_characters: int = _limit(24576, "B10", "Unicode characters", "content.read request ceiling")
    document_read_characters: int = _limit(24576, "B11", "Unicode characters", "free document read request")
    tool_definition_bytes: int = _limit(3 * MiB, "B12", "bytes", "one complete capability definition")
    schema_bytes: int = _limit(1 * MiB, "B13", "bytes", "one input/output JSON Schema")
    schema_states: int = _limit(65536, "B14", "visited states", "one schema reference-graph analysis")
    search_default_limit: int = _limit(8, "B15", "matches", "asset.search default short list")
    candidate_pool: int = _limit(
        100, "B15", "candidates per retrieval path", "hybrid retrieval candidate pool"
    )
    search_page_default_limit: int = _limit(50, "B16", "matches", "ordinary CLI search page default")
    search_max_results: int = _limit(200, "B16", "matches", "one search page ceiling")
    catalog_default_limit: int = _limit(12, "B18", "matches", "capability catalog default page")
    catalog_max_limit: int = _limit(100, "B18", "matches", "one capability catalog page ceiling")
    asset_content_bytes: int = _limit(16 * MiB, "B19", "UTF-8 bytes", "one non-workflow asset body")
    asset_summary_bytes: int = _limit(4 * KiB, "B20", "UTF-8 bytes", "one asset summary")
    capability_description_bytes: int = _limit(4 * KiB, "B21", "UTF-8 bytes", "one capability description")
    path_bytes: int = _limit(4096, "B24", "UTF-8 bytes", "one canonical relative path")
    path_segment_bytes: int = _limit(255, "B22", "UTF-8 bytes", "one portable path segment")
    media_type_bytes: int = _limit(512, "B22", "UTF-8 bytes", "one media type")
    machine_id_chars: int = _limit(80, "B23", "ASCII characters", "one machine identifier")
    capability_name_chars: int = _limit(128, "B23", "ASCII characters", "one capability name")
    error_bytes: int = _limit(4096, "B25", "bytes", "one public diagnostic")
    diagnostic_states: int = _limit(4096, "B25", "visited values", "one diagnostic traversal")
    control_scalar_bytes: int = _limit(128, "B26", "UTF-8 bytes", "one response control scalar")
    document_node_bytes: int = _limit(16 * KiB, "B27", "bytes", "one authenticated document node")
    document_chunk_characters: int = _limit(2048, "B28", "Unicode characters", "one document scalar chunk")
    document_fanout: int = _limit(16, "B29", "children", "one document tree node")
    document_cache_nodes: int = _limit(128, "B30", "nodes", "one document reader cache")
    document_key_prefix: int = _limit(16, "B31", "Unicode characters", "one key-navigation prefix")
    audit_text_characters: int = _limit(8192, "B32", "Unicode characters", "one full-audit text block")
    sqlite_busy_seconds: int = _limit(30, "B33", "seconds", "main, archive and audit SQLite connections")
    document_lock_seconds: int = _limit(30, "B34", "seconds", "archive initialization and writer admission")
    backup_busy_seconds: int = _limit(30, "B35", "seconds", "backup source and destination connections")
    backup_deadline_seconds: int = _limit(300, "B36", "seconds", "each database backup progress deadline")
    backup_pages: int = _limit(128, "B37", "pages per step", "SQLite native backup batch")
    backup_sleep_seconds: float = _limit(0.05, "B37", "seconds", "SQLite native backup busy sleep")
    backup_manifest_bytes: int = _limit(16 * KiB, "B38", "bytes", "one backup manifest")
    restore_chunk_bytes: int = _limit(1 * MiB, "B39", "bytes", "restore file copy chunk")
    install_timeout_seconds: int = _limit(600, "B40", "seconds", "development installation fixture command")
    handoff_json_bytes: int = _limit(16 * MiB, "B41", "bytes", "development handoff metadata")
    submission_bytes: int = _limit(1 * MiB, "B41", "bytes", "development submission document")
    delivery_lock_seconds: int = _limit(30, "B33", "seconds", "delivery directory serialization")
    model_prepare_lock_seconds: int = _limit(300, "B42", "seconds", "shared model-cache preparation")

    def manifest(self) -> list[dict[str, Any]]:
        return [
            {
                "field": item.name,
                "budget": item.metadata["budget"],
                "value": getattr(self, item.name),
                "unit": item.metadata["unit"],
                "consumer": item.metadata["consumer"],
            }
            for item in fields(self)
        ]


LIMITS = Limits()
