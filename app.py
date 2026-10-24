"""
Flask Application for College Resource Hub
Serves static assets, unified frontend, and complete RESTful APIs for Admins and Students.
"""

import os
import re
import io
import math
import subprocess
import threading
import atexit
from werkzeug.utils import secure_filename
from flask import (
    Flask, request, jsonify, session, send_file, render_template,
    send_from_directory, redirect, url_for
)
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
from PIL import Image
import docx
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from database import (
    init_db, get_db, hash_password, ACADEMIC_HIERARCHY,
    UPLOADS_DIR, DB_FILE
)
import time
import socket

# Cloudflare Global Tunnel Controller (Enables Mobile/Remote Access Anywhere)
PUBLIC_TUNNEL_URL = None
TUNNEL_PROCESS = None

def get_public_tunnel_url():
    """Retrieve active Cloudflare public HTTPS URL from memory or file."""
    global PUBLIC_TUNNEL_URL
    if PUBLIC_TUNNEL_URL:
        return PUBLIC_TUNNEL_URL
    url_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public_url.txt")
    if os.path.exists(url_file):
        try:
            with open(url_file, "r") as f:
                content = f.read().strip()
                if content.startswith("http"):
                    PUBLIC_TUNNEL_URL = content
                    return PUBLIC_TUNNEL_URL
        except Exception:
            pass
    return None

def start_public_tunnel(port=5000):
    """Launch cloudflared.exe quick tunnel for secure global remote/mobile access."""
    global TUNNEL_PROCESS, PUBLIC_TUNNEL_URL
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cloudflared_exe = os.path.join(base_dir, "cloudflared.exe")
    if not os.path.exists(cloudflared_exe):
        return

    url_file = os.path.join(base_dir, "public_url.txt")
    if os.path.exists(url_file):
        try:
            os.remove(url_file)
        except Exception:
            pass

    try:
        cmd = [cloudflared_exe, "tunnel", "--url", f"http://127.0.0.1:{port}"]
        creation_flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
        TUNNEL_PROCESS = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creation_flags
        )

        def reader():
            global PUBLIC_TUNNEL_URL
            for line in iter(TUNNEL_PROCESS.stdout.readline, ''):
                m = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                if m and not PUBLIC_TUNNEL_URL:
                    PUBLIC_TUNNEL_URL = m.group(1)
                    try:
                        with open(url_file, "w") as f:
                            f.write(PUBLIC_TUNNEL_URL + "\n")
                    except Exception:
                        pass
                    print("\n" + "=" * 74)
                    print("  COLLEGE RESOURCE HUB - GLOBAL PUBLIC LINK (SHARE WITH FRIENDS)")
                    print(f"  Public URL : {PUBLIC_TUNNEL_URL}")
                    print(f"  Local Host : http://127.0.0.1:{port}")
                    print("  * Anyone on mobile data (Jio, Airtel, etc.) or home Wi-Fi can open it!")
                    print("  * Remote users create an account & login (Demo accounts are hidden).")
                    print("=" * 74 + "\n", flush=True)

        t = threading.Thread(target=reader, daemon=True)
        t.start()

        def stop_tunnel():
            if TUNNEL_PROCESS:
                try:
                    TUNNEL_PROCESS.terminate()
                except Exception:
                    pass
        atexit.register(stop_tunnel)
    except Exception as e:
        print(f"Notice: Could not start Cloudflare tunnel: {e}")

# Live Sync State for Multi-Device / Multi-User Instant Updates
ARCHIVE_STATE = {
    "version": int(time.time() * 1000),
    "last_action": "init"
}

def notify_archive_change(action: str = "update"):
    """Increment sync version to trigger auto-refresh on all open client devices."""
    ARCHIVE_STATE["version"] = int(time.time() * 1000)
    ARCHIVE_STATE["last_action"] = action

