# PR9：视觉请求缓存、并发去重与耗时统计

> 在不改变现有 Doubao 视觉识别和 Qwen 实时语音架构的前提下，减少重复模型调用，记录真实处理耗时，提高系统稳定性并控制成本。

## 1. 目标

- 减少重复调用视觉模型（同一图片 + 同一问题短时间内只调用一次）
- 解决用户快速重复点击或 Qwen 工具并发触发的重复请求
- 记录真实处理耗时，便于排查性能问题
- 缓存与去重对所有视觉分析请求**统一生效**（普通 HTTP 接口和 Qwen 工具）
- 保持现有功能完全正常
- 严格控制：图片不落盘、API Key 不外泄、日志不输出 base64

## 2. 架构

新增统一层 `backend/services/vision_service.py`，所有视觉分析请求都走它：

```text
POST /api/vision-dialogue  ─┐
                            ├─►  VisionService.analyze()
Qwen tool analyze_current_frame ─┘        │
                                          ├─► 缓存查询（SHA-256 + 标准化问题）
                                          ├─► in-flight 等待（如果有并发）
                                          └─► call_vision_model (Doubao)
```

**关键**：
- `vision_model.py` 仍然负责真正调用豆包，**不修改**
- `vision_service.py` 负责缓存 / 去重 / 标准化 / 计时 / 失败处理
- 普通接口和 Qwen 工具调用**共享同一份缓存和去重池**

## 3. 缓存 Key

```
SHA-256(image_bytes) + "|" + normalize(question)
```

缓存 Key 形如：

```
v1|8b4f6e2c1a...|我手里 拿的 是什么
```

### 问题标准化规则

1. 去首尾空白
2. 合并连续空白字符
3. 英文字母转小写（不影响中文）
4. 不改变中文内容

这样 `"Hello   WORLD"` 和 `"hello world"` 是同一个 key；
`"我手里  拿的 是什么"` 和 `"我手里 拿的 是什么"` 也是同一个 key。

### 正确性保证

| 场景 | 缓存命中？ |
|---|---|
| 相同截图 + 相同问题 | ✅ 命中 |
| 相同截图 + 不同问题 | ❌ 不命中（必须重新调用） |
| 不同截图 + 相同问题 | ❌ 不命中 |
| TTL 过期 | ❌ 失效（重新调用） |
| 关闭缓存 (`VISION_CACHE_ENABLED=false`) | ❌ 永远不命中 |
| 模型调用失败 | ❌ 不写入缓存 |

## 4. TTL 与 LRU

环境变量（写入 `backend/.env`，占位写入 `backend/.env.example`）：

```env
VISION_CACHE_ENABLED=true
VISION_CACHE_TTL_SECONDS=300
VISION_CACHE_MAX_ITEMS=100
```

- **TTL 5 分钟**：超过后自动失效，重新调用模型
- **LRU 上限 100 条**：超过后清理最旧记录（用 `OrderedDict.popitem(last=False)`）
- **不缓存的内容**：
  - 图片 Base64 / 原始字节（绝不写入缓存）
  - API Key / Authorization 头
  - 错误响应（超时 / 限流 / 鉴权失败 / 上游 5xx）
  - 模型原始响应体（只保留 `answer` / `model` / `usage`）

## 5. 并发去重（in-flight）

使用 `asyncio.Future` + 进程级 dict 实现：

```python
self._inflight: Dict[str, asyncio.Future] = {}
```

同一缓存 Key 的并发请求：

1. 第一个进入的请求为 **leader**，创建 `Future` 并放入 in-flight
2. 后续相同 Key 的请求为 **waiter**：
   - 等待 leader 的 `Future`
   - leader 成功后**复用结果**（`source: "inflight"`）
   - leader 失败后**得到相同错误**
3. 完成后清理 in-flight 条目

**不会**因为实现去重而阻塞不同图片或不同问题的请求。

测试用例 `test_concurrent_dedup_only_one_model_call` 验证：
5 个并发相同请求 → 只有 1 次真实模型调用 → 1 个 `source: "model"` + 4 个 `source: "inflight"`。

## 6. 耗时统计

使用 `time.perf_counter()` 记录真实耗时（不伪造）：

```json
{
  "timing": {
    "cache_lookup_ms": 1,
    "model_request_ms": 6230,
    "total_ms": 6245
  },
  "cache": {
    "hit": false,
    "source": "model"
  }
}
```

