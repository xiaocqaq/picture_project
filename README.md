# NayutoAI Image Generator

基于 NayutoAI API 的图片生成应用，使用 FastAPI + OpenAI SDK 构建后端，静态页面作为前端，前后端一体化部署，无跨域问题。

## 功能

- 文生图（text-to-image），模型：gpt-image-2
- 支持选择尺寸（1:1 / 2:3 / 3:2）、质量（low / medium / high）、生成数量（1-4）
- 生成结果实时展示，支持下载
- 深色主题现代 UI，响应式布局

## 本地启动

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```
NAYUTO_API_KEY=your_actual_key
NAYUTO_BASE_URL=https://api.nayutoai.online/v1
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动服务

```bash
python run.py
```

浏览器访问 http://localhost:8000

## 服务器部署

### 方式一：直接部署

```bash
# 1. 上传项目到服务器
scp -r . user@your-server:/opt/picture_project

# 2. SSH 登录服务器
ssh user@your-server

# 3. 安装依赖
cd /opt/picture_project
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 5. 后台启动（生产模式）
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 > app.log 2>&1 &
```

### 方式二：Systemd 守护进程（推荐）

创建服务文件 `/etc/systemd/system/picture-app.service`：

```ini
[Unit]
Description=NayutoAI Image Generator
After=network.target

[Service]
Type=exec
User=www-data
WorkingDirectory=/opt/picture_project
ExecStart=/usr/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
EnvironmentFile=/opt/picture_project/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable picture-app
sudo systemctl start picture-app

# 查看状态
sudo systemctl status picture-app

# 查看日志
journalctl -u picture-app -f
```

### 方式三：Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```bash
# 构建镜像
docker build -t picture-app .

# 运行容器
docker run -d --name picture-app -p 8000:8000 --env-file .env picture-app
```

### Nginx 反向代理（可选）

如需域名访问或 HTTPS，配置 Nginx：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
```

## 项目结构

```
├── .env.example          # 环境变量模板
├── requirements.txt      # Python 依赖
├── run.py                # 本地启动入口
└── app/
    ├── config.py          # 配置管理
    ├── main.py            # FastAPI 路由
    ├── service.py         # 生图服务
    └── static/
        └── index.html     # 前端页面
```
