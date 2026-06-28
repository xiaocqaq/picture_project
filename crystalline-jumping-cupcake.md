# NayutoAI 图片生成应用 - 实现计划

## Context

用户需要一个基于 NayutoAI API 的图片生成应用。NayutoAI 提供 OpenAI 兼容的图片生成接口（`/v1/images/generations`），模型为 `gpt-image-2`。后端使用 FastAPI + LangChain，前端使用静态页面（由后端托管，避免跨域），整体可打包部署到服务器。

## NayutoAI API 规格

- **Base URL**: `https://api.nayutoai.online/v1`
- **生图端点**: `POST /v1/images/generations`
- **认证**: `Authorization: Bearer YOUR_API_KEY`
- **模型**: `gpt-image-2`（固定名称）
- **尺寸选项**: `1024x1024`, `1024x1536`, `1536x1024`（WIDTHxHEIGHT 像素值）
- **质量**: `low` / `medium` / `high`
- **返回格式**: `b64_json`（base64 编码图片数据）
- **请求参数**: `prompt`, `model`, `n`, `size`, `quality`

## 项目结构

```
D:\code\picture_project\
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI 入口，挂载静态文件
│   ├── config.py         # 配置管理（读取 .env）
│   ├── service.py        # LangChain 图片生成服务
│   └── static/
│       └── index.html    # 前端单页面（现代美观 UI）
├── .env.example          # 环境变量模板
├── requirements.txt      # Python 依赖
└── run.py                # 启动脚本
```

## 实现步骤

### 1. 配置文件（`app/config.py`）
- 使用 `pydantic-settings` 从 `.env` 读取配置
- 配置项：`NAYUTO_API_KEY`、`NAYUTO_BASE_URL`（默认 `https://api.nayutoai.online/v1`）

### 2. LangChain 生图服务（`app/service.py`）
- 使用 LangChain 的 `DallEAPIWrapper`，设置自定义 `base_url` 指向 NayutoAI
- 封装生图函数：接收 prompt、size、quality 参数，返回 base64 图片数据
- NayutoAI 兼容 OpenAI 接口格式，DallEAPIWrapper 可直接适配

### 3. FastAPI 后端（`app/main.py`）
- `POST /api/generate`：接收生图请求（prompt, size, quality），调用 service 层生成图片
- 返回 JSON：包含 base64 图片数据和生成信息
- 挂载 `app/static/` 目录为静态文件服务，前端从根路径 `/` 访问
- 添加异常处理和超时控制

### 4. 前端页面（`app/static/index.html`）
- 现代渐变风格单页应用，深色主题
- 输入区域：prompt 输入框、size 下拉选择、quality 下拉选择
- 生成按钮 + loading 动画
- 图片展示区域：生成完成后展示图片，支持下载
- 响应式布局，移动端适配
- 纯 HTML/CSS/JS，无需构建工具

### 5. 启动与部署
- `run.py`：使用 uvicorn 启动 FastAPI 应用
- `requirements.txt`：fastapi, uvicorn, langchain, langchain-openai, openai, pydantic-settings, python-dotenv
- `.env.example`：环境变量模板

## 验证方式

1. 创建 `.env` 文件，填入真实 API Key
2. `pip install -r requirements.txt`
3. `python run.py` 启动服务
4. 浏览器访问 `http://localhost:8000`
5. 输入提示词，选择参数，点击生成，验证图片输出
