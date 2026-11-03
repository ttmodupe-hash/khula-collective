"""Real Streamlit form interactions against an isolated synthetic ledger."""
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
import khula_config
import khula_mentor_ui as ui

SCRIPT = "from khula_mentor_ui import render_mentor\nrender_mentor()"


class MentorUITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "synthetic.db")
        with patch.object(khula_config, "DB_PATH", self.db), patch.dict(os.environ, {"KHULA_DEMO_MODE": "0"}):
            khula_config.init_database()
        with sqlite3.connect(self.db) as conn:
            conn.executemany("INSERT INTO Users(user_id,username,password_hash,full_name,is_active,auth_epoch,must_change_password) VALUES(?,?,?, ?,1,0,0)",
                             [(1, "fixture1", "unused", "Synthetic One"), (2, "fixture2", "unused", "Synthetic Two")])
        self.db_patch = patch.object(ui, "DB_PATH", self.db)
        self.db_patch.start()
        self.env_patch = patch.dict(os.environ, {"KHULA_AI_PROVIDER": "none"})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.db_patch.stop()
        self.tmp.cleanup()

    def open(self):
        app = AppTest.from_string(SCRIPT, default_timeout=20)
        app.session_state["authenticated"] = True
        app.session_state["user_id"] = 1
        app.session_state["_auth_epoch"] = 0
        app.run()
        self.assertFalse(app.exception)
        return app

    def button(self, app, label):
        return next(w for w in app.button if w.label == label)

    def test_library_and_quiz_work_without_ai_or_persisting_progress(self):
        with patch("openai.OpenAI") as factory:
            app = self.open()
            self.assertTrue(any("Lesson library mode" in str(w.value) for w in app.info))
            self.assertFalse(next(w for w in app.checkbox if "Save my learning" in w.label).value)
            app.radio[0].set_value(1)
            self.button(app, "Check my understanding").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("got the concept" in w.value for w in app.success))
            self.assertTrue(app.session_state["mentor_local_progress"]["cashflow"]["mastered"])
            with sqlite3.connect(self.db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM Mentor_Progress").fetchone()[0], 0)
            factory.assert_not_called()

    def test_member_can_save_resume_and_delete_only_own_progress(self):
        app = self.open()
        next(w for w in app.checkbox if "Save my learning" in w.label).check()
        self.button(app, "Save my learning preference").click().run()
        app.radio[0].set_value(1)
        self.button(app, "Check my understanding").click().run()
        self.assertFalse(app.exception)
        fresh = self.open()
        self.assertTrue(next(w for w in fresh.checkbox if "Save my learning" in w.label).value)
        self.assertTrue(any("1 of 10" in w.proto.text for w in fresh.get("progress")))
        self.button(fresh, "Delete my saved progress and clear this learning session").click().run()
        self.assertFalse(fresh.exception)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM Mentor_Progress").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM Mentor_Preferences").fetchone()[0], 0)

    def test_questions_receive_labelled_library_answer_and_can_be_cleared(self):
        app = self.open()
        next(w for w in app.text_area if "understand" in w.label).set_value("How do fees affect investing?")
        self.button(app, "Ask my mentor").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["mentor_conversation"][0]["reply"]["lesson_id"], "fees")
        self.assertTrue(any("Khula lesson library" in w.value for w in app.caption))
        self.button(app, "Clear this conversation").click().run()
        self.assertFalse(app.exception)
        self.assertNotIn("mentor_conversation", app.session_state)

    def test_practice_lab_renders_negative_return_without_changing_ledger(self):
        app = self.open()
        next(w for w in app.slider if "return before" in w.label).set_value(-20.0)
        self.button(app, "Explore this hypothetical scenario").click().run()
        self.assertFalse(app.exception)
        scenario = app.session_state["mentor_scenario"]
        self.assertLess(scenario["balance"], scenario["contributed"])
        self.assertEqual(len(app.metric), 3)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM Monthly_Contributions").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM Investments").fetchone()[0], 0)

    def test_session_switch_clears_previous_members_questions_and_scenarios(self):
        app = self.open()
        app.session_state["mentor_conversation"] = [{"question": "Previous private question", "reply": {}}]
        app.session_state["mentor_scenario"] = {"should": "clear"}
        app.session_state["user_id"] = 2
        app.run()
        self.assertFalse(app.exception)
        self.assertNotIn("mentor_conversation", app.session_state)
        self.assertNotIn("mentor_scenario", app.session_state)

    def test_revoked_session_cannot_see_old_learning_state(self):
        app = self.open()
        app.session_state["mentor_conversation"] = [{"question": "Private question", "reply": {}}]
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE Users SET auth_epoch=1 WHERE user_id=1")
        app.run()
        self.assertFalse(app.exception)
        self.assertNotIn("mentor_conversation", app.session_state)
        self.assertTrue(any("fresh sign-in" in w.value for w in app.warning))


if __name__ == "__main__":
    unittest.main()
