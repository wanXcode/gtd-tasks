# GTD × Apple Reminders Requirements v1.1

> 基于《重构方案1.0》输出的产品需求文档。目标不是继续扩张功能，而是把系统收口到“简洁、稳定、不复杂、可长期使用”的状态。

---

## 一、文档目标

本需求文档用于明确：

1. 本轮重构到底要做什么
2. 明确不做什么
3. 产品语义如何定义
4. Apple 同步边界如何收口
5. 什么叫做“开发完成、可以验收”

本文件是后续开发、测试、验收的直接依据。

---

## 二、本轮版本目标

本轮版本目标不是“做一个完整双向任务平台”，而是做一个：

> **以 GTD 主库为核心、由 Mac 本地桥接 Apple Reminders 的轻量同步系统。**

本轮目标分成 3 个：

### 目标 1：统一 GTD 产品语义
- 明确区分 `open / done / deleted`
- 明确主清单展示规则
- 明确 done 与 delete 的产品差异

### 目标 2：稳定 GTD -> Apple Reminders 自动同步
- 主库更新后，Apple Reminders 可自动看到对应变化
- 不依赖服务端
- 不追求复杂同步中心

### 目标 3：增加最小 Apple -> GTD 回写
- 只支持：`completed -> done`
- 不开放标题、备注、分类、删除等复杂回写

---

## 三、产品原则

### 3.1 单主库原则
`data/tasks.json` 是唯一事实源。

这意味着：
- GTD 所有业务状态都以主库为准
- Apple Reminders 不是第二主库
- 所有视图文件都是渲染结果，不是事实源

### 3.2 Mac 本地桥接原则
Apple Reminders 的实际执行端在 Mac 本机。

这意味着：
- 不做独立服务端
- 不做云端同步中心
- 同步逻辑由 Mac 本地桥接脚本承担

### 3.3 默认单向原则
主同步方向始终是：

`GTD -> Apple Reminders`

Apple -> GTD 只允许最小回写，不允许无限扩张。

### 3.4 保守优先原则
同步系统出现异常时：
- 优先保守
- 优先不误删
- 优先不污染主库
- 优先可恢复

---

## 四、任务状态与语义

## 4.1 状态定义

### open
含义：
- 当前未完成任务
- 显示在日常待办主清单
- 参与 GTD -> Apple 同步

### done
含义：
- 已完成任务
- 不显示在主清单
- 进入完成区 / 回顾区
- 可以同步为 Apple completed

### deleted
含义：
- 真删除任务
- 不显示在主清单
- 不显示在 done / weekly review
- 不作为完成记录保留

---

## 4.2 done 与 delete 的差异

### done
是“从日常待办中移除，但保留记录”。

用途：
- 用于回顾
- 用于查看完成历史
- 用于周报 / 复盘

### delete
是真删除。

用途：
- 删除误录任务
- 删除测试任务
- 删除不需要保留历史的记录

结论：

> **done != delete**

这是本轮最重要的规则之一。

---

## 五、主清单展示规则

## 5.1 主清单
主清单只展示：
- `status = open`
- `deleted_at = null`

主清单不展示：
- done
- deleted
- cancelled（如保留该状态，也不应出现在主清单）
- archived（如保留该状态，也不应出现在主清单）

## 5.2 完成区
完成区应展示：
- done
- 可按需要展示 cancelled / archived（如果保留）

建议位置：
- `done.md`
- `weekly/review-latest.md`

## 5.3 删除项
删除项默认不进入任何常规视图。

如未来要审计删除行为，应通过日志或单独历史机制处理，而不是出现在用户日常视图里。

---

## 六、Apple 同步边界

## 6.1 GTD -> Apple 支持范围

本轮应支持：
- 新建任务同步到 Apple Reminders
- 标题变更同步到 Apple Reminders
- 完成状态同步到 Apple Reminders
- reopen / 重新打开状态同步到 Apple Reminders
- 任务按 category 映射到不同 Reminder List

本轮可选支持：
- note 同步
- due date 同步

本轮不强制支持：
- 高复杂度字段对比
- 任意字段双向同步
- 复杂冲突协商

---

## 6.2 Apple -> GTD 支持范围

本轮只支持：

### completed -> done
当用户在 Apple Reminders 中勾选完成后：
- 若能识别对应 GTD 任务
- 则将 GTD 主库中的对应任务标记为 done
- 然后自动刷新视图

### 本轮明确不支持
- Apple 改标题回写 GTD
- Apple 改备注回写 GTD
- Apple 改分类回写 GTD
- Apple 改 bucket / quadrant / tag 回写 GTD
- Apple 删除回写 GTD 删除

结论：

> Apple 侧唯一允许回写的动作，是 completed。

---

## 七、识别与映射规则

## 7.1 稳定锚点
Apple Reminder 与 GTD 任务的关联，必须通过稳定锚点识别。

推荐方式：
- 在 Reminder 中保留 `[GTD_ID] tsk_xxx`

要求：
- 不依赖标题模糊匹配
- 不依赖列表位置猜测
- 不依赖自然语言推断

## 7.2 列表映射
建议保留 GTD category -> Apple List 的映射关系。

