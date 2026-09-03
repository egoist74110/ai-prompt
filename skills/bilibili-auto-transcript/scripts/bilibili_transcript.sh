#!/bin/bash
# B站视频字幕智能获取脚本 v2.1
# 功能：CC字幕 → AI字幕 → Whisper转录（三级降级）
# 支持：macOS/WSL/Windows 浏览器 Cookie、多语言AI字幕、GPU加速

VIDEO_URL="$1"
OUTPUT_DIR="${2:-$HOME/workspace/knowledge/bilibili}"
# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"
BROWSER_HINT="${3:-auto}"

if [ -z "$VIDEO_URL" ]; then
    echo "用法: $0 <B站视频链接> [输出目录] [浏览器类型:auto|chrome|chromium|edge|firefox]"
    exit 1
fi

echo "🔍 正在获取视频信息..."

# ===== 检测浏览器Cookie =====
echo "🔍 检测浏览器Cookie..."

COOKIE_PARAM=""
FOUND_COOKIE=false

# 1. 尝试 macOS 常见浏览器
if [ "$FOUND_COOKIE" = false ] && [ "$(uname -s)" = "Darwin" ]; then
    BROWSER_CANDIDATES=()
    if [ "$BROWSER_HINT" = "auto" ]; then
        BROWSER_CANDIDATES=("chrome" "chromium" "edge" "firefox")
    else
        BROWSER_CANDIDATES=("$BROWSER_HINT")
    fi

    for browser in "${BROWSER_CANDIDATES[@]}"; do
        TEST=$(yt-dlp --list-subs --cookies-from-browser "$browser" "$VIDEO_URL" 2>&1 | head -1)
        if echo "$TEST" | grep -q "Extracting"; then
            echo "   ✅ 使用 macOS $browser Cookie"
            COOKIE_PARAM="--cookies-from-browser $browser"
            FOUND_COOKIE=true
            break
        fi
    done
fi

# 2. 尝试 WSL Chromium
CHROMIUM_PATH="$HOME/snap/chromium/common/chromium"
if [ "$FOUND_COOKIE" = false ] && [ -d "$CHROMIUM_PATH" ]; then
    TEST=$(yt-dlp --list-subs --cookies-from-browser "chromium:$CHROMIUM_PATH" "$VIDEO_URL" 2>&1 | head -1)
    if echo "$TEST" | grep -q "Extracting"; then
        echo "   ✅ 使用 WSL Chromium Cookie"
        COOKIE_PARAM="--cookies-from-browser chromium:$CHROMIUM_PATH"
        FOUND_COOKIE=true
    fi
fi

# 3. 尝试 Windows Edge
if [ "$FOUND_COOKIE" = false ]; then
    WIN_USER=$(ls /mnt/c/Users/ 2>/dev/null | grep -v "Public\|Default\|All Users" | head -1)
    if [ -n "$WIN_USER" ]; then
        EDGE_PATH="/mnt/c/Users/$WIN_USER/AppData/Local/Microsoft/Edge/User Data"
        if [ -d "$EDGE_PATH" ]; then
            echo "   🔑 使用 Windows Edge Cookie"
            COOKIE_PARAM="--cookies-from-browser edge:C:/Users/$WIN_USER/AppData/Local/Microsoft/Edge/User Data"
            FOUND_COOKIE=true
        fi
    fi
fi

if [ "$FOUND_COOKIE" = false ]; then
    echo "   ℹ️ 无可用Cookie，尝试无Cookie模式"
fi
echo ""

# 获取视频元数据
VIDEO_INFO=$(yt-dlp $COOKIE_PARAM --dump-json "$VIDEO_URL" 2>/dev/null | head -1)

if [ -z "$VIDEO_INFO" ]; then
    # 尝试不用cookie
    VIDEO_INFO=$(yt-dlp --dump-json "$VIDEO_URL" 2>/dev/null | head -1)
    if [ -z "$VIDEO_INFO" ]; then
        echo "❌ 无法获取视频信息"
        exit 1
    fi
fi

