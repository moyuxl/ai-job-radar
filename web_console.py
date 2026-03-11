"""
Web 操作台：提供爬虫任务的 Web 界面和 API
"""
import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import logging

from task_manager import task_manager, TaskStatus
from crawler_service import start_crawl_task
from analysis_service import start_analysis_task
from api_server import get_available_models

# 导入代码映射
try:
    from city_codes import COMMON_CITIES
    from degree_codes import COMMON_DEGREES
    from experience_codes import COMMON_EXPERIENCES
    from salary_codes import COMMON_SALARIES
    HAS_CODE_MAPS = True
except ImportError as e:
    HAS_CODE_MAPS = False
    logger.warning(f"代码映射未找到: {e}")
    COMMON_CITIES = [('100010000', '全国')]
    COMMON_DEGREES = [('0', '不限')]
    COMMON_EXPERIENCES = [('101', '不限经验')]
    COMMON_SALARIES = [('', '不限薪资')]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI 职位雷达 - Web 操作台", version="1.0.0")

# 静态文件与模板目录
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
templates_dir = Path(__file__).parent / "templates"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class CrawlRequest(BaseModel):
    """爬虫请求模型"""
    keyword: str
    city: str = "100010000"
    degree: str = ""
    experience: str = ""  # 空=不限（显示全部），101=经验不限
    salary: str = ""
    max_pages: int = 1
    crawl_details: bool = True


class AnalysisRequest(BaseModel):
    """分析请求模型"""
    excel_path: str  # 原始数据 Excel 文件路径
    model_id: str = ""  # 模型 ID（supermind/deepseek），空时使用默认


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str
    progress: dict
    logs: list
    result: dict
    error: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: float = 0.0
    waiting_message: Optional[str] = None  # 等待确认时的提示消息
    top10_file: Optional[str] = None  # Top10 摘要文件路径（分析任务）


@app.get("/", response_class=HTMLResponse)
async def index():
    """返回 Web 操作台首页"""
    html_file = templates_dir / "web_console.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.post("/api/crawl/start")
async def start_crawl(request: CrawlRequest):
    """启动爬虫任务"""
    try:
        params = {
            "keyword": request.keyword,
            "city": request.city,
            "degree": request.degree,
            "experience": request.experience,
            "salary": request.salary,
            "max_pages": request.max_pages,
            "crawl_details": request.crawl_details
        }
        
        task_id = start_crawl_task(params, output_dir="output")
        
        return {"task_id": task_id, "message": "任务已启动"}
    except Exception as e:
        logger.error(f"启动任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/task/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取最近日志
    recent_logs = task_manager.get_recent_logs(task_id, limit=20)
    
    return TaskStatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        logs=recent_logs,
        result=task["result"],
        error=task.get("error"),
        start_time=task.get("start_time"),
        end_time=task.get("end_time"),
        duration=task.get("duration", 0.0),
        waiting_message=task.get("waiting_message"),
        top10_file=task["result"].get("top10_file")
    )


@app.post("/api/task/{task_id}/confirm")
async def confirm_task(task_id: str):
    """确认任务继续执行（如登录确认）"""
    success = task_manager.confirm_task(task_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="任务不存在或不在等待确认状态")
    
    return {"message": "确认成功", "task_id": task_id}


@app.get("/api/options/cities")
async def get_city_options():
    """获取城市选项列表"""
    return {"options": [{"code": code, "name": name} for code, name in COMMON_CITIES]}


@app.get("/api/options/degrees")
async def get_degree_options():
    """获取学历选项列表"""
    return {"options": [{"code": code, "name": name} for code, name in COMMON_DEGREES]}


@app.get("/api/options/experiences")
async def get_experience_options():
    """获取工作经验选项列表"""
    return {"options": [{"code": code, "name": name} for code, name in COMMON_EXPERIENCES]}


@app.get("/api/options/salaries")
async def get_salary_options():
    """获取薪资选项列表"""
    return {"options": [{"code": code, "name": name} for code, name in COMMON_SALARIES]}


@app.get("/api/options/models")
async def get_model_options():
    """获取分析模型选项列表（从 .env 已配置的模型）"""
    models = get_available_models()
    return {"options": [{"id": m["id"], "name": m["name"]} for m in models]}


@app.get("/api/file/{file_path:path}")
async def download_file(file_path: str):
    """下载结果文件"""
    import urllib.parse
    file_path = urllib.parse.unquote(file_path)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(file_path)
    )


@app.post("/api/analysis/start")
async def start_analysis(request: AnalysisRequest):
    """启动分析任务"""
    try:
        # 验证文件是否存在
        excel_path = Path(request.excel_path)
        if not excel_path.exists():
            raise HTTPException(status_code=400, detail=f"文件不存在: {request.excel_path}")
        
        task_id = start_analysis_task(
            str(excel_path.absolute()),
            output_dir="output",
            model_id=request.model_id or ""
        )
        
        return {"task_id": task_id, "message": "分析任务已启动"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动分析任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/top10/{file_path:path}")
async def get_top10(file_path: str):
    """获取 Top10 职位数据（支持 Excel 和 JSON）"""
    import urllib.parse
    import pandas as pd
    import json
    
    file_path = urllib.parse.unquote(file_path)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        # 检查文件扩展名
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.json':
            # 读取 JSON 文件（Top10 摘要）
            with open(file_path, 'r', encoding='utf-8') as f:
                top10_data = json.load(f)
            return {"top10": top10_data}
        else:
            # 读取 Excel 文件（兼容旧版本）
            df = pd.read_excel(file_path)
        
        # 如果有综合评分列，按综合评分排序；否则按前10条
        if '综合评分' in df.columns:
            df_sorted = df.sort_values('综合评分', ascending=False).head(10)
        else:
            df_sorted = df.head(10)
        
        # 转换为字典列表
        top10 = []
        for _, row in df_sorted.iterrows():
            job_data = {
                "岗位名称": str(row.get('岗位名称', '')),
                "公司名称": str(row.get('公司名称', '')),
                "工作地点": str(row.get('工作地点', '')),
                "薪资范围": str(row.get('薪资范围', '')),
                "岗位链接": str(row.get('岗位链接', '')),
                "综合评分": float(row.get('综合评分', 0)) if '综合评分' in row else None
            }
            top10.append(job_data)
        
        return {"top10": top10}
    except Exception as e:
        logger.error(f"获取 Top10 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # 使用导入字符串以支持 reload 功能
    uvicorn.run("web_console:app", host="0.0.0.0", port=8001, reload=True)
