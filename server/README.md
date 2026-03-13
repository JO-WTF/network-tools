# Backend Server

本目录已按分层架构重构：
- transport: WebSocket 协议接入层
- services: 业务编排层
- providers: 第三方地图能力适配层
- infrastructure: HTTP/缓存/日志基础设施

## 当前可用能力
- custom provider: geocode、route（需要先 fetch token，再携带 Authorization 调接口）
- mapbox/here provider: 目录与接口已预留，待逐步实现

## 启动
```bash
python -m server.app
```
