import base64
import gzip
import json
import os
import re
import time
import urllib.request
import zlib

REQ = "request.txt"
OUT = "out"
UA = os.environ.get("FETCH_UA", "okhttp/3.12.0")


def looks_json(t):
    try:
        json.loads(t)
        return True
    except Exception:
        return False


def try_decode(text):
    """返回 (结果文本, 模式名)；失败返回 (None, '')  """
    if looks_json(text):
        return text, "明文"

    cands = []
    if re.fullmatch(r"[A-Za-z0-9+/=\s]{40,}", text.strip()):
        cands.append(text.strip())
    cands += sorted(re.findall(r"[A-Za-z0-9+/=]{200,}", text), key=len, reverse=True)[:3]

    for cand in cands:
        s = re.sub(r"[^A-Za-z0-9+/=]", "", cand)
        s += "=" * (-len(s) % 4)
        try:
            raw = base64.b64decode(s)
        except Exception:
            continue
        for name, fn in (("base64", lambda b: b),
                         ("base64+gzip", gzip.decompress),
                         ("base64+zlib", zlib.decompress)):
            try:
                out = fn(raw).decode("utf-8", "replace")
            except Exception:
                continue
            for mark in ("TVBOX$", "TVBOX_", "FINAL$", "NO_REVERSE$"):
                if mark in out:
                    out = out.split(mark)[-1]
            if looks_json(out):
                return out, name
    return None, ""


def main():
    if not os.path.exists(REQ):
        print("no request.txt, skip")
        return
    lines = [l.strip() for l in open(REQ, encoding="utf-8").read().splitlines()]
    urls = [l for l in lines if l and not l.startswith("#")]
    if not urls:
        print("request.txt empty, skip")
        return

    url = urls[0]
    print("fetch", url, "UA=", UA)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
        ctype = r.headers.get("Content-Type", "")

    text = data.decode("utf-8", "ignore")
    decoded, mode = try_decode(text)
    os.makedirs(OUT, exist_ok=True)

    if decoded:
        obj = json.loads(decoded)
        open(os.path.join(OUT, "config.json"), "w", encoding="utf-8").write(
            json.dumps(obj, ensure_ascii=False, indent=2))
        meta = {
            "url": url,
            "bytes": len(data),
            "content_type": ctype,
            "mode": mode,
            "sites": len(obj.get("sites", [])) if isinstance(obj, dict) else None,
            "lives": len(obj.get("lives", [])) if isinstance(obj, dict) else None,
            "spider": obj.get("spider") if isinstance(obj, dict) else None,
            "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ua": UA,
        }
        print("decoded as", mode)
    else:
        open(os.path.join(OUT, "raw.txt"), "w", encoding="utf-8").write(text)
        meta = {
            "url": url,
            "bytes": len(data),
            "content_type": ctype,
            "mode": "raw",
            "note": "not json, saved as raw.txt",
            "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ua": UA,
        }
        print("saved raw")

    open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8").write(
        json.dumps(meta, ensure_ascii=False, indent=2))
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
