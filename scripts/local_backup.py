"""Create and restore on-demand archives of the local Docker Compose data volumes."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeGuard

STATEFUL_VOLUMES = {
    "postgres": "/var/lib/postgresql/data",
    "valkey": "/data",
    "seaweedfs": "/data",
    "qdrant": "/qdrant/storage",
}
ARCHIVE_IMAGE = "alpine:3.21"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = PROJECT_ROOT / "deploy" / "docker-compose.yml"


def _is_json_object(value: object) -> TypeGuard[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


def validate_manifest(value: object, project_name: str) -> dict[str, dict[str, str]]:
    """Validate a backup manifest before it can select volumes or archive paths."""
    if not _is_json_object(value):
        raise ValueError("Backup manifest must be a JSON object.")
    if value.get("format_version") != 1:
        raise ValueError("Unsupported backup manifest version.")
    if value.get("project_name") != project_name:
        raise ValueError("Backup belongs to a different Compose project.")

    raw_services = value.get("services")
    if not _is_json_object(raw_services) or set(raw_services) != set(STATEFUL_VOLUMES):
        raise ValueError("Backup manifest must contain exactly the local stateful services.")

    services: dict[str, dict[str, str]] = {}
    for service in STATEFUL_VOLUMES:
        entry = raw_services[service]
        if not _is_json_object(entry):
            raise ValueError(f"Invalid manifest entry for {service}.")
        volume_name = entry.get("volume_name")
        archive_name = entry.get("archive")
        if not isinstance(volume_name, str) or not volume_name:
            raise ValueError(f"Invalid volume name for {service}.")
        if archive_name != f"{service}.tar.gz":
            raise ValueError(f"Invalid archive name for {service}.")
        services[service] = {"volume_name": volume_name, "archive": archive_name}
    return services


def _run(command: list[str], *, capture_output: bool = False) -> bytes:
    result = subprocess.run(  # noqa: S603 - argument arrays avoid shell interpolation.
        command,
        check=False,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {error or command[0]}")
    return result.stdout or b""


def _compose_command(project_name: str, env_file: Path, *args: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-name",
        project_name,
        "--env-file",
        str(env_file),
        "--file",
        str(COMPOSE_FILE),
        *args,
    ]


def _container_id(project_name: str, env_file: Path, service: str, *, all_states: bool) -> str:
    args = ["ps"]
    if all_states:
        args.append("--all")
    args.extend(["--quiet", service])
    output = _run(_compose_command(project_name, env_file, *args), capture_output=True)
    container_id = output.decode("utf-8").strip().splitlines()
    if not container_id:
        raise RuntimeError(
            f"No container exists for {service}; create the Compose services before backing up."
        )
    return container_id[0]


def _volume_name(container_id: str, mount_path: str) -> str:
    output = _run(["docker", "inspect", container_id], capture_output=True)
    containers = json.loads(output)
    mounts = containers[0].get("Mounts", [])
    for mount in mounts:
        if mount.get("Destination") == mount_path and mount.get("Type") == "volume":
            name = mount.get("Name")
            if isinstance(name, str) and name:
                return name
    raise RuntimeError(f"Expected named data volume was not found at {mount_path}.")


def _docker_archive(
    volume_name: str,
    backup_directory: Path,
    archive_name: str,
    *,
    restore: bool = False,
) -> None:
    backup_path = backup_directory.resolve().as_posix()
    command = [
        "docker",
        "run",
        "--rm",
        "--mount",
        f"type=volume,source={volume_name},target=/data",
        "--mount",
        (
            f"type=bind,source={backup_path},target=/backup,readonly"
            if restore
            else f"type=bind,source={backup_path},target=/backup"
        ),
        ARCHIVE_IMAGE,
    ]
    if restore:
        command.extend(
            [
                "sh",
                "-c",
                "find /data -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + "
                '&& tar -xzf "/backup/$1" -C /data',
                "restore",
                archive_name,
            ]
        )
    else:
        command.extend(["tar", "-czf", f"/backup/{archive_name}", "-C", "/data", "."])
    _run(command)


def _running_services(project_name: str, env_file: Path) -> list[str]:
    running: list[str] = []
    for service in STATEFUL_VOLUMES:
        output = _run(
            _compose_command(project_name, env_file, "ps", "--quiet", service),
            capture_output=True,
        )
        if output.strip():
            running.append(service)
    return running


def _env_file(path: str) -> Path:
    env_file = Path(path).resolve()
    if not env_file.is_file():
        raise FileNotFoundError(f"Compose environment file not found: {env_file}")
    return env_file


def _validate_project_name(project_name: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", project_name):
        raise ValueError(
            "Project name must use lowercase letters, digits, hyphens, or underscores."
        )


def _backup(args: argparse.Namespace) -> None:
    _validate_project_name(args.project_name)
    env_file = _env_file(args.env_file)
    _run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True)
    running = _running_services(args.project_name, env_file)
    if set(running) != set(STATEFUL_VOLUMES):
        missing = sorted(set(STATEFUL_VOLUMES) - set(running))
        raise RuntimeError(
            f"Start all stateful Compose services before backup: {', '.join(missing)}."
        )

    volumes = {
        service: _volume_name(
            _container_id(args.project_name, env_file, service, all_states=False),
            mount_path,
        )
        for service, mount_path in STATEFUL_VOLUMES.items()
    }

    backup_root = Path(args.output_directory).resolve()
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_directory = backup_root / timestamp
    backup_directory.mkdir()
    stop_attempted = False
    backup_complete = False
    try:
        try:
            _run(["docker", "image", "inspect", ARCHIVE_IMAGE], capture_output=True)
        except RuntimeError:
            _run(["docker", "pull", ARCHIVE_IMAGE])
        stop_attempted = True
        _run(_compose_command(args.project_name, env_file, "stop", *running))
        for service, volume_name in volumes.items():
            _docker_archive(volume_name, backup_directory, f"{service}.tar.gz")
        manifest = {
            "format_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "project_name": args.project_name,
            "services": {
                service: {"volume_name": volumes[service], "archive": f"{service}.tar.gz"}
                for service in STATEFUL_VOLUMES
            },
        }
        (backup_directory / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        backup_complete = True
    finally:
        if not backup_complete:
            shutil.rmtree(backup_directory, ignore_errors=True)
        if stop_attempted:
            try:
                _run(_compose_command(args.project_name, env_file, "start", *running))
            except RuntimeError as error:
                raise RuntimeError(
                    f"Backup operation ended, but Compose services could not be restarted. "
                    f"Inspect the stack; backup directory: {backup_directory}. {error}"
                ) from error
    print(f"Local data backup created: {backup_directory}")


def _restore(args: argparse.Namespace) -> None:
    _validate_project_name(args.project_name)
    env_file = _env_file(args.env_file)
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    services = validate_manifest(manifest, args.project_name)

    for entry in services.values():
        archive_path = manifest_path.parent / entry["archive"]
        if not archive_path.is_file():
            raise FileNotFoundError(f"Backup archive is missing: {archive_path}")

    if not args.yes:
        if not sys.stdin.isatty():
            raise RuntimeError("Pass --yes to confirm restore in non-interactive mode.")
        confirmation = input(
            f"This replaces all local data volumes for '{args.project_name}'. "
            "Type RESTORE to continue: "
        )
        if confirmation != "RESTORE":
            raise RuntimeError("Restore cancelled.")

    running = _running_services(args.project_name, env_file)
    _run(_compose_command(args.project_name, env_file, "create", *STATEFUL_VOLUMES))
    volumes = {
        service: _volume_name(
            _container_id(args.project_name, env_file, service, all_states=True),
            mount_path,
        )
        for service, mount_path in STATEFUL_VOLUMES.items()
    }
    if any(services[name]["volume_name"] != volume for name, volume in volumes.items()):
        raise ValueError("Backup volume names do not match the current Compose project volumes.")

    if running:
        _run(_compose_command(args.project_name, env_file, "stop", *running))
    for service, volume_name in volumes.items():
        _docker_archive(
            volume_name,
            manifest_path.parent,
            services[service]["archive"],
            restore=True,
        )
    if running:
        _run(_compose_command(args.project_name, env_file, "start", *running))
    print(f"Local data restored from: {manifest_path.parent}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or restore on-demand archives of local Compose data volumes."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    backup = subparsers.add_parser("backup", help="Create a clean, offline volume backup.")
    backup.add_argument("--env-file", default=".env", help="Compose env file (default: .env).")
    backup.add_argument("--project-name", default="proofpoint-rag")
    backup.add_argument("--output-directory", default=".backups")
    backup.set_defaults(handler=_backup)

    restore = subparsers.add_parser("restore", help="Replace local volumes from a backup.")
    restore.add_argument("--env-file", default=".env", help="Compose env file (default: .env).")
    restore.add_argument("--project-name", default="proofpoint-rag")
    restore.add_argument("--manifest", required=True, help="Path to the backup manifest.json.")
    restore.add_argument(
        "--yes", action="store_true", help="Confirm destructive volume replacement."
    )
    restore.set_defaults(handler=_restore)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        args.handler(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
