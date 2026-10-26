#!/bin/bash
# 三条通道轮播测试：每条 20 秒，共 3 轮。屏幕表现 + 时间戳对照即可判定。
API='http://127.0.0.1:8655/api/strip'
for round in 1 2 3; do
  for ch in static35 smooth eco; do
    if [ "$ch" = "static35" ]; then BODY='{"mode":"clock","color":"00FFC8","via":"static35"}'
    else BODY="{\"mode\":\"clock\",\"color\":\"00FFC8\",\"refresh\":\"$ch\"}"; fi
    curl -s --noproxy '*' -X POST "$API" -H 'Content-Type: application/json' -d "$BODY" > /dev/null
    echo "[$(date '+%H:%M:%S')] 第${round}轮  通道=$ch  持续20秒"
    sleep 20
  done
done
echo "[$(date '+%H:%M:%S')] 测试结束"
