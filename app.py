from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# --------------------
# 기본 설정
# --------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = "kkerang-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "videos")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# --------------------
# DB 모델
# --------------------
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 🔥 테이블 자동 생성 (이게 핵심)
with app.app_context():
    db.create_all()

# --------------------
# 홈 (유튜브 메인 느낌)
# --------------------
@app.route("/")
def index():
    videos = Video.query.order_by(Video.created_at.desc()).all()
    return render_template("index.html", videos=videos)

# --------------------
# 업로드
# --------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        title = request.form.get("title")
        file = request.files.get("video")

        if not title or not file:
            abort(400)

        filename = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

        video = Video(title=title, filename=filename)
        db.session.add(video)
        db.session.commit()

        return redirect(url_for("index"))

    return render_template("upload.html")

# --------------------
# 영상 시청
# --------------------
@app.route("/watch/<int:video_id>")
def watch(video_id):
    video = Video.query.get_or_404(video_id)
    video.views += 1
    db.session.commit()

    # 추천 영상
    recommends = Video.query.filter(Video.id != video.id)\
        .order_by(Video.created_at.desc()).limit(6).all()

    return render_template(
        "watch.html",
        video=video,
        recommends=recommends
    )

# --------------------
# 좋아요
# --------------------
@app.route("/like/<int:video_id>", methods=["POST"])
def like(video_id):
    video = Video.query.get_or_404(video_id)
    video.likes += 1
    db.session.commit()
    return redirect(url_for("watch", video_id=video_id))

# --------------------
# 영상 스트리밍 (다운로드 X)
# --------------------
@app.route("/video/<filename>")
def video_file(filename):
    return send_from_directory(
        UPLOAD_FOLDER,
        filename,
        as_attachment=False  # 🔥 다운로드 방지
    )

# --------------------
# 로컬 실행용 (Render에서는 사용 안 함)
# --------------------
if __name__ == "__main__":
    app.run(debug=True)
