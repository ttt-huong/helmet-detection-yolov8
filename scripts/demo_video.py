"""Recreate the Kaggle helmet demo on CPU from the retained clip and checkpoint."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from time import perf_counter

CONFIDENCE = 0.25
EXPECTED_FRAMES = 874


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Original 4K, 30 FPS demo clip")
    parser.add_argument("--weights", type=Path, required=True, help="Trusted YOLOv8m checkpoint")
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    source, weights, destination = args.source, args.weights, args.output
    for path in (source, weights):
        if not path.is_file():
            parser.error(f"File not found: {path}")

    import cv2
    import torch
    from ultralytics import YOLO, __version__

    torch.set_num_threads(min(6, os.cpu_count() or 1))
    cv2.setNumThreads(2)
    model = YOLO(str(weights))
    options = dict(imgsz=640, conf=CONFIDENCE, device="cpu", verbose=False)
    size = (1920, 1080)
    destination.mkdir(parents=True, exist_ok=False)

    with TemporaryDirectory(dir=destination) as temp:
        raw = Path(temp) / "intermediate.mp4"
        result = Path(temp) / "encoded.mp4"
        cap = cv2.VideoCapture(str(source))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if not cap.isOpened() or (width, height, fps) != (3840, 2160, 30.0):
            cap.release()
            raise RuntimeError(f"Unexpected source format: {width}x{height}, {fps} FPS")
        writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
        if not writer.isOpened():
            cap.release()
            raise RuntimeError("Could not open the intermediate video writer")

        count = 0
        started = perf_counter()
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                frame = cv2.resize(frame, size)
                prediction = model.predict(frame, **options)[0]
                writer.write(prediction.plot())
                count += 1
                if count % 100 == 0:
                    print(f"Processed {count}/{EXPECTED_FRAMES} frames", flush=True)
        finally:
            writer.release()
            cap.release()
        elapsed = perf_counter() - started
        if count != EXPECTED_FRAMES:
            raise RuntimeError(f"Decoded {count} frames, expected {EXPECTED_FRAMES}")

        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-i", str(raw), "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(result),
        ], check=True)
        check = cv2.VideoCapture(str(result))
        try:
            encoded_count = int(check.get(cv2.CAP_PROP_FRAME_COUNT))
            readable, _ = check.read()
            if not readable or encoded_count != count:
                raise RuntimeError(f"Output validation failed: {encoded_count}/{count} frames")
        finally:
            check.release()
        result.replace(destination / "demo_v8m_clip2.mp4")

    with weights.open("rb") as file:
        weight_sha256 = hashlib.file_digest(file, "sha256").hexdigest()
    log = (
        "Lần chạy tái tạo trên máy, dùng CPU.\n"
        f"Tệp nguồn: {source.name}\n"
        f"YOLOv8m | Ultralytics {__version__} | conf={CONFIDENCE} | imgsz=640\n"
        f"Checkpoint: {weights.name} | SHA-256: {weight_sha256}\n"
        f"Video: {count} khung | {count / fps:.2f} giây | {fps:.2f} FPS phát\n"
        f"Độ phân giải đầu ra: {size[0]} × {size[1]}\n"
        f"Thời gian tái tạo trên CPU: {elapsed:.2f} giây trước bước mã hóa H.264.\n"
        "Số đo Tesla T4 được lưu riêng trong demo_log_chep_tu_Kaggle.txt.\n"
    )
    (destination / "demo_log.txt").write_text(log, encoding="utf-8")
    print(log, flush=True)


if __name__ == "__main__":
    main()