| 场景 | `model_request_ms` | `cache.hit` | `cache.source` |
|---|---|---|---|
| 首次调用 | 真实耗时 | `false` | `"model"` |
| 缓存命中 | 0 | `true` | `"memory"` |
| 并发复用 | 0 | `true` | `"inflight"` |
| 失败 | n/a | n/a | n/a |

**不把缓存命中再次计作模型 Token 消耗**：使用首次真实调用的 `usage`。

## 7. 接口返回

`POST /api/vision-dialogue` 新增字段：

```json
{
  "status": "success",
  "answer": "...",
  "model": "doubao-seed-2.0-pro",
  "question": "我手里拿的是什么？",
  "image": {"content_type": "image/jpeg", "size_bytes": 12345, "sha256": "..."},
  "usage": {"prompt_tokens": 200, "completion_tokens": 80, "total_tokens": 280},
  "cache": {"hit": false, "source": "model"},
  "timing": {"cache_lookup_ms": 1, "model_request_ms": 6230, "total_ms": 6245},
  "request_id": "..."
}
```

## 8. Qwen 工具共享缓存

`backend/services/qwen_realtime.py` 不再直接调用 `call_vision_model`，
改为调用 `VisionService.analyze`：

- 普通 HTTP 提交 + Qwen 工具调用 → 同一个进程级 `VisionService` 单例
- 同一张截图 + 同一问题，**5 分钟内只调用一次豆包**
- 工具完成事件增加字段：
  ```json
  {
    "type": "vision.analyzed",
    "question": "...",
    "output_excerpt": "...",
    "cache_hit": true,
    "source": "memory",
    "timing": {...}
  }
  ```

## 9. 前端展示

### 普通视觉问答区域

新增两行 meta：

```
结果来源：Doubao 实时分析   /   短期缓存（内存）   /   并发复用
总耗时：6.2 秒（模型 6.1 秒）   或   总耗时：3 毫秒（本次未重复调用视觉模型）
```

### Qwen 实时语音区域

工具分析时显示简短提示，4 秒后自动消失：

- `正在分析当前画面（豆包视觉）...`
- `豆包视觉分析完成（6.20 秒，模型 6.10 秒）`
- `已复用最近视觉结果（短期缓存）`
- `已复用最近视觉结果（并发去重）`

不影响主要回答展示。

## 10. 日志脱敏

后端日志可记录：

- `request_id` ✅
- `cache_hit` ✅
- `image_sha256` 前 12 位 ✅
- `total_ms` / `model_request_ms` ✅
- `error_type` ✅

后端日志**绝不**记录：

- API Key / Authorization 头
- 图片 Base64 / 原始字节
- 完整隐私内容

## 11. 限制与权衡

- **进程内缓存**：服务重启后缓存丢失，**不持久化**
- **不区分用户**：本项目无登录，缓存全局共享（题目约束）
- **不实现分布式锁**：单机进程内用 `asyncio.Future` 已经足够
- **不引入 Redis**：保持轻量，符合 MVP 原则
- **不保存图片**：图片 Base64 只在调用时存在于 `analyze()` 局部变量和 Qwen WS 内存中

## 12. 本次未做

- ❌ Redis / 数据库
- ❌ 用户登录 / 限流
- ❌ 长期保存图片或答案
- ❌ 模型自动切换
- ❌ 流式视觉输出
- ❌ 图片相似度（哈希）算法
- ❌ 自动摄像头抽帧
- ❌ UI 大规模重构

## 13. 测试

新增 `tests/test_pr9_cache.py`，14 个用例覆盖：

1. ✅ 问题标准化（去空白 / 保留中文 / 小写）
2. ✅ 图片 SHA-256 确定性
3. ✅ 缓存 Key 格式
4. ✅ 相同图片 + 相同问题 → 第二次命中缓存
5. ✅ 相同图片 + 不同问题 → 重新调用
6. ✅ 不同图片 + 相同问题 → 重新调用
7. ✅ TTL 过期 → 重新调用
8. ✅ 失败不写入缓存
9. ✅ 关闭缓存 → 每次都调用
10. ✅ 并发 5 个相同请求 → 只 1 次真实调用
11. ✅ Leader 失败 → 等待者得到相同错误
12. ✅ LRU 淘汰（max=2）
13. ✅ 耗时字段完整
14. ✅ LRU 行为正确

PR8 测试（7 个）也仍然全部通过，**21/21 passed**。

## 14. 关联

- 依赖 **PR5**（视觉对话接口）
- 依赖 **PR6**（Doubao 视觉模型）
- 兼容 **PR8**（Qwen 实时工具调用）
- 保持 **PR7**（浏览器 TTS）兜底
