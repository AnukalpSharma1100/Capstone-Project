"""
Database module for College Resource Hub
Provides SQLite initialization, migrations, CRUD operations, and pre-seeded data.
"""

import os
import sqlite3
import hashlib
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "papers")

os.makedirs(UPLOADS_DIR, exist_ok=True)


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = "college_resource_hub_salt_2026"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def get_db():
    """Get a database connection with dict-like row factory."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database tables and seed default admins, subjects, and sample papers."""
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        college_id TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        branch TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Question Papers / Resources table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS papers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        branch TEXT NOT NULL,
        year_of_study INTEGER NOT NULL,
        semester TEXT NOT NULL,
        subject TEXT NOT NULL,
        exam_type TEXT NOT NULL,
        exam_year TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        uploaded_by INTEGER NOT NULL,
        uploader_name TEXT NOT NULL,
        download_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (uploaded_by) REFERENCES users (id) ON DELETE SET NULL
    );
    """)

    # Ratings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(paper_id, user_id),
        FOREIGN KEY (paper_id) REFERENCES papers (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    conn.commit()

    # Seed Default 3 Admins
    admins = [
        {
            "name": "Anukalp Sharma (Head Admin)",
            "college_id": "ADM001",
            "email": "admin1@college.edu",
            "branch": "COMPS",
            "password": "happy1100",
            "role": "admin"
        },
        {
            "name": "Prachi Sharma (Exam Cell Admin)",
            "college_id": "ADM002",
            "email": "admin2@college.edu",
            "branch": "AIML",
            "password": "prachi1100",
            "role": "admin"
        },
        {
            "name": "Johara Shaikh (Archive Officer)",
            "college_id": "ADM003",
            "email": "admin3@college.edu",
            "branch": "IT",
            "password": "johara1100",
            "role": "admin"
        }
    ]

    for adm in admins:
        cursor.execute("SELECT id FROM users WHERE email = ?", (adm["email"],))
        existing_admin = cursor.fetchone()
        if not existing_admin:
            cursor.execute("""
                INSERT INTO users (name, college_id, email, branch, password_hash, role)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                adm["name"],
                adm["college_id"],
                adm["email"],
                adm["branch"],
                hash_password(adm["password"]),
                adm["role"]
            ))
        else:
            # Update name, college_id, and password_hash to ensure specified credentials are active
            cursor.execute("""
                UPDATE users SET name = ?, college_id = ?, password_hash = ? WHERE email = ?
            """, (adm["name"], adm["college_id"], hash_password(adm["password"]), adm["email"]))

    # Seed Demo Student
    demo_student = {
        "name": "Rahul Verma",
        "college_id": "STU202401",
        "email": "student@college.edu",
        "branch": "AIML",
        "password": "student123",
        "role": "student"
    }
    cursor.execute("SELECT id FROM users WHERE email = ?", (demo_student["email"],))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (name, college_id, email, branch, password_hash, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            demo_student["name"],
            demo_student["college_id"],
            demo_student["email"],
            demo_student["branch"],
            hash_password(demo_student["password"]),
            demo_student["role"]
        ))

    conn.commit()

    # Seed Sample Papers if table is empty
    cursor.execute("SELECT COUNT(*) as cnt FROM papers")
    if cursor.fetchone()["cnt"] == 0:
        seed_sample_papers(cursor)
        conn.commit()

    conn.close()


