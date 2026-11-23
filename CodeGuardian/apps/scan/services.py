import hashlib
import logging
import posixpath
import shutil
import stat
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from analysis import engine, rules

from .models import Finding, Scan, ScanFile

logger = logging.getLogger("codeguardian")


def _config():
    return settings.CODEGUARDIAN


def _safe_basename(name: str) -> str:
    if not name or "\x00" in name or "\\" in name or "/" in name:
        raise SuspiciousOperation("Invalid filename.")
    clean = Path(name).name
    if clean in {"", ".", ".."} or clean != name:
        raise SuspiciousOperation("Invalid filename.")
    return clean[:200]


def _allowed_extension(name: str) -> bool:
    return Path(name).suffix.lower() in _config()["ALLOWED_EXTENSIONS"]


def _read_hash_and_lines(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    lines = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = len(text.splitlines())
    return digest.hexdigest(), lines


def validate_upload(uploaded: UploadedFile) -> str:
    name = _safe_basename(uploaded.name)
    suffix = Path(name).suffix.lower()
    if suffix == ".zip":
        limit = _config()["MAX_ZIP_SIZE_MB"] * 1024 * 1024
    else:
        if not _allowed_extension(name):
            raise ValidationError("Only .py, .js, .jsx, .ts, .tsx and .java files are accepted.")
        limit = _config()["MAX_FILE_SIZE_MB"] * 1024 * 1024
    if uploaded.size > limit:
        raise ValidationError("The uploaded file exceeds the configured size limit.")
    if suffix == ".zip":
        uploaded.seek(0)
        if not zipfile.is_zipfile(uploaded):
            raise ValidationError("The uploaded ZIP file is not a valid archive.")
        uploaded.seek(0)
        return Scan.SourceType.ZIP
    return Scan.SourceType.FILE


def _scan_directory(scan: Scan) -> Path:
    directory = Path(settings.MEDIA_ROOT) / "uploads" / str(scan.id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _create_scan_file(scan: Scan, path: Path, relative: str) -> ScanFile:
    content_hash, lines = _read_hash_and_lines(path)
    return ScanFile.objects.create(
        scan=scan,
        file=f"uploads/{scan.id}/{relative}",
        relative_path=relative,
        language=rules.language_for(path.name),
        size_bytes=path.stat().st_size,
        line_count=lines,
        content_hash=content_hash,
    )


def _store_single(scan: Scan, uploaded: UploadedFile) -> list[Path]:
    safe_name = _safe_basename(uploaded.name)
    target = _scan_directory(scan) / safe_name
    uploaded.seek(0)
    with target.open("wb") as destination:
        for chunk in uploaded.chunks():
            destination.write(chunk)
    _create_scan_file(scan, target, safe_name)
    return [target]


def _safe_zip_member(member: zipfile.ZipInfo, target: Path) -> Path:
    raw_name = member.filename.replace("\\", "/")
    if raw_name.startswith(("/")) or ":" in raw_name or "\x00" in raw_name:
        raise SuspiciousOperation("Unsafe path in ZIP archive.")
    normalized = posixpath.normpath(raw_name)
    if normalized == ".." or normalized.startswith("../"):
        raise SuspiciousOperation("Path traversal attempt in ZIP archive.")
    mode = member.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise SuspiciousOperation("Symbolic links are not allowed in ZIP archives.")
    destination = (target / normalized).resolve()
    if not destination.is_relative_to(target.resolve()):
        raise SuspiciousOperation("ZIP entry escaped the extraction directory.")
    return destination


def _store_zip(scan: Scan, uploaded: UploadedFile) -> list[Path]:
    target = _scan_directory(scan)
    config = _config()
    uploaded.seek(0)
    paths = []
    total_size = 0
    count = 0
    with zipfile.ZipFile(uploaded) as archive:
        for member in archive.infolist():
            destination = _safe_zip_member(member, target)
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if member.flag_bits & 0x1:
                raise SuspiciousOperation("Encrypted ZIP entries are not supported.")
            if not _allowed_extension(member.filename):
                continue
            if member.file_size > config["MAX_FILE_SIZE_MB"] * 1024 * 1024:
                raise ValidationError("A file inside the ZIP exceeds the size limit.")
            total_size += member.file_size
            if total_size > config["MAX_UNCOMPRESSED_ZIP_MB"] * 1024 * 1024:
                raise ValidationError("The uncompressed ZIP content exceeds the size limit.")
            count += 1
            if count > config["MAX_FILES_PER_ZIP"]:
                raise ValidationError("The ZIP contains too many source files.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)
            relative = destination.relative_to(target).as_posix()
            _create_scan_file(scan, destination, relative)
            paths.append(destination)
    return paths


def process_upload(scan: Scan, uploaded: UploadedFile) -> Scan:
    source_type = validate_upload(uploaded)
    with transaction.atomic():
        if scan._state.adding:
            scan.save()
        if source_type == Scan.SourceType.ZIP:
            paths = _store_zip(scan, uploaded)
        else:
            paths = _store_single(scan, uploaded)
        if not paths:
            raise ValidationError("No supported source files were found in the upload.")
        scan.source_type = source_type
        scan.files_scanned = len(paths)
        scan.lines_scanned = sum(scan.files.values_list("line_count", flat=True))
        scan.save(update_fields=["source_type", "files_scanned", "lines_scanned"])
    return scan


def run_scan(scan: Scan) -> Scan:
    config = _config()
    try:
        scan.status = Scan.Status.SCANNING
        scan.save(update_fields=["status"])
        paths = [Path(scan_file.file.path) for scan_file in scan.files.all()]
        root = Path(settings.MEDIA_ROOT) / "uploads" / str(scan.id)
        raw_findings = engine.analyze_paths(paths, root, config)
        file_map = {item.relative_path: item for item in scan.files.all()}
        with transaction.atomic():
            Finding.objects.filter(scan=scan).delete()
            for item in raw_findings:
                Finding.objects.create(
                    scan=scan,
                    source_file=file_map.get(item.get("file_path")),
                    rule_id=item["rule_id"][:80],
                    title=item["title"][:250],
                    severity=item["severity"],
                    category=item["category"][:100],
                    owasp=item.get("owasp", "")[:120],
                    file_path=item.get("file_path", "unknown")[:500],
                    line=int(item.get("line") or 1),
                    column=int(item.get("column") or 1),
                    code_snippet=item.get("code_snippet", "")[:4000],
                    description=item.get("description", ""),
                    impact=item.get("impact", ""),
                    remediation=item.get("remediation", ""),
                    corrected_code=item.get("corrected_code", ""),
                    confidence=item.get("confidence", "high")[:20],
                    detector=item.get("detector", "CUSTOM")[:20],
                    explanation_source=item.get("explanation_source", "RULE_BASED")[:20],
                )
        scan.total_vulnerabilities = len(raw_findings)
        scan.security_score = engine.security_score(raw_findings)
        scan.tool_versions = {
            "custom_rules": "CG-1.0",
            "bandit": "enabled" if config["BANDIT_ENABLED"] else "disabled",
            "semgrep": "enabled" if config["SEMGREP_ENABLED"] else "disabled",
        }
        scan.status = Scan.Status.COMPLETED
        scan.completed_at = timezone.now()
        scan.error_message = ""
        scan.save(
            update_fields=[
                "total_vulnerabilities",
                "security_score",
                "tool_versions",
                "status",
                "completed_at",
                "error_message",
            ]
        )
    except Exception as exc:
        logger.exception("Scan %s failed", scan.id)
        scan.status = Scan.Status.FAILED
        scan.error_message = str(exc)[:1000]
        scan.save(update_fields=["status", "error_message"])
    return scan
