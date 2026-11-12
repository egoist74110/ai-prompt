#!/usr/bin/env python3
"""Minimal OpenAI-compatible client. Config: LOCAL_LLM_BASE_URL / LOCAL_LLM_API_KEY (env or ../.env)."""
import argparse, base64, json, mimetypes, os, sys, time, urllib.error, urllib.request, uuid
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent


def load_env():
    f = SKILL / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def cfg():
    load_env()
    base = os.environ.get("LOCAL_LLM_BASE_URL", "").rstrip("/")
    key = os.environ.get("LOCAL_LLM_API_KEY", "")
    miss = []
    if not base or "your-host.example" in base:
        miss.append("LOCAL_LLM_BASE_URL")
    if not key or key == "sk-xxxx":
        miss.append("LOCAL_LLM_API_KEY")
    if miss:
        print(f"Missing config: {', '.join(miss)}. Fill {SKILL / '.env'} (copy from .env.example).", file=sys.stderr)
        sys.exit(2)
    return base, key


def call(method, path, body=None, raw_body=None, ctype=None, binary=False, timeout=600):
    base, key = cfg()
    headers = {"Authorization": f"Bearer {key}", "User-Agent": os.environ.get("LOCAL_LLM_UA", "curl/8.4.0"), "Accept": "application/json"}
    data = raw_body
    if body is not None:
        data = json.dumps(body).encode()
        ctype = "application/json"
    if ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
            return payload if binary else (json.loads(payload) if payload else {})
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:2000]
        print(f"HTTP {e.code} on {method} {path}: {msg}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def out_path(a, ext, i=0):
    if a.output:
        return Path(a.output) if i == 0 else Path(a.output).with_name(f"{Path(a.output).stem}_{i}{Path(a.output).suffix}")
    d = Path(os.environ.get("LOCAL_LLM_OUT_DIR") or Path.home() / "Downloads").expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{a.cmd}_{int(time.time())}_{i}.{ext}"


def default(a, env):
    return a.model or os.environ.get(env) or None


def cmd_models(a):
    for m in call("GET", "/models").get("data", []):
        print(m.get("id"))


def cmd_chat(a):
    msgs = ([{"role": "system", "content": a.system}] if a.system else []) + [{"role": "user", "content": a.prompt}]
    model = default(a, "LOCAL_LLM_CHAT_MODEL") or sys.exit("No model: pass -m or set LOCAL_LLM_CHAT_MODEL (see `models`).")
    r = call("POST", "/chat/completions", {"model": model, "messages": msgs})
    print(r["choices"][0]["message"]["content"])


def cmd_image(a):
    body = {"prompt": a.prompt, "n": a.n, "size": a.size, "response_format": "b64_json"}
    m = default(a, "LOCAL_LLM_IMAGE_MODEL")
    if m:
        body["model"] = m
    r = call("POST", "/images/generations", body)
    for i, it in enumerate(r.get("data", [])):
        p = out_path(a, "png", i)
        if it.get("b64_json"):
            p.write_bytes(base64.b64decode(it["b64_json"]))
            print(p)
        elif it.get("url"):
            print(it["url"])


# Known voice languages (only ones the user confirmed). Names containing 中文/_ZH are Chinese.
VOICE_LANG = {"伊莉雅": "ja", "伊利雅": "ja"}


def text_lang(t):
    import re
    if re.search(r"[\u3040-\u30ff]", t):
        return "ja"
    if re.search(r"[\u4e00-\u9fff]", t):
        return "zh"
    return "en" if re.search(r"[A-Za-z]", t) else "?"


def voice_lang(v):
    if v in VOICE_LANG:
        return VOICE_LANG[v]
    if "中文" in v or v.endswith("_ZH"):
        return "zh"
    return None


def check_lang(a):
    vl, tl = voice_lang(a.voice), text_lang(a.prompt)
    if a.force_lang:
        return
    if vl is None:
        sys.exit(f"Language of voice '{a.voice}' is unknown. Ask the user which language it speaks, then pass --force-lang (and make the text match), or add it to VOICE_LANG.")
    if tl != vl:
        sys.exit(f"Language mismatch: voice '{a.voice}' speaks {vl}, text looks {tl}. Translate the text to {vl} (confirm with the user) or pass --force-lang.")


def cmd_speech(a):
    check_lang(a)
    body = {"input": a.prompt, "voice": a.voice, "response_format": a.format}
    m = default(a, "LOCAL_LLM_TTS_MODEL")
    if m:
        body["model"] = m
    p = out_path(a, a.format)
    p.write_bytes(call("POST", "/audio/speech", body, binary=True))
    print(p)


def multipart(fields, files):
    b = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, (name, content) in files.items():
        t = mimetypes.guess_type(name)[0] or "application/octet-stream"
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\nContent-Type: {t}\r\n\r\n'.encode() + content + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={b}"


def cmd_transcribe(a):
    f = Path(a.prompt)
    fields = {}
    m = default(a, "LOCAL_LLM_STT_MODEL")
    if m:
        fields["model"] = m
    body, ct = multipart(fields, {"file": (f.name, f.read_bytes())})
    print(call("POST", "/audio/transcriptions", raw_body=body, ctype=ct).get("text", ""))


def cmd_video(a):
    fields = {"prompt": a.prompt, "seconds": str(a.seconds), "size": a.size}
    m = default(a, "LOCAL_LLM_VIDEO_MODEL")
    if m:
        fields["model"] = m
    body, ct = multipart(fields, {})
    job = call("POST", "/videos", raw_body=body, ctype=ct)
    vid = job.get("id")
    print(f"job {vid} {job.get('status')}", file=sys.stderr)
    deadline = time.time() + a.timeout
    while job.get("status") not in ("completed", "succeeded", "failed", "error", "cancelled"):
        if time.time() > deadline:
            sys.exit(f"Timeout; job {vid} still {job.get('status')}")
        time.sleep(5)
        job = call("GET", f"/videos/{vid}")
        print(f"  {job.get('status')} {job.get('progress', '')}", file=sys.stderr)
    if job.get("status") not in ("completed", "succeeded"):
        sys.exit(f"Video failed: {json.dumps(job)[:500]}")
    p = out_path(a, "mp4")
    p.write_bytes(call("GET", f"/videos/{vid}/content", binary=True))
    print(p)


def cmd_raw(a):
    print(json.dumps(call(a.prompt.upper(), a.path, json.loads(a.json) if a.json else None), ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, prompt=True):
        s = sp.add_parser(name)
        if prompt:
            s.add_argument("prompt")
        s.add_argument("-m", "--model")
        s.add_argument("-o", "--output")
        s.set_defaults(fn=fn)
        return s

    add("models", cmd_models, False)
    s = add("chat", cmd_chat); s.add_argument("-s", "--system")
    s = add("image", cmd_image); s.add_argument("--size", default="1024x1024"); s.add_argument("-n", type=int, default=1)
    s = add("speech", cmd_speech); s.add_argument("--voice", default="alloy"); s.add_argument("--format", default="mp3"); s.add_argument("--force-lang", action="store_true")
    add("transcribe", cmd_transcribe)
    s = add("video", cmd_video); s.add_argument("--seconds", type=int, default=5); s.add_argument("--size", default="1280x720"); s.add_argument("--timeout", type=int, default=900)
    s = add("raw", cmd_raw); s.add_argument("path"); s.add_argument("--json")
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
