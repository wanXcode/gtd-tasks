# GTD 提醒入口排查与切换收口（2026-04-05）

## 目的

本文件用于收口当前 GTD 提醒/手动查询链的真实入口，明确：

1. 哪些入口已经切到新链（digest / manual-query）
2. 哪些入口仍然走旧链（today.md / 本地视图 / 老 prompt）
3. 哪些属于仓库外或线上人工切换项
4. 旧 session 污染该如何处理

---

## 一、当前确认的“真正在跑”的主账号提醒 job / prompt 入口

### 1. OpenClaw cron（当前本机/线上可见）

通过 `openclaw cron list --json` 实查，当前主账号 GTD 真正在跑的是：

- `gtd-morning-brief`
- `gtd-daily-checkin`

当前 payload 已经不是直接读 `today.md`，而是：

- 读取 `prompts/gtd-morning-brief.md`
- 读取 `prompts/gtd-daily-checkin.md`

而这两个 prompt 又继续指向统一模板源：

- `prompts/gtd-reminder-template.md`

这条链路的目标口径已经是：

- 统一走 `scripts/gtd_reminder_digest.py --mode morning|evening`
- 手动待办查询统一走 `scripts/gtd_manual_query.sh`
- 不再把 `today.md / data/tasks.json / readonly-cache` 当提醒正文真源

### 2. 手动查询入口（AIGTD / 人工查看）

当前仓库内统一建议入口：

- `scripts/gtd_manual_query.sh morning --json`
- `scripts/gtd_manual_query.sh evening --json`

其底层都是：

- `scripts/gtd_reminder_digest.py`

### 3. 兼容脚本入口

- `daily-reminder.sh`