def get_network_ip():
    """Detect LAN Wi-Fi IP address for local network testing."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "college_resource_hub_super_secret_session_key_2026"
CORS(app)

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "jpg", "jpeg", "png"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_current_user():
    """Retrieve logged-in user from session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_db()
    user = conn.execute("SELECT id, name, college_id, email, branch, role FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


def is_admin(user):
    return user and user.get("role") == "admin"


# ==========================================
# AUTHENTICATION APIS
# ==========================================

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    college_id = data.get("college_id", "").strip().upper()
    email = data.get("email", "").strip().lower()
    branch = data.get("branch", "").strip()
    password = data.get("password", "").strip()

    if not all([name, college_id, email, branch, password]):
        return jsonify({"success": False, "error": "All fields are required"}), 400

    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Check if college_id or email already exists
    existing = cursor.execute(
        "SELECT id FROM users WHERE email = ? OR college_id = ?", (email, college_id)
    ).fetchone()

    if existing:
        conn.close()
        return jsonify({"success": False, "error": "An account with this Email or College ID already exists"}), 409

    hashed = hash_password(password)
    cursor.execute("""
        INSERT INTO users (name, college_id, email, branch, password_hash, role)
        VALUES (?, ?, ?, ?, ?, 'student')
    """, (name, college_id, email, branch, hashed))
    conn.commit()

    user_id = cursor.lastrowid
    user_data = {
        "id": user_id,
        "name": name,
        "college_id": college_id,
        "email": email,
        "branch": branch,
        "role": "student"
    }
    session["user_id"] = user_id
    conn.close()

    return jsonify({"success": True, "message": "Account created successfully!", "user": user_data}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    identifier = data.get("identifier", "").strip()
    password = data.get("password", "").strip()
    expected_role = data.get("role", "").strip().lower()

    if not identifier or not password:
        return jsonify({"success": False, "error": "Email/College ID and Password are required"}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Find user by email or college_id
    user = cursor.execute("""
        SELECT id, name, college_id, email, branch, password_hash, role
        FROM users
        WHERE LOWER(email) = LOWER(?) OR UPPER(college_id) = UPPER(?)
    """, (identifier, identifier)).fetchone()

    conn.close()

    if not user:
        return jsonify({"success": False, "error": "Invalid credentials or account not found"}), 401

    if hash_password(password) != user["password_hash"]:
        return jsonify({"success": False, "error": "Incorrect password"}), 401

    if expected_role and user["role"] != expected_role:
        return jsonify({
            "success": False,
            "error": f"Role mismatch: This account is registered as '{user['role']}', not '{expected_role}'."
        }), 403

    session["user_id"] = user["id"]
    user_data = {
        "id": user["id"],
        "name": user["name"],
        "college_id": user["college_id"],
        "email": user["email"],
        "branch": user["branch"],
        "role": user["role"]
    }

    return jsonify({"success": True, "message": f"Welcome, {user['name']}!", "user": user_data})


@app.route("/api/auth/me", methods=["GET"])
def me():
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False, "user": None})
    return jsonify({"authenticated": True, "user": user})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"success": True, "message": "Logged out successfully"})


@app.route("/api/auth/admins", methods=["GET"])
def list_admins():
    conn = get_db()
    admins = conn.execute("""
        SELECT id, name, college_id, email, branch, role, created_at
        FROM users
        WHERE role = 'admin'
        ORDER BY id ASC
    """).fetchall()
    conn.close()
    return jsonify({"success": True, "admins": [dict(a) for a in admins]})


# ==========================================
# PAPERS & RESOURCES APIS
# ==========================================

@app.route("/api/papers", methods=["GET"])
def get_papers():
    """Retrieve papers with flexible filtering and search."""
    branch = request.args.get("branch")
    semester = request.args.get("semester")
    subject = request.args.get("subject")
    exam_type = request.args.get("exam_type")
    exam_year = request.args.get("year")
    search_query = request.args.get("search", "").strip()

    conn = get_db()

    query = """
        SELECT p.*,
               COALESCE(AVG(r.rating), 0) as avg_rating,
               COUNT(r.id) as rating_count
        FROM papers p
        LEFT JOIN ratings r ON p.id = r.paper_id
        WHERE 1=1
    """
    params = []

    if branch:
        query += " AND p.branch = ?"
        params.append(branch)

    if semester:
        query += " AND p.semester = ?"
        params.append(semester)

    if subject:
        query += " AND LOWER(p.subject) = LOWER(?)"
        params.append(subject)

    if exam_type:
        query += " AND p.exam_type = ?"
        params.append(exam_type)

    if exam_year:
        query += " AND p.exam_year = ?"
        params.append(exam_year)

    if search_query:
        query += " AND (p.title LIKE ? OR p.subject LIKE ? OR p.branch LIKE ? OR p.exam_type LIKE ? OR p.exam_year LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term, term, term])

    query += " GROUP BY p.id ORDER BY p.exam_year DESC, p.created_at DESC"

    papers = conn.execute(query, params).fetchall()
    conn.close()

    result = []
    for p in papers:
        d = dict(p)
        d["avg_rating"] = round(d["avg_rating"], 1)
        result.append(d)

    return jsonify({"success": True, "count": len(result), "papers": result})


