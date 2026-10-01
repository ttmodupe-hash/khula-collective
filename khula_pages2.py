from khula_config import *
from khula_utils import *
from khula_id_engine import (
    verify_id_from_photo,
    validate_sa_id_format,
    get_user_verification_status,
    store_verification_result,
    TESSERACT_AVAILABLE,
    CV2_AVAILABLE,
)

# ============================================================
# ID VERIFICATION v4.0 — AI-Powered Smart System
# ============================================================

def render_id_verification():
    """AI-powered South African ID verification flow.

    Provides a complete end-to-end ID verification experience:
      1. Photo capture (camera) or upload
      2. OCR extraction via pytesseract
      3. SA ID format, DOB, gender, citizenship & Luhn validation
      4. POPIA-compliant result storage (hash only — never the photo)
      5. Visual status dashboard with manual-entry fallback

    This page can be called during onboarding (after ``render_login()``)
    or from the profile/settings area at any time.
    """
    track_feature_usage(st.session_state.user_id, "id_verification")

    # ── Page Header ──
    st.markdown(
        "<div class='main-header'>"
        "<h1>🆔 ID Verification</h1>"
        "<p>AI-powered document verification — fast, secure & POPIA compliant</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Session-state initialisation ──
    defaults = {
        "idv_step": "upload",          # upload | processing | result
        "idv_result": None,
        "idv_image": None,
        "idv_attempts": 0,
        "idv_show_manual": False,
        "idv_photo_hash": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── 1. Verification Status Dashboard ──
    _render_verification_status_dashboard()

    st.markdown("<hr style='border-color:#2a2a40;margin:1.5rem 0;'>", unsafe_allow_html=True)

    # ── Dependency check banner ──
    if not TESSERACT_AVAILABLE:
        st.warning(
            "⚠️ **OCR engine not available.** The AI ID reader requires `pytesseract` and the Tesseract binary.\n\n"
            "**Install instructions:**\n"
            "- Ubuntu/Debian: `sudo apt-get install tesseract-ocr`\n"
            "- macOS: `brew install tesseract`\n"
            "- Then: `pip install pytesseract`\n\n"
            "You can still verify manually below.",
            icon="📦",
        )

    if not CV2_AVAILABLE and TESSERACT_AVAILABLE:
        st.info(
            "💡 Installing `opencv-python` will improve OCR accuracy through image pre-processing.",
            icon="💡",
        )

    # ── 2. Photo Upload / Capture ──
    if st.session_state.idv_step == "upload":
        _render_capture_section()

    # ── 3. Processing with visual feedback ──
    elif st.session_state.idv_step == "processing":
        _render_processing_feedback()

    # ── 4. Results ──
    elif st.session_state.idv_step == "result":
        _render_result_card()

    # ── POPIA Compliance Footer ──
    st.markdown("<br><br>", unsafe_allow_html=True)
    _render_popia_notice()


# ──────────────────────────────────────────────────────────────
# Sub-renderers (private helpers)
# ──────────────────────────────────────────────────────────────

def _render_verification_status_dashboard():
    """Show current verification status for the logged-in user."""
    user_id = st.session_state.user_id
    status_rec = get_user_verification_status(user_id)

    st.markdown("<h3>📊 Your Verification Status</h3>", unsafe_allow_html=True)

    if status_rec:
        status = status_rec["status"]
        verified_at = status_rec["verified_at"]
        gender = status_rec.get("gender", "—")
        citizenship = status_rec.get("citizenship", "—")
        age = status_rec.get("age", "—")

        # Format date nicely
        try:
            dt = datetime.fromisoformat(verified_at)
            date_str = dt.strftime("%d %B %Y at %H:%M")
        except Exception:
            date_str = str(verified_at)

        if status == "verified":
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #00b89422, #00b89411);
                            border: 1px solid #00b894;
                            padding: 1.25rem;
                            border-radius: 16px;
                            margin-bottom: 1rem;">
                    <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.75rem;">
                        <span style="font-size:2rem;">✅</span>
                        <div>
                            <div style="font-weight:700; font-size:1.1rem; color:#00b894;">Verified</div>
                            <div style="color:#a0a0b0; font-size:0.85rem;">on {date_str}</div>
                        </div>
                    </div>
                    <div style="display:flex; gap:1.5rem; flex-wrap:wrap;">
                        <div><span style="color:#a0a0b0; font-size:0.8rem;">GENDER</span><br><strong>{gender.title()}</strong></div>
                        <div><span style="color:#a0a0b0; font-size:0.8rem;">CITIZENSHIP</span><br><strong>{citizenship.replace('_', ' ').title()}</strong></div>
                        <div><span style="color:#a0a0b0; font-size:0.8rem;">AGE</span><br><strong>{age}</strong></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif status == "pending":
            st.markdown(
                """
                <div style="background: linear-gradient(135deg, #ffa50222, #ffa50211);
                            border: 1px solid #ffa502;
                            padding: 1.25rem;
                            border-radius: 16px;
                            margin-bottom: 1rem;">
                    <div style="display:flex; align-items:center; gap:0.75rem;">
                        <span style="font-size:2rem;">⏳</span>
                        <div>
                            <div style="font-weight:700; font-size:1.1rem; color:#ffa502;">Verification Required</div>
                            <div style="color:#a0a0b0; font-size:0.85rem;">Complete the steps below to verify your identity.</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:  # failed
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #ff475722, #ff475711);
                            border: 1px solid #ff4757;
                            padding: 1.25rem;
                            border-radius: 16px;
                            margin-bottom: 1rem;">
                    <div style="display:flex; align-items:center; gap:0.75rem;">
                        <span style="font-size:2rem;">❌</span>
                        <div>
                            <div style="font-weight:700; font-size:1.1rem; color:#ff4757;">Verification Failed</div>
                            <div style="color:#a0a0b0; font-size:0.85rem;">Last attempt: {date_str} — Try again below.</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        # No record at all
        st.markdown(
            """
            <div style="background: #1e1e30;
                        border: 1px solid #2a2a40;
                        padding: 1.25rem;
                        border-radius: 16px;
                        margin-bottom: 1rem;">
                <div style="display:flex; align-items:center; gap:0.75rem;">
                    <span style="font-size:2rem;">🆔</span>
                    <div>
                        <div style="font-weight:700; font-size:1.1rem; color:#e0e0e0;">Not Yet Verified</div>
                        <div style="color:#a0a0b0; font-size:0.85rem;">Verify your ID to unlock full platform features.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_capture_section():
    """Display camera input and file uploader with tips."""
    st.markdown("<h3>📷 Capture or Upload Your ID</h3>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="background: #1e1e3a; padding: 1rem 1.25rem; border-radius: 12px;
                    border: 1px solid #2a2a50; margin-bottom: 1rem;">
            <p style="margin:0; color:#e0e0e0; font-size:0.9rem;">
                💡 <strong>Tips for a perfect scan:</strong><br>
                • Ensure the ID is <strong>well-lit</strong> with no glare or shadows<br>
                • Keep <strong>all four corners</strong> visible inside the frame<br>
                • Make sure the <strong>13-digit ID number</strong> and text are clearly readable<br>
                • Hold the camera steady and close enough to fill the frame
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_camera, tab_upload = st.tabs(["📷 Take Photo", "📁 Upload ID Photo"])

    captured_image = None
    source = None

    with tab_camera:
        cam_img = st.camera_input(
            "Position your ID card inside the camera frame",
            key="idv_camera",
            help="Click the camera button to capture your ID document.",
        )
        if cam_img is not None:
            captured_image = cam_img
            source = "camera"

    with tab_upload:
        up_img = st.file_uploader(
            "Upload a photo of your South African ID",
            type=["jpg", "jpeg", "png", "webp", "bmp"],
            key="idv_upload",
            help="Supported formats: JPG, PNG, WEBP, BMP",
        )
        if up_img is not None:
            captured_image = up_img
            source = "upload"

    # Preview + action
    if captured_image is not None:
        st.markdown("<h4>👁️ Preview</h4>", unsafe_allow_html=True)
        st.image(captured_image, use_container_width=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "🔍 Verify My ID with AI",
                type="primary",
                use_container_width=True,
                key="idv_start_verify",
            ):
                st.session_state.idv_image = captured_image
                st.session_state.idv_step = "processing"
                st.session_state.idv_attempts += 1
                st.rerun()

        if st.session_state.idv_attempts > 0:
            st.caption(
                f"Attempt {st.session_state.idv_attempts} — if OCR keeps failing, use the manual option below."
            )

    # ── Manual fallback toggle (always available, especially after failures) ──
    if st.session_state.idv_attempts >= 1 or st.session_state.idv_show_manual:
        st.markdown("<hr style='border-color:#2a2a40;margin:1rem 0;'>", unsafe_allow_html=True)
        _render_manual_entry_fallback()


def _render_processing_feedback():
    """Show animated progress while OCR + validation runs."""
    st.markdown("<h3>🔍 AI ID Verification in Progress</h3>", unsafe_allow_html=True)

    # Progress steps
    steps = [
        ("📤 Image uploaded", True),
        ("🔍 OCR reading document", False),
        ("📋 Validating ID format", False),
        ("🔢 Checking Luhn checksum", False),
        ("✅ Verification complete", False),
    ]

    # We'll rerun through the spinner, then land on result.
    # Because Streamlit reruns on every interaction, we do the actual work
    # inside the spinner and immediately transition.
    with st.spinner("🔍 AI is reading your ID document…"):
        image = st.session_state.idv_image
        if image is not None:
            from PIL import Image as PILImage

            try:
                # Seek to start in case of file-like object
                image.seek(0)
                pil_img = PILImage.open(image)
            except Exception as exc:
                st.session_state.idv_result = {
                    "success": False,
                    "stage": "ocr",
                    "message": f"Could not open image: {exc}",
                    "raw_text_preview": None,
                }
                st.session_state.idv_step = "result"
                st.rerun()
                return

            # Run verification engine
            result = verify_id_from_photo(pil_img, user_id=st.session_state.user_id)
            st.session_state.idv_result = result
            if result.get("photo_hash"):
                st.session_state.idv_photo_hash = result["photo_hash"]
            st.session_state.idv_step = "result"
            st.rerun()
            return

    # Fallback if somehow we exit spinner without result
    st.session_state.idv_step = "result"
    st.rerun()


def _render_result_card():
    """Display success or failure card after verification."""
    result = st.session_state.idv_result
    if result is None:
        st.error("Something went wrong — no result found.")
        if st.button("🔄 Start Over", key="idv_restart_err"):
            _reset_idv_state()
            st.rerun()
        return

    success = result.get("success", False)
    stage = result.get("stage", "unknown")
    message = result.get("message", "Unknown result")
    details = result.get("details")
    id_last4 = result.get("id_last4")
    photo_hash = result.get("photo_hash") or st.session_state.idv_photo_hash
    raw_preview = result.get("raw_text_preview")

    if success:
        # ── SUCCESS CARD ──
        gender = details.get("gender", "—") if details else "—"
        citizenship = details.get("citizenship", "—") if details else "—"
        age = details.get("age", "—") if details else "—"
        dob = details.get("dob", "—") if details else "—"

        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #00b89422, #00b89411);
                        border: 1px solid #00b894;
                        padding: 1.5rem;
                        border-radius: 16px;
                        margin-bottom: 1.5rem;">
                <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:1rem;">
                    <span style="font-size:2.5rem;">✅</span>
                    <div>
                        <div style="font-weight:800; font-size:1.3rem; color:#00b894;">ID Verified Successfully</div>
                        <div style="color:#a0a0b0; font-size:0.9rem;">Your South African identity has been confirmed.</div>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:1rem; margin-top:1rem;">
                    <div style="background: #00b89411; padding: 0.75rem; border-radius: 10px;">
                        <div style="color:#a0a0b0; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px;">Gender</div>
                        <div style="font-weight:600; font-size:1rem; color:#e0e0e0;">{gender.title()}</div>
                    </div>
                    <div style="background: #00b89411; padding: 0.75rem; border-radius: 10px;">
                        <div style="color:#a0a0b0; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px;">Citizenship</div>
                        <div style="font-weight:600; font-size:1rem; color:#e0e0e0;">{citizenship.replace('_', ' ').title()}</div>
                    </div>
                    <div style="background: #00b89411; padding: 0.75rem; border-radius: 10px;">
                        <div style="color:#a0a0b0; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px;">Age</div>
                        <div style="font-weight:600; font-size:1rem; color:#e0e0e0;">{age} years</div>
                    </div>
                    <div style="background: #00b89411; padding: 0.75rem; border-radius: 10px;">
                        <div style="color:#a0a0b0; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px;">Date of Birth</div>
                        <div style="font-weight:600; font-size:1rem; color:#e0e0e0;">{dob}</div>
                    </div>
                </div>

                <div style="margin-top:1rem; padding-top:1rem; border-top: 1px solid #00b89444;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                        <div>
                            <span style="color:#a0a0b0; font-size:0.8rem;">ID ends in: </span>
                            <span style="font-family:monospace; font-weight:700; color:#00b894; font-size:1.1rem;">****{id_last4 or '####'}</span>
                        </div>
                        <div style="text-align:right;">
                            <span style="color:#a0a0b0; font-size:0.75rem;">Audit hash: </span>
                            <span style="font-family:monospace; color:#a0a0b0; font-size:0.75rem;">{photo_hash[:8] if photo_hash else '—'}</span>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.success(message)

        # Continue to dashboard
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "I've Verified My ID — Continue to Dashboard →",
                type="primary",
                use_container_width=True,
                key="idv_continue_dashboard",
            ):
                st.session_state.nav_page = "dashboard"
                _reset_idv_state()
                st.rerun()

    else:
        # ── FAILURE CARD ──
        error_color = "#ff4757"
        error_bg = "#ff475722"
        icon = "❌"

        # Specific friendly messages per failure stage
        if stage == "ocr":
            headline = "Could Not Read ID"
            explanation = (
                "The AI could not detect a valid 13-digit ID number in the photo. "
                "This usually happens when the image is blurry, poorly lit, or the ID is not fully in frame."
            )
            suggestion = "Try retaking the photo with better lighting and make sure all corners are visible."
        elif stage == "validation":
            error_detail = details.get("error", "") if details else ""
            if "Checksum" in error_detail or "checksum" in error_detail:
                headline = "Checksum Failed — ID Appears Invalid"
                explanation = (
                    "The ID number was read, but the built-in checksum (Luhn algorithm) does not match. "
                    "This could mean the ID number is not valid, or the OCR misread one or more digits."
                )
                suggestion = "Try retaking with the ID perfectly flat and well-lit. If the problem persists, the document may not be a valid SA ID."
            elif "Date of birth" in error_detail or "date" in error_detail.lower():
                headline = "Date of Birth Invalid"
                explanation = "The date-of-birth digits in the ID number don't form a valid calendar date."
                suggestion = "Check the ID image quality — the OCR may have misread the digits. Retake with better focus."
            elif "Age" in error_detail:
                headline = "Age Validation Failed"
                explanation = error_detail
                suggestion = "Ensure the ID document belongs to a member who meets the minimum age requirement."
            else:
                headline = "ID Validation Failed"
                explanation = error_detail or "The ID number did not pass all validation checks."
                suggestion = "Please review the ID document and try again."
        else:
            headline = "Verification Failed"
            explanation = message
            suggestion = "Please try again or use manual entry below."

        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, {error_bg}, #ff475711);
                        border: 1px solid {error_color};
                        padding: 1.5rem;
                        border-radius: 16px;
                        margin-bottom: 1.5rem;">
                <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:1rem;">
                    <span style="font-size:2.5rem;">{icon}</span>
                    <div>
                        <div style="font-weight:800; font-size:1.3rem; color:{error_color};">{headline}</div>
                        <div style="color:#a0a0b0; font-size:0.9rem;">{explanation}</div>
                    </div>
                </div>
                <div style="background: #ff475711; padding: 0.75rem 1rem; border-radius: 10px;">
                    <span style="color:#e0e0e0; font-size:0.9rem;">💡 <strong>Suggestion:</strong> {suggestion}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Show raw OCR preview if available (helpful for debugging)
        if raw_preview:
            with st.expander("🔬 Show Raw OCR Text (debug)"):
                st.text_area(
                    "What the AI read from the image",
                    value=raw_preview,
                    height=120,
                    disabled=True,
                    label_visibility="collapsed",
                )
                st.caption("This helps diagnose why the ID wasn't recognized.")

        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Try Again", use_container_width=True, key="idv_retry"):
                st.session_state.idv_step = "upload"
                st.session_state.idv_image = None
                st.session_state.idv_result = None
                st.rerun()
        with col2:
            if st.button("✏️ Enter ID Manually", use_container_width=True, key="idv_manual_btn"):
                st.session_state.idv_show_manual = True
                st.rerun()

        # Always show manual fallback after a failure
        if st.session_state.idv_show_manual:
            st.markdown("<hr style='border-color:#2a2a40;margin:1rem 0;'>", unsafe_allow_html=True)
            _render_manual_entry_fallback()


def _render_manual_entry_fallback():
    """Allow user to type their ID number when OCR fails."""
    st.markdown("<h4>✏️ Manual ID Entry</h4>", unsafe_allow_html=True)
    st.caption("When the AI can't read your ID photo, you can enter the number manually. It will still be validated securely.")

    with st.form("manual_id_form"):
        manual_id = st.text_input(
            "South African ID Number",
            max_chars=13,
            placeholder="Enter your 13-digit ID number",
            help="Format: YYMMDDSSSSCAZ (13 digits, no spaces)",
        )
        submitted = st.form_submit_button(
            "Validate ID Number",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if not manual_id or len(manual_id.strip()) != 13:
                st.error("Please enter exactly 13 digits.")
            elif not manual_id.strip().isdigit():
                st.error("ID number must contain only digits.")
            else:
                is_valid, details = validate_sa_id_format(manual_id.strip())
                if is_valid:
                    # Store as manual verification
                    store_verification_result(
                        st.session_state.user_id,
                        manual_id.strip(),
                        "verified",
                        details,
                        photo_hash=None,
                        method="manual",
                    )
                    st.success("✅ ID validated and verified successfully!")
                    st.balloons()

                    gender = details.get("gender", "—")
                    citizenship = details.get("citizenship", "—")
                    age = details.get("age", "—")

                    st.markdown(
                        f"""
                        <div style="background: #00b89422; border: 1px solid #00b894;
                                    padding: 1rem; border-radius: 12px; margin-top: 1rem;">
                            <div style="font-weight:600; color:#00b894; margin-bottom:0.5rem;">Verified Details</div>
                            <div style="display:flex; gap:1.5rem; flex-wrap:wrap;">
                                <div><span style="color:#a0a0b0; font-size:0.8rem;">GENDER</span><br><strong>{gender.title()}</strong></div>
                                <div><span style="color:#a0a0b0; font-size:0.8rem;">CITIZENSHIP</span><br><strong>{citizenship.replace('_', ' ').title()}</strong></div>
                                <div><span style="color:#a0a0b0; font-size:0.8rem;">AGE</span><br><strong>{age}</strong></div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button(
                            "Continue to Dashboard →",
                            type="primary",
                            use_container_width=True,
                            key="idv_manual_continue",
                        ):
                            st.session_state.nav_page = "dashboard"
                            _reset_idv_state()
                            st.rerun()
                else:
                    error_msg = details.get("error", "Validation failed")
                    st.error(f"❌ {error_msg}")
                    st.caption("Please double-check the ID number and try again.")


def _render_popia_notice():
    """Display POPIA compliance notice."""
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1e1e3a, #1a1a2e);
                    border: 1px solid #2a2a50;
                    padding: 1.25rem;
                    border-radius: 16px;
                    margin-top: 1rem;">
            <div style="display:flex; align-items:start; gap:0.75rem;">
                <span style="font-size:1.5rem;">🔒</span>
                <div>
                    <div style="font-weight:700; color:#00b894; margin-bottom:0.25rem;">POPIA Compliant & Privacy First</div>
                    <div style="color:#a0a0b0; font-size:0.85rem; line-height:1.5;">
                        Your ID photo is processed <strong>in-memory only</strong> and is <strong>NEVER stored</strong>.
                        We keep only a secure SHA-256 hash and the last 4 digits for confirmation purposes.
                        No human ever sees your full ID number or photograph.
                        <br><br>
                        This processing is done in accordance with the
                        <a href="https://www.gov.za/documents/protection-personal-information-act" target="_blank" style="color:#00b894;">
                            Protection of Personal Information Act (POPIA) 4 of 2013
                        </a>.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _reset_idv_state():
    """Reset all ID-verification session state keys."""
    keys = ["idv_step", "idv_result", "idv_image", "idv_attempts", "idv_show_manual", "idv_photo_hash"]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]


# ============================================================
# Existing pages (unchanged)
# ============================================================

def render_feature_discovery():
    track_feature_usage(st.session_state.user_id, "feature_discovery")
    st.markdown("<div class='main-header'><h1>✨ Discover Khula</h1><p>Explore everything your collective can do</p></div>", unsafe_allow_html=True)

    # Personalized recommendations
    st.markdown("<h3>🎯 Recommended for You</h3>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT feature_id FROM Feature_Usage WHERE user_id=? GROUP BY feature_id", (st.session_state.user_id,))
    used = {row[0] for row in c.fetchall()}
    conn.close()

    recommended = [f for f in APP_FEATURES if f["id"] not in used][:3]
    if recommended:
        cols = st.columns(len(recommended))
        for col, feat in zip(cols, recommended):
            with col:
                st.markdown(f"""
                <div class='feature-card'>
                    <div class='feature-icon'>{feat['icon']}</div>
                    <div class='feature-name'>{feat['name']}</div>
                    <div class='feature-desc'>{feat['description']}</div>
                    <div class='feature-badge badge-new'>Try it</div>
                </div>
                """, unsafe_allow_html=True)

    # All features by category
    st.markdown("<h3>📂 Features by Category</h3>", unsafe_allow_html=True)
    categories = sorted(set(f["category"] for f in APP_FEATURES))
    for cat in categories:
        st.markdown(f"<h4>{cat}</h4>", unsafe_allow_html=True)
        feats = [f for f in APP_FEATURES if f["category"] == cat]
        cols = st.columns(min(len(feats), 3))
        for col, feat in zip(cols, feats):
            with col:
                badges = ""
                if feat["new"]:
                    badges += "<span class='feature-badge badge-new'>NEW</span> "
                if feat["premium"]:
                    badges += "<span class='feature-badge badge-premium'>PREMIUM</span>"
                st.markdown(f"""
                <div class='feature-card'>
                    <div class='feature-icon'>{feat['icon']}</div>
                    <div class='feature-name'>{feat['name']}</div>
                    <div class='feature-desc'>{feat['description']}</div>
                    {badges}
                </div>
                """, unsafe_allow_html=True)

    # Setup checklist
    st.markdown("<h3>✅ Getting Started Checklist</h3>", unsafe_allow_html=True)
    checklist = [
        ("Complete your profile", True),
        ("Link your FNB account", False),
        ("Make your first contribution", True),
        ("Vote on an investment proposal", False),
        ("Set up notifications", True),
        ("Invite a member", False),
    ]
    completed = sum(1 for _, done in checklist if done)
    st.progress(completed / len(checklist))
    st.write(f"{completed}/{len(checklist)} completed")
    for item, done in checklist:
        st.checkbox(item, value=done, disabled=True)

    # Coming soon
    st.markdown("<h3>🚀 Coming Soon</h3>", unsafe_allow_html=True)
    coming_soon = [
        ("📱 Native Mobile App", "iOS and Android apps with push notifications"),
        ("💳 Card Payments", "Pay contributions with debit/credit card"),
        ("🏠 Property Investments", "Fractional property investment integration"),
        ("📊 Advanced Analytics", "Portfolio forecasting and risk analysis"),
        ("🤖 AI Advisor v2", "Personalized investment recommendations"),
    ]
    for name, desc in coming_soon:
        st.markdown(f"**{name}** - {desc}")

def render_fnb_api_guide():
    track_feature_usage(st.session_state.user_id, "fnb_api_guide")
    st.markdown("<h2>🏦 FNB API Access Guide</h2>", unsafe_allow_html=True)

    st.markdown("""
    <div style='background: #1e1e3a; padding: 1.5rem; border-radius: 12px; border: 1px solid #2a2a50; margin-bottom: 1.5rem;'>
        <h3 style='color: #00b894; margin-top: 0;'>Current Status: Statement Upload Mode ✅</h3>
        <p style='color: #e0e0e0;'>Your club can already generate reports from uploaded FNB statements (PDF/CSV).
        This guide explains how to get <strong>real-time API access</strong> for automatic sync.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h3>🚪 Step 1: Register a Business Entity</h3>", unsafe_allow_html=True)
    st.markdown("""
    FNB does not offer self-serve developer APIs for personal transaction history.
    You need a **registered business or trust** to apply:
    - Register your stokvel/investment club as a **stokvel association** or **private company**
    - Obtain a tax number from SARS
    - Open a **FNB Business Account** (or ensure your club banks with FNB)
    """, unsafe_allow_html=True)

    st.markdown("<h3>📝 Step 2: Contact FNB Business Solutions</h3>", unsafe_allow_html=True)
    st.markdown("""
    Reach out to FNB via:
    - **Email:** business@fnb.co.za
    - **Phone:** 087 575 9404 (Business Banking)
    - **Branch:** Visit your relationship manager

    Request access to **FNB Open Banking / API Services** for:
    - Account information (read-only transaction history)
    - Payment initiation (optional, for automated contributions)
    """, unsafe_allow_html=True)

    st.markdown("<h3>📋 Step 3: Submit Application</h3>", unsafe_allow_html=True)
    st.markdown("""
    FNB will require:
    1. **Business registration documents** (CIPC certificate)
    2. **FICA compliance** (ID copies, proof of address for all signatories)
    3. **Tax clearance certificate** (SARS)
    4. **API use case description** (explain you're building an investment club management tool)
    5. **Data protection plan** (how you'll secure member transaction data)
    6. **Expected transaction volume** (monthly API call estimates)
    """, unsafe_allow_html=True)

    st.markdown("<h3>⏱️ Step 4: Wait for Approval</h3>", unsafe_allow_html=True)
    st.markdown("""
    - Approval typically takes **4–8 weeks**
    - FNB will provide **sandbox credentials** first for testing
    - After successful UAT, you'll receive **production API keys**
    - You'll need to sign an **API Service Agreement** with liability clauses
    """, unsafe_allow_html=True)

    st.markdown("<h3>⚡ Alternative: Bank Aggregator (Faster)</h3>", unsafe_allow_html=True)
    st.markdown("""
    While waiting for direct FNB API approval, consider these SA fintech aggregators:

    | Provider | FNB Support | Setup Time | Cost |
    |----------|------------|------------|------|
    | **Banklink** | ✅ Live | 1–2 weeks | From R500/mo |
    | **Ozow** | ✅ Live | 1–2 weeks | Per-transaction |
    | **Stitch** | ✅ Available | 1–2 weeks | Developer-friendly |
    | **Investec Programmable Banking** | ✅ Direct API | 2–3 weeks | Free for devs |

    These providers already have FNB partnerships and can provide transaction data via their APIs.
    """, unsafe_allow_html=True)

    st.markdown("<h3>🔐 Security Requirements</h3>", unsafe_allow_html=True)
    st.markdown("""
    Before handling real banking data, ensure:
    - **HTTPS only** (SSL certificate installed)
    - **AES-256 encryption** for data at rest
    - **OAuth 2.0** for API authentication
    - **PCI-DSS compliance** if handling card data
    - **POPIA compliance** (South Africa's data protection law)
    - Regular **penetration testing** and security audits
    """, unsafe_allow_html=True)

    st.markdown("<h3>🛠️ What We Need From You</h3>", unsafe_allow_html=True)
    st.markdown("""
    Once you have API credentials, simply add them as environment variables in Railway:
    ```
    FNB_CLIENT_ID=your_client_id
    FNB_CLIENT_SECRET=your_client_secret
    FNB_API_BASE=https://api.fnb.co.za/openbanking/v1
    ```
    The app will automatically switch from **Statement Upload Mode** to **Live API Mode**.
    """, unsafe_allow_html=True)

    st.info("💡 **Tip:** For now, the statement upload feature gives you 90% of the value. Upload PDFs or CSVs from FNB Online Banking and the app will auto-parse transactions, categorize spending, and generate reports.")

def render_member_voice():
    track_feature_usage(st.session_state.user_id, "member_voice")
    st.markdown("<div class='main-header'><h1>🗳️ Member Voice</h1><p>Democratic investment decisions</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create suggestion
    with st.expander("💡 Submit Investment Proposal"):
        with st.form("suggestion_form"):
            title = st.text_input("Proposal Title")
            desc = st.text_area("Description")
            inv_type = st.selectbox("Type", INVESTMENT_TYPES)
            amount = st.number_input("Amount (R)", min_value=1000, step=1000)
            submitted = st.form_submit_button("Submit Proposal", use_container_width=True, type="primary")
            if submitted and title and desc:
                c.execute("INSERT INTO Suggestions (user_id, title, description, investment_type, amount) VALUES (?, ?, ?, ?, ?)",
                          (st.session_state.user_id, title, desc, inv_type, amount))
                conn.commit()
                add_notification(1, "New Proposal", f"{st.session_state.full_name} submitted: {title}", "info")
                st.success("Proposal submitted!")
                st.rerun()

    # Active proposals
    st.markdown("<h3>📋 Active Proposals</h3>", unsafe_allow_html=True)
    c.execute("SELECT suggestion_id, user_id, title, description, investment_type, amount, votes, voted_by, status FROM Suggestions WHERE status='open'")
    proposals = c.fetchall()

    if proposals:
        for prop in proposals:
            sid, uid, title, desc, inv_type, amount, votes, voted_by, status = prop
            voted_list = voted_by.split(",") if voted_by else []
            has_voted = str(st.session_state.user_id) in voted_list

            c.execute("SELECT full_name FROM Users WHERE user_id=?", (uid,))
            proposer = c.fetchone()[0]

            with st.container():
                st.markdown(f"""
                <div style="background: #1e1e30; padding: 1.5rem; border-radius: 16px; border: 1px solid #2a2a40; margin-bottom: 1rem;">
                    <div style="display:flex; justify-content:space-between; align-items:start;">
                        <div>
                            <h4 style="margin:0;">{title}</h4>
                            <p style="color:#a0a0b0; margin:0.25rem 0;">by {proposer} · {inv_type} · R{amount:,.0f}</p>
                        </div>
                        <span style="background: #00b89433; color: #00b894; padding: 0.3rem 0.8rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">{votes} votes</span>
                    </div>
                    <p style="margin-top:0.75rem;">{desc}</p>
                </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    if not has_voted:
                        if st.button(f"👍 Vote for \"{title[:30]}...\"", key=f"vote_{sid}", use_container_width=True):
                            new_votes = votes + 1
                            new_voted = voted_by + "," + str(st.session_state.user_id) if voted_by else str(st.session_state.user_id)
                            c.execute("UPDATE Suggestions SET votes=?, voted_by=? WHERE suggestion_id=?", (new_votes, new_voted, sid))
                            conn.commit()
                            st.success("Vote recorded!")
                            st.rerun()
                    else:
                        st.button("✅ Voted", key=f"voted_{sid}", use_container_width=True, disabled=True)
                with col2:
                    if st.session_state.role == "admin":
                        if st.button("✓ Approve", key=f"approve_{sid}", use_container_width=True):
                            c.execute("UPDATE Suggestions SET status='approved' WHERE suggestion_id=?", (sid,))
                            conn.commit()
                            st.success("Proposal approved!")
                            st.rerun()
    else:
        st.info("No active proposals. Submit one above!")

    conn.close()

def render_constitution():
    track_feature_usage(st.session_state.user_id, "constitution")
    st.markdown("<div class='main-header'><h1>📜 Constitution</h1><p>Rules and governance of our collective</p></div>", unsafe_allow_html=True)

    sections = [
        ("1. Name & Purpose", "The name of this collective is Khula Collective. Our purpose is to pool resources for collective investment and wealth creation."),
        ("2. Membership", "Membership is open to individuals over 18 with valid South African ID. All members must complete FICA verification."),
        ("3. Contributions", "Each member contributes R500 monthly, due by the 5th of each month. Late payments incur a R50 penalty."),
        ("4. Investment Decisions", "All investment proposals require a simple majority vote (50%+1) of active members."),
        ("5. Withdrawals", "Members may withdraw after giving 30 days notice. Withdrawal value is calculated based on current portfolio value."),
        ("6. Governance", "The collective is administered by elected trustees who serve 2-year terms."),
        ("7. Dispute Resolution", "Disputes are resolved through mediation by an independent financial advisor."),
        ("8. Dissolution", "The collective may be dissolved by a 75% vote of all members. Assets are distributed proportionally."),
    ]

    for title, content in sections:
        with st.expander(title):
            st.write(content)

    st.download_button("📥 Download Constitution (PDF)", data="Khula Collective Constitution\\n\\n" + "\\n\\n".join([f"{t}\\n{c}" for t, c in sections]), file_name="khula_constitution.txt", use_container_width=True)

def render_directory():
    track_feature_usage(st.session_state.user_id, "directory")
    st.markdown("<div class='main-header'><h1>👥 Member Directory</h1><p>Connect with your collective</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    df_members = pd.read_sql_query(
        "SELECT full_name, email, phone, fica_status, role, joined_date FROM Users WHERE is_active=1 AND role='member' ORDER BY full_name", conn)
    conn.close()

    if not df_members.empty:
        df_members['fica_status'] = df_members['fica_status'].str.upper()
        st.dataframe(df_members.rename(columns={
            'full_name': 'Name', 'email': 'Email', 'phone': 'Phone',
            'fica_status': 'FICA', 'role': 'Role', 'joined_date': 'Joined'
        }), use_container_width=True, hide_index=True)
    else:
        st.info("No members found")
