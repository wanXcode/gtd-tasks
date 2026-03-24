# GTD v2.0 Phase 1 部署说明

## 快速开始

### 1. 环境准备

```bash
cd gtd-tasks

# 创建虚拟环境
python3 -m venv .venv-server

# 激活虚拟环境
source .venv-server/bin/activate

# 安装依赖
pip install -r server/requirements.txt
```

### 2. 启动服务

```bash
# 使用默认配置（端口 8000）
python3 -m server.app

# 或使用自定义端口
python3 -c "from server.app import run; run(port=8001)"
```

服务启动后会自动初始化数据库 `data/gtd.db`。

### 3. 验证服务

```bash
# 健康检查
curl https://gtd.5666.net/health
# 预期返回: {"ok": true}

# 获取任务列表
curl https://gtd.5666.net/api/tasks

# 获取变更记录
curl https://gtd.5666.net/api/changes
```

### 4. 导入现有数据

```bash
# 从 data/tasks.json 导入到服务端数据库
source .venv-server/bin/activate
python3 scripts/import_tasks_to_server.py

# 同时写入变更记录（可选）
python3 scripts/import_tasks_to_server.py --write-changes
```

## 核心功能验证

### 任务 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/tasks` | GET | 任务列表（支持过滤） |
| `/api/tasks` | POST | 创建任务 |
| `/api/tasks/{id}` | GET | 获取单个任务 |
| `/api/tasks/{id}` | PATCH | 更新任务 |
| `/api/tasks/{id}/done` | POST | 完成任务 |
| `/api/tasks/{id}/reopen` | POST | 重开任务 |
| `/api/tasks/{id}` | DELETE | 删除任务（软删除） |
| `/api/changes` | GET | 获取变更记录 |
| `/api/sync/clients/{id}/ack` | POST | 确认同步游标 |

### 过滤参数

GET `/api/tasks` 支持以下参数：
- `status`: open/done/cancelled/archived
- `bucket`: today/tomorrow/future/archive
- `category`: inbox/project/next_action/waiting_for/maybe
- `tag`: 标签名称
- `text`: 标题/备注搜索
- `include_deleted`: true/false
- `limit`: 数量限制

### CLI 使用

```bash
# 本地模式（默认）
python3 scripts/task_cli.py list --limit 10
python3 scripts/task_cli.py add "新任务"

# API 模式
GTD_TASK_BACKEND=api python3 scripts/task_cli.py list
python3 scripts/task_cli.py --backend api add "API任务"

# NLP 录入
python3 scripts/nlp_capture.py "明天下午3点开会" --mode preview
python3 scripts/nlp_capture.py "明天下午3点开会" --mode apply --backend api
```

## 常见问题

### Q1: 服务启动失败，端口被占用

```bash
# 查找占用端口的进程
lsof -i :8000

# 使用其他端口启动
python3 -c "from server.app import run; run(port=8001)"
```

### Q2: ImportError: No module named 'xxx'

```bash
# 确保在虚拟环境中
source .venv-server/bin/activate

# 重新安装依赖
pip install -r server/requirements.txt
```

### Q3: 数据库权限错误

```bash
# 确保 data 目录存在且有写入权限
mkdir -p data
chmod 755 data
```

### Q4: CLI 报错找不到 backend

```bash
# 检查环境变量
export GTD_TASK_BACKEND=local  # 或 api

# 或在命令行指定
python3 scripts/task_cli.py --backend local list
```

### Q5: 导入后数据不一致

```bash
# 重新导入（清空旧数据）
python3 scripts/import_tasks_to_server.py

# 或追加模式（保留旧数据）
python3 scripts/import_tasks_to_server.py --append
```

## 项目状态

### 已完成 ✅

1. **服务端骨架**: FastAPI 服务可启动
2. **数据库层**: SQLite + WAL 模式，自动建表
3. **Schema 定义**: TaskCreate/TaskUpdate/TaskOut/ChangeOut
4. **Repository 层**: TaskRepository 完整实现
5. **Service 层**: TaskService + ChangeService
6. **任务 API**: CRUD + done/reopen/delete
7. **Changes API**: 增量同步 + ack 游标
8. **导入脚本**: tasks.json -> SQLite
9. **CLI 抽象**: LocalJsonTaskRepository + ApiTaskRepository
10. **NLP 支持**: preview + apply 双模式

### 已知限制 ⚠️

1. **move/tag API 模式**: 暂未完全实现，local 模式可用
2. **批量操作**: 服务端暂未提供批量 update 接口
3. **Apple 同步**: Phase 1 未改造，仍走本地 JSON 链路
4. **WebSocket**: Phase 1 不包含实时推送

### 下一步建议

1. 稳定运行服务端主库
2. 完成 move/tag 的 API 实现
3. 实现 pull_tasks_cache.py 增量刷新
4. 评估 CLI 默认 backend 切换为 api
5. Phase 2: Apple 同步改造

## 目录结构

```
gtd-tasks/
├── server/              # 服务端代码
│   ├── app.py          # HTTP 服务入口
│   ├── db.py           # 数据库连接
│   ├── models.py       # 数据模型
│   ├── schemas.py      # Pydantic Schema
│   ├── repository.py   # 数据访问层
│   ├── routes/         # 路由定义
│   └── services/       # 业务逻辑层
├── scripts/            # CLI 脚本
│   ├── task_cli.py     # 命令行工具
│   ├── nlp_capture.py  # NLP 录入
│   ├── task_repository.py # Repository 抽象
│   ├── import_tasks_to_server.py # 导入脚本
│   └── pull_tasks_cache.py # 缓存导出（脚手架）
├── data/               # 数据目录
│   ├── tasks.json      # 本地 JSON 主库
│   └── gtd.db          # SQLite 数据库
└── .venv-server/       # Python 虚拟环境
```

## 测试命令

```bash
# 验证所有 Python 文件语法
cd gtd-tasks
source .venv-server/bin/activate
python3 -m py_compile server/*.py server/**/*.py scripts/*.py

# 验证核心链路
python3 << 'EOF'
from server.db import init_db
from server.services.task_service import TaskService
from server.services.change_service import ChangeService
from server.schemas import TaskCreate

init_db()
ts = TaskService()
cs = ChangeService()

# 创建任务
t = ts.create_task(TaskCreate(title='测试'))
assert t['id']

# 列表查询
assert ts.list_tasks()['total'] >= 1

# changes
assert len(cs.list_changes()['items']) >= 1

print('All tests passed!')
EOF
```

---

**结论**: Phase 1 服务端主库 MVP 已完成，可部署运行。核心 API 和 CLI 链路已验证通过。
