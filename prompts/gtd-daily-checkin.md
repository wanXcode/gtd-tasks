# GTD Daily Check-in Template

请直接遵循统一模板源：`/root/.openclaw/workspace/gtd-tasks/prompts/gtd-reminder-template.md`

当前这是“晚上提醒”场景，因此：
- 使用统一骨架（今日 / 明日 / 未来 / 币价监控 / 下一步）
- 运行模式固定为 `evening`
- 推荐直接调用：`python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode evening`
- 与手动查看“待办清单”以及早上提醒保持同一版式
- 不再把 `today.md` / `data/tasks.json` 当成提醒输入真源

## 发送要求
生成正文后，必须使用 `message` 工具发送到 Feishu：
- `action=send`
- `channel=feishu`
- `accountId=aigtd`
- `target=user:ou_6ab7ba428602cd1b577b677e255c5d5f`

发送成功后，最终回复必须是：
NO_REPLY
