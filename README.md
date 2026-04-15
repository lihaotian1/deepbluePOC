# API610 询价文件智能比对系统

React + FastAPI Web 项目，面向“甲方询价要求 vs 我方标准化配套条目”的整篇文档比对场景，支持全文上传、模型比对、P/A/B/C 分类筛选、人工审核、Excel 导出，以及标准化配套知识库维护。

## 当前产品形态

系统当前采用“整篇询价文件 + 标准化配套知识库”的单知识库工作流：

1. 上传 PDF/MD/TXT/DOCX，后端抽取整篇文本。
2. 将整篇询价文件全文与 `标准化配套知识库.json` 一次性交给大模型。
3. 模型只输出与标准化配套条目在讨论“同一件事”的命中结果。
4. 每条结果包含：
   - 章节标题
   - 询价文件原文段落或句子
   - 知识库标准化配套条目的原文
   - 大模型总结的差异结论
   - 分类（P/A/B/C）
5. 前端以浅色表格主视图展示结果，支持 `ALL / P / A / B / C` 筛选。
6. 用户可在结果抽屉中填写审核意见、标记已审、删除结果、翻译命中原文句段。
7. 审核结果可提交并导出为 Excel。
8. 知识库页面仅维护 `标准化配套知识库.json`。

## 目录结构

- `backend/` FastAPI 后端
- `frontend/` React 前端
- `data/知识库/标准化配套知识库.json` 标准化配套知识库
- `data/input/` 示例输入文件目录
- `docs/manuals/2026-03-19-user-manual-home-analysis-review-export.md` 当前操作手册

## 本地启动

### 1) 后端

```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

默认后端地址：`http://localhost:8000`

### 2) 前端

```bash
cd frontend
npm install
npm run dev
```

默认前端地址：`http://localhost:5173`

默认前端请求后端地址：`http://localhost:8000/api/v1`

## 环境变量

复制 `.env.example` 为 `.env`，并填写模型配置：

- `OPENAI_BASE_URL` OpenAI 兼容接口地址
- `OPENAI_API_KEY` 模型 key
- `OPENAI_MODEL` 模型名
- `OPENAI_TIMEOUT` 超时秒数

说明：

- 当前产品将整篇文档直接交给模型处理。
- 如果上传文档超过当前模型上下文上限，后端会直接返回错误，不会自动拆分、摘要或降级处理。

## Docker 部署

### 启动前准备

```bash
copy .env.example .env
```

根据实际模型服务补齐 `.env` 中的参数后执行：

```bash
docker compose up --build
```

### 部署结果

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

### Docker 说明

- `backend` 容器启动 FastAPI 服务，暴露 `8000` 端口。
- `frontend` 容器构建并托管静态页面，暴露 `5173` 端口。
- 前端默认通过 `/api/v1` 访问后端接口。

## 主要页面说明

### 主页

- 上传完整询价文件
- 启动全文智能比对
- 查看结果表格与日志
- 按 `P/A/B/C` 分类筛选
- 在右侧抽屉中审核单条结果
- 提交审核、导出 Excel

### 知识库页

- 仅编辑 `标准化配套知识库.json`
- 支持分类、条目、类型值（P/A/B/C）维护
- 支持搜索、分页、保存

## 测试与构建

```bash
python -m pytest backend/tests tests -q
node --test frontend/tests/*.test.ts
npm --prefix frontend run build
```

## 操作文档

- 操作手册：[`docs/manuals/2026-03-19-user-manual-home-analysis-review-export.md`](docs/manuals/2026-03-19-user-manual-home-analysis-review-export.md)
