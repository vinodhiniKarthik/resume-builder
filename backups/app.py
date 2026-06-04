from flask import send_file
from reportlab.pdfgen import canvas
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

    pdf_file = f"resume_{id}.pdf"

    c = canvas.Canvas(pdf_file)

    c.drawString(100, 800, f"Name: {resume.full_name}")
    c.drawString(100, 780, f"Email: {resume.email}")
    c.drawString(100, 760, f"Phone: {resume.phone}")

    c.drawString(100, 720, "Skills:")
    c.drawString(120, 700, str(resume.skills))

    c.drawString(100, 660, "Education:")
    c.drawString(120, 640, str(resume.education))

    c.drawString(100, 600, "Experience:")
    c.drawString(120, 580, str(resume.experience))

    c.save()

    return send_file(pdf_file, as_attachment=True)

   

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