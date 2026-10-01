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
# KHULA_APPEND_MARKER_7a3f9e2d
