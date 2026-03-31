from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
import subprocess
import uuid
import os

from fastapi.staticfiles import StaticFiles


app = FastAPI()

BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
WORK_DIR = "jobs"
os.makedirs(WORK_DIR, exist_ok=True)


# 👉 THIS SERVES YOUR WEB PAGE
@app.get("/", response_class=HTMLResponse)
def homepage():
    with open("index.html", "r") as f:
        return f.read()


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.post("/generate")
async def generate(
    
    file: UploadFile = File(...), x: float = 0, y: float = 0, scale: float = 1.0
):
    job_id = str(uuid.uuid4())

    svg_path = os.path.join(WORK_DIR, f"{job_id}.svg")
    stl_path = os.path.join(WORK_DIR, f"{job_id}.stl")
    print('wtf')
    #console.log("🔥 GENERATE CLICKED");

    #alert("clicked");  // temporary
    with open(svg_path, "wb") as f:
        f.write(await file.read())

    cmd = [
        BLENDER,
        "-b",
        "template.blend",
        "-P",
        "apply_logo.py",
        "--",
        svg_path,
        stl_path,
        str(x),
        str(y),
        str(scale),
    ]

    subprocess.run(cmd)

    return FileResponse(stl_path, filename="output.stl")
