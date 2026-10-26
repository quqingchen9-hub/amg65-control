#!/bin/sh
# Claude Code / Codex 钩子 -> AMG65 长条屏编程状态灯
# 用法(在 hooks 配置里): agent_hook.sh claude|codex <事件名>
# 把 stdin 的事件 JSON 原样转发给面板服务; 服务没开也立即返回, 不输出任何东西, 不影响 agent。
AGENT="$1"; EVENT="$2"
curl -s -m 1 -o /dev/null -X POST --data-binary @- \
  "http://127.0.0.1:${AMG65_PORT:-8655}/api/agent?agent=${AGENT}&event=${EVENT}" 2>/dev/null
exit 0