def seed_sample_papers(cursor):
    """Seed initial sample question papers with real demo PDF content."""
    cursor.execute("SELECT id, name FROM users WHERE email = 'admin1@college.edu'")
    admin = cursor.fetchone()
    admin_id = admin["id"] if admin else 1
    admin_name = admin["name"] if admin else "Prof. Sharma"

    sample_items = [
        {
            "title": "Data Structures - End Sem 2024 Question Paper",
            "branch": "AIML",
            "year_of_study": 2,
            "semester": "Semester 3",
            "subject": "Data Structures",
            "exam_type": "END SEM",
            "exam_year": "2024",
            "content": "%PDF-1.4\n% Sample Question Paper - Data Structures END SEM 2024\n1. Explain Binary Search Trees and AVL Trees.\n2. Write Dijkstra Algorithm for shortest path.\n3. Differentiate between Stack and Queue."
        },
        {
            "title": "DBMS - IAE 1 2024 Question Paper",
            "branch": "AIML",
            "year_of_study": 2,
            "semester": "Semester 3",
            "subject": "DBMS",
            "exam_type": "IAE 1",
            "exam_year": "2024",
            "content": "%PDF-1.4\n% Sample Question Paper - DBMS IAE 1 2024\n1. Explain ER Model concepts and attributes.\n2. What is 3NF and BCNF normalization?\n3. Write SQL queries for JOIN operations."
        },
        {
            "title": "Machine Learning I - End Sem 2024 Question Paper",
            "branch": "AIML",
            "year_of_study": 2,
            "semester": "Semester 4",
            "subject": "Machine Learning I",
            "exam_type": "END SEM",
            "exam_year": "2024",
            "content": "%PDF-1.4\n% Sample Question Paper - Machine Learning I 2024\n1. Explain Linear Regression vs Logistic Regression.\n2. Derive Decision Tree Information Gain.\n3. What is Bias-Variance tradeoff?"
        },
        {
            "title": "Engineering Mathematics I - End Sem 2024",
            "branch": "FIRST YEAR",
            "year_of_study": 1,
            "semester": "Semester 1",
            "subject": "Engineering Mathematics I",
            "exam_type": "END SEM",
            "exam_year": "2024",
            "content": "%PDF-1.4\n% Sample Question Paper - Engineering Mathematics I\n1. Find eigenvalues and eigenvectors of Matrix A.\n2. State and prove Euler's Theorem for homogeneous functions.\n3. Test convergence of infinite series."
        },
        {
            "title": "Engineering Physics - IAE 2 2023",
            "branch": "FIRST YEAR",
            "year_of_study": 1,
            "semester": "Semester 1",
            "subject": "Engineering Physics",
            "exam_type": "IAE 2",
            "exam_year": "2023",
            "content": "%PDF-1.4\n% Sample Question Paper - Engineering Physics\n1. Explain Interference in thin films.\n2. What is Laser population inversion?\n3. Explain Heisenberg Uncertainty Principle."
        },
        {
            "title": "Algorithms - End Sem 2024",
            "branch": "COMPS",
            "year_of_study": 2,
            "semester": "Semester 4",
            "subject": "Algorithms",
            "exam_type": "END SEM",
            "exam_year": "2024",
            "content": "%PDF-1.4\n% Sample Question Paper - Algorithms\n1. Explain Master Theorem with examples.\n2. Describe 0/1 Knapsack problem using Dynamic Programming.\n3. Explain Kruskal's algorithm for MST."
        },
        {
            "title": "Computer Networks - IAE 1 2025",
            "branch": "IT",
            "year_of_study": 2,
            "semester": "Semester 4",
            "subject": "Computer Networks",
            "exam_type": "IAE 1",
            "exam_year": "2025",
            "content": "%PDF-1.4\n% Sample Question Paper - Computer Networks\n1. Compare OSI 7-Layer model and TCP/IP protocol suite.\n2. Explain CSMA/CD and collision detection.\n3. Describe IPv4 packet header structure."
        }
    ]

    for item in sample_items:
        clean_filename = f"{item['branch']}_{item['subject'].replace(' ', '_')}_{item['exam_type'].replace(' ', '_')}_{item['exam_year']}.pdf"
        file_path = os.path.join(UPLOADS_DIR, clean_filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(item["content"])

        cursor.execute("""
            INSERT INTO papers (
                title, branch, year_of_study, semester, subject,
                exam_type, exam_year, file_name, file_path, file_size,
                uploaded_by, uploader_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["title"],
            item["branch"],
            item["year_of_study"],
            item["semester"],
            item["subject"],
            item["exam_type"],
            item["exam_year"],
            clean_filename,
            file_path,
            os.path.getsize(file_path),
            admin_id,
            admin_name
        ))


# Academic Hierarchy Data (Dictionary/HashMap)
ACADEMIC_HIERARCHY = {
    "FIRST YEAR": {
        1: {
            "Semester 1": [
                "Engineering Mathematics I",
                "Engineering Physics",
                "Engineering Chemistry",
                "Basic Programming"
            ],
            "Semester 2": [
                "Engineering Mathematics II",
                "Applied Physics",
                "Engineering Graphics",
                "Problem Solving with C"
            ]
        }
    },
    "AIML": {
        2: {
            "Semester 3": [
                "Data Structures",
                "DBMS",
                "Discrete Mathematics",
                "Python for AI",
                "Linear Algebra for AI (LAIOA)"
            ],
            "Semester 4": [
                "Design & Analysis of Algorithms",
                "Operating Systems",
                "Computer Networks",
                "Machine Learning I"
            ]
        },
        3: {
            "Semester 5": [
                "Machine Learning II",
                "Deep Learning",
                "Software Engineering",
                "NLP"
            ],
            "Semester 6": [
                "Computer Vision",
                "Big Data Analytics",
                "Cloud Computing",
                "AI Ethics"
            ]
        },
        4: {
            "Semester 7": [
                "Reinforcement Learning",
                "MLOps",
                "Elective I",
                "Project Phase I"
            ],
            "Semester 8": [
                "Elective II",
                "Industry Internship",
                "Project Phase II"
            ]
        }
    },
    "DS": {
        2: {
            "Semester 3": [
                "Data Structures",
                "DBMS",
                "Statistics for DS",
                "Python Programming"
            ],
            "Semester 4": [
                "Algorithms",
                "Operating Systems",
                "Data Visualization",
                "Probability Theory"
            ]
        },
        3: {
            "Semester 5": [
                "Data Mining",
                "Big Data Technologies",
                "Software Engineering",
                "R Programming"
            ],
            "Semester 6": [
                "Predictive Analytics",
                "Cloud Computing",
                "Data Warehousing",
                "Time Series Analysis"
            ]
        },
        4: {
            "Semester 7": [
                "Deep Learning for DS",
                "Business Analytics",
                "Elective I",
                "Project Phase I"
            ],
            "Semester 8": [
                "Elective II",
                "Industry Internship",
                "Project Phase II"
            ]
        }
    },
    "COMPS": {
        2: {
            "Semester 3": [
                "Data Structures",
                "DBMS",
                "Discrete Mathematics",
                "Computer Organization"
            ],
            "Semester 4": [
                "Algorithms",
                "Operating Systems",
                "Computer Networks",
                "OOP with Java"
            ]
        },
        3: {
            "Semester 5": [
                "Software Engineering",
                "Web Technologies",
                "Theory of Computation",
                "Cyber Security"
            ],
            "Semester 6": [
                "Cloud Computing",
                "Compiler Design",
                "Mobile Computing",
                "Distributed Systems"
            ]
        },
        4: {
            "Semester 7": [
                "Machine Learning",
                "Elective I",
                "Project Phase I",
                "Blockchain"
            ],
            "Semester 8": [
                "Elective II",
                "Industry Internship",
                "Project Phase II"
            ]
        }
    },
    "IT": {
        2: {
            "Semester 3": [
                "Data Structures",
                "DBMS",
                "Discrete Mathematics",
                "Computer Organization"
            ],
            "Semester 4": [
                "Algorithms",
                "Operating Systems",
                "Computer Networks",
                "Web Programming"
            ]
        },
        3: {
            "Semester 5": [
                "Software Engineering",
                "Information Storage & Retrieval",
                "Theory of Computation",
                "Cyber Security"
            ],
            "Semester 6": [
                "Cloud Computing",
                "Data Warehousing",
                "Mobile Computing",
                "IT Service Management"
            ]
        },
        4: {
            "Semester 7": [
                "Machine Learning",
                "Elective I",
                "Project Phase I",
                "Enterprise Systems"
            ],
            "Semester 8": [
                "Elective II",
                "Industry Internship",
                "Project Phase II"
            ]
        }
    },
    "ECS": {
        2: {
            "Semester 3": [
                "Circuit Theory",
                "Digital Electronics",
                "Signals & Systems",
                "Electronic Devices"
            ],
            "Semester 4": [
                "Analog Electronics",
                "Microprocessors",
                "Control Systems",
                "EM Theory"
            ]
        },
        3: {
            "Semester 5": [
                "VLSI Design",
                "Communication Systems",
                "Embedded Systems",
                "Digital Signal Processing"
            ],
            "Semester 6": [
                "Wireless Communication",
                "VLSI Testing",
                "Antenna Theory",
                "Optical Communication"
            ]
        },
        4: {
            "Semester 7": [
                "IoT Systems",
                "Elective I",
                "Project Phase I",
                "RF Engineering"
            ],
            "Semester 8": [
                "Elective II",
                "Industry Internship",
                "Project Phase II"
            ]
        }
    },
    "CIVIL": {
        2: {
            "Semester 3": [
                "Strength of Materials",
                "Fluid Mechanics",
                "Surveying",
                "Building Materials"
            ],
            "Semester 4": [
                "Structural Analysis",
                "Concrete Technology",
                "Geotechnical Engineering",
                "Hydraulics"
            ]
        },
        3: {
            "Semester 5": [
                "Design of Steel Structures",
                "Transportation Engineering",
                "Environmental Engineering",
                "Estimation & Costing"
            ],
            "Semester 6": [
                "Design of Concrete Structures",
                "Foundation Engineering",
                "Water Resources Engineering",
                "Construction Management"
            ]
        },
        4: {
            "Semester 7": [
                "Earthquake Engineering",
                "Elective I",
                "Project Phase I",
                "Urban Planning"
            ],
            "Semester 8": [
                "Elective II",
                "Industry Internship",
                "Project Phase II"
            ]
        }
    },
    "MECHANICAL": {
        2: {
            "Semester 3": [
                "Thermodynamics",
                "Strength of Materials",
                "Manufacturing Processes",
                "Fluid Mechanics"
            ],
            "Semester 4": [
                "Machine Design I",
                "Heat Transfer",
                "Kinematics of Machinery",
                "Materials Science"
            ]
        },
        3: {
            "Semester 5": [
                "Machine Design II",
                "Dynamics of Machinery",
                "Refrigeration & AC",
                "Industrial Engineering"
            ],
            "Semester 6": [
                "CAD/CAM",
                "Automobile Engineering",
                "Power Plant Engineering",
                "Mechatronics"
            ]
        },
        4: {
            "Semester 7": [
                "Robotics",
                "Elective I",
                "Project Phase I",
                "Finite Element Analysis"
            ],
            "Semester 8": [
                "Elective II",
                "Industry Internship",
                "Project Phase II"
            ]
        }
    }
}
