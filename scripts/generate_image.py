#!/usr/bin/env python3

import argparse
import json
import math
import os
import re
import sys
from io import BytesIO

import requests
from PIL import Image

from config import ARK_IMAGES_GENERATIONS_URL, SEEDREAM_MODEL
from upload_file import upload_file

# API 侧总像素允许区间 [3686400, 10404496]（约 1920² ~ 3225²）
MIN_PIXELS = 3686400
MAX_PIXELS = 10404496

def _lanczos_resample():
    try:
        return Image.Resampling.LANCZOS
    except AttributeError:
        return Image.LANCZOS


def validate_output_path(path: str) -> None:
    """必须为绝对路径，且以 .png 结尾（如 /path/to/hello.png）。"""
    if not path:
        sys.exit("ERROR: --output 不能为空")
    if not os.path.isabs(path):
        sys.exit(
            f"ERROR: --output 必须是绝对路径，当前为: {path!r}（示例: /path/to/hello.png）"
        )
    if not path.lower().endswith(".png"):
        sys.exit(
            f"ERROR: --output 必须以 .png 结尾，当前为: {path!r}（示例: /path/to/hello.png）"
        )


def expand_output_paths(output_path: str, n: int) -> list[str]:
    """单张：原路径；多张：在同一目录下使用 stem_0.png、stem_1.png …"""
    if n == 1:
        return [output_path]
    root, ext = os.path.splitext(output_path)
    return [f"{root}_{i}{ext}" for i in range(n)]


def parse_size_wh(size_str):
    """解析「宽x高」或「宽*高」，返回 (w, h)；无法解析则返回 None。"""
    s = size_str.strip().lower().replace("*", "x")
    m = re.match(r"^(\d+)\s*x\s*(\d+)$", s)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def normalize_dimensions_for_api(w, h):
    """
    将 (w,h) 等比缩放到总像素落在 [MIN_PIXELS, MAX_PIXELS]。
    返回 (api_w, api_h, need_resize_to_target)，其中 need_resize_to_target 表示
    与原始 (w,h) 不一致，生成后需缩放回用户设定尺寸。
    """
    a = w * h
    if MIN_PIXELS <= a <= MAX_PIXELS:
        return w, h, False
    if a < MIN_PIXELS:
        k = math.sqrt(MIN_PIXELS / a)
    else:
        k = math.sqrt(MAX_PIXELS / a)
    nw = max(1, math.ceil(w * k))
    nh = max(1, math.ceil(h * k))
    while nw * nh < MIN_PIXELS:
        if nw <= nh:
            nw += 1
        else:
            nh += 1
    while nw * nh > MAX_PIXELS:
        if nw >= nh:
            nw = max(1, nw - 1)
        else:
            nh = max(1, nh - 1)
    need_resize = nw != w or nh != h
    return nw, nh, need_resize


def get_image_url(image_input):
    if image_input.startswith("http"):
        return image_input
    url = upload_file(image_input)
    if not url:
        sys.exit(1)
    return url

def download_resize_save(api_url, target_wh, local_path: str):
    """
    下载生成图；若 target_wh 为 (w,h) 则 LANCZOS 缩放到该尺寸；
    保存到 local_path（PNG），再上传，返回 CDN URL。
    """
    r = requests.get(api_url, timeout=120)
    r.raise_for_status()
    img = Image.open(BytesIO(r.content))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if img.mode in ("P", "LA") else "RGB")
    if target_wh is not None:
        tw, th = target_wh
        img = img.resize((tw, th), _lanczos_resample())
    parent = os.path.dirname(local_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    img.save(local_path, "PNG")
    return local_path

def resolve_size_for_request(size_str):
    """
    返回 (payload_size_str, resize_target_or_none)。
    若能解析为宽x高，则 resize_target 为用户请求的 (w,h)，保存前始终按该尺寸 LANCZOS 缩放后再上传；
    无法解析时 resize_target 为 None，按 API 返回尺寸原样保存。
    """
    parsed = parse_size_wh(size_str)
    if parsed is None:
        return size_str, None
    w, h = parsed
    api_w, api_h, _ = normalize_dimensions_for_api(w, h)
    return f"{api_w}x{api_h}", (w, h)


def generate_image(
    prompt,
    size,
    output_path,
    image_input=None,
    sequential=False,
):
    validate_output_path(output_path)

    url = ARK_IMAGES_GENERATIONS_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('ARK_DOUBAO_SEEDREAM_API_KEY')}",
    }

    payload_size, resize_target = resolve_size_for_request(size)

    payload = {
        "model": SEEDREAM_MODEL,
        "prompt": prompt,
        "size": payload_size,
        "output_format": "png",
        "response_format": "url",
        "watermark": False,
    }

    if image_input:
        if isinstance(image_input, (list, tuple)):
            imgs = [get_image_url(x) for x in image_input]
            payload["image"] = imgs[0] if len(imgs) == 1 else imgs
        else:
            print("ERROR: Invalid image input type")
            sys.exit(1)

    payload["sequential_image_generation"] = "auto" if sequential else "disabled"

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        if "data" not in result or len(result["data"]) == 0:
            print(
                f"ERROR: No image data in response. Full response: {json.dumps(result)}"
            )
            return

        items = [x for x in result["data"] if "url" in x]
        if not items:
            print("ERROR: No image URLs in response.")
            return

        paths = expand_output_paths(output_path, len(items))

        for idx, item in enumerate(items):
            raw_url = item["url"]
            save_path = paths[idx]
            media_url = download_resize_save(raw_url, resize_target, save_path)
            if not media_url:
                print(
                    "ERROR: 保存或上传失败，原始生成 URL:",
                    raw_url,
                    file=sys.stderr,
                )
                sys.exit(1)
            print(f"MEDIA_URL: {raw_url}")
            print(f"SAVED: {save_path}")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: API request failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response body: {e.response.text}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Volcengine Seedream API."
    )
    parser.add_argument("--prompt", required=True, help="Text prompt for image generation")
    parser.add_argument(
        "--output",
        required=True,
        help="保存路径：绝对路径且以 .png 结尾，例如 /path/to/hello.png；多图时为 hello_0.png、hello_1.png",
    )
    parser.add_argument(
        "--size",
        default="1024x1024",
        help="宽x高 或 宽*高（如 1024x1024）；总像素会被约束在 API 允许区间，必要时生成后再缩放回目标尺寸",
    )
    parser.add_argument(
        "--image",
        nargs="+",
        metavar="PATH_OR_URL",
        help="参考图，可多个：URL 或本地路径。示例：--image /a.png /b.png 或 --image https://...",
    )
    parser.add_argument(
        "--sequential", action="store_true", help="Enable sequential image generation (group)"
    )

    args = parser.parse_args()

    generate_image(
        prompt=args.prompt,
        size=args.size,
        output_path=args.output,
        image_input=list(args.image) if args.image else None,
        sequential=args.sequential,
    )

if __name__ == "__main__":
    main()
