# Server 模块

重构后的后端按 websocket / services / providers / infrastructure / utils 分层。

- 启动：`python -m server.app`
- WebSocket 入口：`server/websocket/server.py`
- 缓存目录保持不变：`backend/cache`

能力矩阵见 `server/support_matrix.py`。
