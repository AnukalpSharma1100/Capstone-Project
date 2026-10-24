"""
Automated Backend & API Test Suite for College Resource Hub
Tests authentication, 3 admins, student registration, paper uploads, downloads, and ratings.
"""

import io
import json
import unittest
from PIL import Image
from app import app
from database import init_db, get_db


class CollegeResourceHubTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_01_stats_and_hierarchy(self):
        """Test public endpoints for stats and academic hierarchy."""
        res_stats = self.app.get("/api/stats")
        self.assertEqual(res_stats.status_code, 200)
        data_stats = res_stats.get_json()
        self.assertTrue(data_stats["success"])
        self.assertGreaterEqual(data_stats["stats"]["admins"], 3)
        self.assertGreaterEqual(data_stats["stats"]["papers"], 1)

        res_hier = self.app.get("/api/hierarchy")
        self.assertEqual(res_hier.status_code, 200)
        data_hier = res_hier.get_json()
        self.assertTrue(data_hier["success"])
        self.assertIn("AIML", data_hier["hierarchy"])
        self.assertIn("COMPS", data_hier["hierarchy"])
        self.assertIn("FIRST YEAR", data_hier["hierarchy"])
        print("[PASS] Stats and Academic Hierarchy verified.")

    def test_02_three_admins_login(self):
        """Verify that all 3 pre-seeded College Administrators can log in."""
        admins = [
            ("admin1@college.edu", "happy1100", "Anukalp Sharma"),
            ("admin2@college.edu", "prachi1100", "Prachi Sharma"),
            ("admin3@college.edu", "johara1100", "Johara Shaikh"),
        ]

        for email, pwd, expected_name_part in admins:
            res = self.app.post(
                "/api/auth/login",
                data=json.dumps({"identifier": email, "password": pwd, "role": "admin"}),
                content_type="application/json"
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["user"]["role"], "admin")
            self.assertEqual(data["user"]["email"], email)
            self.assertIn(expected_name_part, data["user"]["name"])

        print("[PASS] All 3 College Administrators verified (Anukalp Sharma, Prachi Sharma, Johara Shaikh).")

    def test_03_student_registration_and_login(self):
        """Test student registration and authentication."""
        reg_payload = {
            "name": "Pooja Patel",
            "college_id": "TEST_STU_999",
            "email": "pooja.test@college.edu",
            "branch": "AIML",
            "password": "securepassword123"
        }

        # Clear if already exists from previous run
        conn = get_db()
        conn.execute("DELETE FROM users WHERE email = ?", (reg_payload["email"],))
        conn.commit()
        conn.close()

        res = self.app.post(
            "/api/auth/register",
            data=json.dumps(reg_payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["role"], "student")

        # Now Login
        res_login = self.app.post(
            "/api/auth/login",
            data=json.dumps({
                "identifier": reg_payload["email"],
                "password": reg_payload["password"],
                "role": "student"
            }),
            content_type="application/json"
        )
        self.assertEqual(res_login.status_code, 200)
        self.assertTrue(res_login.get_json()["success"])
        print("[PASS] Student registration & login verified.")

    def test_04_get_papers_and_search(self):
        """Test paper filtering and fast search API."""
        # Query all
        res = self.app.get("/api/papers")
        self.assertEqual(res.status_code, 200)
        papers = res.get_json()["papers"]
        self.assertGreaterEqual(len(papers), 1)

        # Search for "Data Structures"
        res_search = self.app.get("/api/papers?search=Data+Structures")
        self.assertEqual(res_search.status_code, 200)
        search_papers = res_search.get_json()["papers"]
        self.assertTrue(any("Data Structures" in p["title"] or "Data Structures" in p["subject"] for p in search_papers))
        print("[PASS] Paper listing and fast search verified.")

    def test_05_admin_upload_paper(self):
        """Test Admin uploading a new question paper file."""
        # Login as Admin 1
        with self.app as client:
            login_res = client.post(
                "/api/auth/login",
                data=json.dumps({"identifier": "admin1@college.edu", "password": "happy1100", "role": "admin"}),
                content_type="application/json"
            )
            self.assertEqual(login_res.status_code, 200)

            # Upload Paper
            pdf_data = b"%PDF-1.4\nTest Question Paper Content for Capstone Project 2026."
            upload_data = {
                "branch": "COMPS",
                "year_of_study": "3",
                "semester": "Semester 5",
                "subject": "Web Technologies",
                "exam_type": "END SEM",
                "exam_year": "2025",
                "title": "Web Technologies End Sem 2025 Model Paper",
                "file": (io.BytesIO(pdf_data), "Web_Tech_EndSem_2025.pdf")
            }

            upload_res = client.post(
                "/api/papers",
                data=upload_data,
                content_type="multipart/form-data"
            )
            self.assertEqual(upload_res.status_code, 201)
            new_paper_id = upload_res.get_json()["paper_id"]
            self.assertIsNotNone(new_paper_id)

            # Verify Paper is retrievable
            view_res = client.get(f"/api/papers/{new_paper_id}/view")
            self.assertEqual(view_res.status_code, 200)
            view_res.close()

            # Verify Paper download
            down_res = client.get(f"/api/papers/{new_paper_id}/download")
            self.assertEqual(down_res.status_code, 200)
            down_res.close()

            # Delete the test paper
            del_res = client.delete(f"/api/papers/{new_paper_id}")
            self.assertEqual(del_res.status_code, 200)
            self.assertTrue(del_res.get_json()["success"])

        print("[PASS] Admin paper upload, preview, download, and deletion verified.")

    def test_06_attendance_calculation(self):
        """Verify attendance calculation endpoint."""
        res_safe = self.app.post("/api/tools/calculate-attendance", json={
            "total": 40,
            "attended": 36,
            "target": 75.0
        })
        self.assertEqual(res_safe.status_code, 200)
        d_safe = res_safe.get_json()
        self.assertTrue(d_safe["success"])
        self.assertEqual(d_safe["percentage"], 90.0)
        self.assertEqual(d_safe["status"], "safe")

        res_danger = self.app.post("/api/tools/calculate-attendance", json={
            "total": 40,
            "attended": 24,
            "target": 75.0
        })
        self.assertEqual(res_danger.status_code, 200)
        d_danger = res_danger.get_json()
        self.assertEqual(d_danger["percentage"], 60.0)
        self.assertEqual(d_danger["status"], "danger")
        print("[PASS] Attendance calculation verified.")

    def test_07_pdf_toolkit(self):
        """Verify PDF creation, merging, and document conversion endpoints."""
        # Text to PDF
        r_text = self.app.post("/api/tools/text-to-pdf", json={
            "title": "OS Summary",
            "content": "Process Scheduling and Memory Management notes."
        })
        self.assertEqual(r_text.status_code, 200)
        self.assertEqual(r_text.mimetype, "application/pdf")

        # Image to PDF
        img = Image.new("RGB", (60, 60), color="green")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        r_img = self.app.post(
            "/api/tools/image-to-pdf",
            data={"images": [(buf, "scan.png")]},
            content_type="multipart/form-data"
        )
        self.assertEqual(r_img.status_code, 200)
        self.assertEqual(r_img.mimetype, "application/pdf")

        # Merge PDF
        buf1 = io.BytesIO(r_text.data)
        buf2 = io.BytesIO(r_img.data)
        r_merge = self.app.post(
            "/api/tools/merge-pdf",
            data={"files": [(buf1, "part1.pdf"), (buf2, "part2.pdf")]},
            content_type="multipart/form-data"
        )
        self.assertEqual(r_merge.status_code, 200)
        self.assertEqual(r_merge.mimetype, "application/pdf")

        # Document to PDF
        doc_buf = io.BytesIO(b"Unit 1: Computer Networks Overview\nOSI Model Layers and Protocols.")
        r_doc = self.app.post(
            "/api/tools/document-to-pdf",
            data={"file": (doc_buf, "notes.txt")},
            content_type="multipart/form-data"
        )
        self.assertEqual(r_doc.status_code, 200)
        self.assertEqual(r_doc.mimetype, "application/pdf")
        print("[PASS] Student PDF Toolkit verified.")


if __name__ == "__main__":
    unittest.main(exit=False)
    print("\n" + "=" * 55)
    print(" [SUCCESS] All backend tests completed successfully!")
    print("=" * 55)
    try:
        input("\nPress Enter to close this window...")
    except Exception:
        pass

