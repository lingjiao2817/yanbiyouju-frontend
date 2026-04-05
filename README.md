# AI 检测小助手

> 面向内容创作者的 AI 生成内容检测与改进建议工具  
> 帮助用户识别文本中疑似 AI 生成的部分，提供可操作的修改建议和真实文献推荐，提升内容原创性与可信度。

**适用场景**：大学生论文自查 · 自媒体"去 AI 味"润色 · 职场报告人性化改写

---

## 功能模块


| 模块   | 功能                                |
| ---- | --------------------------------- |
| 输入处理 | 文本粘贴 / PDF / DOCX / TXT 上传，统一分段   |
| 检测引擎 | 7 项统计特征评分 + 可选 GPT2 困惑度（40% 权重）   |
| 改写建议 | 检测原因分析 + 3~5 条具体建议 + 改写示例         |
| 文献推荐 | 基于段落关键词调用 Semantic Scholar 推荐真实论文 |
| 历史记录 | SQLite 持久化，支持随时回看历史检测结果           |
| 报告导出 | 一键导出 Markdown 格式完整报告              |


---

## 技术架构

```
frontend/   Vue 3 + Vite（端口 5173）
backend/    Python Flask（端口 5000）
            ├─ checker.py            统计特征评分引擎
            ├─ perplexity_service.py 可选 GPT2 困惑度
            ├─ llm_service.py        改写建议（本地模板 / ZhipuAI / DeepSeek）
            ├─ crossref_service.py   Semantic Scholar 文献推荐
            ├─ document_parser.py    PDF / DOCX 解析（含 OCR 兜底）
            └─ database.py           SQLite 历史记录
```

---

## 快速启动

### 1. 后端

```bash
cd backend
pip install -r requirements.txt
python app.py
# → http://127.0.0.1:5000
```

Windows（Anaconda）：

```powershell
cd backend
C:\Users\zyb86\anaconda3\python.exe -m pip install -r requirements.txt
C:\Users\zyb86\anaconda3\python.exe app.py
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
# → http://127.0.0.1:5173
```

打开 `http://localhost:5173` 即可使用。Vite 已配置代理，前端的 `/api` 请求自动转发到 Flask。

---

## 可选功能配置

### 启用困惑度检测（更精准，需额外约 400MB 空间）

```bash
pip install transformers torch
ENABLE_PERPLEXITY=1 python app.py
```

启用后评分权重自动切换为：**困惑度 40% + 统计特征 60%**。

### 接入大模型（更智能的改写建议）

#### 智谱 GLM-4-Flash（推荐，免费额度）

```bash
pip install zhipuai
AI_SUGGESTION_PROVIDER=zhipuai ZHIPUAI_API_KEY=your_key python app.py
```

#### DeepSeek

```bash
AI_SUGGESTION_PROVIDER=deepseek DEEPSEEK_API_KEY=your_key python app.py
```

未配置时默认使用**本地模板**，无需任何 API Key 即可运行。

### 关闭在线文献推荐（离线演示）

```bash
DISABLE_PAPER_SEARCH=1 python app.py
```

---

## 检测特征说明


| 特征         | 说明             | 权重（纯统计模式） |
| ---------- | -------------- | --------- |
| 句长方差       | 越小越均匀，AI 特征越明显 | 22%       |
| 连接词密度      | "首先/其次/因此"密度   | 18%       |
| 词汇多样性（TTR） | 越低重复越多         | 16%       |
| 套话数量       | "在当今社会"等套话     | 14%       |
| 标点多样性      | 越单调越像 AI       | 12%       |
| 模板短语       | "综上所述"等模板      | 10%       |
| 字词重复率      | 字符级重复比例        | 8%        |
| 困惑度（可选）    | 对语言模型的预测难度     | 40%（启用后）  |


风险等级基于文档内相对分布判定，避免固定阈值的局限性。

---

## API 端点


| 方法   | 路径                         | 功能          |
| ---- | -------------------------- | ----------- |
| GET  | `/api/health`              | 健康检查        |
| GET  | `/api/checks`              | 获取历史记录      |
| GET  | `/api/checks/:id`          | 获取单条记录详情    |
| POST | `/api/checks`              | 提交文本/文件进行检测 |
| GET  | `/api/checks/:id/comments` | 获取点评        |
| POST | `/api/checks/:id/comments` | 添加点评        |


---

## 项目结构

```
yanbiyouju-assistant/
├── backend/
│   ├── app.py                     Flask 入口
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py            Flask 应用工厂
│       ├── routes.py              RESTful API
│       ├── checker.py             核心检测引擎
│       ├── perplexity_service.py  可选困惑度模块（新增）
│       ├── llm_service.py         改写建议生成（已升级）
│       ├── crossref_service.py    Semantic Scholar 文献推荐
│       ├── document_parser.py     文档解析
│       └── database.py            数据层
├── frontend/
│   ├── src/
│   │   ├── App.vue                主应用（蓝紫 UI 风格）
│   │   ├── main.js
│   │   └── styles.css             全局样式
│   ├── index.html
│   └── vite.config.js
├── docs/
│   ├── TEAM_HANDOFF.md
│   └── ACCURACY_VALIDATION.md
└── README.md
```

---

## 信息

- **目标**：完整技术闭环 + 演示效果 + 创新价值
- **核心亮点**：多维特征融合 + 可选困惑度 + 大模型改写建议 + 真实文献推荐

---

## 免责声明

本工具基于统计特征分析，结果仅供创作前自查参考，**不等同于学校或平台的官方 AI 检测结论**。