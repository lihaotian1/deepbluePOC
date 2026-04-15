# API610 智能比对系统部署说明

## 1. 部署前准备

### 1.1 基础环境

- Python 3.12
- Node.js 20+
- Docker Desktop（如使用容器部署）

### 1.2 模型服务配置

在项目根目录复制环境变量模板：

```bash
copy .env.example .env
```

填写以下配置：

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_TIMEOUT`

说明：

- 当前系统采用“整篇文档直接送模型”的方式。
- 若文档长度超出所选模型上下文限制，系统会直接报错，不会自动分段。

## 2. 本地开发部署

### 2.1 启动后端

```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端地址：

- `http://localhost:8000`

### 2.2 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端地址：

- `http://localhost:5173`

前端默认调用：

- `http://localhost:8000/api/v1`

## 3. Docker 部署

### 3.1 构建并启动

```bash
docker compose up --build
```

### 3.2 访问地址

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

### 3.3 容器说明

- `backend`
  - 基于 `backend/Dockerfile`
  - 启动 FastAPI 服务
  - 监听 `8000`
- `frontend`
  - 基于 `frontend/Dockerfile`
  - 构建 Vite 前端并通过 Nginx 提供静态服务
  - 对外暴露 `5173`

## 4. 部署后检查

### 4.1 服务检查

浏览器访问：

- 前端首页：`http://localhost:5173`
- 后端健康检查：`http://localhost:8000/health`

期望健康检查返回：

```json
{"status":"ok"}
```

### 4.2 功能检查

部署完成后建议至少验证以下流程：

1. 上传一份 PDF/MD/TXT/DOCX 文件。
2. 成功显示全文上传完成状态。
3. 点击“开始智能分析”后，日志区出现全文比对过程。
4. 结果表格显示命中结果。
5. `ALL / P / A / B / C` 筛选可正常工作。
6. 打开结果抽屉，填写审核意见并标记已审。
7. 成功提交审核。
8. 成功导出 Excel。

## 5. 当前部署限制

- 当前仅支持 `标准化配套知识库.json` 参与比对。
- 当前不支持多知识库切换。
- 当前不支持文档在线编辑。
- 当前不显示未命中内容，因此没有 `OTHER` 分类。
- 当前会话状态保存在内存中，后端服务重启后已上传文档和比对结果会丢失。