当前已是兼容包装层，默认转发：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode "$MODE"
```

所以主账号仓库内的旧脚本名还在，但内容已经切到新链。

---

## 二、仓库内已改到新链的引用点

以下引用点已经明确改到 digest/manual-query：

### 代码 / 脚本

- `scripts/gtd_reminder_digest.py`
- `scripts/gtd_manual_query.sh`
- `daily-reminder.sh`（兼容壳，已转发到 digest）
- `deploy.sh`（本次补改：默认创建的提醒说明已改成指向 prompt/digest，不再教人直接读 today.md 拼正文）

### prompt / runtime

- `prompts/gtd-reminder-template.md`
- `prompts/gtd-morning-brief.md`
- `prompts/gtd-daily-checkin.md`
- `agent-runtime/aigtd/PROMPT.md`
- `agent-runtime/aigtd/OPERATING-GUIDE.md`
- `agent-runtime/aigtd/MEMORY.md`
- `docs/aigtd-runtime-rules.md`
- `docs/api-first-reminder-cutover.md`
- `README.md`

这些文件已经形成统一口径：

- 正式提醒正文 -> `gtd_reminder_digest.py`
- 手动“待办清单 / 当前待办” -> `gtd_manual_query.sh`
- `today.md / inbox.md / done.md / matrix/*.md` 只是展示层

---

## 三、仍在走旧链或可能污染新链的入口

### A. 线上 cron delivery 元信息仍保留旧 target

实查 `openclaw cron list --json` 后发现：

- `payload.message` 已经改成新 prompt 链
- 但 `delivery.to` 仍显示旧 target：`user:ou_18141fecfe60134330583fc2f781dd45`
- 实际发送依赖 payload 内文案要求 agent 用 `message` 工具发到新 target：`user:ou_6ab7ba428602cd1b577b677e255c5d5f`

这意味着：

- 当前真实发送链主要靠 payload 中的“显式 message 发送”规则
- `delivery` 字段虽然是 `mode:none`，理论上不直接投递，但它仍是一个容易误判/误回滚的旧痕迹

**结论：这是人工切换项，不是仓库内代码能彻底修掉的。**

### B. OpenClaw cron 备份文件里仍大量保存旧 today.md 读取链

例如：

- `memory/cron-backups/jobs-20260309T032601Z.json`
- `memory/cron-backups/jobs-before-gtd-format-fix-2026-03-12-150146.json`

里面仍保存旧 prompt：

- “读取 `today.md` 和 matrix...”
- “读取 wife/today.md ...”

这些是**历史备份，不是当前真正在跑的 job**，但很容易在人工恢复/回滚时把旧链带回来。

**结论：它们是高风险旧入口，不能拿来直接 restore。**

### C. `deploy.sh` 是历史安装脚本，曾经会创建旧链 cron

本次已补改仓库内 `deploy.sh`，但如果线上有人之前已经跑过旧版脚本创建 cron，旧 job 不会自动被仓库变更覆盖。

**结论：仓库已修，线上已存在 job 仍需人工检查/重建。**

### D. wife 子目录仍是旧 Markdown 视图链

以下内容仍明显依赖：

- `users/wife/morning-brief.sh`
- `users/wife/daily-reminder.sh`
- `users/wife/bot-引导话术.md`

它们仍读：

- `users/wife/today.md`
- 四象限 markdown

这套链路和主账号 API-first digest 链不是一回事。

**结论：wife 目录目前仍是独立旧链，若未来也要统一，需要单独设计，不应误以为已自动切换。**

### E. 文档中的历史 today.md 说明仍然存在

例如：

- 各类 history 文档
- setup / memory 旧记录

这些更多是历史记录，不是当前运行入口；但对排障的人会造成“以为现在还在读 today.md 发提醒”的认知污染。

**结论：历史文档可以保留，但不能当当前运行说明。当前应优先看本文件 + `docs/api-first-reminder-cutover.md`。**

---

## 四、旧 session 污染处理说明

这次排查再次确认：

即使仓库内 prompt / 运行规则已经切到新链，**旧 session 仍可能继续沿用老规则**，包括：

- 继续把 `today.md` / readonly-cache 当提醒或查询真源
- 继续沿用旧的“无需回复”判断
- 继续直接读旧快照，导致任务状态答错

### 已知现象

常见表现包括：

- 明明文档已改，agent 仍按旧行为执行
- 明明 API / cache / done.md 已更新，agent 还回答旧状态
- 日志出现 `dispatch complete (replies=0)`，但用户其实应该收到回应

### 建议处理

优先删除对应 agent session，让下一条消息重建会话。

主账号 / AIGTD 排障时，重点检查：

- `/root/.openclaw/agents/aigtd/sessions/sessions.json`

如果需要重建，删除对应 key，例如：

- `agent:aigtd:feishu:direct:<open_id>`

注意：

- 先备份 `sessions.json`
- 只删对应用户会话 key，不要整库乱删
- 删除后让用户再发一条消息重建 session

相关经验也已记入工作区：

- `TOOLS.md`
- `docs/gtd-api-first-reminders-aigtd-retrospective-2026-03-28.md`

---

## 五、剩余人工切换清单

### 必做

1. **人工核对线上 cron payload 仍为新 prompt 链**
   - `gtd-morning-brief`
   - `gtd-daily-checkin`
   - 确认 payload.message 仍是读取 `prompts/gtd-morning-brief.md` / `prompts/gtd-daily-checkin.md`

2. **人工核对 cron 实际发送目标**
   - 虽然当前 payload 要求显式 `message` 到新 target
   - 仍建议把 cron 相关元信息 / 备注也统一确认，避免后续误恢复旧人

3. **禁止用 memory/cron-backups 下旧 json 直接 restore**
   - 如果必须恢复，先人工审 prompt，确认不再读 `today.md`

4. **若 AIGTD 仍表现出旧链行为，先处理 session 污染**
   - 删除对应 `agent:aigtd:feishu:direct:<open_id>`
   - 再重测

### 可后做

5. **决定是否给 wife 链路也做同样的 digest 化**
   - 当前它仍是独立 markdown 视图链
   - 不建议和主账号切换混在同一波操作里做

6. **如需继续降噪，可在历史 backup 文件旁补“禁止直接 restore”说明**
   - 这次先不批量改历史备份内容本体
   - 避免污染原始存档

---

## 六、建议切换顺序

建议按这个顺序做：

1. **先看线上 cron 当前 payload**
   - 确认仍是 prompt -> digest 新链

2. **再看实际发送目标是否完全一致**
   - 尤其核对 account / target / payload 内显式 message 目标

3. **再处理旧 session 污染**
   - 如果行为还像旧链，优先删 session 重建

4. **最后才考虑清理历史 backup / wife 链路**
   - 这些不是主链是否正确的前置条件

---

## 七、一句话结论

主账号 GTD 的“当前真实正式链”已经基本收口到：

- 定时提醒：`prompts/*` -> `gtd-reminder-template.md` -> `scripts/gtd_reminder_digest.py`
- 手动查询：`scripts/gtd_manual_query.sh` -> `scripts/gtd_reminder_digest.py`

现在剩下的风险点，主要不在仓库主代码，而在：

- 线上 cron 元信息/历史备份
- 旧 session 污染
- wife 独立旧链未纳入本次切换
