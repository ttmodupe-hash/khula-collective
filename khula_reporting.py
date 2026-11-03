"""Role-enforced Khula financial reporting and member-directory queries.

No member-level contribution totals, payment references or FICA statuses are
returned to non-administrators. Role checks are made against the current
database, not caller-supplied role labels or cached session state.
"""
import sqlite3
from decimal import Decimal

from khula_advisory_core import zar


def _authorised(conn, user_id):
    row = conn.execute(
        "SELECT role,is_active FROM Users WHERE user_id=?", (user_id,),
    ).fetchone()
    if not row or row[1] != 1 or row[0] not in ("member", "admin"):
        raise PermissionError("Active club membership required.")
    return row[0]


def read_reports(db_path, viewer_id):
    with sqlite3.connect(db_path) as conn:
        role = _authorised(conn, viewer_id)
        investments = conn.execute(
            "SELECT name,type,amount_invested,current_value,returns,status FROM Investments"
        ).fetchall()
        club_paid = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM Monthly_Contributions "
            "WHERE status='paid'"
        ).fetchone()[0]
        personal_paid = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM Monthly_Contributions "
            "WHERE status='paid' AND user_id=?",
            (viewer_id,),
        ).fetchone()[0]
        personal_history = conn.execute(
            "SELECT year,month,COALESCE(SUM(amount),0) "
            "FROM Monthly_Contributions WHERE status='paid' AND user_id=? "
            "GROUP BY year,month ORDER BY year DESC,month DESC LIMIT 24",
            (viewer_id,),
        ).fetchall()
        if role == "admin":
            member_totals = conn.execute(
                "SELECT u.full_name,COALESCE(SUM(mc.amount),0) "
                "FROM Users u LEFT JOIN Monthly_Contributions mc "
                "ON mc.user_id=u.user_id AND mc.status='paid' "
                "WHERE u.role='member' GROUP BY u.user_id ORDER BY u.full_name"
            ).fetchall()
            admin_csv = conn.execute(
                "SELECT contribution_id,user_id,year,month,amount,status,"
                "payment_date,payment_method,reference "
                "FROM Monthly_Contributions ORDER BY contribution_id"
            ).fetchall()
        else:
            member_totals = []
            admin_csv = []
    return {
        "is_admin": role == "admin",
        "club_recorded_paid_zar": zar(club_paid),
        "viewer_recorded_paid_zar": zar(personal_paid),
        "viewer_history": [(year, month, zar(amount)) for year, month, amount in personal_history],
        "investment_rows": investments,
        "member_totals": [(str(name), zar(amount)) for name, amount in member_totals],
        "admin_csv": admin_csv,
    }


def read_member_directory(db_path, viewer_id):
    with sqlite3.connect(db_path) as conn:
        role = _authorised(conn, viewer_id)
        if role == "admin":
            rows = conn.execute(
                "SELECT user_id,full_name,email,phone,role,fica_verified,"
                "join_date,is_active FROM Users ORDER BY join_date DESC"
            ).fetchall()
        else:
            # No disclosure of another member's identity, FICA status,
            # account activation or contact details without their consent.
            rows = conn.execute(
                "SELECT user_id,full_name,email,phone,role,fica_verified,"
                "join_date,is_active FROM Users WHERE user_id=?",
                (viewer_id,),
            ).fetchall()
    return rows
