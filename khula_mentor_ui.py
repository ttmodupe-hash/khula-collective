"""Member-only Khula Mentor. Native Streamlit controls work on phone and desktop."""
import streamlit as st

from khula_config import DB_PATH
from khula_mentor import (
    MentorUnavailable, ai_ready, check_answer, generate_ai_reply, learning_state,
    library_reply, next_lesson, practice_projection, record_answer, set_progress_consent,
)
from khula_mentor_content import BY_ID, CONTENT_VERSION, LESSONS, LEVELS, PATHS, SOURCES


def _clear_learning_session():
    for key in list(st.session_state):
        if str(key).startswith("mentor_"):
            del st.session_state[key]


def _identity():
    if not st.session_state.get("authenticated"):
        raise PermissionError("Sign in to open your financial mentor.")
    uid, epoch = st.session_state.get("user_id"), st.session_state.get("_auth_epoch")
    state = learning_state(DB_PATH, uid, epoch)
    if st.session_state.get("mentor_session_owner") != (uid, epoch):
        _clear_learning_session()
        st.session_state.mentor_session_owner = (uid, epoch)
    return uid, epoch, state


def render_mentor_profile_card():
    try:
        _, _, state = _identity()
    except PermissionError as exc:
        st.info(str(exc))
        return
    with st.container(border=True):
        st.subheader("🌱 My financial mentor")
        st.write("Build financial wisdom, one practical lesson at a time. Learn about investing, "
                 "test your understanding and explore hypothetical outcomes.")
        checked = sum(bool(row["mastered"]) for row in state["progress"].values())
        st.caption(f"{checked} of {len(LESSONS)} concepts checked in your saved learning journey. "
                   "Progress is private; saving it is optional.")
        if st.button("Open Khula Mentor", key="open_profile_mentor", use_container_width=True, type="primary"):
            st.session_state.nav_page = "mentor"
            st.rerun()


def _sources(lesson):
    st.caption("Background reading from official sources. Khula wrote these lessons; source organisations "
               "have not endorsed the app. Links are not live fact checks of an AI answer.")
    for key in lesson["sources"]:
        title, url = SOURCES[key]
        st.link_button(title, url)


def _lesson_view(uid, epoch, state):
    path = st.selectbox("What would you like to learn?", tuple(PATHS), key="mentor_path")
    progress = state["progress"] if state["save_progress"] else st.session_state.get("mentor_local_progress", {})
    next_id, reason = next_lesson(progress, path)
    checked = sum(bool(row.get("mastered")) for row in progress.values())
    st.progress(checked / len(LESSONS), text=f"{checked} of {len(LESSONS)} concepts checked")
    st.caption("Learning progress measures completed knowledge checks. It does not assess investment suitability.")
    st.info(f"Suggested next lesson: {BY_ID[next_id]['title']}. {reason}")
    if st.button("Take my suggested lesson", key="mentor_take_next"):
        st.session_state.mentor_lesson = next_id
    if "mentor_lesson" not in st.session_state:
        st.session_state.mentor_lesson = next_id
    lesson_id = st.selectbox("Explore a lesson", tuple(BY_ID), key="mentor_lesson",
                             format_func=lambda key: BY_ID[key]["title"])
    lesson = BY_ID[lesson_id]
    with st.container(border=True):
        st.caption(lesson["stage"] + " · about 5 minutes")
        st.subheader(lesson["title"])
        st.write(lesson["body"])
        st.info(lesson["example"])
        with st.expander("Try this in your own words", expanded=True):
            st.write(lesson["activity"])
            st.caption("Keep any personal amounts or details private. This activity does not need an upload.")
        with st.form("mentor_quiz_" + lesson_id):
            choice = st.radio(lesson["question"], range(len(lesson["options"])), index=None,
                              format_func=lambda index: lesson["options"][index])
            submitted = st.form_submit_button("Check my understanding")
        if submitted:
            if choice is None:
                st.warning("Choose an answer first.")
            else:
                result = (record_answer(DB_PATH, uid, epoch, lesson_id, choice) if state["save_progress"]
                          else check_answer(lesson_id, choice))
                if not state["save_progress"]:
                    local = dict(st.session_state.get("mentor_local_progress", {}))
                    previous = local.get(lesson_id, {})
                    local[lesson_id] = {"mastered": bool(previous.get("mastered") or result["correct"]),
                                        "attempts": previous.get("attempts", 0) + 1}
                    st.session_state.mentor_local_progress = local
                st.session_state.mentor_feedback = (lesson_id, result)
                st.rerun()
        feedback = st.session_state.get("mentor_feedback")
        if feedback and feedback[0] == lesson_id:
            result = feedback[1]
            (st.success if result["correct"] else st.info)(
                ("You've got the concept. " if result["correct"] else "Let's revisit this. ") + result["explanation"])
        with st.expander("Read the official background sources"):
            _sources(lesson)
    return lesson_id


