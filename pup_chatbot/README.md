# PUP Parañaque IT FAQ Chatbot (Web App)

## Run locally
    pip install -r requirements.txt
    python app.py
Open http://127.0.0.1:5000  (Admin: http://127.0.0.1:5000/admin)

Set a real admin password first:
    Windows (cmd):   set ADMIN_PASSWORD=yourpassword
    Mac/Linux:       export ADMIN_PASSWORD=yourpassword

## Test
    python chatbot.py --test    # response accuracy (32 questions)
    python test_web.py          # website/API smoke test

## Files
    app.py               Flask web server + admin API
    chatbot.py           Rule-based engine (also has --cli and desktop GUI)
    knowledge_base.json  FAQ entries, synonyms, rules (editable)
    templates/ static/   Website pages, CSS, JavaScript
    chat_log.csv         Auto-created: every question asked
    feedback_log.csv     Auto-created: 👍/👎 ratings
