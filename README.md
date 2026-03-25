# 《言必有据》- 大学生课程论文/作业 AI 查证助手

一个面向大学生课程论文、课程作业的事实核查原型系统。它不判断“是不是 AI 写的”，而是专注识别 AI 文本里常见的高风险内容:

- 疑似编造或信息不完整的文献引用
- 疑似未经核实的法条/法规表述
- 缺少来源支撑的统计数据
- 仅靠人名/机构背书的强断言

当前版本是可运行的 MVP，采用离线规则引擎做初筛，适合课程展示、产品原型和后续二次开发。

当前展示版额外包含：

- 核验路径建议：按风险类型给出推荐检索平台和核验动作
- 教师点评：可为每次查证结果追加评语
- 报告导出：前端可一键导出 Markdown 查证报告

## 技术栈

- 后端: Flask + SQLite
- 前端: Vue 3 + Vite
- 数据库: SQLite

## 项目结构

```text
yanbiyouju-assistant/
├─ backend/
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ checker.py
│  │  ├─ database.py
│  │  └─ routes.py
│  ├─ data/
│  ├─ app.py
│  └─ requirements.txt
├─ frontend/
│  ├─ src/
│  │  ├─ App.vue
│  │  ├─ main.js
│  │  └─ styles.css
│  ├─ index.html
│  ├─ package.json
│  └─ vite.config.js
└─ README.md
```

## 启动方式

### 1. 启动后端

```powershell
cd C:\Users\zyb86\PycharmProjects\yanbiyouju-assistant\backend
C:\Users\zyb86\anaconda3\python.exe -m pip install -r requirements.txt
C:\Users\zyb86\anaconda3\python.exe app.py
```

默认地址: `http://127.0.0.1:5000`

### 2. 启动前端

```powershell
cd C:\Users\zyb86\PycharmProjects\yanbiyouju-assistant\frontend
npm install
npm run dev
```

默认地址: `http://127.0.0.1:5173`

Vite 已配置代理，前端访问 `/api` 时会自动转发到 Flask。

## 核心接口

- `GET /api/health` 健康检查
- `GET /api/rules/meta` 获取当前规则库版本和条目数量
- `GET /api/checks` 获取最近查证记录
- `GET /api/checks/<id>` 获取单条查证详情
- `POST /api/checks` 提交文本并生成查证结果
- `GET /api/checks/<id>/comments` 获取点评列表
- `POST /api/checks/<id>/comments` 添加教师点评

## 规则库接入

规则库目录：

```text
backend/rules/
├─ rules.json
└─ rules.sample.json
```

说明：

- `rules.json` 是正式规则库，优先读取
- `rules.sample.json` 是模板和兜底文件
- 当前后端会自动读取规则库，不需要手动改代码

支持的规则字段：

```json
{
  "version": "team-template-v1",
  "fake_authors": ["张宇恒"],
  "fake_journals": ["国际生成式人工智能研究学报"],
  "fake_publishers": ["未来教育国际出版社"],
  "suspicious_doi_patterns": ["10\\.1234/[A-Z]{3,}-FAKE\\d+"],
  "suspicious_phrases": ["权威研究一致证明"],
  "suspicious_keywords": ["待查"]
}
```

## 协作说明

队友交接文档见：

```text
docs/TEAM_HANDOFF.md
```

### 示例请求

```json
{
  "title": "人工智能课程论文草稿",
  "text": "据《人工智能赋能高校思政教育研究》(李明，2024)指出，大学生使用生成式AI的比例已达67%。《教育数字化促进条例》第12条明确规定..."
}
```

## 当前规则引擎说明

系统会优先标记这些高风险信号:

- 出现论文/书名，但正文没有作者、期刊、年份、DOI 等关键信息
- 出现“研究表明/数据显示/报告指出”，但没有可靠来源
- 出现具体法条或法规结论，但没有版本、发布机关或官方出处
- 出现具体学者/高校/机构结论，但没有可追溯引用
- 参考文献行缺少年份、刊名、页码、出版社等关键字段

这不是最终的“真假判定”，而是帮助用户快速锁定需要手工复核的部分。

## 下一步适合扩展的方向

- 接入知网、Crossref、Google Scholar、国家法律法规数据库等外部检索
- 支持真正的文献去重与 DOI 校验
- 接入大模型做“解释性核查”
- 支持导出 PDF 查证报告
- 增加用户系统、作业项目夹和教师点评功能
