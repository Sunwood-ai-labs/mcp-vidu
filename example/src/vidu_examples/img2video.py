#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv, find_dotenv


VIDU_ENDPOINT = "https://api.vidu.com/ent/v2/img2video"


def positive_int(value: str) -> int:
    try:
        ivalue = int(value)
        if ivalue < 0:
            raise ValueError
        return ivalue
    except Exception as e:
        raise argparse.ArgumentTypeMismatch(f"invalid positive int: {value}") from e


def str_to_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    v = value.strip().lower()
    if v in {"true", "1", "yes", "y"}:
        return True
    if v in {"false", "0", "no", "n"}:
        return False
    return None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Call Vidu Image-to-Video API (Python)"
    )
    p.add_argument("--model", default="viduq1", help="viduq1 | viduq1-classic | vidu2.0 | vidu1.5")
    p.add_argument(
        "--image",
        default="https://prod-ss-images.s3.cn-northwest-1.amazonaws.com.cn/vidu-maas/template/image2video.png",
        help="Image URL or data URL (base64)",
    )
    p.add_argument("--prompt", default="The astronaut waved and the camera moved up.")
    p.add_argument("--duration", type=positive_int)
    p.add_argument("--seed", type=positive_int)
    p.add_argument("--resolution", choices=["360p", "720p", "1080p"])
    p.add_argument("--movement_amplitude", default="auto", choices=["auto", "small", "medium", "large"])
    p.add_argument("--bgm", help="true|false")
    p.add_argument("--payload", help="transparent payload string")
    p.add_argument("--off_peak", help="true|false", default="false")
    p.add_argument("--watermark", help="true|false")
    p.add_argument("--callback_url")
    return p


def drop_none(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def main() -> None:
    # Load .env (prefer CWD to match README; fallback to package dir)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path)
    else:
        load_dotenv(os.path.join(script_dir, ".env"))

    api_key = os.getenv("VIDU_API_KEY")
    if not api_key:
        print("Error: VIDU_API_KEY is not set. Create example/.env or export it in your shell.", file=sys.stderr)
        sys.exit(1)

    parser = build_parser()
    argv = sys.argv[1:]
    # Be forgiving: if the first token is a lone "--", drop it.
    if argv and argv[0] == "--":
        argv = argv[1:]
    args = parser.parse_args(argv)

    body: Dict[str, Any] = {
        "model": args.model,
        "images": [args.image],
        "prompt": args.prompt,
        "duration": args.duration,
        "seed": args.seed,
        "resolution": args.resolution,
        "movement_amplitude": args.movement_amplitude,
        "bgm": str_to_bool(args.bgm),
        "payload": args.payload,
        "off_peak": str_to_bool(args.off_peak),
        "watermark": str_to_bool(args.watermark),
        "callback_url": args.callback_url,
    }
    body = drop_none(body)

    if not isinstance(body.get("images"), list) or len(body["images"]) != 1:
        print("Error: exactly one image must be provided via --image", file=sys.stderr)
        sys.exit(1)

    print("POST", VIDU_ENDPOINT)
    print("Payload:")
    print(json.dumps(body, indent=2, ensure_ascii=False))

    try:
        resp = requests.post(
            VIDU_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Token {api_key}",
            },
            json=body,
            timeout=60,
        )
    except requests.RequestException as e:
        print(f"Request error: {e}", file=sys.stderr)
        sys.exit(1)

    if not resp.ok:
        print(f"\nRequest failed: {resp.status_code} {resp.reason}", file=sys.stderr)
        try:
            print(json.dumps(resp.json(), indent=2, ensure_ascii=False), file=sys.stderr)
        except Exception:
            print(resp.text, file=sys.stderr)
        sys.exit(1)

    try:
        data = resp.json()
        print("\nResponse:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except ValueError:
        print("\nResponse (raw):")
        print(resp.text)


if __name__ == "__main__":
    main()
