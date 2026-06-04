import io
from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    login_required, current_user
)
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

# ─── App Setup ─────────────────────────────────────────────

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# ─── Models ───────────────────────────────────────────────

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    skills = db.Column(db.Text)
    education = db.Column(db.Text)
    experience = db.Column(db.Text)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

# ─── Login Loader ─────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ─── Forms ────────────────────────────────────────────────

class RegisterForm(FlaskForm):
    username = StringField(validators=[DataRequired()])
    email = StringField(validators=[DataRequired(), Email()])
    password = PasswordField(validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField(validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField(validators=[DataRequired(), Email()])
    password = PasswordField(validators=[DataRequired()])
    submit = SubmitField("Login")

# ─── Routes ───────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():

        existing_user = User.query.filter(
            (User.email == form.email.data) |
            (User.username == form.username.data)
        ).first()

        if existing_user:
            flash("Username or email already exists")
            return redirect(url_for("register"))

        hashed_pw = bcrypt.generate_password_hash(
            form.password.data
        ).decode("utf-8")

        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_pw
        )

        db.session.add(user)
        db.session.commit()

        flash("Account created successfully")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(
            email=form.email.data
        ).first()

        if user and bcrypt.check_password_hash(
            user.password,
            form.password.data
        ):
            login_user(user)
            flash("Login successful")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password")

    return render_template("login.html", form=form)


@app.route("/dashboard")
@login_required
def dashboard():
    resumes = Resume.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        "dashboard.html",
        user=current_user,
        resumes=resumes
    )


@app.route("/builder", methods=["GET", "POST"])
@login_required
def builder():

    if request.method == "POST":
        resume = Resume(
            full_name=request.form.get("full_name"),
            email=request.form.get("email"),
            phone=request.form.get("phone"),
            skills=request.form.get("skills"),
            education=request.form.get("education"),
            experience=request.form.get("experience"),
            user_id=current_user.id
        )

        db.session.add(resume)
        db.session.commit()

        flash("Resume saved successfully")
        return redirect(url_for("dashboard"))

    return render_template("builder.html")


@app.route("/edit_resume/<int:id>", methods=["GET", "POST"])
@login_required
def edit_resume(id):
    resume = Resume.query.get_or_404(id)

    if resume.user_id != current_user.id:
        flash("Unauthorized access")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        resume.full_name = request.form.get("full_name")
        resume.email = request.form.get("email")
        resume.phone = request.form.get("phone")
        resume.skills = request.form.get("skills")
        resume.education = request.form.get("education")
        resume.experience = request.form.get("experience")

        db.session.commit()

        flash("Resume updated successfully")
        return redirect(url_for("dashboard"))

    return render_template(
        "edit_resume.html",
        resume=resume
    )


@app.route("/delete_resume/<int:id>")
@login_required
def delete_resume(id):
    resume = Resume.query.get_or_404(id)

    if resume.user_id != current_user.id:
        flash("Unauthorized access")
        return redirect(url_for("dashboard"))

    db.session.delete(resume)
    db.session.commit()

    flash("Resume deleted successfully")
    return redirect(url_for("dashboard"))


@app.route("/download_resume/<int:id>")
@login_required
def download_resume(id):
    resume = Resume.query.get_or_404(id)

    if resume.user_id != current_user.id:
        flash("Unauthorized access")
        return redirect(url_for("dashboard"))

    # ── Build PDF in memory (no file writing needed) ──────
    buffer = io.BytesIO()
    width, height = A4                          # 595 x 842 pt

    c = canvas.Canvas(buffer, pagesize=A4)

    # ── Header bar ───────────────────────────────────────
    c.setFillColorRGB(0.07, 0.07, 0.15)
    c.rect(0, height - 80, width, 80, fill=1, stroke=0)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 20)
    name = resume.full_name or "Resume"
    c.drawString(40, height - 45, name)

    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.7, 0.85, 1)
    contact_parts = []
    if resume.email:    contact_parts.append(resume.email)
    if resume.phone:    contact_parts.append(resume.phone)
    c.drawString(40, height - 62, "  |  ".join(contact_parts))

    # ── Helper: section title ─────────────────────────────
    y = height - 110

    def section(title, content):
        nonlocal y
        if not content:
            return

        # Section label
        c.setFillColorRGB(0.1, 0.35, 0.7)
        c.rect(40, y - 2, width - 80, 18, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(44, y + 2, title.upper())
        y -= 26

        # Section body — word-wrap long text
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.15, 0.15, 0.2)
        max_width = width - 100
        lines = []
        for raw_line in content.splitlines():
            words = raw_line.split()
            if not words:
                lines.append("")
                continue
            current = ""
            for word in words:
                test = (current + " " + word).strip()
                if c.stringWidth(test, "Helvetica", 10) <= max_width:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)

        for line in lines:
            if y < 60:          # new page
                c.showPage()
                y = height - 40
                c.setFont("Helvetica", 10)
                c.setFillColorRGB(0.15, 0.15, 0.2)
            c.drawString(48, y, line)
            y -= 15

        y -= 10   # spacing after section

    section("Skills",      resume.skills)
    section("Education",   resume.education)
    section("Experience",  resume.experience)

    # ── Footer ────────────────────────────────────────────
    c.setFillColorRGB(0.6, 0.6, 0.7)
    c.setFont("Helvetica", 8)
    c.drawString(40, 30, "Generated by ResumeForge")
    c.drawRightString(width - 40, 30, resume.email or "")

    c.save()
    buffer.seek(0)

    safe_name = (resume.full_name or "resume").replace(" ", "_").lower()
    filename = f"{safe_name}_resume.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully")
    return redirect(url_for("home"))

# ─── Run Application ──────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)