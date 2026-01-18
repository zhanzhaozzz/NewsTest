# 📬 TrendRadar 通知渠道配置

本文档详细介绍 TrendRadar 支持的所有通知渠道配置方式。

## 目录

- [企业微信机器人](#企业微信机器人)
- [个人微信推送](#个人微信推送)
- [飞书机器人](#飞书机器人)
- [钉钉机器人](#钉钉机器人)
- [Telegram Bot](#telegram-bot)
- [邮件推送](#邮件推送)
- [ntfy 推送](#ntfy-推送)
- [Bark 推送](#bark-推送)
- [Slack 推送](#slack-推送)
- [多账号推送配置](#多账号推送配置)

---

## 企业微信机器人

**GitHub Secret 配置：**
- **Name（名称）**：`WEWORK_WEBHOOK_URL`
- **Secret（值）**：你的企业微信机器人 Webhook 地址

**机器人设置步骤：**

### 手机端设置：
1. 打开企业微信 App → 进入目标内部群聊
2. 点击右上角"…"按钮 → 选择"消息推送"
3. 点击"添加" → 名称输入"TrendRadar"
4. 复制 Webhook 地址，点击保存

### PC 端设置：
流程类似手机端

---

## 个人微信推送

> 基于企业微信的插件机制，推送样式为纯文本（无 markdown 格式），但可以直接推送到个人微信，无需安装企业微信 App。

**GitHub Secret 配置：**
- **Name（名称）**：`WEWORK_WEBHOOK_URL`
- **Secret（值）**：你的企业微信应用 Webhook 地址

- **Name（名称）**：`WEWORK_MSG_TYPE`
- **Secret（值）**：`text`

**设置步骤：**
1. 完成上方的企业微信机器人 Webhook 设置
2. 添加 `WEWORK_MSG_TYPE` Secret，值设为 `text`
3. 在企业微信 App 上关联个人微信
4. 配置好后，手机上的企业微信 App 可以删除

---

## 飞书机器人

**GitHub Secret 配置：**
- **Name（名称）**：`FEISHU_WEBHOOK_URL`
- **Secret（值）**：你的飞书机器人 Webhook 地址

**方案一：机器人指令（简单）**

1. 电脑浏览器打开 https://botbuilder.feishu.cn/home/my-command
2. 点击"新建机器人指令"
3. 点击"选择触发器"，往下滑动，点击"Webhook 触发"
4. 复制"Webhook 地址"到记事本暂存
5. "参数"里面放上以下内容：

```json
{
  "message_type": "text",
  "content": {
    "total_titles": "{{内容}}",
    "timestamp": "{{内容}}",
    "report_type": "{{内容}}",
    "text": "{{内容}}"
  }
}
```

6. 点击"选择操作" > "通过官方机器人发消息"
7. 消息标题填写"TrendRadar 热点监控"
8. 点击 + 按钮，选择"Webhook 触发"，按顺序摆放参数

**方案二：机器人应用（稳定）**

1. 电脑浏览器打开 https://botbuilder.feishu.cn/home/my-app
2. 点击"新建机器人应用"
3. 进入创建的应用后，点击"流程设计" > "创建流程" > "选择触发器"
4. 其余步骤与方案一类似

---

## 钉钉机器人

**GitHub Secret 配置：**
- **Name（名称）**：`DINGTALK_WEBHOOK_URL`
- **Secret（值）**：你的钉钉机器人 Webhook 地址

**机器人设置步骤：**

1. **创建机器人（仅 PC 端支持）**：
   - 打开钉钉 PC 客户端，进入目标群聊
   - 点击群设置图标（⚙️）→ 往下翻找到"机器人"点开
   - 选择"添加机器人" → "自定义"

2. **配置机器人**：
   - 设置机器人名称
   - **安全设置**：自定义关键词设置 "热点"

3. **完成设置**：
   - 勾选服务条款协议 → 点击"完成"
   - 复制获得的 Webhook URL

---

## Telegram Bot

**GitHub Secret 配置：**
- **Name（名称）**：`TELEGRAM_BOT_TOKEN`
- **Secret（值）**：你的 Telegram Bot Token

- **Name（名称）**：`TELEGRAM_CHAT_ID`
- **Secret（值）**：你的 Telegram Chat ID

**机器人设置步骤：**

1. **创建机器人**：
   - 在 Telegram 中搜索 `@BotFather`（有蓝色徽章勾勾）
   - 发送 `/newbot` 命令创建新机器人
   - 设置机器人名称（必须以"bot"结尾）
   - 获取 Bot Token（格式如：`123456789:AAHfiqksKZ8WmR2zSjiQ7_v4TMAKdiHm9T0`）

2. **获取 Chat ID**：
   - 先向你的机器人发送一条消息
   - 访问：`https://api.telegram.org/bot<你的Bot Token>/getUpdates`
   - 在返回的 JSON 中找到 `"chat":{"id":数字}` 中的数字

---

## 邮件推送

> ⚠️ **重要配置依赖**：邮件推送需要 HTML 报告文件。请确保 `config/config.yaml` 中的 `storage.formats.html` 设置为 `true`

**GitHub Secret 配置：**

**必需配置（3 项）：**
- `EMAIL_FROM`：发件人邮箱地址
- `EMAIL_PASSWORD`：邮箱密码或授权码
- `EMAIL_TO`：收件人邮箱地址（多个收件人用英文逗号分隔）

**可选配置：**
- `EMAIL_SMTP_SERVER`：SMTP服务器地址（可留空，系统会自动识别）
- `EMAIL_SMTP_PORT`：SMTP端口（可留空，系统会自动识别）

**支持的邮箱服务商**（自动识别 SMTP 配置）：

| 邮箱服务商 | 域名 | SMTP 服务器 | 端口 |
|-----------|------|------------|------|
| Gmail | gmail.com | smtp.gmail.com | 587 |
| QQ邮箱 | qq.com | smtp.qq.com | 465 |
| Outlook | outlook.com | smtp-mail.outlook.com | 587 |
| 163邮箱 | 163.com | smtp.163.com | 465 |
| 126邮箱 | 126.com | smtp.126.com | 465 |

---

## ntfy 推送

### 免费使用（推荐新手）

**特点**：
- ✅ 无需注册账号，立即使用
- ✅ 每天 250 条消息（足够 90% 用户）
- ✅ Topic 名称即"密码"

**快速开始：**

1. **下载 ntfy 应用**：
   - Android：[Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [F-Droid](https://f-droid.org/en/packages/io.heckel.ntfy/)
   - iOS：[App Store](https://apps.apple.com/us/app/ntfy/id1625396347)

2. **订阅主题**（选择一个难猜的名称）：
   ```
   建议格式：trendradar-{你的名字缩写}-{随机数字}
   ✅ 好例子：trendradar-zs-8492
   ❌ 坏例子：news、alerts（太容易被猜到）
   ```

3. **配置 GitHub Secret：**
   - `NTFY_TOPIC`：填写你刚才订阅的主题名称

### 自托管（完全隐私控制）

**Docker 一键部署**：
```bash
docker run -d \
  --name ntfy \
  -p 80:80 \
  -v /var/cache/ntfy:/var/cache/ntfy \
  binwiederhier/ntfy \
  serve --cache-file /var/cache/ntfy/cache.db
```

---

## Bark 推送

> iOS 专属，简洁高效

**GitHub Secret 配置：**
- **Name（名称）**：`BARK_URL`
- **Secret（值）**：你的 Bark 推送 URL

**使用官方服务器：**

1. **下载 Bark App**：
   - iOS：[App Store](https://apps.apple.com/cn/app/bark-给你的手机发推送/id1403753865)

2. **获取推送 URL**：
   - 打开 Bark App
   - 复制首页显示的推送 URL（格式如：`https://api.day.app/your_device_key`）

**自建服务器：**
```bash
docker run -d \
  --name bark-server \
  -p 8080:8080 \
  finab/bark-server
```

---

## Slack 推送

**GitHub Secret 配置：**
- **Name（名称）**：`SLACK_WEBHOOK_URL`
- **Secret（值）**：你的 Slack Incoming Webhook URL

**设置步骤：**

1. **创建 Slack App**：
   - 访问 https://api.slack.com/apps?new_app=1
   - 点击 "From scratch"
   - 填写 App Name（如 `TrendRadar`）
   - 选择你的 Workspace

2. **启用 Incoming Webhooks**：
   - 在左侧菜单中点击 "Incoming Webhooks"
   - 将开关从 `OFF` 切换到 `ON`

3. **生成 Webhook URL**：
   - 点击 "Add New Webhook to Workspace"
   - 选择要接收消息的频道
   - 点击 "Allow" 完成授权

4. **复制并保存 URL**：
   - 格式如：`https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXX`

---

## 多账号推送配置

> ⚠️ **安全警告**：GitHub Fork 用户请勿在 `config.yaml` 中配置推送信息！

### 配置说明

- **支持多账号配置**：所有推送渠道均支持配置多个账号
- **配置方式**：使用英文分号 `;` 分隔多个账号值
- **数量限制**：默认每个渠道最多 3 个账号

### 多账号配置示例

**单渠道多账号：**
```bash
# 飞书多账号（3个群组）
FEISHU_WEBHOOK_URL=https://webhook1;https://webhook2;https://webhook3
```

**配对配置（Telegram 和 ntfy）：**
```bash
# Telegram：token 和 chat_id 数量必须一致
TELEGRAM_BOT_TOKEN=token1;token2
TELEGRAM_CHAT_ID=id1;id2
```

### 支持的渠道

| 渠道 | 配置项 | 是否需要配对 |
|------|--------|-------------|
| **飞书** | `feishu_url` | 否 |
| **钉钉** | `dingtalk_url` | 否 |
| **企业微信** | `wework_url` | 否 |
| **Telegram** | `telegram_bot_token` + `telegram_chat_id` | ✅ 是 |
| **ntfy** | `ntfy_topic` + `ntfy_token` | ✅ 是 |
| **Bark** | `bark_url` | 否 |
| **Slack** | `slack_webhook_url` | 否 |
| **邮件** | `email_to` | 已支持多收件人 |

---

[返回主文档](../README.md)
