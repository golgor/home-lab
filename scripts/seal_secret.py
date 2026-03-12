#!/usr/bin/env python3
"""Interactive Kubernetes secret sealing tool using kubeseal.

Reads key=value pairs from a .env file and produces a SealedSecret manifest
in the current working directory.

Prerequisites:
    - certs/cert.pem must exist (run: mise run fetch-cert)
    - kubeseal and kubectl must be installed and on PATH

Usage:
    uv run scripts/seal_secret.py
"""

import re
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CERT = REPO_ROOT / "certs" / "cert.pem"


def print_header():
    separator = "=" * 50
    print("\n" + separator)
    print("       Seal Secret Tool")
    print(separator + "\n")


def validate_k8s_name(name: str, field_name: str) -> bool:
    """Validate a Kubernetes resource name.

    Rules:
    - Must be lowercase alphanumeric or hyphen
    - Must start and end with alphanumeric
    - Max 63 characters
    """
    if not name:
        print(f"\n❌ Error: {field_name} cannot be empty")
        return False

    if len(name) > 63:
        print(f"\n❌ Error: {field_name} must be 63 characters or less")
        return False

    pattern = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"
    if not re.match(pattern, name):
        print(
            f"\n❌ Error: {field_name} must contain only lowercase letters, numbers, and hyphens"
        )
        print("         Must start and end with a letter or number")
        return False

    return True


def get_namespace() -> str:
    """Get namespace with validation."""
    while True:
        namespace = input("Namespace: ").strip()
        if validate_k8s_name(namespace, "Namespace"):
            return namespace
        print()


def get_secret_name(default: str) -> str:
    """Get sealed secret name with validation (optional field)."""
    while True:
        name = input(f"Sealed secret name [{default}]: ").strip()
        if not name:
            return default
        if validate_k8s_name(name, "Secret name"):
            return name
        print()


def get_env_file() -> Path:
    """Get .env file path with validation."""
    while True:
        path_str = input(".env file path [.env]: ").strip() or ".env"
        path = Path(path_str)

        if not path.exists():
            print(f"\n❌ Error: File not found: {path}\n")
            continue
        if not path.is_file():
            print(f"\n❌ Error: Not a file: {path}\n")
            continue

        return path


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict, skipping blank lines and comments."""
    secrets: dict[str, str] = {}
    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            print(
                f"  Warning: skipping line {lineno} (no '='): {raw!r}", file=sys.stderr
            )
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if not key:
            print(f"  Warning: skipping line {lineno} (empty key)", file=sys.stderr)
            continue
        secrets[key] = value
    return secrets


def format_sealed_secret(yaml_content: str) -> str:
    """Format sealed secret YAML to wrap encrypted values at 76 characters.

    Transforms inline base64 values into literal block scalars with proper wrapping.
    Uses 6-space indentation for wrapped content lines to stay within 80 char limit.
    """
    lines = yaml_content.splitlines()
    result = []
    in_encrypted_data = False
    encrypted_data_indent = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        # Track when we enter/exit the encryptedData section
        if stripped == "encryptedData:":
            in_encrypted_data = True
            encrypted_data_indent = len(line) - len(stripped)
            result.append(line)
            i += 1
            continue

        # Exit encryptedData section when we see a key at same or lower indent level
        if in_encrypted_data:
            current_indent = len(line) - len(stripped)
            if (
                stripped
                and not stripped.startswith("#")
                and current_indent <= encrypted_data_indent
            ):
                in_encrypted_data = False

        # Process lines within encryptedData section
        if in_encrypted_data and stripped and not stripped.startswith("#"):
            # Check if this is a key: value line (inline format)
            if ": " in stripped and not stripped.endswith(":"):
                key, value = stripped.split(": ", 1)
                # Check if value looks like base64 (no newlines, alphanumeric + special chars)
                if value and not value.startswith("|") and not value.startswith(">"):
                    # Wrap the base64 value at 74 characters to fit within 80-char limit
                    # (6 spaces indent + 74 chars content = 80 chars max)
                    wrapped_lines = textwrap.wrap(
                        value, width=74, break_on_hyphens=False, break_long_words=True
                    )
                    # Add the key with literal block scalar indicator (4 spaces total: 2 base + 2)
                    result.append(" " * (encrypted_data_indent + 2) + f"{key}: |-")
                    # Add wrapped lines with 6-space indentation (2 base + 4)
                    for wrapped_line in wrapped_lines:
                        result.append(" " * (encrypted_data_indent + 4) + wrapped_line)
                    i += 1
                    continue

        result.append(line)
        i += 1

    return "\n".join(result)


def seal_secret(namespace: str, secret_name: str, secrets: dict[str, str]) -> Path:
    """Seal secrets and return the output path."""
    if not CERT.exists():
        print(f"\n❌ Error: Certificate not found: {CERT}")
        print("   Run 'mise run fetch-cert' to download the cluster certificate.")
        sys.exit(1)

    output_path = Path.cwd() / f"{secret_name}-sealedsecret.yaml"
    print(f"\nSealing {len(secrets)} key(s) → {output_path.name}")

    kubectl_cmd = [
        "kubectl", "create", "secret", "generic", secret_name,
        f"--namespace={namespace}",
        "--dry-run=client", "-o", "yaml",
        *[f"--from-literal={k}={v}" for k, v in secrets.items()],
    ]

    kubeseal_cmd = ["kubeseal", "--cert", str(CERT), "--format", "yaml"]

    kubectl_result = subprocess.run(kubectl_cmd, capture_output=True, text=True)
    if kubectl_result.returncode != 0:
        print(f"\n❌ kubectl error:\n{kubectl_result.stderr}")
        sys.exit(1)

    kubeseal_result = subprocess.run(
        kubeseal_cmd, input=kubectl_result.stdout, capture_output=True, text=True
    )
    if kubeseal_result.returncode != 0:
        print(f"\n❌ kubeseal error:\n{kubeseal_result.stderr}")
        sys.exit(1)

    output_path.write_text(format_sealed_secret(kubeseal_result.stdout) + "\n")
    print(f"✓ Written: {output_path}")
    return output_path


def main() -> None:
    print_header()

    namespace = get_namespace()
    secret_name = get_secret_name(namespace)
    print()
    env_file = get_env_file()
    print()
    secrets = parse_env_file(env_file)

    if not secrets:
        print("❌ Error: No key=value pairs found in env file.")
        sys.exit(1)

    print(f"Loaded {len(secrets)} key(s): {', '.join(secrets.keys())}")

    output_path = seal_secret(namespace, secret_name, secrets)

    print("\n" + ("=" * 50))
    print("✓ Done!")
    print(f"\nGenerated file:\n  - {output_path}\n")


if __name__ == "__main__":
    main()