例如：
- `inbox` -> 收集箱
- `project` -> 项目
- `next_action` -> 下一步行动
- `waiting_for` -> 等待
- `maybe` -> 可能的事

如果 category 变化，应同步到对应 Apple List。
- `inbox` 表示收集箱，是统一命名，不再使用 `index`。

---

## 八、删除策略

删除是高风险动作，本轮采用保守策略。

## 8.1 GTD 删除
当 GTD 任务被 delete：
- 从主清单隐藏
- 从 done / weekly review 隐藏
- 不要求 Apple 侧立即硬删除

建议：
- 第一版先不做 Apple 硬删除
- 由后续版本再决定是否需要同步删除

## 8.2 Apple 删除
当用户在 Apple 中删除 reminder：
- 本轮不回写 GTD 删除
- 默认忽略
- 不把 Apple 删除当作主库删除依据

原因：
- Apple 删除太容易误操作
- 一旦回写主库，风险过高

---

## 九、同步触发与运行方式

## 9.1 不做服务端
本轮明确不引入：
- 独立服务端
- 公网 API
- Webhook 服务
- 独立同步中心

## 9.2 运行方式
采用：
- Linux / OpenClaw 端维护主库并 push Git
- Mac 本地定时 `git pull`
- Mac 本地执行桥接脚本

## 9.3 Mac 桥接执行流程
推荐流程：
1. Git pull 最新主库
2. 执行 GTD -> Apple 同步
3. 导出 Apple completed 事件
4. 回写 GTD 主库
5. 如主库有变化，再 git push

---

## 十、系统模块要求

## 10.1 主库层
必须保留：
- `data/tasks.json`

要求：
- 唯一事实源
- 所有业务状态最终写回这里

## 10.2 视图层
要求继续保留并自动生成：
- `today.md`
- `inbox.md`
- `done.md`
- `weekly/review-latest.md`
- `matrix/*.md`

要求：
- 这些文件全部由主库渲染产生
- 不允许手工长期作为事实源修改

## 10.3 同步层
同步层应被收敛为 3 个逻辑模块：

### 模块 1：push_to_apple
职责：
- 将主库变更推送到 Apple Reminders

### 模块 2：pull_completed_from_apple
职责：
- 从 Apple 导出 completed 事件

### 模块 3：apply_completed_to_gtd
职责：
- 将 completed 事件落回主库并刷新视图

---

## 十一、验收标准

## 11.1 状态语义验收
满足以下条件即通过：

1. 用户将任务标 done 后：
   - 主清单不再显示该任务
   - `done.md` 中可看到该任务
   - `weekly/review-latest.md` 中可统计该任务

2. 用户 delete 任务后：
   - 主清单不再显示该任务
   - `done.md` 中也不应显示该任务
   - 不把 delete 当作 done

## 11.2 GTD -> Apple 同步验收
满足以下条件即通过：

3. 新建 GTD 任务后，Apple 中可看到对应 reminder
4. 修改 GTD 任务标题后，Apple 中可看到对应更新
5. 将 GTD 任务标 done 后，Apple 中对应任务可变为 completed
6. reopen 后，Apple 中对应任务恢复为未完成（如技术可行）
7. 不会因重复同步生成多个 reminder

## 11.3 Apple -> GTD completed 回写验收
满足以下条件即通过：

8. 用户在 Apple 中勾选完成后，对应 GTD 任务会被标记 done
9. 若同一 completed 事件重复导入，不会重复污染主库
10. 若任务已 done，再次消费相同 completed 事件不会出错

## 11.4 边界验收
满足以下条件即通过：

11. Apple 改标题，不会自动污染 GTD 主库
12. Apple 改备注，不会自动污染 GTD 主库
13. Apple 删除，不会自动删除 GTD 主库任务
14. 系统不依赖独立服务端即可运行

---

## 十二、明确不做的事项

本轮明确不做：
- 独立服务端
- 完整双向字段同步
- 标题双向回写
- note 双向回写
- category / bucket / quadrant / tag 双向回写
- Apple 删除回写 GTD 删除
- 复杂冲突处理中心
- 多终端复杂一致性系统

这部分必须明确冻结，避免需求蔓延。

---

## 十三、建议实施顺序

### Step 1：统一语义
- done vs delete 明确分开
- 主清单只显示 open
- done 进入完成区

### Step 2：稳住 GTD -> Apple
- 先保证单向自动同步可用
- 再做 completed 回写

### Step 3：上线 completed 回写
- 只做 completed -> done
- 做幂等与去重

### Step 4：运行观察
- 至少稳定跑 2~4 周
- 再评估是否需要更多能力

---

## 十四、版本建议

建议把这一轮定义为：

### 产品版本
- `requirements v1.1`

### 实施版本（可选映射）
- `v0.2.3`：状态语义 + 主清单规则收口
- `v0.4.0-a 收敛版`：单向同步 + completed 回写稳定化

---

## 十五、最终定义

本轮版本最终定义如下：

> **这是一个以 GTD 主库为核心、由 Mac 本地桥接 Apple Reminders 的轻量同步系统。主通道是 GTD -> Apple，唯一允许的回写是 Apple completed -> GTD done。done 与 delete 严格区分，不做独立服务端，不做复杂全字段双向同步。**