def _tutor_view(uid, epoch, lesson_id):
    st.subheader("💬 Talk through a concept")
    ready = ai_ready()
    st.caption("Ask about a concept, without names, account details, passwords, statements or personal balances. "
               "Questions and replies stay in this signed-in tab and are not saved to your learning profile.")
    if ready:
        st.info("Live AI explanations are available with your permission. AI can make mistakes; check the lesson sources.")
    else:
        st.info("Lesson library mode is active. Live AI is not connected. Your question searches Khula's written lessons.")
    with st.form("mentor_question_form", clear_on_submit=True):
        question = st.text_area("What would you like to understand?", max_chars=400,
                                placeholder="For example: Why can fees make a big difference over time?")
        level = st.selectbox("Explanation level", LEVELS)
        consent = st.checkbox(
            "Use OpenAI for this question. Send my question, chosen level and this lesson's text; "
            "do not send my profile or ledger.", value=False, disabled=not ready)
        if ready:
            st.caption("The provider receives only the information listed above. Provider processing and retention "
                       "terms apply. Up to 10 AI requests per member per UTC day; library answers remain available.")
        submitted = st.form_submit_button("Ask my mentor", use_container_width=True)
    if submitted:
        if not question.strip():
            st.warning("Write a short question first.")
        else:
            try:
                if ready and consent:
                    with st.spinner("Preparing your learning explanation…"):
                        reply = generate_ai_reply(DB_PATH, uid, epoch, lesson_id, question, level, consent=True)
                else:
                    reply = library_reply(question, lesson_id)
                history = list(st.session_state.get("mentor_conversation", []))[-4:]
                history.append({"question": question, "reply": reply})
                st.session_state.mentor_conversation = history
            except (ValueError, PermissionError, MentorUnavailable) as exc:
                st.warning(str(exc))
    for item in st.session_state.get("mentor_conversation", []):
        reply = item["reply"]
        # Plain text prevents model/question markdown from loading remote content or links.
        with st.chat_message("user"):
            st.text(item["question"])
        with st.chat_message("assistant"):
            st.caption(reply["source"] + (" · " + reply["model"] if reply.get("model") else ""))
            st.text(reply["text"])
            if reply["source"] == "Khula lesson library" and not reply["matched"]:
                st.caption("No topic match found. Here is the current lesson to help you frame the question.")
            if reply["lesson_id"] != lesson_id:
                st.caption("Related lesson: " + BY_ID[reply["lesson_id"]]["title"])
    if st.session_state.get("mentor_conversation") and st.button("Clear this conversation", key="mentor_clear_chat"):
        del st.session_state["mentor_conversation"]
        st.rerun()