@app.route("/api/papers", methods=["POST"])
def upload_paper():
    """Admin-only endpoint to upload new question paper."""
    user = get_current_user()
    if not is_admin(user):
        return jsonify({"success": False, "error": "Unauthorized: Admin privileges required to upload papers."}), 403

    title = request.form.get("title", "").strip()
    branch = request.form.get("branch", "").strip()
    year_of_study = request.form.get("year_of_study", "").strip()
    semester = request.form.get("semester", "").strip()
    subject = request.form.get("subject", "").strip()
    exam_type = request.form.get("exam_type", "").strip()
    exam_year = request.form.get("exam_year", "").strip()

    if not all([branch, semester, subject, exam_type, exam_year]):
        return jsonify({"success": False, "error": "Missing required metadata fields"}), 400

    if not title:
        title = f"{subject} — {exam_type} ({exam_year})"

    try:
        year_num = int(year_of_study) if year_of_study else 1
    except ValueError:
        year_num = 1

    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "No question paper file provided"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Invalid file format. Allowed: PDF, DOCX, DOC, JPG, PNG"}), 400

    raw_filename = secure_filename(file.filename)
    extension = raw_filename.rsplit(".", 1)[1].lower() if "." in raw_filename else "pdf"
    clean_prefix = re.sub(r'[^a-zA-Z0-9_-]', '_', f"{branch}_{subject}_{exam_type}_{exam_year}")
    timestamp = int(os.times().system * 1000)
    saved_filename = f"{clean_prefix}_{timestamp}.{extension}"
    saved_path = os.path.join(UPLOADS_DIR, saved_filename)

    file.save(saved_path)
    file_size = os.path.getsize(saved_path)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO papers (
            title, branch, year_of_study, semester, subject,
            exam_type, exam_year, file_name, file_path, file_size,
            uploaded_by, uploader_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title, branch, year_num, semester, subject,
        exam_type, exam_year, saved_filename, saved_path, file_size,
        user["id"], user["name"]
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    notify_archive_change("paper_uploaded")

    return jsonify({
        "success": True,
        "message": "Question paper uploaded and cataloged successfully!",
        "paper_id": new_id
    }), 201


@app.route("/api/papers/<int:paper_id>", methods=["PUT"])
def update_paper(paper_id):
    """Admin-only endpoint to update paper metadata."""
    user = get_current_user()
    if not is_admin(user):
        return jsonify({"success": False, "error": "Unauthorized: Admin privileges required."}), 403

    data = request.get_json() or {}
    title = data.get("title", "").strip()
    branch = data.get("branch", "").strip()
    semester = data.get("semester", "").strip()
    subject = data.get("subject", "").strip()
    exam_type = data.get("exam_type", "").strip()
    exam_year = data.get("exam_year", "").strip()

    conn = get_db()
    paper = conn.execute("SELECT id FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if not paper:
        conn.close()
        return jsonify({"success": False, "error": "Paper not found"}), 404

    conn.execute("""
        UPDATE papers
        SET title = COALESCE(NULLIF(?, ''), title),
            branch = COALESCE(NULLIF(?, ''), branch),
            semester = COALESCE(NULLIF(?, ''), semester),
            subject = COALESCE(NULLIF(?, ''), subject),
            exam_type = COALESCE(NULLIF(?, ''), exam_type),
            exam_year = COALESCE(NULLIF(?, ''), exam_year)
        WHERE id = ?
    """, (title, branch, semester, subject, exam_type, exam_year, paper_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Paper details updated successfully."})


@app.route("/api/papers/<int:paper_id>", methods=["DELETE"])
def delete_paper(paper_id):
    """Admin-only endpoint to delete paper from database and disk."""
    user = get_current_user()
    if not is_admin(user):
        return jsonify({"success": False, "error": "Unauthorized: Admin privileges required."}), 403

    conn = get_db()
    paper = conn.execute("SELECT file_path FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if not paper:
        conn.close()
        return jsonify({"success": False, "error": "Paper not found"}), 404

    # Remove physical file if exists
    file_path = paper["file_path"]
    if file_path and os.path.exists(file_path):
        try:
            import gc
            gc.collect()
            os.remove(file_path)
        except Exception as e:
            app.logger.warning(f"Failed to delete file from disk: {e}")

    conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
    conn.commit()
    conn.close()

    notify_archive_change("paper_deleted")

    return jsonify({"success": True, "message": "Paper removed from archive successfully."})


@app.route("/api/papers/<int:paper_id>/download", methods=["GET"])
def download_paper(paper_id):
    conn = get_db()
    paper = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()

    if not paper:
        conn.close()
        return jsonify({"error": "File not found"}), 404

    # Increment download counter
    conn.execute("UPDATE papers SET download_count = download_count + 1 WHERE id = ?", (paper_id,))
    conn.commit()
    conn.close()

    file_path = paper["file_path"]
    if not os.path.exists(file_path):
        return jsonify({"error": "Physical file missing on server"}), 404

    download_name = f"{paper['subject']}_{paper['exam_type']}_{paper['exam_year']}.pdf"
    return send_file(file_path, as_attachment=True, download_name=download_name)


@app.route("/api/papers/<int:paper_id>/view", methods=["GET"])
def view_paper(paper_id):
    conn = get_db()
    paper = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    conn.close()

    if not paper:
        return jsonify({"error": "File not found"}), 404

    file_path = paper["file_path"]
    if not os.path.exists(file_path):
        return jsonify({"error": "Physical file missing on server"}), 404

    # Inline preview (browser opens PDF directly)
    return send_file(file_path, mimetype="application/pdf", as_attachment=False)


# ==========================================
# RATINGS & REVIEWS
# ==========================================

@app.route("/api/papers/<int:paper_id>/rate", methods=["POST"])
def rate_paper(paper_id):
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "error": "Please login to submit a rating"}), 401

    data = request.get_json() or {}
    rating = data.get("rating")
    comment = data.get("comment", "").strip()

    if not rating or not (1 <= int(rating) <= 5):
        return jsonify({"success": False, "error": "Rating must be an integer between 1 and 5"}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Insert or update rating
    cursor.execute("""
        INSERT INTO ratings (paper_id, user_id, user_name, rating, comment)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(paper_id, user_id) DO UPDATE SET
            rating = excluded.rating,
            comment = excluded.comment,
            created_at = CURRENT_TIMESTAMP
    """, (paper_id, user["id"], user["name"], int(rating), comment))

    conn.commit()
    conn.close()

    notify_archive_change("paper_rated")

    return jsonify({"success": True, "message": "Rating saved successfully!"})


@app.route("/api/papers/<int:paper_id>/ratings", methods=["GET"])
def get_paper_ratings(paper_id):
    conn = get_db()
    ratings = conn.execute("""
        SELECT rating, comment, user_name, created_at
        FROM ratings
        WHERE paper_id = ?
        ORDER BY created_at DESC
    """, (paper_id,)).fetchall()
    conn.close()
    return jsonify({"success": True, "ratings": [dict(r) for r in ratings]})


# ==========================================
# HIERARCHY & STATS
# ==========================================

@app.route("/api/hierarchy", methods=["GET"])
def get_hierarchy():
    """Return complete academic dictionary for fast client-side navigation."""
    return jsonify({"success": True, "hierarchy": ACADEMIC_HIERARCHY})


@app.route("/api/stats", methods=["GET"])
def get_stats():
    conn = get_db()
    papers_count = conn.execute("SELECT COUNT(*) as c FROM papers").fetchone()["c"]
    downloads_count = conn.execute("SELECT COALESCE(SUM(download_count), 0) as s FROM papers").fetchone()["s"]
    users_count = conn.execute("SELECT COUNT(*) as u FROM users").fetchone()["u"]
    admins_count = conn.execute("SELECT COUNT(*) as a FROM users WHERE role = 'admin'").fetchone()["a"]
    conn.close()

    return jsonify({
        "success": True,
        "stats": {
            "papers": papers_count,
            "downloads": downloads_count,
            "users": users_count,
            "admins": admins_count,
            "branches": len(ACADEMIC_HIERARCHY)
        }
    })


@app.route("/api/sync/status", methods=["GET"])
def get_sync_status():
    """Return real-time sync state, paper count, and network connection URL for sharing."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) as c FROM papers").fetchone()["c"]
    downloads = conn.execute("SELECT COALESCE(SUM(download_count), 0) as s FROM papers").fetchone()["s"]
    conn.close()

    network_ip = get_network_ip()
    port = 5000
    network_url = f"http://{network_ip}:{port}"

    return jsonify({
        "success": True,
        "version": ARCHIVE_STATE["version"],
        "last_action": ARCHIVE_STATE["last_action"],
        "papers_count": count,
        "downloads_count": downloads,
        "network_ip": network_ip,
        "network_url": network_url,
        "public_url": get_public_tunnel_url(),
        "server_time": int(time.time())
    })


@app.route("/api/recent-papers", methods=["GET"])
def get_recent_papers():
    """Retrieve 6 most recently uploaded question papers for the dashboard live feed."""
    conn = get_db()
    papers = conn.execute("""
        SELECT p.*,
               COALESCE(AVG(r.rating), 0) as avg_rating,
               COUNT(r.id) as rating_count
        FROM papers p
        LEFT JOIN ratings r ON p.id = r.paper_id
        GROUP BY p.id
        ORDER BY p.id DESC
        LIMIT 6
    """).fetchall()
    conn.close()
    return jsonify({"success": True, "papers": [dict(p) for p in papers]})


# ==========================================
# STUDENT UTILITY TOOLS APIS
# ==========================================

@app.route("/api/tools/merge-pdf", methods=["POST"])
def tool_merge_pdf():
    """Merge 2 or more PDF files into a single unified PDF."""
    files = request.files.getlist("files")
    if not files or len(files) < 2:
        return jsonify({"success": False, "error": "Please select at least 2 PDF files to merge"}), 400

    writer = PdfWriter()
    total_pages = 0

    try:
        for f in files:
            if not f.filename.lower().endswith(".pdf"):
                return jsonify({"success": False, "error": f"File '{f.filename}' is not a valid PDF"}), 400
            reader = PdfReader(f.stream)
            for page in reader.pages:
                writer.add_page(page)
                total_pages += 1

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        custom_name = request.form.get("output_name", "merged_document").strip()
        if not custom_name.lower().endswith(".pdf"):
            custom_name += ".pdf"
        custom_name = secure_filename(custom_name) or "merged_document.pdf"

        return send_file(
            output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=custom_name
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to merge PDFs: {str(e)}"}), 500


@app.route("/api/tools/image-to-pdf", methods=["POST"])
def tool_image_to_pdf():
    """Convert one or more images (JPG, PNG, WebP) into an A4 PDF."""
    files = request.files.getlist("images") or request.files.getlist("files")
    if not files:
        return jsonify({"success": False, "error": "Please select at least 1 image file"}), 400

    pil_images = []
    allowed_img = {"jpg", "jpeg", "png", "webp", "bmp"}

    try:
        for f in files:
            ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
            if ext not in allowed_img:
                return jsonify({"success": False, "error": f"Unsupported image format in '{f.filename}'"}), 400

            img = Image.open(f.stream)
            if img.mode in ("RGBA", "P"):
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    rgb_img.paste(img, mask=img.split()[3])
                else:
                    rgb_img.paste(img)
                pil_images.append(rgb_img)
            else:
                pil_images.append(img.convert("RGB"))

        if not pil_images:
            return jsonify({"success": False, "error": "No valid images could be processed"}), 400

        output = io.BytesIO()
        first = pil_images[0]
        first.save(
            output,
            format="PDF",
            save_all=True,
            append_images=pil_images[1:],
            resolution=100.0
        )
        output.seek(0)

        custom_name = request.form.get("output_name", "converted_photos").strip()
        if not custom_name.lower().endswith(".pdf"):
            custom_name += ".pdf"
        custom_name = secure_filename(custom_name) or "converted_photos.pdf"

        return send_file(
            output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=custom_name
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to convert images to PDF: {str(e)}"}), 500


@app.route("/api/tools/text-to-pdf", methods=["POST"])
def tool_text_to_pdf():
    """Generate a clean, styled academic PDF from title, student name, and text."""
    if request.is_json:
        data = request.get_json() or {}
        title = data.get("title", "Lecture Notes").strip()
        author = data.get("author", "Student").strip()
        subject = data.get("subject", "").strip()
        content = data.get("content", "").strip()
    else:
        title = request.form.get("title", "Lecture Notes").strip()
        author = request.form.get("author", "Student").strip()
        subject = request.form.get("subject", "").strip()
        content = request.form.get("content", "").strip()

    if not content:
        return jsonify({"success": False, "error": "Document content text is required"}), 400

    try:
        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'AcademicTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1B2A41"),
            spaceAfter=6
        )

        sub_style = ParagraphStyle(
            'AcademicSub',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#6E7F6C"),
            spaceAfter=14
        )

        body_style = ParagraphStyle(
            'AcademicBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#21201C"),
            spaceAfter=8
        )

        story = []
        story.append(Paragraph(title, title_style))
        meta_info = f"Author: {author}" + (f" • Subject: {subject}" if subject else "")
        story.append(Paragraph(meta_info, sub_style))
        story.append(Spacer(1, 10))

        for line in content.split("\n"):
            line = line.strip()
            if line:
                escaped = (
                    line.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                )
                story.append(Paragraph(escaped, body_style))
            else:
                story.append(Spacer(1, 6))

        doc.build(story)
        output.seek(0)

        filename = secure_filename(title.replace(" ", "_")) or "notes"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        return send_file(
            output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to generate PDF from text: {str(e)}"}), 500


@app.route("/api/tools/document-to-pdf", methods=["POST"])
def tool_document_to_pdf():
    """Convert .docx, .txt, or .md file into academic formatted PDF."""
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"success": False, "error": "Please provide a document file"}), 400

    filename = file.filename.lower()
    paragraphs = []
    doc_title = file.filename.rsplit(".", 1)[0]

    try:
        if filename.endswith(".docx"):
            doc_file = docx.Document(file.stream)
            for p in doc_file.paragraphs:
                text = p.text.strip()
                if text:
                    paragraphs.append(text)
        elif filename.endswith(".txt") or filename.endswith(".md"):
            content = file.stream.read().decode("utf-8", errors="replace")
            for line in content.splitlines():
                text = line.strip()
                if text:
                    paragraphs.append(text)
        else:
            return jsonify({"success": False, "error": "Only .docx, .txt, and .md files are supported"}), 400

        if not paragraphs:
            return jsonify({"success": False, "error": "The uploaded document contains no readable text"}), 400

        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1B2A41"),
            spaceAfter=12
        )

        body_style = ParagraphStyle(
            'DocBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#21201C"),
            spaceAfter=7
        )

        story = [Paragraph(doc_title, title_style), Spacer(1, 8)]
        for p_text in paragraphs:
            escaped = (
                p_text.replace("&", "&amp;")
                      .replace("<", "&lt;")
                      .replace(">", "&gt;")
            )
            story.append(Paragraph(escaped, body_style))

        doc.build(story)
        output.seek(0)

        out_name = secure_filename(doc_title) or "document"
        return send_file(
            output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{out_name}.pdf"
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to convert document: {str(e)}"}), 500


@app.route("/api/tools/calculate-attendance", methods=["POST"])
def tool_calculate_attendance():
    """Calculate attendance percentage, status, safe bunks and catch-up count."""
    data = request.get_json() or {}
    try:
        total = int(data.get("total", 0))
        attended = int(data.get("attended", 0))
        target = float(data.get("target", 75.0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid numerical parameters"}), 400

    if total < 0 or attended < 0:
        return jsonify({"success": False, "error": "Total and attended lectures cannot be negative"}), 400

    if attended > total:
        return jsonify({"success": False, "error": "Attended lectures cannot exceed total conducted lectures"}), 400

    if target <= 0 or target > 100:
        return jsonify({"success": False, "error": "Target percentage must be between 1 and 100"}), 400

    if total == 0:
        return jsonify({
            "success": True,
            "total": 0,
            "attended": 0,
            "percentage": 0.0,
            "target": target,
            "status": "neutral",
            "message": "No lectures recorded yet"
        })

    percent = round((attended / total) * 100, 2)

    if percent >= target:
        status = "safe"
        msg = f"Eligible for examinations: You meet the mandatory {target}% attendance criteria."
    elif percent >= 65:
        status = "warning"
        msg = f"Borderline: Current attendance is {percent}%, below the required {target}% threshold."
    else:
        status = "danger"
        msg = f"Attendance warning: Current attendance is {percent}%, which puts you at risk of being debarred."

    return jsonify({
        "success": True,
        "total": total,
        "attended": attended,
        "percentage": percent,
        "target": target,
        "status": status,
        "message": msg
    })


# ==========================================
# FRONTEND PAGES
# ==========================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login_page():
    return send_from_directory(".", "login.html")


@app.route("/register")
def register_page():
    return send_from_directory(".", "register.html")


@app.route("/hub")
def hub_page():
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
    
    # Start Cloudflare Tunnel once (in reloader parent process)
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        start_public_tunnel(port=5000)

    print("Starting College Resource Hub server on http://127.0.0.1:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=True)
