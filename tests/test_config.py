"""ytfeed.config — machine-specific paths have no default and fail loudly."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ytfeed.config import PROJECT_ROOT, Config, ConfigError, load_config, require_path


def _write(tmp: str, body: str) -> Path:
    p = Path(tmp) / "config.toml"
    p.write_text(body)
    return p


class DefaultsTest(unittest.TestCase):
    def test_required_paths_default_to_none(self):
        cfg = Config()
        self.assertIsNone(cfg.paths.client_secret_path)
        self.assertIsNone(cfg.paths.rag_output_dir)

    def test_other_paths_keep_project_relative_defaults(self):
        cfg = Config()
        self.assertEqual(cfg.paths.db_path, PROJECT_ROOT / "data" / "ytfeed.db")
        self.assertEqual(cfg.paths.token_path, PROJECT_ROOT / "secrets" / "token.json")

    def test_every_default_is_unset_or_inside_the_project(self):
        # nothing machine-specific may ship as a default in a public repo
        for key, value in vars(Config().paths).items():
            if value is None:
                continue
            self.assertTrue(Path(value).is_relative_to(PROJECT_ROOT), f"{key}={value}")


class LoadTest(unittest.TestCase):
    def test_empty_string_means_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(_write(tmp, '[paths]\nclient_secret_path = ""\nrag_output_dir = "  "\n'))
        self.assertIsNone(cfg.paths.client_secret_path)
        self.assertIsNone(cfg.paths.rag_output_dir)

    def test_example_config_leaves_required_paths_unset(self):
        cfg = load_config(PROJECT_ROOT / "config.example.toml")
        self.assertIsNone(cfg.paths.client_secret_path)
        self.assertIsNone(cfg.paths.rag_output_dir)

    def test_relative_path_resolves_against_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(_write(tmp, '[paths]\nclient_secret_path = "secrets/client.json"\n'))
        self.assertEqual(cfg.paths.client_secret_path, PROJECT_ROOT / "secrets" / "client.json")

    def test_tilde_and_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(_write(tmp, '[paths]\nrag_output_dir = "~/vault/raw"\ndb_path = "/tmp/x.db"\n'))
        self.assertEqual(cfg.paths.rag_output_dir, Path("~/vault/raw").expanduser())
        self.assertEqual(cfg.paths.db_path, Path("/tmp/x.db"))


class RequirePathTest(unittest.TestCase):
    def test_unset_raises_config_error_naming_the_key(self):
        with self.assertRaises(ConfigError) as ctx:
            require_path(Config(), "rag_output_dir")
        self.assertIn("paths.rag_output_dir", str(ctx.exception))
        self.assertIn("config.toml", str(ctx.exception))

    def test_set_returns_path(self):
        cfg = Config()
        cfg.paths.client_secret_path = Path("/somewhere/client.json")
        self.assertEqual(require_path(cfg, "client_secret_path"), Path("/somewhere/client.json"))


class SettingsMaskTest(unittest.TestCase):
    def test_mask_renders_unset(self):
        from ytfeed.web.routes.settings import NOT_SET, _mask

        self.assertEqual(_mask(None), NOT_SET)
        self.assertEqual(_mask(Path("/a/b/c.json")), "…/b/c.json")


if __name__ == "__main__":
    unittest.main()
