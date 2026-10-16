import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")
from dotenv import load_dotenv
load_dotenv()
import cv2
import json
import time
import threading
import numpy as np
from pathlib import Path
from flask import Flask, Response, render_template, jsonify, request

from core.detector import PoseDetector
from chatbot import get_chatbot_response, clear_history, get_quick_questions
from core.angle_calculator import AngleCalculator, ShoulderStabilityChecker
from core.fsm import ExerciseFSM
from core.form_checker import FormChecker

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# --- Konfigurasyon yukle ---
CONFIG_PATH = Path("config/exercises.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    EXERCISES = json.load(f)["exercises"]
EXERCISE_MAP = {ex["id"]: ex for ex in EXERCISES}

# --- Global durum ---
state_lock = threading.Lock()
app_state = {
    "active_exercise": None,
    "running": False,
    "fsm_status": {},
    "form_feedback": {},
    "angle_data": {},
    "shoulder_data": {},
    "confidence": 0.0,
    "fps": 0.0,
    "angle_zone": "neutral",
    "session_log": [],
    "lighting": "good",
    "camera_distance": "optimal",
    "camera_check": {
        "face_detected": False,
        "pose_detected": False,
        "shoulders_visible": False,
        "confidence": 0.0,
        "is_ready": False,
        "message": "Kamera kontrolü bekleniyor."
    }
}

detector = PoseDetector(min_confidence=0.6)
angle_calc = None
shoulder_checker = None
fsm = None
form_checker = None

camera = None
frame_buffer = None
frame_lock = threading.Lock()


def check_lighting_quality(frame):
    """Ortam ışık seviyesini kontrol et"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    avg_brightness = np.mean(gray)
    
    if avg_brightness < 50:
        return "low", "Ortam cok karanlik, aydinlatmayi artirin"
    elif avg_brightness > 200:
        return "high", "Ortam cok parlak, perdelerinizi kapatin"
    else:
        return "good", ""


def check_camera_distance(detection, frame_size):
    """Yüz büyüklüğüne göre mesafe kontrol et"""
    if not detection.get("face_detected"):
        return "unknown", ""
    
    lm = detection["landmarks_2d"]
    w, h = frame_size
    
    # Yüz genişliği (göz arası mesafe)
    left_eye = lm[33]
    right_eye = lm[263]
    face_width = abs((right_eye.x - left_eye.x) * w)
    
    if face_width < 80:
        return "far", "Kameraya daha yaklasın"
    elif face_width > 350:
        return "close", "Kameradan uzaklasin"
    else:
        return "optimal", ""


def camera_thread():
    global camera, frame_buffer, angle_calc, shoulder_checker
    global fsm, form_checker

    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 30)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Gecikmeyi azalt

    prev_time = time.time()
    
    # 🚀 Frame atlama (MediaPipe her 3 frame'de bir çalışır)
    frame_skip_counter = 0
    last_detection = None

    while True:
        with state_lock:
            running = app_state["running"]
            active_ex = app_state["active_exercise"]

        if not running:
            success, frame = camera.read()
            if success:
                frame = cv2.flip(frame, 1)

                # 🚀 Her 3 frame'de bir MediaPipe çalıştır
                frame_skip_counter += 1
                if frame_skip_counter % 3 == 0 or last_detection is None:
                    detection = detector.detect(frame)
                    last_detection = detection
                else:
                    detection = last_detection

                confidence = detection.get("confidence", 0.0)
                face_detected = detection.get("face_detected", False)
                pose_detected = detection.get("pose_detected", False)

                left_shoulder = detection.get("left_shoulder")
                right_shoulder = detection.get("right_shoulder")

                shoulders_visible = (
                    left_shoulder is not None and
                    right_shoulder is not None and
                    left_shoulder[2] > 0.4 and
                    right_shoulder[2] > 0.4
                )

                is_ready = (
                    face_detected and
                    confidence >= 0.6 and
                    shoulders_visible
                )

                if is_ready:
                    check_message = "Kamera uygun - egzersize baslayabilirsiniz"
                    color = (0, 220, 0)
                elif not face_detected:
                    check_message = "Yuz algilanamadi - kameraya donun"
                    color = (0, 0, 220)
                elif confidence < 0.6:
                    check_message = "Algilama dusuk - isik ve mesafeyi kontrol edin"
                    color = (0, 165, 255)
                elif not shoulders_visible:
                    check_message = "Omuzlar gorunmuyor - kameradan biraz uzaklasin"
                    color = (0, 165, 255)
                else:
                    check_message = "Kamera kontrol ediliyor"
                    color = (255, 255, 255)

                cv2.putText(frame, check_message,
                            (25, 40), cv2.FONT_HERSHEY_SIMPLEX,
                            0.65, color, 2)

                cv2.putText(frame, f"Algilama: {int(confidence * 100)}%",
                            (25, 70), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, color, 1)

                with state_lock:
                    app_state["camera_check"] = {
                        "face_detected": face_detected,
                        "pose_detected": pose_detected,
                        "shoulders_visible": shoulders_visible,
                        "confidence": round(confidence, 2),
                        "is_ready": is_ready,
                        "message": check_message
                    }

                with frame_lock:
                    frame_buffer = frame.copy()

            time.sleep(0.03)
            continue

        success, frame = camera.read()
        if not success:
            continue

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        # 🚀 Her 3 frame'de bir MediaPipe çalıştır (görüntü her frame render)
        frame_skip_counter += 1
        if frame_skip_counter % 3 == 0 or last_detection is None:
            detection = detector.detect(frame)
            last_detection = detection
        else:
            detection = last_detection

        confidence = detection.get("confidence", 0.0)

        # 🆕 YENİ: Işık kontrolü
        lighting, light_warning = check_lighting_quality(frame)
        
        # 🆕 YENİ: Mesafe kontrolü
        distance, dist_warning = check_camera_distance(detection, (w, h))

        angle_data = {"raw_angle": 0, "filtered_angle": 0,
                      "speed": 0, "abs_angle": 0}
        shoulder_data = {"stable": True, "deviation": 0.0, "detected": False}
        fsm_status = {}
        form_fb = {}
        angle_zone = "neutral"
        annotated = frame.copy()

        if active_ex and fsm is not None:
            ex_config = EXERCISE_MAP[active_ex]
            direction = ex_config["direction"]

            angle_data = angle_calc.update(0, direction, detection)

            shoulder_data = shoulder_checker.update(
                detection.get("left_shoulder"),
                detection.get("right_shoulder"),
                h
            )

            current_state = fsm.update(angle_data["filtered_angle"])
            fsm_status = fsm.get_status()

            fb = form_checker.check(
                angle_data, shoulder_data,
                confidence, current_state.value,
                fsm_status.get("current_side", "")
            )
            form_fb = {
                "is_valid": fb.is_valid,
                "warnings": fb.warnings,
                "errors": fb.errors,
                "suggestions": fb.suggestions,
                "quality_score": round(fb.quality_score, 2),
                "quality_label": form_checker.get_quality_label(fb.quality_score),
                "error_details": fb.error_details
            }

            angle_zone = form_checker.get_angle_zone(angle_data["abs_angle"])

            if fsm_status.get("rep_just_completed"):
                with state_lock:
                    app_state["session_log"].append({
                        "time": time.strftime("%H:%M:%S"),
                        "event": "rep",
                        "exercise_id": active_ex,
                        "exercise_name": EXERCISE_MAP[active_ex]["name"],
                        "rep": fsm_status.get("last_completed_rep", 0),
                        "set": fsm_status.get("last_completed_set", 1),
                        "quality": round(fb.quality_score, 2),
                        "quality_label": form_checker.get_quality_label(fb.quality_score),
                        "error_details": fb.error_details,
                        "warnings": fb.warnings,
                        "errors": fb.errors
                    })

            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            annotated = draw_overlay(frame, detection, angle_data,
                                     fsm_status, form_fb, angle_zone,
                                     confidence, fps, active_ex,
                                     light_warning, dist_warning)

            with state_lock:
                app_state.update({
                    "fsm_status": fsm_status,
                    "form_feedback": form_fb,
                    "angle_data": {
                        "filtered": round(angle_data["filtered_angle"], 1),
                        "speed": round(angle_data["speed"], 1),
                        "abs": round(angle_data["abs_angle"], 1)
                    },
                    "shoulder_data": shoulder_data,
                    "confidence": round(confidence, 2),
                    "fps": round(fps, 1),
                    "angle_zone": angle_zone,
                    "lighting": lighting,
                    "camera_distance": distance
                })

        with frame_lock:
            frame_buffer = annotated.copy()


def draw_overlay(frame, detection, angle_data, fsm_status,
                 form_fb, angle_zone, confidence, fps, active_ex,
                 light_warning="", dist_warning=""):
    h, w = frame.shape[:2]

    # Ust panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 75), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # FPS
    cv2.putText(frame, f"FPS:{fps:.0f}", (w - 75, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 120, 120), 1)

    # Algilama durumu
    conf_pct = int(confidence * 100)
    conf_color = (0, 200, 0) if confidence > 0.7 else \
                 (0, 165, 255) if confidence > 0.4 else (0, 0, 220)
    cv2.putText(frame, f"Alg:{conf_pct}%", (w - 75, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, conf_color, 1)

    # 🆕 YENİ: Işık ve mesafe uyarılarını ekrana yazdır
    warning_y = h - 45
    if light_warning:
        cv2.putText(frame, light_warning, (15, warning_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 165, 255), 1)
        warning_y -= 20
    if dist_warning:
        cv2.putText(frame, dist_warning, (15, warning_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 165, 255), 1)

    if not active_ex or not fsm_status:
        return frame

    # Aci degeri
    abs_angle = angle_data.get("abs_angle", 0.0)
    zone_colors = {
        "neutral":    (150, 150, 150),
        "approaching":(0, 165, 255),
        "target":     (0, 220, 0),
        "over":       (0, 0, 220)
    }
    a_color = zone_colors.get(angle_zone, (255, 255, 255))
    cv2.putText(frame, f"Aci: {abs_angle:.1f}",
                (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, a_color, 2)

    # FSM durumu (ASCII)
    state_names = {
        "neutral": "HAZIR",
        "move":    "HAREKET",
        "hold":    "BEKLE",
        "return":  "DON"
    }
    state_str = state_names.get(fsm_status.get("state", ""), "HAZIR")
    state_colors = {
        "HAZIR":   (150, 150, 150),
        "HAREKET": (0, 165, 255),
        "BEKLE":   (0, 220, 0),
        "DON":     (255, 200, 0)
    }
    s_color = state_colors.get(state_str, (255, 255, 255))

    current_side = fsm_status.get("current_side", "")
    if current_side == "right":
        state_str += " (SAG)"
    elif current_side == "left":
        state_str += " (SOL)"

    cv2.putText(frame, state_str,
                (15, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, s_color, 2)

    # Tekrar / Set
    rep = fsm_status.get("rep", 0)
    rps = fsm_status.get("reps_per_set", 0)
    sn  = fsm_status.get("set", 1)
    ts  = fsm_status.get("total_sets", 3)
    cv2.putText(frame, f"Tekrar:{rep}/{rps}  Set:{sn}/{ts}",
                (w//2 - 110, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    # Hold progress bar
    hold_prog = fsm_status.get("hold_progress", 0.0)
    if hold_prog > 0:
        bar_w = int((w - 40) * hold_prog)
        cv2.rectangle(frame, (20, h - 28), (w - 20, h - 15), (50, 50, 50), -1)
        cv2.rectangle(frame, (20, h - 28), (20 + bar_w, h - 15), (0, 200, 100), -1)

    # Uyarilar (ASCII, alt kisim)
    all_msgs = form_fb.get("errors", []) + form_fb.get("warnings", [])
    for i, msg in enumerate(all_msgs[:2]):
        color = (0, 0, 220) if i < len(form_fb.get("errors", [])) \
                else (0, 165, 255)
        # Turkce karakterleri ASCII'ye donustur (OpenCV icin)
        msg_safe = _to_ascii(msg)
        cv2.putText(frame, msg_safe, (15, h - 45 - i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1)

    # Yuz landmark noktalari
    if detection.get("face_detected") and detection.get("landmarks_2d"):
        lm = detection["landmarks_2d"]
        fw = frame.shape[1]
        fh = frame.shape[0]
        for idx in [1, 33, 263, 61, 291, 152, 234, 454, 10]:
            x = int(lm[idx].x * fw)
            y = int(lm[idx].y * fh)
            cv2.circle(frame, (x, y), 3, (0, 255, 180), -1)

    # Omuz noktalari
    if detection.get("left_shoulder"):
        ls = detection["left_shoulder"]
        cv2.circle(frame, (int(ls[0]), int(ls[1])), 6, (255, 100, 0), -1)
    if detection.get("right_shoulder"):
        rs = detection["right_shoulder"]
        cv2.circle(frame, (int(rs[0]), int(rs[1])), 6, (255, 100, 0), -1)

    return frame


def _to_ascii(text: str) -> str:
    """Turkce karakterleri ASCII karsiligina donusturur (OpenCV icin)"""
    tr_map = {
        'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U', 'ş': 's', 'Ş': 'S',
        'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
    }
    for tr, en in tr_map.items():
        text = text.replace(tr, en)
    return text


def generate_frames():
    while True:
        with frame_lock:
            if frame_buffer is None:
                time.sleep(0.01)  # 0.03 → 0.01
                continue
            _, buffer = cv2.imencode(".jpg", frame_buffer,
                                     [cv2.IMWRITE_JPEG_QUALITY, 85])  # 80 → 85 (daha net)
            frame_bytes = buffer.tobytes()

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" +
               frame_bytes + b"\r\n")
        time.sleep(0.020)  # 0.033 → 0.020 (50 FPS stream)


# --- Flask rotalari ---

@app.route("/")
def index():
    return render_template("index.html", exercises=EXERCISES)


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/status")
def get_status():
    with state_lock:
        data = dict(app_state)
    resp = app.response_class(
        response=json.dumps(data, ensure_ascii=False),
        status=200,
        mimetype='application/json'
    )
    return resp


@app.route("/api/start_exercise", methods=["POST"])
def start_exercise():
    global angle_calc, shoulder_checker, fsm, form_checker

    data = request.get_json()
    ex_id = data.get("exercise_id")

    if ex_id not in EXERCISE_MAP:
        return jsonify({"success": False, "error": "Gecersiz egzersiz"}), 400

    ex_config = EXERCISE_MAP[ex_id]

    angle_calc = AngleCalculator(smoothing=0.35)
    shoulder_checker = ShoulderStabilityChecker(
        threshold=ex_config["shoulder_stability_threshold"]
    )
    fsm = ExerciseFSM(ex_config)
    form_checker = FormChecker(ex_config)

    with state_lock:
        app_state["active_exercise"] = ex_id
        app_state["running"] = True
        app_state["fsm_status"] = {}

    return jsonify({"success": True, "exercise": ex_config["name"]})


@app.route("/api/stop_exercise", methods=["POST"])
def stop_exercise():
    with state_lock:
        app_state["active_exercise"] = None
        app_state["running"] = False
        log = app_state["session_log"].copy()

    if angle_calc:
        angle_calc.reset()
    if shoulder_checker:
        shoulder_checker.reset()
    if fsm:
        fsm.reset()

    return jsonify({"success": True, "session_log": log})


@app.route("/api/exercises")
def get_exercises():
    resp = app.response_class(
        response=json.dumps(EXERCISES, ensure_ascii=False),
        status=200,
        mimetype='application/json'
    )
    return resp


@app.route("/api/session_log")
def get_session_log():
    with state_lock:
        log = app_state["session_log"].copy()
    resp = app.response_class(
        response=json.dumps(log, ensure_ascii=False),
        status=200,
        mimetype='application/json'
    )
    return resp



@app.route("/api/chat", methods=["POST"])
def chat():
    data       = request.get_json()
    message    = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not message:
        return jsonify({"success": False, "error": "Mesaj bos olamaz"}), 400

    with state_lock:
        session_log = app_state["session_log"].copy()

        current_status = {
            "active_exercise": app_state.get("active_exercise"),
            "active_exercise_name": EXERCISE_MAP.get(
                app_state.get("active_exercise"), {}
            ).get("name", ""),
            "running": app_state.get("running"),
            "fsm_status": app_state.get("fsm_status", {}),
            "form_feedback": app_state.get("form_feedback", {}),
            "angle_data": app_state.get("angle_data", {}),
            "shoulder_data": app_state.get("shoulder_data", {}),
            "confidence": app_state.get("confidence", 0.0),
            "angle_zone": app_state.get("angle_zone", "neutral")
        }

    result = get_chatbot_response(
        message,
        session_id=session_id,
        session_log=session_log,
        current_status=current_status,
        exercises=EXERCISES
    )

    resp = app.response_class(
        response=json.dumps(result, ensure_ascii=False),
        status=200,
        mimetype="application/json"
    )
    return resp


@app.route("/api/chat/clear", methods=["POST"])
def chat_clear():
    data = request.get_json() or {}
    session_id = data.get("session_id", "default")
    clear_history(session_id)
    return jsonify({"success": True})


@app.route("/api/chat/questions")
def chat_questions():
    resp = app.response_class(
        response=json.dumps(get_quick_questions(), ensure_ascii=False),
        status=200,
        mimetype="application/json"
    )
    return resp


if __name__ == "__main__":
    t = threading.Thread(target=camera_thread, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

@app.route("/api/session_report")
def get_session_report():
    with state_lock:
        log = app_state["session_log"].copy()

    if not log:
        resp = app.response_class(
            response=json.dumps({
                "success": False,
                "message": "Henüz tamamlanmış tekrar yok.",
                "report": None
            }, ensure_ascii=False),
            status=200,
            mimetype="application/json"
        )
        return resp

    total_reps = len(log)
    avg_quality = sum(item.get("quality", 0) for item in log) / total_reps

    exercise_stats = {}
    error_counts = {
        "too_fast": 0,
        "shoulder_movement": 0,
        "low_confidence": 0,
        "angle_exceeded": 0
    }

    for item in log:
        ex_name = item.get("exercise_name", "Bilinmiyor")
        quality = item.get("quality", 0)
        details = item.get("error_details", {}) or {}

        if ex_name not in exercise_stats:
            exercise_stats[ex_name] = {
                "count": 0,
                "total_quality": 0
            }

        exercise_stats[ex_name]["count"] += 1
        exercise_stats[ex_name]["total_quality"] += quality

        for key in error_counts.keys():
            if details.get(key):
                error_counts[key] += 1

    exercise_summary = []
    for name, data in exercise_stats.items():
        count = data["count"]
        avg_q = data["total_quality"] / count if count else 0

        exercise_summary.append({
            "exercise_name": name,
            "repeat_count": count,
            "average_quality": round(avg_q, 2)
        })

    best_exercise = max(
        exercise_summary,
        key=lambda x: x["average_quality"]
    ) if exercise_summary else None

    most_common_error_key = None
    if max(error_counts.values()) > 0:
        most_common_error_key = max(error_counts, key=error_counts.get)

    error_labels = {
        "too_fast": "Çok hızlı hareket",
        "shoulder_movement": "Omuz hareketi",
        "low_confidence": "Düşük algılama",
        "angle_exceeded": "Hedef açı aşımı"
    }

    if avg_quality >= 0.90:
        general_comment = "Genel performansın mükemmel. Hareketleri kontrollü ve doğru formda yapmışsın."
    elif avg_quality >= 0.75:
        general_comment = "Genel performansın iyi. Küçük form hataları olsa da egzersizleri başarılı şekilde tamamlamışsın."
    elif avg_quality >= 0.55:
        general_comment = "Genel performansın orta seviyede. Hareket hızına, omuz sabitliğine ve kamera konumuna daha fazla dikkat etmelisin."
    elif avg_quality >= 0.40:
        general_comment = "Genel performansın zayıf. Egzersizleri daha yavaş yapman ve form uyarılarını dikkate alman gerekiyor."
    else:
        general_comment = "Form kaliten düşük görünüyor. Hareketleri tekrar denemeden önce kamera konumu, omuz sabitliği ve hareket hızını düzeltmelisin."

    report = {
        "total_reps": total_reps,
        "average_quality": round(avg_quality, 2),
        "best_exercise": best_exercise,
        "most_common_error": error_labels.get(most_common_error_key, "Belirgin hata yok"),
        "error_counts": {
            "too_fast": error_counts["too_fast"],
            "shoulder_movement": error_counts["shoulder_movement"],
            "low_confidence": error_counts["low_confidence"],
            "angle_exceeded": error_counts["angle_exceeded"]
        },
        "exercise_summary": exercise_summary,
        "general_comment": general_comment
    }

    resp = app.response_class(
        response=json.dumps({
            "success": True,
            "report": report
        }, ensure_ascii=False),
        status=200,
        mimetype="application/json"
    )
    return resp