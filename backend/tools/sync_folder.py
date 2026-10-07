"""Continuously upload changed local files as source revisions.

Only paths under the selected folder are read. Deleting a local file never
deletes its server copy. The API bearer token is read from the environment.
"""
import argparse
import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.error import HTTPError
from urllib.request import Request, urlopen

EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".png", ".jpg", ".jpeg",
              ".webp", ".mp3", ".wav", ".m4a", ".mp4", ".mov", ".txt", ".log", ".json", ".jsonl"}


def api(base: str, token: str, route: str, body: bytes | None = None, boundary: str = ""):
    headers = {"Authorization": "Bearer " + token}
    if body is not None:
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
    with urlopen(Request(base.rstrip("/") + route, data=body, headers=headers,
                         method="POST" if body is not None else "GET"), timeout=240) as response:
        return json.load(response)


def refresh(base: str, refresh_token: str) -> dict:
    body = json.dumps({"refresh_token": refresh_token}).encode()
    with urlopen(Request(base.rstrip("/") + "/auth/refresh", data=body, method="POST",
                         headers={"Content-Type": "application/json"}), timeout=30) as response:
        return json.load(response)


def save_refresh_token(path: Path, token: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(token)
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def multipart(path: Path, old_id: str, method: str, languages: str) -> tuple[bytes, str]:
    boundary = "atlas" + secrets.token_hex(16)
    body = bytearray()
    for name, value in (("chunk_method", method), ("ocr_languages", languages), ("replace_file_id", old_id)):
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    filename = path.name.replace('"', "_").replace("\r", "_").replace("\n", "_")
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode())
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    return bytes(body), boundary


def sync_once(folder: Path, state_path: Path, base: str, token: str, method: str, languages: str) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    server = {item["id"]: item for item in api(base, token, "/files/list") if not item["read_only"]}
    changed = 0
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in EXTENSIONS or path == state_path:
            continue
        relative = str(path.relative_to(folder))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        previous = state.get(relative, {})
        if digest == previous.get("sha256") and previous.get("file_id") in server:
            continue
        old_id = previous.get("file_id", "") if previous.get("file_id") in server and server[previous["file_id"]]["is_current"] else ""
        body, boundary = multipart(path, old_id, method, languages)
        result = api(base, token, "/files/upload", body, boundary)
        if result.get("duplicate") and result["id"] != previous.get("file_id"):
            raise RuntimeError(f"{relative} matched another source's bytes; add unique content before syncing independently")
        state[relative] = {"sha256": digest, "file_id": result["id"]}
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = state_path.with_suffix(state_path.suffix + ".tmp")
        temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(temporary, state_path)
        server[result["id"]] = {"is_current": True}
        changed += 1
        print(f"Synced {relative}: {result['id']} (version {result.get('version', 'existing')})", flush=True)
    return {"scanned": len(state), "uploaded": changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--state", type=Path)
    parser.add_argument("--refresh-token-file", type=Path, help="Rotated refresh-token storage (mode 0600)")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--chunk-method", choices=["document", "recursive", "fixed", "semantic"], default="document")
    parser.add_argument("--ocr-languages", default="eng")
    args = parser.parse_args()
    token = os.getenv("ATLAS_SYNC_TOKEN", "")
    folder = args.folder.resolve()
    if not folder.is_dir() or args.interval < 10: parser.error("Specify an existing folder and an interval of at least 10 seconds")
    host = urlparse(args.api_base)
    if host.scheme != "https" and not (host.scheme == "http" and host.hostname in {"localhost", "127.0.0.1"}):
        parser.error("Use HTTPS for remote servers")
    state = args.state.resolve() if args.state else folder / ".atlas-sync-state.json"
    refresh_file = args.refresh_token_file.resolve() if args.refresh_token_file else None
    if refresh_file and refresh_file.is_relative_to(folder):
        parser.error("Keep the refresh-token file outside the watched folder")
    if refresh_file and refresh_file.exists() and refresh_file.stat().st_mode & 0o077:
        parser.error("Refresh-token file must be private (chmod 600)")
    refresh_token = (refresh_file.read_text(encoding="utf-8").strip() if refresh_file and refresh_file.exists()
                     else os.getenv("ATLAS_SYNC_REFRESH_TOKEN", ""))
    if not token and not refresh_token:
        parser.error("Set ATLAS_SYNC_TOKEN or ATLAS_SYNC_REFRESH_TOKEN for the target account")
    if refresh_token and not refresh_file:
        parser.error("Provide --refresh-token-file to store rotated refresh tokens")
    def rotate():
        nonlocal token, refresh_token
        if not refresh_token: raise RuntimeError("Access token expired; set a new ATLAS_SYNC_TOKEN or provide a refresh token")
        credentials = refresh(args.api_base, refresh_token)
        token, refresh_token = credentials["access_token"], credentials["refresh_token"]
        save_refresh_token(refresh_file, refresh_token)
    if not token: rotate()
    while True:
        try:
            try:
                result = sync_once(folder, state, args.api_base, token, args.chunk_method, args.ocr_languages)
            except HTTPError as exc:
                if exc.code != 401: raise
                rotate()
                result = sync_once(folder, state, args.api_base, token, args.chunk_method, args.ocr_languages)
            print(result, flush=True)
        except Exception as exc:
            print(f"Sync failed; retrying next interval: {exc}", flush=True)
            if args.once: raise
        if args.once: break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
