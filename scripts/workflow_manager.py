"""Load, validate, parameterize, and sync named ComfyUI API workflows."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

try:
    from .common import DEFAULT_CONFIG, PROJECT_ROOT, load_config
    from .drive_manager import get_drive_root, sync_workflow_templates
except ImportError:
    from common import DEFAULT_CONFIG, PROJECT_ROOT, load_config
    from drive_manager import get_drive_root, sync_workflow_templates


REGISTRY_PATH = PROJECT_ROOT / "workflows" / "registry.json"


class WorkflowError(RuntimeError):
    pass


def load_registry(path: str | Path = REGISTRY_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        registry = json.load(handle)
    if not isinstance(registry.get("workflows"), dict):
        raise WorkflowError("Workflow registry must have a 'workflows' object")
    return registry


def get_workflow(workflow_id: str, *, registry_path: str | Path = REGISTRY_PATH,
                 project_root: str | Path = PROJECT_ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = load_registry(registry_path)
    workflows = registry["workflows"]
    if workflow_id not in workflows:
        raise WorkflowError(f"Unknown workflow '{workflow_id}'. Available: {', '.join(workflows)}")
    descriptor = workflows[workflow_id]
    graph_path = Path(project_root) / "workflows" / descriptor["api_file"]
    try:
        with graph_path.open("r", encoding="utf-8") as handle:
            graph = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise WorkflowError(f"Could not load workflow graph {graph_path}: {error}") from error
    validate_api_graph(graph, graph_path)
    return descriptor, graph


def validate_api_graph(graph: dict[str, Any], source: str | Path = "workflow") -> None:
    if not isinstance(graph, dict) or not graph:
        raise WorkflowError(f"Workflow graph is empty or invalid: {source}")
    for node_id, node in graph.items():
        if not isinstance(node, dict) or not isinstance(node.get("class_type"), str):
            raise WorkflowError(f"Node {node_id} in {source} has no class_type")
        if not isinstance(node.get("inputs", {}), dict):
            raise WorkflowError(f"Node {node_id} in {source} has invalid inputs")


def apply_parameters(graph: dict[str, Any], descriptor: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(graph)
    nodes = descriptor.get("nodes", {})
    for parameter, value in parameters.items():
        if value is None or parameter not in nodes:
            continue
        mapping = nodes[parameter]
        node_id = str(mapping["id"])
        if node_id not in result:
            raise WorkflowError(f"Registry maps '{parameter}' to missing node {node_id}")
        result[node_id]["inputs"][mapping["input"]] = value
    return result


def install_workflows(drive_root: str | Path, *, project_root: str | Path = PROJECT_ROOT) -> list[Path]:
    return sync_workflow_templates(project_root, drive_root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--drive-root")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--sync", action="store_true")
    args = parser.parse_args()
    registry = load_registry()
    if args.list or not args.sync:
        for workflow_id, entry in registry["workflows"].items():
            print(f"{workflow_id}: {entry['title']} [{entry['model']}]")
    if args.sync:
        config = load_config(args.config)
        drive_root = get_drive_root(config, args.drive_root)
        copied = install_workflows(drive_root)
        print(f"Workflow/prompt files ready in Drive: {len(copied)} copied, existing files preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
