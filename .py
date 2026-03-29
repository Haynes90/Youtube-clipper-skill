from fastapi import FastAPI, BackgroundTasks
import subprocess
import os
import uuid

app = FastAPI()

@app.get("/")
def home():
    return {"status": "ok"}

@app.post("/jobs")
def create_job(data: dict, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())

    video_url = data.get("video_url")
    drive_folder_id = data.get("drive_folder_id")

    background_tasks.add_task(process_video, video_url, drive_folder_id, job_id)

    return {"status": "queued", "job_id": job_id}


def process_video(video_url, drive_folder_id, job_id):
    try:
        os.makedirs(f"/tmp/{job_id}", exist_ok=True)

        # STEP 1 — download video
        subprocess.run([
            "yt-dlp",
            "-o", f"/tmp/{job_id}/video.%(ext)s",
            video_url
        ])

        # STEP 2 — placeholder for clipping logic
        print("Downloaded video, next step will process clips")

        # TODO: call your clipping scripts here

    except Exception as e:
        print("Error:", e)
