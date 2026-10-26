"""Secure account self-service with enforced first-login password rotation."""
import streamlit as st

from khula_config import DB_PATH
from khula_security import change_member_password, member_auth_state


def render_change_password(force=False):
    if force:
        st.title("🔐 Secure your Khula administrator account")
        st.warning(
            "This is your first sign-in. Set a new, private password before "
            "accessing club data. Use 12–72 UTF-8 bytes and never reuse the "
            "temporary bootstrap credential."
        )
    else:
        st.subheader("Change your password")
        st.caption("A password change invalidates other active sessions.")
    with st.form("password_rotation_form"):
        old = st.text_input("Current password", type="password")
        new = st.text_input("New unique password (12–72 bytes)", type="password")
        again = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Change password"):
            if new != again:
                st.error("The new passwords do not match.")
            else:
                try:
                    change_member_password(DB_PATH, st.session_state.user_id, old, new)
                    state = member_auth_state(DB_PATH, st.session_state.user_id)
                    st.session_state._auth_epoch = state[3]
                    st.success("Password changed successfully. Older sessions are no longer valid.")
                    st.rerun()
                except (ValueError, PermissionError) as exc:
                    st.error(str(exc))
