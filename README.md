# 🎓 College Resource Hub — Capstone Project

> An intelligent, full-stack Academic Archive & Question Paper Resource Hub built with Python (Flask), SQLite, and modern Vanilla Web Architecture.

---

## 📌 Project Overview
**College Resource Hub** is a centralized digital repository designed for college students and faculty. It allows seamless browsing, searching, downloading, and uploading of Previous Year Question Papers (PYQs) across different academic branches, semesters, and subjects.

### Key Features:
- 📚 **Academic Hierarchy & Archive:** Filter question papers by Year, Branch, Semester, Subject, and Exam Type (IAE 1, IAE 2, END SEM).
- ⚡ **Instant Search & Filters:** Real-time search across question paper titles, subjects, and years.
- 🔐 **Role-Based Access Control (RBAC):**
  - **Student Access:** Browse, search, preview, and download papers, rate resources, calculate attendance.
  - **Administrator Access:** Upload new PYQs, manage records, view resource analytics.
- 📊 **Smart Attendance Tracker:** Calculates attendance percentage and verifies eligibility for semester examinations.
- 🛠️ **Built-in PDF & Document Tools:** In-browser document preview and operations.
- 🌐 **Cloudflare Remote Tunnel Support:** Built-in tunnel integration for sharing live public access securely across mobile devices and networks.

---

## 🛠️ Technology Stack
- **Backend:** Python 3.8+, Flask, Werkzeug, Flask-CORS
- **Database:** SQLite3 (Local, lightweight, zero-configuration database)
- **Document Processing:** PyPDF, python-docx, Pillow, ReportLab
- **Frontend:** Responsive HTML5, Vanilla CSS3 (Custom design system), Vanilla JavaScript (ES6+)

---

## 🚀 How to Run the Project

### Option 1: 1-Click Launch on Windows (Recommended)
1. Clone or download this repository:
   ```bash
   git clone https://github.com/AnukalpSharma1100/Capstone-Project.git
   cd Capstone-Project
   ```
2. Simply double-click **`run.bat`**.
   - It will automatically verify Python, install required dependencies from `requirements.txt` if missing, launch the server, and automatically open your default browser to `http://127.0.0.1:5000`.

---

### Option 2: Manual Setup (Windows, macOS, Linux)
1. **Clone the repository:**
   ```bash
   git clone https://github.com/AnukalpSharma1100/Capstone-Project.git
   cd Capstone-Project
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the application server:**
   ```bash
   python app.py
   ```

4. **Access in browser:**
   Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in Chrome, Edge, Safari, or Firefox.

---

## 🔑 Demo Login Credentials
The system comes pre-seeded with sample administrator and student credentials for evaluation:

| Role | Name | Email / College ID | Password |
|---|---|---|---|
| **Head Admin** | Anukalp Sharma | `admin1@college.edu` | `happy1100` |
| **Admin** | Prachi Sharma | `admin2@college.edu` | `prachi1100` |
| **Admin** | Johara Shaikh | `admin3@college.edu` | `johara1100` |
| **Student** | Test Student | `student@college.edu` | `student123` |

*New students can also create their own accounts instantly using the `/register` page.*

---

## 🧪 Testing Backend Integrity
To verify the database, routes, and APIs at any time, run:
```bash
python test_backend.py
```
This runs 7 comprehensive automated unit tests covering authentication, academic hierarchy, paper management, attendance calculations, and document processing.
