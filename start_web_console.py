"""
启动 Web 操作台
"""
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("AI 职位雷达 - Web 操作台")
    print("=" * 60)
    print("\n服务器启动中...")
    print("访问地址: http://localhost:8001")
    print("\n按 Ctrl+C 停止服务器")
    print("已启用自动重载：修改代码后会自动重新加载\n")
    
    # 使用导入字符串以支持 reload 功能
    uvicorn.run("web_console:app", host="0.0.0.0", port=8001, reload=True)
