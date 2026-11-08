"""Quick smoke test of the web app (python test_web.py)."""
import json, shutil, os, app as A

shutil.copy(A.KB_PATH, A.KB_PATH + ".bak")
try:
    c = A.app.test_client()
    assert c.get("/").status_code == 200
    r = c.post("/api/ask", json={"question": "Paano mag-enroll?"}).get_json()
    assert r["entry_id"] == "enroll_how", r
    r = c.post("/api/ask", json={"question": "pizza"}).get_json()
    assert r["entry_id"] is None
    assert c.post("/api/feedback", json={"question": "x", "helpful": True}).status_code == 200
    assert c.get("/admin").status_code == 302                    # protected
    assert c.get("/admin/api/entries").status_code == 401
    assert c.post("/admin/login", data={"password": "wrong"}).status_code == 200
    c.post("/admin/login", data={"password": A.ADMIN_PASSWORD})
    assert c.get("/admin").status_code == 200
    assert len(c.get("/admin/api/entries").get_json()) > 20
    r = c.post("/admin/api/entries", json={"id": "parking", "category": "Offices",
          "patterns": "parking, parking+fee", "answer": "Test parking answer", "verified": True})
    assert r.status_code == 200, r.get_json()
    assert c.post("/api/ask", json={"question": "saan ang parking?"}).get_json()["entry_id"] == "parking"
    assert c.post("/admin/api/entries", json={"id": "Bad ID"}).status_code == 400
    assert c.delete("/admin/api/entries/parking").status_code == 200
    assert c.post("/api/ask", json={"question": "saan ang parking?"}).get_json()["entry_id"] is None
    print(c.get("/admin/api/stats").get_json()["total_questions"], "logged questions")
    print("ALL WEB TESTS PASSED")
finally:
    shutil.move(A.KB_PATH + ".bak", A.KB_PATH)
    A.engine.load()
