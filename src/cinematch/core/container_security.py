"""Runtime container security introspection."""

from __future__ import annotations

import logging
import os
import platform
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_FULL_CAP_EFF = 0x0000003FFFFFFFFF


def _get_current_user() -> str:
    """Return the current username, falling back to UID string."""
    try:
        import pwd

        return pwd.getpwuid(os.getuid()).pw_name
    except (ImportError, KeyError):
        return str(os.getuid())


def _check_root_writable() -> bool:
    """Return True if the root filesystem is writable."""
    probe = Path("/.__container_probe")
    try:
        probe.write_text("probe")
        probe.unlink()
        return True
    except OSError:
        return False


def _check_tmp_writable() -> bool:
    """Return True if /tmp is writable (tmpfs mount)."""
    probe = Path("/tmp/.__container_probe")  # nosec B108 - intentional /tmp check
    try:
        probe.write_text("probe")
        probe.unlink()
        return True
    except OSError:
        return False


def _read_proc_status_field(field: str) -> str | None:
    """Read a field from /proc/1/status. Returns None if unavailable."""
    try:
        for line in Path("/proc/1/status").read_text().splitlines():
            if line.startswith(f"{field}:"):
                return line.split(":", 1)[1].strip()
    except (FileNotFoundError, PermissionError):
        return None
    return None


def _check_no_new_privileges() -> tuple[bool, str]:
    """Check if no_new_privileges is set on PID 1."""
    value = _read_proc_status_field("NoNewPrivs")
    if value is None:
        return False, "Not running in container — check skipped"
    if value == "1":
        return True, "no-new-privileges is enabled"
    return False, "no-new-privileges is NOT enabled"


def _check_capabilities() -> tuple[bool, str]:
    """Check if effective capabilities are restricted."""
    value = _read_proc_status_field("CapEff")
    if value is None:
        return False, "Not running in container — check skipped"
    try:
        cap_int = int(value, 16)
    except ValueError:
        return False, f"Could not parse CapEff: {value}"
    if cap_int < _FULL_CAP_EFF:
        return True, f"Capabilities restricted (CapEff=0x{cap_int:016x})"
    return False, f"Full capabilities detected (CapEff=0x{cap_int:016x})"


def get_container_security_status() -> dict:
    """Inspect the runtime environment and return container security status."""
    uid = os.getuid()
    gid = os.getgid()
    username = _get_current_user()
    is_root = uid == 0

    root_writable = _check_root_writable()
    tmp_writable = _check_tmp_writable()

    gcc_absent = shutil.which("gcc") is None
    python_version = platform.python_version()
    # Detect base image heuristically
    is_linux = sys.platform == "linux"
    base_image = f"python:{python_version}-slim" if is_linux else f"python:{python_version} (dev)"

    no_new_privs_passed, no_new_privs_detail = _check_no_new_privileges()
    caps_passed, caps_detail = _check_capabilities()

    checks = [
        {
            "name": "Non-root user",
            "passed": not is_root,
            "detail": f"Running as {username} (UID {uid})"
            if not is_root
            else "Running as root — container should use USER directive",
        },
        {
            "name": "Read-only root filesystem",
            "passed": not root_writable,
            "detail": "Root filesystem is read-only"
            if not root_writable
            else "Root filesystem is writable — set read_only: true",
        },
        {
            "name": "Writable /tmp",
            "passed": tmp_writable,
            "detail": "/tmp is writable (tmpfs mounted)"  # nosec B108
            if tmp_writable
            else "/tmp is not writable — mount tmpfs at /tmp",  # nosec B108
        },
        {
            "name": "No new privileges",
            "passed": no_new_privs_passed,
            "detail": no_new_privs_detail,
        },
        {
            "name": "Minimal capabilities",
            "passed": caps_passed,
            "detail": caps_detail,
        },
        {
            "name": "Multi-stage build",
            "passed": gcc_absent,
            "detail": "Build tools absent from runtime image"
            if gcc_absent
            else "gcc found in PATH — use multi-stage build to exclude build tools",
        },
    ]

    all_passed = all(c["passed"] for c in checks)

    return {
        "runtime": {
            "running_as_root": is_root,
            "current_uid": uid,
            "current_gid": gid,
            "current_user": username,
        },
        "filesystem": {
            "root_writable": root_writable,
            "tmp_writable": tmp_writable,
        },
        "image": {
            "base_image": base_image,
            "python_version": python_version,
            "multi_stage_build": gcc_absent,
        },
        "checks": checks,
        "all_passed": all_passed,
    }
