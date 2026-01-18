# 🚀 TrendRadar 部署指南

本文档详细介绍 TrendRadar 的各种部署方式。

## 目录

- [部署方式选择](#部署方式选择)
- [Docker 部署](#docker-部署)
- [GitHub Actions 部署](#github-actions-部署)
- [本地运行](#本地运行)
- [远程云存储配置](#远程云存储配置)

---

## 部署方式选择

| 部署方式 | 特点 | 适用场景 |
|---------|------|---------|
| **Docker 部署** | 比 GitHub Actions 更稳定 | 有自己的服务器、NAS 或长期运行的电脑 |
| **GitHub Actions** | 免费、无需服务器 | 无服务器、轻量使用 |
| **本地运行** | 最简单、直接运行 | 开发测试、临时使用 |

---

## Docker 部署

### 镜像说明

| 镜像名称 | 用途 | 说明 |
|---------|------|------|
| `wantcat/trendradar` | 新闻推送服务 | 定时抓取新闻、推送通知（必选） |
| `wantcat/trendradar-mcp` | AI 分析服务 | MCP 协议支持、AI 对话分析（可选） |

### 使用 docker compose（推荐）

#### 1. 创建项目目录和配置

**方式 A：使用 git clone（推荐）**
```bash
git clone https://github.com/sansan0/TrendRadar.git
cd TrendRadar
```

**方式 B：使用 wget 下载配置文件**
```bash
mkdir -p trendradar/{config,docker}
cd trendradar

wget https://raw.githubusercontent.com/sansan0/TrendRadar/master/config/config.yaml -P config/
wget https://raw.githubusercontent.com/sansan0/TrendRadar/master/config/frequency_words.txt -P config/
wget https://raw.githubusercontent.com/sansan0/TrendRadar/master/docker/.env -P docker/
wget https://raw.githubusercontent.com/sansan0/TrendRadar/master/docker/docker-compose.yml -P docker/
```

#### 2. 目录结构

```
当前目录/
├── config/
│   ├── config.yaml
│   └── frequency_words.txt
└── docker/
    ├── .env
    └── docker-compose.yml
```

#### 3. 配置文件说明

- `config/config.yaml` - **功能配置**（报告模式、推送设置、存储格式等）
- `config/frequency_words.txt` - **关键词配置**
- `docker/.env` - **敏感信息 + Docker 特有配置**（webhook URLs、S3 密钥）

#### 4. 环境变量覆盖机制

`.env` 文件中的环境变量会覆盖 `config.yaml` 中的对应配置：

| 环境变量 | 对应配置 | 示例值 |
|---------|---------|-------|
| `ENABLE_CRAWLER` | `advanced.crawler.enabled` | `true` / `false` |
| `ENABLE_NOTIFICATION` | `notification.enabled` | `true` / `false` |
| `REPORT_MODE` | `report.mode` | `daily` / `incremental` / `current` |
| `DISPLAY_MODE` | `report.display_mode` | `keyword` / `platform` |
| `ENABLE_WEBSERVER` | - | `true` / `false` |
| `WEBSERVER_PORT` | - | `8080` |

#### 5. 启动服务

**选项 A：启动所有服务（推送 + AI 分析）**
```bash
docker compose pull
docker compose up -d
```

**选项 B：仅启动新闻推送服务**
```bash
docker compose pull trendradar
docker compose up -d trendradar
```

**选项 C：仅启动 MCP AI 分析服务**
```bash
docker compose pull trendradar-mcp
docker compose up -d trendradar-mcp
```

#### 6. 查看运行状态

```bash
# 查看新闻推送服务日志
docker logs -f trendradar

# 查看 MCP AI 分析服务日志
docker logs -f trendradar-mcp

# 查看所有容器状态
docker ps | grep trendradar
```

### 服务管理命令

```bash
# 查看运行状态
docker exec -it trendradar python manage.py status

# 手动执行一次爬虫
docker exec -it trendradar python manage.py run

# 查看实时日志
docker exec -it trendradar python manage.py logs

# Web 服务器管理
docker exec -it trendradar python manage.py start_webserver   # 启动
docker exec -it trendradar python manage.py stop_webserver    # 停止
docker exec -it trendradar python manage.py webserver_status  # 状态
```

### 镜像更新

```bash
docker compose pull
docker compose up -d
```

### 数据持久化

生成的报告和数据默认保存在 `./output` 目录下。

**网页版报告访问路径**：

| 文件位置 | 访问方式 | 适用场景 |
|---------|---------|---------|
| `output/index.html` | 宿主机直接访问 | Docker 部署 |
| `index.html` | 根目录访问 | GitHub Pages |
| `output/html/YYYY-MM-DD/` | 历史报告访问 | 所有环境 |

---

## GitHub Actions 部署

### 1. 获取项目代码

点击本仓库页面右上角的绿色 **[Use this template]** 按钮 → 选择 "Create a new repository"。

> ⚠️ 提醒：使用 Fork 可能导致运行异常

### 2. 设置 GitHub Secrets

在你 Fork 后的仓库中，进入 `Settings` > `Secrets and variables` > `Actions` > `New repository secret`

**重要说明：**
- 一个 Name 对应一个 Secret
- 保存后看不到值是正常的
- Name（名称）必须严格使用规定名称
- 可以同时配置多个平台

### 3. 手动测试新闻推送

1. 进入你项目的 Actions 页面
2. 找到 **"Get Hot News"** 点进去
3. 点击右侧的 **"Run workflow"** 按钮运行
4. 3 分钟左右，消息会推送到你配置的平台

### 4. 签到续期机制

- **运行周期**：有效期为 **7 天**
- **续期方式**：在 Actions 页面手动触发 "Check In" workflow
- **操作路径**：`Actions` → `Check In` → `Run workflow`

### 两种部署模式对比

| 模式 | 配置要求 | 功能范围 |
|------|---------|---------|
| **轻量模式** | 无需配置存储 | 实时抓取 + 关键词筛选 + 多渠道推送 |
| **完整模式** | 配置远程云存储 | 轻量模式 + 新增检测 + 趋势追踪 + AI分析 |

---

## 本地运行

### 环境要求

- Python 3.10+
- UV（推荐）或 pip

### 安装步骤

**Windows：**
```bash
# 安装依赖
uv sync

# 运行
uv run python -m trendradar
```

**Mac/Linux：**
```bash
# 安装依赖
uv sync

# 运行
uv run python -m trendradar
```

---

## 远程云存储配置

> 配置远程云存储后即可解锁全部功能

### 以 Cloudflare R2 为例

**前置条件**：开通 R2 需绑定支付方式（仅作身份验证，不产生扣费）

### GitHub Secret 配置

**必需配置（4 项）：**

| Name（名称） | Secret（值）说明 |
|-------------|-----------------|
| `S3_BUCKET_NAME` | 存储桶名称（如 `trendradar-data`） |
| `S3_ACCESS_KEY_ID` | 访问密钥 ID |
| `S3_SECRET_ACCESS_KEY` | 访问密钥 |
| `S3_ENDPOINT_URL` | S3 API 端点 |

**可选配置：**

| Name（名称） | Secret（值）说明 |
|-------------|-----------------|
| `S3_REGION` | 区域（默认 `auto`） |

### 如何获取凭据（Cloudflare R2）

1. **进入 R2 概览**：
   - 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
   - 点击左侧 `R2对象存储`

2. **创建存储桶**：
   - 点击 `概述` → `创建存储桶`
   - 输入名称（如 `trendradar-data`）

3. **创建 API 令牌**：
   - 回到概述页面
   - 点击右下角 `Manage R2 API Tokens`
   - 复制 `S3 API` 地址作为 `S3_ENDPOINT_URL`
   - 点击 `创建 Account APl 令牌`
   - 权限选择 `管理员读和写`
   - **立即复制** `Access Key ID` 和 `Secret Access Key`

---

[返回主文档](../README.md)
