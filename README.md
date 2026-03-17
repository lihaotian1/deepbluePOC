# API610 询价文件智能比对系统

React + FastAPI Web 项目，支持询价文件章节切分、在线编辑、流式知识库比对、Excel 导出，以及知识库文件管理。

## 目录结构

- `backend/` FastAPI 后端
- `frontend/` React 前端
- `data/知识库/标准化配套知识库.json` 标准知识库
- `data/input/` 示例输入文件目录

## 核心能力

1. 上传 PDF/MD/TXT/DOCX，并按章节切分为有序内容块。
2. 前端以 Markdown 预览 + 编辑方式审阅每一段。
3. 点击“比对知识库”后，后端按段流式处理：
   - 先判定所属知识库分类；
   - 再判定分类条目语义一致性；
   - 命中输出条目 + 类型（P/A/B/C），否则输出“其他”。
4. 比对结果可导出为 Excel。
5. 左侧导航支持主页 / 知识库切换，并显示 `data/logo/logo.png` 作为系统 logo。
6. 知识库页面支持读取 `data/知识库/*.json`，兼容两种格式：
   - `{分类: [{条目: 值}]}`
   - `{key: value}`
7. 知识库页面支持新建/删除文件、结构化编辑、搜索和分页。

## 本地启动

### 1) 后端

```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -r backend/requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

工作目录切到 `backend/` 后运行上面的 `uvicorn` 命令。

### 2) 前端

```bash
cd frontend
npm install
npm run dev
```

默认前端地址 `http://localhost:5173`，默认请求后端 `http://localhost:8000/api/v1`。

## 环境变量

复制 `.env.example` 为 `.env`，并填写你的模型配置。

- `OPENAI_BASE_URL` OpenAI 兼容接口地址
- `OPENAI_API_KEY` 模型 key
- `OPENAI_MODEL` 模型名
- `OPENAI_TIMEOUT` 超时秒数

## Docker 部署

```bash
copy .env.example .env
docker compose up --build
```

- 前端: `http://localhost:5173`
- 后端: `http://localhost:8000`

## 测试与构建

```bash
python -m pytest backend/tests -q
npm --prefix frontend run build
```
