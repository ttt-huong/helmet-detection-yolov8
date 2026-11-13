"""Hiển thị dự đoán mũ bảo hộ trực tiếp từ webcam."""

import argparse
import os
from pathlib import Path
import sys

WINDOW_NAME = "YOLOv8m - Webcam | Q / Esc: thoat"


def forehead_covered(hands, face, width, height):
    left = face.origin_x - 0.10 * face.width
    right = face.origin_x + 1.10 * face.width
    top = face.origin_y - 0.45 * face.height
    bottom = face.origin_y + 0.50 * face.height
    return any(
        sum(left <= p.x * width <= right and top <= p.y * height <= bottom for p in hand) >= 2
        for hand in hands
    )


def detect_status(model, face_detector, hand_detector, frame):
    """Return one face-aligned prediction, or a reason to abstain."""
    import cv2
    import mediapipe as mp

    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    faces = face_detector.detect(image).detections
    if not faces:
        return None, None, "Chua thay mat"
    detection = max(faces, key=lambda item: item.bounding_box.width * item.bounding_box.height)
    face = detection.bounding_box
    height, width = frame.shape[:2]
    if forehead_covered(hand_detector.detect(image).hand_landmarks, face, width, height):
        return face, None, "Chua xac dinh: tay che tran"

    result = model.predict(frame, imgsz=640, conf=0.25, device="cpu", verbose=False)[0]
    # BlazeFace supplies a nose landmark. For the close-up webcam demo,
    # abstain when a helmet candidate extends over the lower face.
    helmet_bottom = detection.keypoints[2].y * height + 0.08 * face.height
    candidates = []
    for left, top, right, bottom, confidence, label in result.boxes.data.tolist():
        x = (left + right) / 2
        y = (top + bottom) / 2
        if (
            face.origin_x - 0.15 * face.width <= x <= face.origin_x + 1.15 * face.width
            and face.origin_y - 0.75 * face.height <= y <= face.origin_y + 0.88 * face.height
            and (int(label) == 1 or bottom <= helmet_bottom)
        ):
            candidates.append((left, top, right, bottom, confidence, int(label)))
    return face, max(candidates, key=lambda item: item[4], default=None), "Chua xac dinh"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True, help="Checkpoint YOLOv8m của nhóm")
    parser.add_argument("--camera", type=int, default=0, help="Chỉ số camera, mặc định 0")
    parser.add_argument("--models-dir", type=Path, required=True, help="Thư mục chứa mô hình MediaPipe")
    args = parser.parse_args()
    if not args.weights.is_file():
        parser.error(f"Không tìm thấy checkpoint {args.weights}")
    if args.camera < 0:
        parser.error("Chỉ số camera phải từ 0 trở lên")
    face_path = args.models_dir / "blaze_face_short_range.tflite"
    hand_path = args.models_dir / "hand_landmarker.task"
    for path in (face_path, hand_path):
        if not path.is_file():
            parser.error(f"Không tìm thấy mô hình hỗ trợ {path}")

    import cv2

    try:
        run_demo(args, parser, face_path, hand_path)
    except (RuntimeError, cv2.error) as error:
        print(error, file=sys.stderr)
        sys.exit(1)


def run_demo(args, parser, face_path, hand_path):
    import cv2
    import mediapipe as mp
    import torch
    from ultralytics import YOLO

    torch.set_num_threads(min(6, os.cpu_count() or 1))
    cv2.setNumThreads(2)
    model = YOLO(str(args.weights))
    if model.names != {0: "helmet", 1: "bare_head"}:
        parser.error("Checkpoint cần có hai lớp helmet và bare_head")

    face_options = mp.tasks.vision.FaceDetectorOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(face_path)),
        min_detection_confidence=0.45,
    )
    hand_options = mp.tasks.vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(hand_path)),
        num_hands=2,
        min_hand_detection_confidence=0.35,
        min_hand_presence_confidence=0.35,
    )
    with (
        mp.tasks.vision.FaceDetector.create_from_options(face_options) as faces,
        mp.tasks.vision.HandLandmarker.create_from_options(hand_options) as hands,
    ):
        show_camera(args.camera, model, faces, hands)


def show_camera(index, model, face_detector, hand_detector):
    import cv2

    camera = cv2.VideoCapture(index)
    window_open = False
    previous_label, consecutive = None, 0
    try:
        if not camera.isOpened():
            raise RuntimeError(f"Không mở được camera {index}. Hãy kiểm tra quyền camera hoặc thử camera 1.")
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError(f"Không đọc được hình từ camera {index}.")
            face, box, message = detect_status(model, face_detector, hand_detector, frame)
            label = box[5] if box is not None else None
            consecutive = consecutive + 1 if label == previous_label and label is not None else int(label is not None)
            previous_label = label
            if box is not None and consecutive >= 3:
                left, top, right, bottom = map(round, box[:4])
                color = (40, 200, 70) if label == 0 else (0, 210, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                message = f"{model.names[label]} {box[4]:.2f}"
            else:
                color = (0, 210, 255)
                if face is not None:
                    x, y = face.origin_x, face.origin_y
                    cv2.rectangle(frame, (x, y), (x + face.width, y + face.height), color, 2)
            cv2.putText(frame, message, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
            cv2.imshow(WINDOW_NAME, frame)
            window_open = True
            if (cv2.waitKey(1) & 0xFF) in (27, ord("q"), ord("Q")):
                break
            try:
                visible = cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE)
            except cv2.error:
                break
            if visible < 1:
                break
    finally:
        camera.release()
        if window_open:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
