#!/bin/bash
# 飞书小三通道 - 使用服务端 API 启动脚本

export GTD_TASK_BACKEND=api
export GTD_API_BASE_URL=https://gtd.5666.net

# 运行飞书 bot（假设入口是 nlp_capture.py）
cd "$(dirname "$0")/.."
python3 scripts/nlp_capture.py "$@"