def _practice_lab():
    import pandas as pd
    st.subheader("🧪 Investment practice lab")
    st.write("Explore how contributions, assumed returns, fees and inflation interact using fictional money.")
    with st.form("mentor_simulator"):
        start = st.number_input("Hypothetical starting amount (R)", 0, 10000000, 1000, 100)
        monthly = st.number_input("Hypothetical monthly contribution (R)", 0, 100000, 500, 100)
        years = st.slider("Practice period (years)", 1, 40, 10)
        rate = st.slider("Assumed annual return before fees (%)", -50.0, 30.0, 0.0, 0.5)
        fee = st.slider("Assumed annual percentage fee (%)", 0.0, 5.0, 1.0, 0.1)
        inflation = st.slider("Assumed annual inflation (%)", 0.0, 20.0, 5.0, 0.5)
        run = st.form_submit_button("Explore this hypothetical scenario", use_container_width=True)
    if run:
        st.session_state.mentor_scenario = practice_projection(start, monthly, years, rate, fee, inflation)
    result = st.session_state.get("mentor_scenario")
    if result:
        st.metric("Contributions only", f"R{result['contributed']:,.2f}")
        st.metric("Hypothetical final balance after fees", f"R{result['balance']:,.2f}")
        st.metric("Final balance in today's purchasing power", f"R{result['today_money']:,.2f}")
        st.caption(f"Difference from the same scenario without fees, including lost growth: R{result['fee_effect']:,.2f}.")
        frame = pd.DataFrame([{
            "Year": row["year"], "Contributions only": float(row["contributed"]),
            "After fees": float(row["balance"]), "Today's purchasing power": float(row["today_money"]),
        } for row in result["rows"]]).set_index("Year")
        st.line_chart(frame, x_label="Years", y_label="Hypothetical ZAR")
        with st.expander("See the numbers"):
            st.dataframe(frame, use_container_width=True)
    st.caption("These are user-selected assumptions, not forecasts or current market rates. Returns are modelled "
               "as constant effective annual rates converted to monthly growth. Contributions arrive at month-end, "
               "then the proportional monthly fee is charged. Inflation is constant. No taxes, withdrawals, fixed "
               "charges or market fluctuations are included. Real outcomes can be worse and capital can be lost.")


def _privacy_view(uid, epoch, state):
    st.subheader("Your learning privacy")
    st.write("By default, learning progress lasts only in this tab. You can choose to save lesson completion, "
             "attempt counts and dates privately to your Khula account. Your answers, questions and replies "
             "are not saved in the learning database. Backups may retain deleted records under the club's retention policy.")
    with st.form("mentor_privacy_form"):
        enabled = st.checkbox("Save my learning progress to my account", value=state["save_progress"])
        if st.form_submit_button("Save my learning preference"):
            set_progress_consent(DB_PATH, uid, epoch, enabled)
            st.session_state.mentor_privacy_saved = True
            st.rerun()
    if st.session_state.get("mentor_privacy_saved"):
        st.success("Learning preference saved.")
    if st.button("Delete my saved progress and clear this learning session", key="mentor_delete_progress"):
        set_progress_consent(DB_PATH, uid, epoch, False)
        _clear_learning_session()
        st.rerun()
    st.caption("AI request counts are retained for up to 62 days to enforce service limits. "
               "Deleting learning progress does not reset those limits. AI provider retention is separate.")


def render_mentor():
    try:
        uid, epoch, state = _identity()
    except PermissionError as exc:
        _clear_learning_session()
        st.warning(str(exc))
        return
    st.title("🌱 Khula Mentor")
    st.write("Your space to build financial knowledge, practise judgement and learn how investing works.")
    st.caption("Financial education. Product choices and personal investment advice require an appropriately "
               "authorised professional. A lesson or AI reply cannot approve a club investment.")
    lessons, tutor, lab, privacy = st.tabs(["My learning journey", "Ask my mentor", "Practice lab", "My privacy"])
    try:
        with lessons:
            lesson_id = _lesson_view(uid, epoch, state)
        with tutor:
            _tutor_view(uid, epoch, lesson_id)
        with lab:
            _practice_lab()
        with privacy:
            _privacy_view(uid, epoch, state)
    except PermissionError as exc:
        _clear_learning_session()
        st.warning(str(exc))
    st.caption("Khula lesson edition " + CONTENT_VERSION + " · English edition")
