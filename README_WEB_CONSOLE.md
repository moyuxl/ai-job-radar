# Web 操作台使用说明

## 功能概述

Web 操作台提供了一个可视化的界面来管理 Boss 直聘职位爬取任务，支持：

- ✅ 可视化任务配置
- ✅ 实时进度跟踪
- ✅ 日志实时显示
- ✅ Top10 职位推荐
- ✅ 结果文件下载

## 启动方式

### 方式一：使用启动脚本（推荐）

```bash
python start_web_console.py
```

### 方式二：直接运行

```bash
python web_console.py
```

### 方式三：使用 uvicorn

```bash
uvicorn web_console:app --host 0.0.0.0 --port 8001
```

## 访问地址

启动后，在浏览器中访问：

```
http://localhost:8001
```

## 使用流程

### 1. 配置搜索条件

在 Web 界面中填写：
- **职位关键词**：必填，例如 "Python开发"、"AI产品经理"
- **城市代码**：可选，默认 "100010000"（全国）
- **学历代码**：可选，例如 "203"（本科）
- **工作经验代码**：可选，默认 "101"（不限经验）
- **薪资代码**：可选
- **最大页数**：1-20，默认 5
- **爬取详情页**：是否爬取职位描述

### 2. 启动任务

点击 "🚀 开始抓取" 按钮，系统会：
1. 立即返回任务ID
2. 在后台启动爬虫任务
3. 开始显示实时进度和日志

### 3. 监控进度

页面会每 2 秒自动刷新，显示：
- **任务状态**：空闲/运行中/完成/失败
- **进度条**：当前进度百分比
- **日志窗口**：实时日志输出
- **结果文件**：完成后显示文件路径

### 4. 查看结果

任务完成后：
- **下载文件**：点击结果文件链接下载 Excel
- **Top10 推荐**：自动显示评分最高的 10 个职位
- **统计信息**：显示成功/失败数量

## API 端点

### 启动爬虫任务

```bash
POST /api/crawl/start
Content-Type: application/json

{
  "keyword": "Python开发",
  "city": "100010000",
  "degree": "203",
  "experience": "101",
  "salary": "",
  "max_pages": 5,
  "crawl_details": true
}
```

响应：
```json
{
  "task_id": "uuid-string",
  "message": "任务已启动"
}
```

### 查询任务状态

```bash
GET /api/task/{task_id}/status
```

响应：
```json
{
  "task_id": "uuid-string",
  "status": "running",
  "progress": {
    "current": 3,
    "total": 5,
    "percentage": 60.0
  },
  "logs": [...],
  "result": {
    "success_count": 0,
    "failed_count": 0,
    "output_file": null
  }
}
```

### 下载结果文件

```bash
GET /api/file/{file_path}
```

### 获取 Top10

```bash
GET /api/top10/{file_path}
```

## 文件结构

```
ai-job-radar2/
├── web_console.py          # Web 操作台主文件
├── task_manager.py         # 任务管理系统
├── crawler_service.py      # 爬虫服务封装
├── task_log_handler.py     # 日志处理器
├── start_web_console.py    # 启动脚本
└── output/                 # 输出目录（自动创建）
```

## 注意事项

1. **浏览器窗口**：爬虫会打开浏览器窗口，请勿关闭
2. **登录**：如果需要登录，请在浏览器中手动登录
3. **任务状态**：任务完成后会停止自动刷新
4. **文件路径**：结果文件保存在 `output/` 目录下
5. **任务清理**：旧任务会在 24 小时后自动清理

## 故障排除

### 任务一直显示"运行中"

- 检查浏览器窗口是否正常
- 查看日志窗口中的错误信息
- 可能需要手动登录 Boss 直聘

### 无法下载文件

- 检查文件路径是否正确
- 确认文件已生成（查看日志）

### Top10 不显示

- 确认任务已完成
- 检查 Excel 文件是否包含"综合评分"列
- 查看浏览器控制台的错误信息

## 技术架构

- **后端**：FastAPI
- **任务管理**：线程 + 内存存储
- **日志系统**：自定义日志处理器
- **前端**：原生 HTML + JavaScript（无框架依赖）
