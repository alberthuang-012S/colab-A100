from __future__ import annotations

import hashlib
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.drive_manager import LAYOUT, ensure_drive_layout, get_drive_root, sync_workflow_templates
from scripts.environment_check import detect_environment
from scripts.metadata_manager import build_metadata
from scripts.model_manager import model_cached_valid, model_is_valid
from scripts.output_manager import make_output_filename, write_output_bundle
from scripts.workflow_manager import apply_parameters, get_workflow, load_registry
from scripts.common import DEFAULT_CONFIG, load_config


class ConfigTests(unittest.TestCase):
    def test_config_loads_and_has_model_switches(self) -> None:
        config = load_config(DEFAULT_CONFIG)
        self.assertTrue(config["install_flux"])
        self.assertFalse(config["install_sdxl"])


class EnvironmentTests(unittest.TestCase):
    def test_detect_environment_with_mock_cuda_and_drive(self) -> None:
        fake_torch = types.SimpleNamespace(
            __version__="2.7.0-test",
            version=types.SimpleNamespace(cuda="12.8"),
            cuda=types.SimpleNamespace(
                is_available=lambda: True,
                current_device=lambda: 0,
                get_device_name=lambda _index: "NVIDIA A100-SXM4-40GB",
                get_device_properties=lambda _index: types.SimpleNamespace(total_memory=40 * 1024**3),
            ),
        )
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict("sys.modules", {"torch": fake_torch}), patch(
                "scripts.environment_check._nvidia_smi_info", return_value={}
            ):
                report = detect_environment(load_config(DEFAULT_CONFIG), temporary)
        self.assertEqual(report.status, "READY")
        self.assertEqual(report.gpu_name, "NVIDIA A100-SXM4-40GB")
        self.assertAlmostEqual(report.vram_gb or 0, 40.0, places=1)
        self.assertTrue(report.torch_cuda_available)

    def test_no_gpu_is_reported_as_warning(self) -> None:
        fake_torch = types.SimpleNamespace(
            __version__="cpu-test", version=types.SimpleNamespace(cuda=None),
            cuda=types.SimpleNamespace(is_available=lambda: False),
        )
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict("sys.modules", {"torch": fake_torch}), patch(
                "scripts.environment_check._nvidia_smi_info", return_value={}
            ):
                report = detect_environment(load_config(DEFAULT_CONFIG), temporary)
        self.assertEqual(report.status, "WARNING")
        self.assertFalse(report.gpu_exists)
        self.assertTrue(any("No GPU" in warning for warning in report.warnings))


class DriveTests(unittest.TestCase):
    def test_drive_path_override_and_directory_creation_are_idempotent(self) -> None:
        config = load_config(DEFAULT_CONFIG)
        with tempfile.TemporaryDirectory() as temporary:
            root = get_drive_root(config, temporary)
            first_created = ensure_drive_layout(root)
            second_created = ensure_drive_layout(root)
            self.assertEqual(root, Path(temporary))
            self.assertEqual(len(first_created), len(LAYOUT))
            self.assertEqual(second_created, [])
            self.assertTrue((root / "outputs" / "final").is_dir())

    def test_template_sync_updates_managed_files_and_keeps_user_edits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            drive = Path(temporary) / "drive"
            source = project / "workflows" / "text-to-image" / "example.json"
            source.parent.mkdir(parents=True)
            source.write_text("v1", encoding="utf-8")
            first = sync_workflow_templates(project, drive)
            self.assertEqual(len(first), 1)
            source.write_text("v2", encoding="utf-8")
            second = sync_workflow_templates(project, drive)
            self.assertEqual(len(second), 1)
            target = drive / "workflows" / "text-to-image" / "example.json"
            self.assertEqual(target.read_text(encoding="utf-8"), "v2")
            target.write_text("drive customization", encoding="utf-8")
            source.write_text("v3", encoding="utf-8")
            third = sync_workflow_templates(project, drive)
            self.assertEqual(third, [])
            self.assertEqual(target.read_text(encoding="utf-8"), "drive customization")