# 提取元数据
TITLE=$(echo "$VIDEO_INFO" | python3 -c "import sys, json; print(json.load(sys.stdin).get('title', '未知标题'))")
AUTHOR=$(echo "$VIDEO_INFO" | python3 -c "import sys, json; print(json.load(sys.stdin).get('uploader', '未知作者'))")
UPLOAD_DATE=$(echo "$VIDEO_INFO" | python3 -c "import sys, json; print(json.load(sys.stdin).get('upload_date', '未知时间'))")
DURATION=$(echo "$VIDEO_INFO" | python3 -c "import sys, json; d=json.load(sys.stdin).get('duration', 0); print(f'{d//60}分{d%60}秒')")
VIDEO_ID=$(echo "$VIDEO_INFO" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")

# 格式化日期
if [ "$UPLOAD_DATE" != "未知时间" ]; then
    UPLOAD_DATE_FORMATTED=$(echo "$UPLOAD_DATE" | sed 's/\(....\)\(..\)\(..\)/\1-\2-\3/')
else
    UPLOAD_DATE_FORMATTED="$UPLOAD_DATE"
fi

echo "📹 视频: $TITLE"
echo "👤 作者: $AUTHOR"
echo "📅 发布: $UPLOAD_DATE_FORMATTED"
echo "⏱️  时长: $DURATION"

# 检查字幕（带cookie）
echo ""
echo "🔍 正在检查字幕..."
SUB_CHECK=$(yt-dlp $COOKIE_PARAM --list-subs "$VIDEO_URL" 2>&1)

# 检查人工字幕
HAS_CC_SUBS=false
if echo "$SUB_CHECK" | grep -E "^[[:space:]]*(zh|en|ja|ko|es|ar|pt|de|fr)-" | grep -v "danmaku" | grep -v "^.*ai-" | grep -q "[[:space:]]"; then
    HAS_CC_SUBS=true
fi

# 检查AI字幕
HAS_AI_SUBS=false
AI_LANG=""
for lang in "ai-zh" "ai-en" "ai-ja" "zh-CN" "zh" "en" "ja"; do
    if echo "$SUB_CHECK" | grep -q "$lang"; then
        HAS_AI_SUBS=true
        AI_LANG="$lang"
        break
    fi
done

TRANSCRIPT_SOURCE=""
TRANSCRIPT_TEXT=""

# 第1级：人工CC字幕
if [ "$HAS_CC_SUBS" = true ]; then
    echo "✅ 发现人工CC字幕，优先下载..."
    
    yt-dlp $COOKIE_PARAM --skip-download --write-subs --sub-langs zh-CN,zh-TW,zh-Hans,zh --convert-subs srt \
        -o "${OUTPUT_DIR}/bilibili_subtitle.%(ext)s" "$VIDEO_URL" 2>&1
    
    SUB_FILE=$(find "$OUTPUT_DIR" -maxdepth 1 -name "bilibili_subtitle*.srt" -type f 2>/dev/null | head -1)
    
    if [ -n "$SUB_FILE" ] && [ -s "$SUB_FILE" ]; then
        echo "✅ CC字幕下载成功"
        TRANSCRIPT_SOURCE="B站CC字幕"
        TRANSCRIPT_TEXT=$(sed '/^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/d' "$SUB_FILE" | sed '/^[0-9]*$/d' | sed '/^$/d')
    else
        echo "⚠️  CC字幕下载失败..."
        HAS_CC_SUBS=false
    fi
fi

# 第2级：AI字幕
if [ -z "$TRANSCRIPT_TEXT" ] && [ "$HAS_AI_SUBS" = true ]; then
    echo "✅ 发现AI字幕（$AI_LANG），正在下载..."
    
    yt-dlp $COOKIE_PARAM --skip-download --write-subs --write-auto-subs --sub-langs "$AI_LANG" --convert-subs srt \
        -o "${OUTPUT_DIR}/bilibili_ai_subtitle.%(ext)s" "$VIDEO_URL" 2>&1
    
    SUB_FILE=$(find "$OUTPUT_DIR" -maxdepth 1 -name "bilibili_ai_subtitle*.srt" -type f 2>/dev/null | head -1)
    
    if [ -n "$SUB_FILE" ] && [ -s "$SUB_FILE" ]; then
        echo "✅ AI字幕下载成功"
        TRANSCRIPT_SOURCE="B站AI字幕 ($AI_LANG)"
        TRANSCRIPT_TEXT=$(sed '/^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/d' "$SUB_FILE" | sed '/^[0-9]*$/d' | sed '/^$/d')
    else
        echo "⚠️  AI字幕下载失败..."
        HAS_AI_SUBS=false
    fi
fi

# 第3级：Whisper本地转录
if [ -z "$TRANSCRIPT_TEXT" ]; then
    echo "🎤 未发现字幕，使用Whisper本地转录（GPU加速）..."
    echo "⏳ 这可能需要一些时间，请耐心等待..."
    
    # 下载音频
    yt-dlp $COOKIE_PARAM -x --audio-format mp3 -o "${OUTPUT_DIR}/bilibili_audio.%(ext)s" "$VIDEO_URL" 2>&1 || \
    yt-dlp -x --audio-format mp3 -o "${OUTPUT_DIR}/bilibili_audio.%(ext)s" "$VIDEO_URL" 2>&1
    
    AUDIO_FILE=$(find "$OUTPUT_DIR" -maxdepth 1 \( -name "bilibili_audio*.mp3" -o -name "bilibili_audio*.m4a" \) 2>/dev/null | head -1)
    
    if [ -z "$AUDIO_FILE" ]; then
        echo "❌ 音频下载失败"
        exit 1
    fi
    
    # 使用 medium 模型 + GPU
    whisper "$AUDIO_FILE" --model medium --language Chinese --output_format txt --output_dir "$OUTPUT_DIR" 2>&1
    
    # 只找 whisper 输出的 bilibili_audio.txt，不能乱捡其他 .txt 文件
    TXT_FILE="${OUTPUT_DIR}/bilibili_audio.txt"
    if [ ! -f "$TXT_FILE" ]; then
        TXT_FILE=$(find "$OUTPUT_DIR" -maxdepth 1 -name "*bilibili_audio*.txt" -type f 2>/dev/null | head -1)
    fi
    
    if [ -n "$TXT_FILE" ] && [ -s "$TXT_FILE" ]; then
        echo "✅ 转录完成"
        TRANSCRIPT_SOURCE="Whisper medium 模型"
        TRANSCRIPT_TEXT=$(cat "$TXT_FILE")
        rm -f "$TXT_FILE"
    else
        echo "❌ 转录失败"
        exit 1
    fi
fi

# 繁体转简体
if command -v opencc >/dev/null 2>&1; then
    echo "🔄 正在转换为简体字..."
    TRANSCRIPT_TEXT_SIMPLIFIED=$(echo "$TRANSCRIPT_TEXT" | opencc -c tw2s)
else
    TRANSCRIPT_TEXT_SIMPLIFIED="$TRANSCRIPT_TEXT"
fi

# 生成输出文件名：标题-UP主-日期-BVid.txt
# 标点符号→连字符(-)，字段间用下划线(_)分隔
SAFE_TITLE=$(echo "$TITLE" | python3 -c "import sys, re; s=sys.stdin.read().strip(); s=re.sub(r'[\\\\/:*?\"<>|]', '', s); s=re.sub(r'[\\s\\W]+', '-', s); s=re.sub(r'-+', '-', s).strip('-'); print(s[:60])")
AUTHOR_SAFE=$(echo "$AUTHOR" | python3 -c "import sys, re; s=sys.stdin.read().strip(); s=re.sub(r'[\\\\/:*?\"<>|]', '', s); s=re.sub(r'[\\s\\W]+', '-', s); s=re.sub(r'-+', '-', s).strip('-'); print(s[:30])")
OUTPUT_FILE="${OUTPUT_DIR}/${SAFE_TITLE}_${AUTHOR_SAFE}_${UPLOAD_DATE_FORMATTED}_${VIDEO_ID}.txt"

# 生成格式化的 TXT 文件
echo "📝 正在生成转录文件..."

cat > "$OUTPUT_FILE" << EOF
================================================================================
B站视频转录文档
================================================================================

📹 视频标题：$TITLE
🔗 B站链接：$VIDEO_URL
👤 作者：$AUTHOR
📅 发布时间：$UPLOAD_DATE_FORMATTED
⏱️  视频时长：$DURATION
📝 转录来源：$TRANSCRIPT_SOURCE
⏰ 转录时间：$(date '+%Y-%m-%d %H:%M:%S')

================================================================================
第一部分：视频摘要（AI生成）
================================================================================

【AI待处理：请阅读全文后，替换此行，写结构化摘要】

================================================================================
第二部分：完整原文
================================================================================

$TRANSCRIPT_TEXT_SIMPLIFIED

================================================================================
文档结束
================================================================================
EOF

echo ""
echo "✅ 转录完成！"
echo "📄 文件已保存: $OUTPUT_FILE"
echo "$OUTPUT_FILE"
