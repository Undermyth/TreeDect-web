from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import base64
import uvicorn

app = FastAPI()

# 添加CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/load_image")
async def load_image():
    try:
        # 读取example.jpg文件并进行base64编码
        with open("example.jpg", "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        # 返回base64编码的图像
        return JSONResponse(content={"image": encoded_string})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)