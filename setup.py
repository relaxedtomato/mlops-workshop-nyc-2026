#!/usr/bin/env python3
"""
Workshop environment setup script.

Reads ~/$(whoami)-mlops-config.yaml and for each lab:
  1. Copies config.example.yaml -> config.yaml (if needed)
  2. Copies secrets.example.yaml -> secrets.yaml (if needed)
  3. Copies example.env -> .env (if needed)
  4. Substitutes placeholder values with your credentials
  5. Replaces $USER with your username in all pipeline-config.yaml files

Skips a file if it already exists and contains no placeholder values.

Usage:
  python3 setup.py
"""
import pathlib
import re
import shutil
import os

import yaml

REPO_ROOT   = pathlib.Path(__file__).parent
LABS_DIR    = REPO_ROOT / "labs"
USERNAME    = os.getenv("USER")
_config_name = f"{USERNAME}-mlops-config.yaml"
CONFIG_FILE = (
    REPO_ROOT / _config_name
    if (REPO_ROOT / _config_name).exists()
    else pathlib.Path.home() / _config_name
)

PLACEHOLDER_PATTERN = re.compile(r"<[^>]+>")


def is_placeholder(text):
    return bool(PLACEHOLDER_PATTERN.search(text))


def already_configured(path):
    """Return True if the file exists and has no placeholder values remaining."""
    if not path.exists():
        return False
    content = path.read_text()
    return not is_placeholder(content)


def substitute(content, cfg):
    replacements = {
        # S3 — http:// variant first so it matches before the bare placeholder
        "http://<your-s3-endpoint>":     cfg.get("s3_endpoint", ""),
        "<your-s3-endpoint>":            cfg.get("s3_endpoint", ""),
        "<your-region>":                 "us-east-1",
        # LLM / VLM
        "<your-llm-endpoint>":           cfg.get("vlm_endpoint", ""),
        "<your-model-name>":             cfg.get("llm_model", ""),
        "<your-vlm-endpoint>":           cfg.get("vlm_endpoint", ""),
        "<your-vision-model>":           cfg.get("vision_model", ""),
        "<your-embedding-model>":        cfg.get("embedding_model", ""),
        "<your-summary-model>":          cfg.get("summary_model", ""),
        # VastDB — http:// variant first
        "http://<your-vastdb-endpoint>": cfg.get("vdb_endpoint", ""),
        "<your-vastdb-endpoint>":        cfg.get("vdb_endpoint", ""),
        "<your-vastdb-bucket>":          cfg.get("vdb_bucket", ""),
        # secrets
        "<your-s3-access-key>":          cfg.get("s3_access_key_id", ""),
        "<your-s3-secret-key>":          cfg.get("s3_secret_access_key", ""),
        "<your-vlm-api-key>":            cfg.get("llm_api_key", ""),
        "<your-vastdb-access-key>":      cfg.get("vdb_access_key_id", ""),
        "<your-vastdb-secret-key>":      cfg.get("vdb_secret_access_key", ""),
        # lab6 .env — literal defaults in the example file
        "http://localhost:11434/v1":     cfg.get("vlm_endpoint", ""),
        "qwen3-embedding:0.6b":          cfg.get("embedding_model", ""),
        "<your-llm-key>":                cfg.get("llm_api_key", ""),
        "<your-bucket>":                 cfg.get("vdb_bucket", ""),
        "<your-access-key>":             cfg.get("vdb_access_key_id", ""),
        "<your-secret-key>":             cfg.get("vdb_secret_access_key", ""),
        # OUTPUT_BUCKET must come before $USER so the pattern still contains the literal $USER
        "OUTPUT_BUCKET: \"$USER-video-segments\"": f"OUTPUT_BUCKET: \"{cfg.get('s3_bucket_video_segments', '')}\"",
        # $USER last
        "$USER":                         USERNAME,
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, str(value))
    return content


def process_file(example_path, target_path, cfg):
    if not example_path.exists():
        return

    if already_configured(target_path):
        print(f"  skipping {target_path.name} (already configured)")
        return

    shutil.copy(example_path, target_path)
    content = target_path.read_text()
    content = substitute(content, cfg)
    target_path.write_text(content)

    if is_placeholder(content):
        remaining = PLACEHOLDER_PATTERN.findall(content)
        print(f"  wrote {target_path.name} (warning: unfilled placeholders: {remaining})")
    else:
        print(f"  wrote {target_path.name}")


def write_root_env(cfg):
    """Write a .env at the repo root with registry and user variables."""
    env_path = REPO_ROOT / ".env"
    lines = [
        f"export USER={USERNAME}",
        f"export DE_REG_HOST={cfg.get('de_reg_host', '')}",
        f"export DE_REG_USER={USERNAME}",
        f"export DE_REG_NAME={cfg.get('de_reg_name', '')}",
    ]
    env_path.write_text("\n".join(lines) + "\n")
    print(f"  wrote .env (source .env to set DE_REG_HOST, DE_REG_USER, DE_REG_NAME, USER)")


def replace_user_in_pipeline_configs():
    for pipeline_config in LABS_DIR.rglob("pipeline-config.yaml"):
        content = pipeline_config.read_text()
        if "$USER" in content:
            pipeline_config.write_text(content.replace("$USER", USERNAME))
            print(f"  replaced $USER in {pipeline_config.relative_to(REPO_ROOT)}")


def main():
    if not CONFIG_FILE.exists():
        raise SystemExit(
            f"Config file not found: {_config_name}\n"
            f"Drop your {_config_name} into the repo root or home directory and re-run."
        )

    print(f"Reading {CONFIG_FILE}...")
    cfg = yaml.safe_load(CONFIG_FILE.read_text())
    print(f"Username: {USERNAME}\n")

    labs_with_config = [
        "lab3-llm-connect",
        "lab4-video-ingest",
        "lab5-video-embeddings",
    ]
    labs_with_env = [
        "lab6-video-search",
    ]

    for lab_slug in labs_with_config:
        lab_dir = LABS_DIR / lab_slug
        if not lab_dir.exists():
            print(f"{lab_slug}: directory not found, skipping")
            continue
        print(f"{lab_slug}:")
        process_file(lab_dir / "config.example.yaml",  lab_dir / "config.yaml",  cfg)
        process_file(lab_dir / "secrets.example.yaml", lab_dir / "secrets.yaml", cfg)

    for lab_slug in labs_with_env:
        lab_dir = LABS_DIR / lab_slug
        if not lab_dir.exists():
            print(f"{lab_slug}: directory not found, skipping")
            continue
        print(f"{lab_slug}:")
        process_file(lab_dir / "example.env", lab_dir / ".env", cfg)

    print("\nWriting root .env...")
    write_root_env(cfg)

    print("\nReplacing $USER in pipeline configs (modifies committed files — revert with git checkout if needed)...")
    replace_user_in_pipeline_configs()

    print(f"\nSetup complete for user: {USERNAME}")
    print(f"Run: source .env")


if __name__ == "__main__":
    main()
