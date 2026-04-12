#!/usr/bin/env python3
"""
Zapier Webhook 入口
接收 Zapier POST 的 JSON 数据，并调用现有下载/剪辑逻辑。
"""

import json
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from download_video import download_video
from clip_video import clip_video


def _build_output_path(output_dir: str, output_filename: str, video_id: str = None) -> Path:
    """构建输出路径并确保目录存在。"""
    base_dir = Path(output_dir or ".").expanduser().resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    if output_filename:
        filename = output_filename
    elif video_id:
        filename = f"{video_id}_clip.mp4"
    else:
        filename = "zapier_clip.mp4"

    return base_dir / filename


class ZapierWebhookHandler(BaseHTTPRequestHandler):
    """简单的 webhook 处理器（只处理 POST /zapier-webhook）。"""

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/zapier-webhook":
            self._send_json(404, {"success": False, "error": "Not Found"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            payload = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"success": False, "error": "Invalid JSON payload"})
            return

        try:
            result = self._process_payload(payload)
            self._send_json(200, {"success": True, **result})
        except Exception as e:
            self._send_json(500, {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"success": False, "error": "Not Found"})

    def _process_payload(self, payload: dict) -> dict:
        """
        支持两种触发模式：
        1) 传入 youtube_url：先下载，再剪辑
        2) 传入 video_path：直接剪辑
        """
        youtube_url = payload.get("youtube_url") or payload.get("youtubeUrl") or payload.get("url")
        video_path = payload.get("video_path") or payload.get("videoPath")
        start_time = payload.get("start_time") or payload.get("startTime") or payload.get("clip_start")
        end_time = payload.get("end_time") or payload.get("endTime") or payload.get("clip_end")
        output_dir = payload.get("output_dir") or payload.get("outputDir") or "./youtube-clips"
        output_filename = payload.get("output_filename") or payload.get("outputFilename")

        if not start_time or not end_time:
            raise ValueError("Missing required fields: start_time/startTime and end_time/endTime")

        download_result = None
        if youtube_url:
            download_result = download_video(youtube_url, output_dir=output_dir)
            video_path = download_result["video_path"]
            output_path = _build_output_path(
                output_dir=output_dir,
                output_filename=output_filename,
                video_id=download_result.get("video_id")
            )
        elif video_path:
            output_path = _build_output_path(
                output_dir=output_dir,
                output_filename=output_filename
            )
        else:
            raise ValueError("Missing required fields: provide youtube_url/youtubeUrl OR video_path/videoPath")

        clipped_output = clip_video(
            video_path=video_path,
            start_time=start_time,
            end_time=end_time,
            output_path=str(output_path)
        )

        return {
            "mode": "download_and_clip" if youtube_url else "clip_only",
            "input_video_path": video_path,
            "output_path": clipped_output,
            "download": download_result
        }

    def _send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # 降低默认日志噪音
        return


def main():
    host = "0.0.0.0"
    port = 8765

    server = ThreadingHTTPServer((host, port), ZapierWebhookHandler)
    print(f"🚀 Zapier webhook server started at http://{host}:{port}")
    print("📥 Endpoint: POST /zapier-webhook")
    print("💓 Health:   GET  /health")
    server.serve_forever()


if __name__ == "__main__":
    main()
