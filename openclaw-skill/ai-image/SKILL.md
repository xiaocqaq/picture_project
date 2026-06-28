---
name: ai-image
description: "调用本地 NayutoAI 图片生成服务，根据文字描述生成图片"
trigger: "生成图片|画一张|画一个|生图|画图|image|generate image|draw"
tools: [exec]
user-invocable: true
metadata: { "openclaw": { "emoji": "🎨" } }
---

# AI 图片生成

根据用户的文字描述生成图片。服务运行在本地 `http://localhost:8000`。

## 使用流程

1. 从用户消息中提取图片描述作为 prompt（保留原文，不要翻译或改写）
2. 根据用户意图选择合适的参数：
   - **尺寸**：`1024x1024`（方图，默认）、`1024x1536`（竖图，适合人像/海报）、`1536x1024`（横图，适合风景/横幅）
   - **画质**：`low`（快速预览）、`medium`（默认）、`high`（高质量）
3. 调用 API 生成图片
4. 将返回的图片展示给用户

## API 调用

```bash
curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "<用户描述>", "size": "<尺寸>", "quality": "<画质>", "n": 1}'
```

响应格式：
```json
{
  "images": [{"b64_json": "<base64数据>", "data_url": "data:image/png;base64,..."}],
  "prompt": "...",
  "size": "1024x1024",
  "quality": "medium"
}
```

## 处理结果

- 成功时：`images` 数组中每个元素的 `b64_json` 是 base64 编码的 PNG 图片，将其保存为文件并展示给用户
- 失败时：告知用户错误原因，常见问题是服务未启动（提示用户运行 `python run.py`）

## 保存图片

将 base64 数据解码后保存到文件：

```bash
echo '<b64_json值>' | base64 -d > generated_image.png
```

## 注意事项

- 生成过程通常需要 60-180 秒，请提前告知用户耐心等待
- 如果服务未运行，会返回连接错误，提示用户先启动服务
- 用户没有指定尺寸时默认使用 `1024x1024`
- 用户没有指定画质时默认使用 `medium`