class ModelTests(unittest.TestCase):
    def test_model_existence_and_optional_hash_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.safetensors"
            path.write_bytes(b"0123456789")
            model = {"min_size_bytes": 5}
            self.assertTrue(model_is_valid(path, model))
            self.assertFalse(model_is_valid(path, {"min_size_bytes": 11}))
            good_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            bad_hash = "0" * 64
            self.assertTrue(model_is_valid(path, model, good_hash))
            self.assertFalse(model_is_valid(path, model, bad_hash))

    def test_model_hash_is_cached_after_first_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.safetensors"
            path.write_bytes(b"0123456789")
            model = {"min_size_bytes": 5}
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertTrue(model_cached_valid(path, model, digest))
            marker = path.with_name(path.name + ".sha256")
            self.assertTrue(marker.exists())
            with patch("scripts.model_manager.sha256_file", side_effect=AssertionError("unexpected rehash")):
                self.assertTrue(model_cached_valid(path, model, digest))


class MetadataAndOutputTests(unittest.TestCase):
    def test_metadata_has_reproducibility_fields(self) -> None:
        metadata = build_metadata(
            prompt="A white jar on a stone surface", negative_prompt="clutter", seed=123,
            model="FLUX.1-schnell FP8", model_version="model.safetensors",
            workflow="product-kv", workflow_version="1.0.0", width=1024, height=1024,
            steps=4, guidance=1.0, sampler="euler", scheduler="simple", gpu="NVIDIA A100",
            generated_at="2026-09-29T12:00:00+08:00",
        )
        required = {"prompt", "negative_prompt", "seed", "model", "model_version", "workflow",
                    "workflow_version", "width", "height", "steps", "cfg_guidance", "sampler",
                    "scheduler", "date", "gpu"}
        self.assertEqual(set(metadata), required)
        self.assertEqual(metadata["seed"], 123)

    def test_filename_and_sidecar_generation(self) -> None:
        self.assertEqual(
            make_output_filename("NNE Product", "product-kv", 12345, date="2026-09-29"),
            "NNE-Product_product-kv_20260929_seed12345.png",
        )
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "comfy.png"
            source.write_bytes(b"fake png data")
            root = Path(temporary) / "drive"
            metadata = {"date": "2026-09-29T12:00:00+08:00", "seed": 12345}
            image, sidecar = write_output_bundle(
                source, root, product="NNE", workflow="product-kv", seed=12345,
                metadata=metadata,
            )
            self.assertTrue(image.exists())
            self.assertEqual(json.loads(sidecar.read_text(encoding="utf-8")), metadata)


class WorkflowTests(unittest.TestCase):
    def test_configured_workflow_loads_and_parameters_are_applied(self) -> None:
        descriptor, graph = get_workflow("text-to-image")
        parameterized = apply_parameters(graph, descriptor, {"prompt": "Test prompt", "seed": 77, "width": 1536})
        self.assertEqual(parameterized["2"]["inputs"]["text"], "Test prompt")
        self.assertEqual(parameterized["5"]["inputs"]["seed"], 77)
        self.assertEqual(parameterized["4"]["inputs"]["width"], 1536)
        self.assertNotEqual(graph["2"]["inputs"]["text"], "Test prompt")
        self.assertEqual(len(load_registry()["workflows"]), 6)

    def test_all_registry_parameter_mappings_point_to_graph_inputs(self) -> None:
        for workflow_id in load_registry()["workflows"]:
            with self.subTest(workflow=workflow_id):
                descriptor, graph = get_workflow(workflow_id)
                for parameter, mapping in descriptor.get("nodes", {}).items():
                    node = graph[str(mapping["id"])]
                    self.assertIn(mapping["input"], node["inputs"], f"{workflow_id}.{parameter}")


if __name__ == "__main__":
    unittest.main()
