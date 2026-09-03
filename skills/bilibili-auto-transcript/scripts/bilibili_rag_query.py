#!/usr/bin/env python3
"""
bilibili_rag_query.py — 搜索 B站转录 RAG 索引

用法：
  python3 bilibili_rag_query.py "搜索内容"
  python3 bilibili_rag_query.py "搜索内容" --top 10
  python3 bilibili_rag_query.py "搜索内容" --author "付鹏" --detail
"""

import os, sys, json
import numpy as np
import requests

# ===== 配置 =====
INDEX_DIR = os.path.expanduser("~/.openclaw/workspace/skills/bilibili-auto-transcript/rag_data")
OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "qwen3-embedding:0.6b"
TOP_K = 5


def load_index():
    """加载索引"""
    index_file = os.path.join(INDEX_DIR, "index.json")
    vectors_file = os.path.join(INDEX_DIR, "vectors.npy")

    if not os.path.exists(index_file):
        print("❌ 索引不存在，请先运行 bilibili_rag_index.py")
        sys.exit(1)

    with open(index_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    vectors = np.load(vectors_file)
    return chunks, vectors


def embed(text):
    """调用 Ollama 获取向量"""
    resp = requests.post(OLLAMA_URL, json={
        "model": EMBED_MODEL,
        "prompt": text,
    }, timeout=30)
    resp.raise_for_status()
    return np.array(resp.json()["embedding"], dtype=np.float32)


def search(query, top_k=TOP_K, author=None, detail=False):
    """搜索最相关的段落"""
    chunks, vectors = load_index()

    # 获取查询向量
    qvec = embed(query)

    # 计算余弦相似度
    dots = np.dot(vectors, qvec)
    norms = np.linalg.norm(vectors, axis=1) * np.linalg.norm(qvec)
    scores = dots / np.clip(norms, 1e-10, None)

    # 排序索引
    indices = np.argsort(scores)[::-1]

    # 过滤作者（如果有）
    results = []
    seen_sources = set()
    for idx in indices:
        chunk = chunks[idx]
        score = float(scores[idx])

        if author and author not in chunk.get("author", ""):
            continue
        if score < 0.3:
            break

        results.append((score, chunk))
        if len(results) >= top_k:
            break

    if not results:
        print("😴 没有找到相关结果")
        return

    print(f"🔍 搜索: {query}\n")
    for i, (score, chunk) in enumerate(results):
        bvid = chunk.get("bvid", "")
        date = chunk.get("date", "")
        author_name = chunk.get("author", "")
        title = chunk.get("title", "")
        chunk_idx = chunk.get("chunk_index", 0)

        print(f"{'='*60}")
        print(f"  [{i+1}] 相似度: {score:.3f}")
        print(f"  📹 {title}")
        print(f"  👤 {author_name}  📅 {date}  🆔 {bvid}")
        if detail:
            print(f"  📄 {chunk.get('filename','')} (段落 #{chunk_idx+1})")
        print()

        # 显示上下文
        text = chunk["text"]
        if len(text) > 300:
            text = text[:300] + "..."
        print(f"  {text}")
        print()

    # 统计：哪些视频被命中
    print(f"\n{'='*60}")
    print(f"📊 共 {len(results)} 条结果")


def show_stats():
    """显示索引统计"""
    chunks, vectors = load_index()
    videos = {}
    for c in chunks:
        key = c.get("bvid", c.get("filename", ""))
        if key not in videos:
            videos[key] = {
                "title": c.get("title", ""),
                "author": c.get("author", ""),
                "date": c.get("date", ""),
                "chunks": 0,
            }
        videos[key]["chunks"] += 1

    print(f"📊 RAG 索引统计")
    print(f"   总段落数: {len(chunks)}")
    print(f"   视频数:   {len(videos)}")
    print()
    for bvid, info in videos.items():
        print(f"  {info['title'][:40]:<40} {info['author']:<10} {info['chunks']}段")


if __name__ == "__main__":
    args = sys.argv[1:]
    detail = "--detail" in args
    if "--stats" in args:
        show_stats()
        sys.exit(0)

    # 过滤作者
    author = None
    for i, a in enumerate(args):
        if a == "--author" and i + 1 < len(args):
            author = args[i + 1]
            break

    # 提取 top_k
    top_k = TOP_K
    for i, a in enumerate(args):
        if a == "--top" and i + 1 < len(args):
            top_k = int(args[i + 1])
            break

    # 查询内容：去掉所有 flag 后的第一个参数
    query = None
    for a in args:
        if not a.startswith("--"):
            query = a
            break

    if not query or query in ["--stats", "--author", "--top", "--detail"]:
        print("用法:")
        print("  python3 bilibili_rag_query.py '搜索内容'")
        print("  python3 bilibili_rag_query.py '搜索内容' --top 10 --detail")
        print("  python3 bilibili_rag_query.py '搜索内容' --author 付鹏")
        print("  python3 bilibili_rag_query.py --stats")
        sys.exit(1)

    search(query, top_k=top_k, author=author, detail=detail)
