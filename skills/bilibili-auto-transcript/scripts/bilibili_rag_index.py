#!/usr/bin/env python3
"""
bilibili_rag_index.py — 索引 B站转录文件到向量数据库

扫描 ~/workspace/Bilibili transcript/ 下所有 TXT 文件，
切片、向量化、存入本地索引（numpy + JSON，0额外依赖）。
"""

import os, json, re, sys, hashlib
from pathlib import Path

import numpy as np
import requests

# ===== 配置 =====
TRANSCRIPT_DIR = os.path.expanduser("~/workspace/knowledge/bilibili")
INDEX_DIR = os.path.expanduser("~/.openclaw/workspace/skills/bilibili-auto-transcript/rag_data")
OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "qwen3-embedding:0.6b"
CHUNK_SIZE = 512      # 每段约多少字符
CHUNK_OVERLAP = 64    # 段落重叠

os.makedirs(INDEX_DIR, exist_ok=True)

# ===== 解析 TXT 文件 =====
def parse_transcript(path):
    """解析一个转录文件，返回 {title, author, date, bvid, source, content}"""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    meta = {
        "title": "",
        "author": "",
        "date": "",
        "bvid": "",
        "source": "",
        "filepath": str(path),
        "filename": os.path.basename(path),
    }

    # 从文件头提取元数据
    for line in text.split("\n")[:20]:
        m = re.match(r"📹 视频标题[：:]\s*(.+)", line)
        if m: meta["title"] = m.group(1).strip()
        m = re.match(r"👤 作者[：:]\s*(.+)", line)
        if m: meta["author"] = m.group(1).strip()
        m = re.match(r"📅 发布时间[：:]\s*(.+)", line)
        if m: meta["date"] = m.group(1).strip()
        m = re.match(r"🔗 B站链接[：:].*BV(\w+)", line)
        if m: meta["bvid"] = "BV" + m.group(1).strip()
        m = re.match(r"📝 转录来源[：:]\s*(.+)", line)
        if m: meta["source"] = m.group(1).strip()
        # 也直接从文件名提取 BV 号
        m2 = re.search(r"BV[a-zA-Z0-9]+", os.path.basename(path))
        if not meta["bvid"] and m2:
            meta["bvid"] = m2.group(0)

    # 提取正文（第二部分：完整原文之后的内容）
    body_start = text.find("第二部分：完整原文")
    if body_start == -1:
        body_start = text.find("完整原文")
    if body_start == -1:
        # 找不到就全文
        body = text
    else:
        body = text[body_start:]
        # 跳过标题行
        body = re.sub(r"^.*第.部分.*\n?", "", body)

    # 去掉文档结束标记
    body = re.sub(r"文档结束.*", "", body)

    meta["content"] = body.strip()
    return meta


def chunk_text(text, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """按行拼接切块，每段 max_chars 字符左右，带重叠"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    chunks = []
    current = ""

    for line in lines:
        # 跳过分隔线
        if line.startswith("==="):
            continue
        if len(line) > max_chars:
            # 单行太长，直接截断
            line = line[:max_chars]
        if len(current) + len(line) + 1 < max_chars:
            current += "\n" + line if current else line
        else:
            if current:
                chunks.append(current)
            # 重叠：保留上段的末尾
            if overlap > 0 and current:
                overlap_text = current[-overlap:] if len(current) > overlap else current
                current = overlap_text + "\n" + line
            else:
                current = line

    if current:
        chunks.append(current)
    return chunks


def embed(text):
    """调用 Ollama 获取文本向量"""
    resp = requests.post(OLLAMA_URL, json={
        "model": EMBED_MODEL,
        "prompt": text,
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["embedding"]


def build_index(force=False):
    """构建/增量更新索引"""
    index_file = os.path.join(INDEX_DIR, "index.json")
    vectors_file = os.path.join(INDEX_DIR, "vectors.npy")

    # 读取已有索引
    existing = {}
    if not force and os.path.exists(index_file):
        with open(index_file, "r") as f:
            existing = {e["filepath"]: e for e in json.load(f)}

    # 扫描所有 TXT 文件
    txt_files = sorted(Path(TRANSCRIPT_DIR).glob("*.txt"))
    new_docs = []
    updated_count = 0

    for fp in txt_files:
        fpath = str(fp)
        fhash = hashlib.md5(open(fp, "rb").read()).hexdigest()

        # 检查是否有变化
        if not force and fpath in existing:
            if existing[fpath].get("hash") == fhash:
                continue

        meta = parse_transcript(fpath)
        meta["hash"] = fhash
        chunks = chunk_text(meta["content"])

        doc_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{os.path.basename(fpath)}#chunk{i}"
            doc_chunks.append({
                "id": chunk_id,
                "text": chunk,
                "title": meta["title"],
                "author": meta["author"],
                "date": meta["date"],
                "bvid": meta["bvid"],
                "source": meta["source"],
                "filepath": meta["filepath"],
                "filename": meta["filename"],
                "chunk_index": i,
                "hash": fhash,
            })
        new_docs.append(meta["filepath"])
        existing[fpath] = doc_chunks
        updated_count += 1
        print(f"  [{updated_count}] {meta['filename']} → {len(chunks)} 个段落")

    if updated_count == 0:
        print("✅ 没有新的或变化的文件，索引已是最新")
        return

    # 展平所有 chunk
    all_chunks = []
    for chunks_list in existing.values():
        if isinstance(chunks_list, list) and len(chunks_list) > 0 and isinstance(chunks_list[0], dict):
            all_chunks.extend(chunks_list)

    # 批量向量化
    print(f"\n🧠 正在向量化 {len(all_chunks)} 个段落...")
    vectors = []
    for i, chunk in enumerate(all_chunks):
        vec = embed(chunk["text"])
        vectors.append(vec)
        if (i + 1) % 10 == 0 or i == len(all_chunks) - 1:
            print(f"  {i+1}/{len(all_chunks)}")

    # 保存
    meta_for_save = [{k: v for k, v in c.items() if k != "text"} for c in all_chunks]
    np.save(vectors_file, np.array(vectors, dtype=np.float32))
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 索引完成！共 {len(all_chunks)} 个段落向量")
    print(f"   索引文件: {index_file}")
    print(f"   向量文件: {vectors_file}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    build_index(force=force)
