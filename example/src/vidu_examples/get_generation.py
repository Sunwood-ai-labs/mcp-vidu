#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional, Tuple, List

import requests
from dotenv import load_dotenv, find_dotenv


API_BASE_DEFAULT = "https://api.vidu.com/ent/v2"


def load_env() -> None:
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path)
    else:
        # fallback to current file directory
        load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def get_api_key() -> str:
    api_key = os.getenv("VIDU_API_KEY")
    if not api_key:
        print("Error: VIDU_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)
    return api_key


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Get Vidu generation status and optionally download video")
    p.add_argument("--task_id", required=True, help="Task ID from img2video response")
    p.add_argument("--wait", action="store_true", help="Poll until success/failed")
    p.add_argument("--interval", type=float, default=3.0, help="Polling interval seconds")
    p.add_argument("--timeout", type=float, default=300.0, help="Polling timeout seconds")
    p.add_argument("--download", metavar="PATH", help="If provided, download the video to this file when available")
    p.add_argument("--verbose", action="store_true", help="Print details of HTTP attempts")
    p.add_argument("--url", help="Override full endpoint URL template. Use {task_id} placeholder.")
    p.add_argument("--method", choices=["GET", "POST"], default="GET", help="HTTP method when using --url")
    return p.parse_args()


def try_endpoints(api_key: str, task_id: str, verbose: bool = False, url_override: Optional[str] = None, method: str = "GET") -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    headers = {"Authorization": f"Token {api_key}"}

    api_base = os.getenv("VIDU_API_BASE", API_BASE_DEFAULT).rstrip("/")

    attempts: List[Tuple[str, str, Dict[str, Any]]] = []

    if url_override:
        filled = url_override.replace("{task_id}", task_id)
        attempts.append((method.upper(), filled, {}))
    else:
        # Official endpoint per docs: GET /tasks/{id}/creations
        attempts.extend([
            ("GET", f"{api_base}/tasks/{task_id}/creations", {}),
            # Additional common patterns for compatibility/fallbacks
            ("GET", f"{api_base}/get_generation?task_id={task_id}", {}),
            ("POST", f"{api_base}/get_generation", {"task_id": task_id}),
            ("GET", f"{api_base}/generation?task_id={task_id}", {}),
            ("GET", f"{api_base}/generation/{task_id}", {}),
            ("GET", f"{api_base}/task?task_id={task_id}", {}),
            ("GET", f"{api_base}/task/{task_id}", {}),
            ("GET", f"{api_base}/tasks/{task_id}", {}),
            ("GET", f"{api_base}/tasks?task_id={task_id}", {}),
            ("POST", f"{api_base}/task/get", {"task_id": task_id}),
            ("POST", f"{api_base}/generation/get", {"task_id": task_id}),
        ])

    last_status = None
    last_text = None
    last_url = None

    for m, url, payload in attempts:
        try:
            if m == "GET":
                r = requests.get(url, headers=headers, timeout=30)
            else:
                r = requests.post(url, headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=30)
        except requests.RequestException as e:
            if verbose:
                print(f"Request error for {m} {url}: {e}", file=sys.stderr)
            continue

        if verbose:
            print(f"Tried {m} {url} -> {r.status_code}")

        if r.ok:
            try:
                return r.json(), url
            except Exception:
                if verbose:
                    print("Response was not valid JSON:", r.text[:1000])
                continue
        else:
            last_status = r.status_code
            last_text = r.text[:1000]
            last_url = url

    if verbose and last_url is not None:
        print(f"Last failure {last_status} from {last_url}:\n{last_text}", file=sys.stderr)
    return None, None


def extract_video_url(payload: Dict[str, Any]) -> Optional[str]:
    # Heuristics: check common fields
    # 1) direct fields
    for key in ("video_url", "url"):
        val = payload.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
    # 2) nested under result/data/creations
    for top in ("result", "data", "creations"):
        v = payload.get(top)
        if isinstance(v, dict):
            for key in ("video_url", "url"):
                val = v.get(key)
                if isinstance(val, str) and val.startswith("http"):
                    return val
        # If this is the documented array format under `creations`
        if isinstance(v, list) and v:
            first = v[0]
            if isinstance(first, dict):
                for key in ("url", "video_url"):
                    val = first.get(key)
                    if isinstance(val, str) and val.startswith("http"):
                        return val
    # 3) list of assets
    for top in ("videos", "assets"):
        v = payload.get(top)
        if isinstance(v, list) and v:
            first = v[0]
            if isinstance(first, str) and first.startswith("http"):
                return first
            if isinstance(first, dict):
                for key in ("video_url", "url"):
                    val = first.get(key)
                    if isinstance(val, str) and val.startswith("http"):
                        return val
    return None


def download_file(url: str, dest: str) -> None:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def main() -> None:
    load_env()
    api_key = get_api_key()
    args = parse_args()

    start = time.time()
    last_state: Optional[str] = None

    while True:
        data, used_url = try_endpoints(api_key, args.task_id, verbose=args.verbose, url_override=args.url, method=args.method)
        if data is None:
            print("Failed to query generation status (all tried endpoints).", file=sys.stderr)
            sys.exit(1)

        state = data.get("state") or data.get("status")
        if state != last_state:
            print(f"State: {state} (via {used_url})")
            last_state = state

        if not args.wait or state in {"success", "failed"}:
            print("\nFull response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            if state == "success":
                vurl = extract_video_url(data)
                if vurl:
                    print(f"\nVideo URL: {vurl}")
                    if args.download:
                        print(f"Downloading to: {args.download}")
                        download_file(vurl, args.download)
                        print("Download complete.")
                else:
                    print("Could not auto-detect a video URL in the response. Check fields above.")
            sys.exit(0 if state == "success" else 1 if state == "failed" else 0)

        if time.time() - start > args.timeout:
            print("Timeout waiting for completion.", file=sys.stderr)
            sys.exit(2)

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
