# 《言必有据》队友协作说明

这份文档给钟同学、万同学、李同学直接对接使用。目标不是“谁等谁”，而是并行推进。

## 1. 当前项目状态

当前主项目已经具备：

- Flask 后端、Vue 前端、SQLite 数据库
- 文本提交与查证结果返回
- 历史记录、教师点评、报告导出
- 离线规则引擎
- JSON 规则库接入机制

项目路径：

```text
C:\Users\zyb86\PycharmProjects\yanbiyouju-assistant
```

前端运行地址：

```text
http://127.0.0.1:5173
```

后端运行地址：

```text
http://127.0.0.1:5000
```

## 2. 三位同学怎么衔接

### 钟同学负责

- 主线开发
- 后端接口
- 规则引擎接入
- Crossref / 大模型 / 实体提取等模块预留
- 总体联调

### 万同学负责

- 维护规则库 JSON 内容
- 提供典型测试文本
- 整理假作者、假期刊、假 DOI 规则
- 补充作品文档和技术方案文字材料

### 李同学负责

- 前端视觉优化
- 交互细节、加载动画、错误提示
- 响应式适配
- 页面测试与 bug 反馈

协作原则：

- 钟同学先把“接口、规则插槽、项目骨架”搭好
- 万同学往 JSON 规则库里填内容
- 李同学在不破坏接口的前提下调整前端展示

不要串行等待，不要“等全部做完再合并”。

## 3. 给万同学的交接

### 她要改的文件

```text
backend/rules/rules.json
```

### 规则库字段格式

```json
{
  "version": "team-template-v1",
  "fake_authors": ["张宇恒", "赵思远"],
  "fake_journals": ["国际生成式人工智能研究学报"],
  "fake_publishers": ["未来教育国际出版社"],
  "suspicious_doi_patterns": ["10\\.1234/[A-Z]{3,}-FAKE\\d+"],
  "suspicious_phrases": ["权威研究一致证明"],
  "suspicious_keywords": ["待查", "内部资料"]
}
```

### 她交给你的内容

- 正式版 `rules.json`
- 10 到 20 条测试样例文本
- 每条规则的文字说明

### 你这边会怎么接

- 后端每次查证都会自动读取 `backend/rules/rules.json`
- 如果 `rules.json` 缺失，会自动回退到 `rules.sample.json`
- 命中规则库后，结果里会显示“命中规则库中的疑似虚构作者 / 期刊 / DOI / 高风险表述”

### 你和万同学的最小协作动作

1. 你先把这份 JSON 模板发给她
2. 她按模板填
3. 她把新的 `rules.json` 发你，或直接替换仓库中的同名文件
4. 你本地重启后端，立即可以验证效果

## 4. 给李同学的交接

### 她主要改的文件

```text
frontend/src/App.vue
frontend/src/styles.css
```

### 她尽量不要改的文件

```text
backend/app/checker.py
backend/app/routes.py
backend/app/database.py
```

### 当前可用接口

- `GET /api/health`
- `GET /api/rules/meta`
- `GET /api/checks`
- `GET /api/checks/<id>`
- `POST /api/checks`
- `GET /api/checks/<id>/comments`
- `POST /api/checks/<id>/comments`

### `POST /api/checks` 请求体

```json
{
  "title": "人工智能课程论文草稿",
  "text": "待核查文本"
}
```

### 返回结果里她会用到的字段

- `result.overview`
- `result.flags`
- `result.paragraphs`
- `result.reference_checks`
- `result.verification_routes`
- `result.recommended_actions`
- `result.rules_summary`
- `comments`

### 她交给你的内容

- 样式优化后的前端文件
- 发现的 bug 列表
- 页面交互建议

## 5. 推荐协作方式

最优先：`Git`

建议做法：

1. 钟同学维护主分支
2. 万同学只改 `backend/rules/rules.json` 和文档
3. 李同学只改 `frontend/src/*`
4. 合并前先跑一次前端和后端

如果暂时不用 Git，次选方案：

1. 钟同学每天发一次“主版本压缩包”
2. 万同学只回传 `rules.json`
3. 李同学只回传 `App.vue` 和 `styles.css`

不建议多人同时改整项目压缩包，容易互相覆盖。

## 6. 钟同学下一步优先级

### 现在立刻做

1. 让万同学按模板补正式 `rules.json`
2. 让李同学开始前端美化和测试
3. 你继续做模块插槽

### 你下一批可继续开发的模块

- `entity_service.py`
  - 实体提取模块占位
- `crossref_service.py`
  - Crossref 查询占位
- `llm_service.py`
  - 语义核查占位

建议都先做成“可以返回 mock 结果”的结构，先把流程串起来。

## 7. 演示时怎么说

你可以这样讲：

1. 系统先接收 AI 生成的作业文本
2. 后端基础规则会先做首轮风险筛查
3. 再叠加规则库 JSON，对假作者、假期刊、假 DOI 做定向命中
4. 前端把高风险句子、参考文献、核验路径和教师点评统一展示
5. 后续可以继续接 Crossref 和大模型 API，把系统从“规则初筛”升级到“检索加语义复核”

## 8. 你可以直接发给队友的话

### 发给万同学

“你不用等我开发完。你现在直接按 `backend/rules/rules.json` 这个格式整理假作者、假期刊、假 DOI 和测试文本，给我 JSON 就行，我这边已经把读取逻辑接好了。”

### 发给李同学

“你现在可以直接接前端了，主要改 `frontend/src/App.vue` 和 `frontend/src/styles.css`。接口已经稳定，重点做样式优化、加载动画、错误提示和测试反馈，后端逻辑你先不用碰。”
