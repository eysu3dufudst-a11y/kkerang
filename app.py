from flask import (
    Flask, render_template, request,
    redirect, url_for, session,
    send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# ======================
# APP
# ======================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kkerang.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/videos'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ======================
# MODELS
# ======================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User')

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    filename = db.Column(db.String(200))
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'))
    channel = db.relationship('Channel')

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    video_id = db.Column(db.Integer)

# ======================
# LOGIN
# ======================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ======================
# ROUTES
# ======================

@app.route('/')
def index():
    videos = Video.query.order_by(Video.created_at.desc()).all()
    return render_template('index.html', videos=videos)

# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='이미 존재하는 아이디')

        user = User(
            username=username,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        channel = Channel(
            name=f"{username} 채널",
            owner=user
        )
        db.session.add(channel)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(
            username=request.form.get('username')
        ).first()

        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))

        return render_template('login.html', error='로그인 실패')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ---------- UPLOAD ----------
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files.get('video')
        title = request.form.get('title') or "제목 없는 동영상"

        if not file:
            return "동영상 없음", 400

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(path)

        channel = Channel.query.filter_by(owner=current_user).first()

        video = Video(
            title=title,
            filename=file.filename,
            channel=channel
        )
        db.session.add(video)
        db.session.commit()

        return redirect(url_for('watch', id=video.id))

    return render_template('upload.html')

# ---------- WATCH ----------
@app.route('/watch/<int:id>')
def watch(id):
    video = Video.query.get_or_404(id)

    viewed = session.get('viewed_videos', [])
    if id not in viewed:
        video.views += 1
        viewed.append(id)
        session['viewed_videos'] = viewed
        db.session.commit()

    recommends = Video.query.filter(Video.id != id)\
        .order_by(Video.views.desc())\
        .limit(8).all()

    return render_template(
        'watch.html',
        video=video,
        recommends=recommends
    )

# ---------- LIKE ----------
@app.route('/like/<int:id>')
@login_required
def like(id):
    video = Video.query.get_or_404(id)

    if not Like.query.filter_by(
        user_id=current_user.id,
        video_id=id
    ).first():
        db.session.add(Like(
            user_id=current_user.id,
            video_id=id
        ))
        video.likes += 1
        db.session.commit()

    return redirect(url_for('watch', id=id))

# ---------- VIDEO STREAM (🔥 다운로드 차단 핵심) ----------
@app.route('/video/<filename>')
def stream_video(filename):
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        as_attachment=False
    )

# ======================
# START
# ======================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
