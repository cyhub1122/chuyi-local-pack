import base64
import hashlib
import json
import os
import re
import sys
import urllib.request
import zipfile

UA = "okhttp/3.12.0"
CONFIG_URL = "https://yc.wya6.cn/wykj.php"
OUT = "packs/wyjk-local-pack.zip"


def get(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json, */*"}
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def main():
    text = get(CONFIG_URL).decode("utf-8", "ignore")
    cfg = None
    try:
        cfg = json.loads(text)
    except Exception:
        pass

    if cfg is None:
        for cand in sorted(re.findall(r"[A-Za-z0-9+/=]{200,}", text), key=len, reverse=True):
            try:
                raw = base64.b64decode(cand + "=" * (-len(cand) % 4))
                cfg = json.loads(raw.decode("utf-8"))
                break
            except Exception:
                continue

    if not isinstance(cfg, dict):
        sys.exit("no config extracted")

    spider = str(cfg.get("spider", ""))
    jar_url = spider.split(";")[0]
    if not jar_url.startswith("http"):
        sys.exit("spider url missing")

    jar = get(jar_url)
    if len(jar) < 100000:
        sys.exit("jar too small: %d" % len(jar))

    md5 = hashlib.md5(jar).hexdigest()
    cfg["spider"] = "./jar/spider.jar;md5;" + md5

    os.makedirs("packs", exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("api.json", json.dumps(cfg, ensure_ascii=False, indent=2).encode("utf-8"))
        z.writestr("jar/spider.jar", jar, compress_type=zipfile.ZIP_STORED)

    print("pack ok md5=%s jar=%d sites=%d lives=%d" % (
        md5, len(jar), len(cfg.get("sites", [])), len(cfg.get("lives", [])))
    )


if __name__ == "__main__":
    main()
