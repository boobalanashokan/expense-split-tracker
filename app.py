import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
import random
import string

st.set_page_config(
    page_title="SplitSaathi",
    page_icon="💸",
    layout="centered"
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3, .stMetricLabel, .stMetricValue {
    font-family: 'Syne', sans-serif !important;
}

/* Hide default Streamlit header chrome */
#MainMenu, footer, header { visibility: hidden; }

.stApp {
    background: #0f0f13;
    color: #e8e4dc;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #17171f !important;
    border-right: 1px solid #2a2a38;
}
[data-testid="stSidebar"] .stRadio label {
    color: #b0acaa !important;
    font-size: 14px;
}

/* Buttons */
.stButton > button {
    background: #f0e040 !important;
    color: #0f0f13 !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px;
    transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
    background: #1e1e2a !important;
    border: 1px solid #2e2e40 !important;
    border-radius: 4px !important;
    color: #e8e4dc !important;
}

/* Metrics */
[data-testid="stMetricValue"] {
    color: #f0e040 !important;
    font-size: 2rem !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #17171f; border-radius: 6px; }
.stTabs [data-baseweb="tab"] { color: #888 !important; }
.stTabs [aria-selected="true"] { color: #f0e040 !important; border-bottom: 2px solid #f0e040 !important; }

/* Cards */
.card {
    background: #17171f;
    border: 1px solid #2a2a38;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 8px 0;
}
.badge-green { color: #4ade80; font-weight: 600; }
.badge-red   { color: #f87171; font-weight: 600; }
.badge-gray  { color: #888;    font-weight: 600; }

/* Group code display */
.group-code {
    background: #0f0f13;
    border: 2px dashed #f0e040;
    border-radius: 8px;
    padding: 12px 20px;
    font-family: 'Syne', monospace;
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: 6px;
    color: #f0e040;
    text-align: center;
    margin: 12px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SHEET_ID = "10BMoKrsmSquiLh47IjMzcVL-NHJk7cdpAwmLgCyJZlQ"

REQUIRED_TABS = {
    "users":         ["user_id", "name", "pin", "created_at"],
    "groups":        ["group_id", "group_name", "invite_code", "created_by", "created_at"],
    "group_members": ["member_id", "group_id", "user_id", "joined_at"],
    "expenses":      ["expense_id", "group_id", "date", "paid_by", "total_amount", "note", "created_at"],
    "expense_items": ["item_id", "expense_id", "group_id", "category", "item_name",
                      "amount", "split_type", "split_with"],
    "settlements":   ["settlement_id", "group_id", "date", "from_user", "to_user", "amount", "note"],
}

CATEGORIES = [
    "🍳 Breakfast", "🍛 Lunch", "🍕 Dinner", "☕ Snacks",
    "🛒 Groceries", "🏠 Household", "⛽ Petrol", "🏍️ Bike/Car",
    "✈️ Travel", "🎁 Gift", "📺 Subscription", "💊 Medical", "🎉 Fun", "📦 Other"
]

# ── GSheets helpers ───────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPE
    )
    return gspread.authorize(creds)

def get_sheet():
    return get_client().open_by_key(SHEET_ID)

def setup_database():
    workbook = get_sheet()
    existing_tabs = [ws.title for ws in workbook.worksheets()]
    for tab_name, headers in REQUIRED_TABS.items():
        if tab_name not in existing_tabs:
            ws = workbook.add_worksheet(title=tab_name, rows=2000, cols=len(headers))
            ws.append_row(headers)
        else:
            ws = workbook.worksheet(tab_name)
            if not ws.row_values(1):
                ws.append_row(headers)

def read_tab(tab_name):
    ws = get_sheet().worksheet(tab_name)
    data = ws.get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame(columns=REQUIRED_TABS[tab_name])

def append_row(tab_name, row):
    get_sheet().worksheet(tab_name).append_row(row)

def gen_invite_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ── Auth ──────────────────────────────────────────────────────────────────────
def login_page():
    st.markdown("<h1 style='font-size:2.8rem; margin-bottom:0'>💸 SplitSaathi</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#888; margin-top:4px'>Track expenses. Split fairly. No drama.</p>", unsafe_allow_html=True)
    st.markdown("---")

    users = read_tab("users")
    tab1, tab2 = st.tabs(["Login", "Create Account"])

    with tab1:
        if users.empty:
            st.info("No users yet. Create an account first.")
        else:
            name = st.selectbox("Who are you?", users["name"].tolist())
            pin  = st.text_input("PIN", type="password", key="login_pin")
            if st.button("Login →", use_container_width=True):
                user = users[
                    (users["name"].astype(str) == str(name)) &
                    (users["pin"].astype(str)  == str(pin))
                ]
                if len(user) == 1:
                    st.session_state["user_id"] = user.iloc[0]["user_id"]
                    st.session_state["name"]    = user.iloc[0]["name"]
                    st.rerun()
                else:
                    st.error("Wrong PIN.")

    with tab2:
        name = st.text_input("Your name", key="reg_name")
        pin  = st.text_input("Create PIN", type="password", key="reg_pin")
        pin2 = st.text_input("Confirm PIN", type="password", key="reg_pin2")
        if st.button("Create Account", use_container_width=True, key="reg_btn"):
            if not name.strip():
                st.error("Enter a name.")
            elif not pin:
                st.error("Enter a PIN.")
            elif pin != pin2:
                st.error("PINs don't match.")
            elif not users.empty and name.strip().lower() in users["name"].str.lower().tolist():
                st.error("Name already taken.")
            else:
                uid = "U_" + uuid.uuid4().hex[:6]
                append_row("users", [uid, name.strip(), pin, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                st.success(f"Account created! Login now.")

# ── Group management ───────────────────────────────────────────────────────────
def group_page():
    st.markdown("<h2>Groups</h2>", unsafe_allow_html=True)
    uid = st.session_state["user_id"]

    groups   = read_tab("groups")
    members  = read_tab("group_members")
    users    = read_tab("users")

    # Groups this user belongs to
    my_gids = members[members["user_id"] == uid]["group_id"].tolist() if not members.empty else []
    my_groups = groups[groups["group_id"].isin(my_gids)] if not groups.empty else pd.DataFrame()

    if not my_groups.empty:
        st.markdown("### Your Groups")
        for _, g in my_groups.iterrows():
            gid = g["group_id"]
            gname = g["group_name"]
            code  = g["invite_code"]
            gmems = members[members["group_id"] == gid]["user_id"].tolist() if not members.empty else []
            mem_names = users[users["user_id"].isin(gmems)]["name"].tolist()

            st.markdown(f"""
            <div class="card">
                <div style="font-family:Syne;font-size:1.1rem;font-weight:700">{gname}</div>
                <div style="color:#888;font-size:13px">👥 {', '.join(mem_names)}</div>
            </div>""", unsafe_allow_html=True)

            if st.button(f"Open → {gname}", key=f"open_{gid}"):
                st.session_state["group_id"]   = gid
                st.session_state["group_name"] = gname
                st.rerun()

            with st.expander(f"Invite code for {gname}"):
                st.markdown(f'<div class="group-code">{code}</div>', unsafe_allow_html=True)
                st.caption("Share this code with friends to let them join.")

        st.markdown("---")

    tab1, tab2 = st.tabs(["Create Group", "Join Group"])

    with tab1:
        gname = st.text_input("Group name (e.g. Goa Trip, Home)")
        if st.button("Create Group", use_container_width=True):
            if not gname.strip():
                st.error("Enter a group name.")
            else:
                gid   = "G_" + uuid.uuid4().hex[:6]
                code  = gen_invite_code()
                now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                append_row("groups",        [gid, gname.strip(), code, uid, now])
                append_row("group_members", ["M_" + uuid.uuid4().hex[:6], gid, uid, now])
                st.success(f"Group '{gname}' created!")
                st.markdown(f'<div class="group-code">{code}</div>', unsafe_allow_html=True)
                st.caption("Share this invite code with your friends.")
                st.rerun()

    with tab2:
        code = st.text_input("Enter invite code", placeholder="ABC123").strip().upper()
        if st.button("Join Group", use_container_width=True):
            if not code:
                st.error("Enter a code.")
            elif groups.empty or code not in groups["invite_code"].tolist():
                st.error("Invalid invite code.")
            else:
                target = groups[groups["invite_code"] == code].iloc[0]
                gid    = target["group_id"]
                already = members[(members["group_id"] == gid) & (members["user_id"] == uid)]
                if not already.empty:
                    st.info("You're already in this group.")
                else:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    append_row("group_members", ["M_" + uuid.uuid4().hex[:6], gid, uid, now])
                    st.success(f"Joined '{target['group_name']}'!")
                    st.rerun()

# ── Add Expense ───────────────────────────────────────────────────────────────
def add_expense():
    st.markdown("<h2>Add Expense</h2>", unsafe_allow_html=True)

    gid      = st.session_state["group_id"]
    uid      = st.session_state["user_id"]
    members  = read_tab("group_members")
    users    = read_tab("users")

    group_uids  = members[members["group_id"] == gid]["user_id"].tolist()
    group_users = users[users["user_id"].isin(group_uids)]

    if group_users.empty:
        st.warning("No members in this group yet.")
        return

    paid_by_name = st.selectbox("Paid by", group_users["name"].tolist())
    paid_by      = group_users[group_users["name"] == paid_by_name].iloc[0]["user_id"]
    total_amount = st.number_input("Total amount paid (₹)", min_value=0.0, step=10.0)
    note         = st.text_input("Bill note (optional)", placeholder="Dinner at Haldiram's")

    st.markdown("---")
    st.markdown("### Items")
    item_count = st.number_input("Number of items", min_value=1, max_value=20, value=2)

    items = []
    total_entered = 0.0

    other_users = group_users[group_users["user_id"] != uid]

    for i in range(int(item_count)):
        with st.expander(f"Item {i+1}", expanded=True):
            category  = st.selectbox("Category",  CATEGORIES, key=f"cat_{i}")
            item_name = st.text_input("Item name", key=f"iname_{i}")
            amount    = st.number_input("Amount (₹)", min_value=0.0, step=1.0, key=f"amt_{i}")
            total_entered += amount

            split_options = ["Only me"]
            if not other_users.empty:
                split_options += ["Shared equally (all)", "Split with specific people", "Only specific person pays"]

            split_type = st.selectbox("Split type", split_options, key=f"split_{i}")

            split_with = []  # list of user_ids this is split among

            if split_type == "Only me":
                split_with = [uid]

            elif split_type == "Shared equally (all)":
                split_with = group_uids  # everyone

            elif split_type == "Split with specific people":
                chosen_names = st.multiselect(
                    "Split with (select people, you're included automatically)",
                    other_users["name"].tolist(), key=f"msel_{i}"
                )
                chosen_ids = other_users[other_users["name"].isin(chosen_names)]["user_id"].tolist()
                split_with = [uid] + chosen_ids  # always include self

            elif split_type == "Only specific person pays":
                chosen_name = st.selectbox("Who pays for this?", group_users["name"].tolist(), key=f"solo_{i}")
                chosen_id   = group_users[group_users["name"] == chosen_name].iloc[0]["user_id"]
                split_with  = [chosen_id]

            items.append({
                "category":   category,
                "item_name":  item_name,
                "amount":     amount,
                "split_type": split_type,
                "split_with": ",".join(split_with),
            })

    st.markdown(f"**Items total: ₹{total_entered:.2f}**")

    if st.button("💾 Save Expense", use_container_width=True):
        if round(total_entered, 2) != round(total_amount, 2):
            st.error(f"Item total ₹{total_entered:.2f} ≠ Total paid ₹{total_amount:.2f}. Please fix.")
            return

        expense_id = "E_" + uuid.uuid4().hex[:8]
        now        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today      = datetime.now().strftime("%Y-%m-%d")

        append_row("expenses", [expense_id, gid, today, paid_by, total_amount, note, now])

        for item in items:
            item_id = "I_" + uuid.uuid4().hex[:8]
            append_row("expense_items", [
                item_id, expense_id, gid,
                item["category"], item["item_name"], item["amount"],
                item["split_type"], item["split_with"]
            ])

        st.success("✅ Expense saved!")

# ── Balances ──────────────────────────────────────────────────────────────────
def balances():
    st.markdown("<h2>Balances</h2>", unsafe_allow_html=True)

    gid   = st.session_state["group_id"]
    uid   = st.session_state["user_id"]
    users = read_tab("users")
    members = read_tab("group_members")

    group_uids  = members[members["group_id"] == gid]["user_id"].tolist()

    expenses   = read_tab("expenses")
    items      = read_tab("expense_items")
    settlements= read_tab("settlements")

    # Filter to this group only
    if expenses.empty or items.empty:
        st.info("No expenses in this group yet.")
        return

    grp_expenses = expenses[expenses["group_id"] == gid]
    if grp_expenses.empty:
        st.info("No expenses in this group yet.")
        return

    grp_items = items[items["group_id"] == gid]

    # net[a][b] = amount b owes a
    net = {}  # net[creditor][debtor] = amount

    def add_debt(creditor, debtor, amount):
        if creditor == debtor or amount == 0:
            return
        if creditor not in net:
            net[creditor] = {}
        net[creditor][debtor] = net[creditor].get(debtor, 0) + amount

    for _, exp in grp_expenses.iterrows():
        paid_by  = exp["paid_by"]
        eid      = exp["expense_id"]
        exp_items= grp_items[grp_items["expense_id"] == eid]

        for _, row in exp_items.iterrows():
            amount     = float(row["amount"])
            split_with = [s.strip() for s in str(row["split_with"]).split(",") if s.strip()]

            if not split_with:
                continue

            per_person = amount / len(split_with)

            for person in split_with:
                if person != paid_by:
                    add_debt(paid_by, person, per_person)

    # Apply settlements
    if not settlements.empty:
        grp_settlements = settlements[settlements["group_id"] == gid]
        for _, row in grp_settlements.iterrows():
            from_user = row["from_user"]
            to_user   = row["to_user"]
            amount    = float(row["amount"])
            # from_user paid to_user → reduces to_user's debt to from_user
            if to_user in net and from_user in net[to_user]:
                net[to_user][from_user] = max(0, net[to_user].get(from_user, 0) - amount)

    def user_name(uid_):
        r = users[users["user_id"] == uid_]
        return r.iloc[0]["name"] if not r.empty else uid_

    # Show balances relevant to current user
    found = False
    for creditor, debtors in net.items():
        for debtor, amount in debtors.items():
            if amount < 0.01:
                continue
            if creditor == uid:
                found = True
                st.markdown(f"""
                <div class="card">
                    <span class="badge-green">↑ {user_name(debtor)} owes you ₹{amount:.2f}</span>
                </div>""", unsafe_allow_html=True)
            elif debtor == uid:
                found = True
                st.markdown(f"""
                <div class="card">
                    <span class="badge-red">↓ You owe {user_name(creditor)} ₹{amount:.2f}</span>
                </div>""", unsafe_allow_html=True)

    if not found:
        st.markdown('<div class="card"><span class="badge-gray">✓ All settled up!</span></div>', unsafe_allow_html=True)

    # Group-wide summary
    st.markdown("---")
    st.markdown("### Group Overview")
    for creditor, debtors in net.items():
        for debtor, amount in debtors.items():
            if amount < 0.01:
                continue
            st.markdown(f"<div class='card' style='font-size:13px;color:#999'>"
                        f"{user_name(debtor)} → {user_name(creditor)}: "
                        f"<b style='color:#e8e4dc'>₹{amount:.2f}</b></div>",
                        unsafe_allow_html=True)

# ── Settle Up ─────────────────────────────────────────────────────────────────
def settle_up():
    st.markdown("<h2>Settle Up</h2>", unsafe_allow_html=True)

    gid     = st.session_state["group_id"]
    members = read_tab("group_members")
    users   = read_tab("users")

    group_uids  = members[members["group_id"] == gid]["user_id"].tolist()
    group_users = users[users["user_id"].isin(group_uids)]

    if len(group_users) < 2:
        st.warning("Need at least 2 members to settle.")
        return

    from_name = st.selectbox("Who paid?",      group_users["name"].tolist(), key="s_from")
    to_name   = st.selectbox("Who received?",  group_users["name"].tolist(), key="s_to")
    amount    = st.number_input("Amount (₹)",  min_value=0.0, step=10.0)
    note      = st.text_input("Note (optional)", placeholder="GPay / Cash")

    if st.button("Save Settlement", use_container_width=True):
        from_uid = group_users[group_users["name"] == from_name].iloc[0]["user_id"]
        to_uid   = group_users[group_users["name"] == to_name].iloc[0]["user_id"]

        if from_uid == to_uid:
            st.error("Payer and receiver can't be the same.")
            return

        sid   = "S_" + uuid.uuid4().hex[:8]
        today = datetime.now().strftime("%Y-%m-%d")
        append_row("settlements", [sid, gid, today, from_uid, to_uid, amount, note])
        st.success("Settlement recorded!")

# ── Expense History ────────────────────────────────────────────────────────────
def history():
    st.markdown("<h2>Expense History</h2>", unsafe_allow_html=True)

    gid   = st.session_state["group_id"]
    users = read_tab("users")

    expenses = read_tab("expenses")
    items    = read_tab("expense_items")

    if expenses.empty:
        st.info("No expenses yet.")
        return

    grp_exp = expenses[expenses["group_id"] == gid].sort_values("date", ascending=False)

    if grp_exp.empty:
        st.info("No expenses in this group yet.")
        return

    def uname(uid_):
        r = users[users["user_id"] == uid_]
        return r.iloc[0]["name"] if not r.empty else uid_

    for _, exp in grp_exp.iterrows():
        eid       = exp["expense_id"]
        paid_by   = uname(exp["paid_by"])
        exp_items = items[items["expense_id"] == eid] if not items.empty else pd.DataFrame()

        with st.expander(f"📋 {exp['date']}  |  {exp['note'] or 'Expense'}  |  ₹{float(exp['total_amount']):.2f}  (paid by {paid_by})"):
            if exp_items.empty:
                st.write("No items found.")
            else:
                for _, it in exp_items.iterrows():
                    sw = [uname(x.strip()) for x in str(it["split_with"]).split(",") if x.strip()]
                    st.markdown(
                        f"**{it['item_name'] or '—'}** ({it['category']})  "
                        f"₹{float(it['amount']):.2f}  "
                        f"— split: {', '.join(sw)}"
                    )

# ── Dashboard ─────────────────────────────────────────────────────────────────
def dashboard():
    st.markdown("<h2>Dashboard</h2>", unsafe_allow_html=True)

    gid   = st.session_state["group_id"]
    uid   = st.session_state["user_id"]
    users = read_tab("users")

    expenses = read_tab("expenses")
    items    = read_tab("expense_items")

    if expenses.empty or items.empty:
        st.info("No data yet.")
        return

    grp_exp   = expenses[expenses["group_id"] == gid]
    grp_items = items[items["group_id"] == gid]

    if grp_exp.empty:
        st.info("No data yet.")
        return

    total_group = grp_exp["total_amount"].astype(float).sum()
    members     = read_tab("group_members")
    mem_count   = len(members[members["group_id"] == gid])

    # My share items
    my_items = grp_items[grp_items["split_with"].astype(str).str.contains(uid, na=False)]
    my_share = 0.0
    for _, row in my_items.iterrows():
        sw = [s.strip() for s in str(row["split_with"]).split(",") if s.strip()]
        my_share += float(row["amount"]) / max(len(sw), 1)

    c1, c2, c3 = st.columns(3)
    c1.metric("Group Total",  f"₹{total_group:.0f}")
    c2.metric("Your Share",   f"₹{my_share:.0f}")
    c3.metric("Members",      mem_count)

    st.markdown("---")
    st.markdown("### Spending by Category")

    if not grp_items.empty:
        grp_items = grp_items.copy()
        grp_items["amount"] = grp_items["amount"].astype(float)
        cat = grp_items.groupby("category")["amount"].sum().reset_index()
        cat = cat.sort_values("amount", ascending=False)
        st.bar_chart(cat.set_index("category")["amount"])

    st.markdown("### My Category Breakdown")
    if not my_items.empty:
        my_items = my_items.copy()
        my_items["my_share"] = my_items.apply(
            lambda r: float(r["amount"]) / max(len([s for s in str(r["split_with"]).split(",") if s.strip()]), 1), axis=1
        )
        cat2 = my_items.groupby("category")["my_share"].sum().reset_index()
        st.bar_chart(cat2.set_index("category")["my_share"])

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if "db_ready" not in st.session_state:
        setup_database()
        st.session_state["db_ready"] = True

    # Not logged in
    if "user_id" not in st.session_state:
        login_page()
        return

    # Logged in but no group selected
    if "group_id" not in st.session_state:
        st.sidebar.markdown(f"**👤 {st.session_state['name']}**")
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()
        group_page()
        return

    # Logged in + group selected
    gname = st.session_state.get("group_name", "Group")
    st.sidebar.markdown(f"**👤 {st.session_state['name']}**")
    st.sidebar.markdown(f"<div style='color:#f0e040;font-size:13px;margin-bottom:8px'>📁 {gname}</div>",
                        unsafe_allow_html=True)

    if st.sidebar.button("⬅ Switch Group"):
        del st.session_state["group_id"]
        del st.session_state["group_name"]
        st.rerun()

    page = st.sidebar.radio("Menu", ["Add Expense", "Balances", "Settle Up", "History", "Dashboard"])

    if page == "Add Expense": add_expense()
    elif page == "Balances":  balances()
    elif page == "Settle Up": settle_up()
    elif page == "History":   history()
    elif page == "Dashboard": dashboard()

    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()


main()
