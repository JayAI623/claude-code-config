---
name: wechat-investment-summary
description: 分析总结贝版投资微信群每日消息要点。当用户要求"总结投资群"、"看看群里今天说了什么"、"贝版群日报"时触发。
---

# 微信投资群每日总结

分析贝版投资俱乐部系列微信群，提取今日消息并生成投资要点总结。

## 已配置信息

- **工作目录**: `~/Desktop/微信相关/wechat-decrypt/`
- **解密后数据库**: `~/Desktop/微信相关/wechat-decrypt/decrypted/`
- **消息提取脚本**: `~/.claude/skills/wechat-investment-summary/fetch_messages.py`
- **注意**: 数据库每天更新，每次查询前必须先重新解密

## 贝版群列表

| 群名 | username |
|------|----------|
| RWA 贝版投资俱乐部 | 26927313011@chatroom |
| 贝版投资俱乐部Creative Financing | 26552422185@chatroom |
| 贝版俱乐部 大饼铭文&L2 | 27899422963@chatroom |
| 贝版 特斯拉投资 | 25877913860@chatroom |
| 贝版 俱乐部AI群 | 27609622050@chatroom |
| 贝版俱乐部股票交易群 | 27173218763@chatroom |
| 贝版投资俱乐部西雅图群 | 26729310942@chatroom |
| 贝版私人投资俱乐部 | 26421307056@chatroom |
| 贝版投资俱乐部风投 | 25873310541@chatroom |
| 贝版俱乐部 量子计算 | 26734024923@chatroom |
| 贝版 贵金属逃顶群 | 26045425768@chatroom |
| 贝版 太空经济 | 27191115774@chatroom |

## 标准工作流程

### 第一步：获取今日消息

```bash
python3 ~/.claude/skills/wechat-investment-summary/fetch_messages.py
```

选项：
- `--days 2`：查最近2天（默认1天=今天）
- `--group "贝版私人"`：只查特定群
- `--no-decrypt`：跳过重新解密（数据库已是最新时使用）

### 第二步：两阶段分析（重要）

**阶段一：先输出 Topic 列表（默认行为）**

每个活跃群只给 3-5 个 topic，格式如下，让用户选感兴趣的再深挖：

```
## 贝版私人投资俱乐部（67条）

1. 💰 TS Token 打新 — Bayfamily 组织，超购257倍，开盘涨50倍，最终14倍退出
2. 🔐 USDT vs BTC 质押策略 — 下跌时 USDT 本位更抗跌，永续空单利息收入
3. 📈 AAOI 股价异动 — 跌至$88，原因是老黄"光铜并行"论修正市场预期
4. 🛠️ Elliott Wave 分析工具 — 有人分享网站，14天免费trial

👉 对哪个话题感兴趣？回复编号深度解析。
```

**阶段二：用户指定编号后，输出完整分析**

包含：具体论点、对话上下文、可操作结论。

### 第三步：输出日报（可选）

用户确认后保存到 `~/Desktop/贝版群日报_YYYY-MM-DD.md`

## 数据库技术细节

- 消息表名：`Msg_{md5(username)}`，例如贝版私人投资俱乐部 → `Msg_b1ee91da0e677b677a9ecbca28ce69aa`
- 时间字段：`create_time`（Unix 秒）
- 内容字段：`message_content`（文本/XML），`compress_content`（ZSTD 压缩内容）
- XML 消息需解析 `<title>` 和 `<refermsg>` 字段提取有效文字
- 引用回复格式：`<type>57</type>`，需提取 `<title>` 作为回复内容

## 联系人解析

发送者 ID 是数字，需从 contact.db 映射到昵称：
```bash
sqlite3 ~/Desktop/微信相关/wechat-decrypt/decrypted/contact/contact.db \
  "SELECT username, nick_name, remark FROM contact WHERE username = '目标ID';"
```
