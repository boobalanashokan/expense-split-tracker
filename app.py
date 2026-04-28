import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound
from datetime import datetime
import uuid

st.set_page_config(
    page_title="Expense Split Tracker",
    page_icon="💸",
    layout="centered"
)

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Better: use Sheet ID instead of sheet name
SHEET_ID = "10BMoKrsmSquiLh47IjMzcVL-NHJk7cdpAwmLgCyJZlQ"

REQUIRED_TABS = {
    "users": ["user_id", "name", "pin", "created_at"],
    "expenses": ["expense_id", "date", "paid_by", "total_amount", "note", "created_at"],
    "expense_items": ["item_id", "expense_id", "category", "item_name", "amount", "split_type", "visible_to", "friend_user_id"],
    "settlements": ["settlement_id", "date", "from_user", "to_user", "amount", "note", "month_key"],
}


def get_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPE
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)


def setup_database():
    workbook = get_sheet()
    existing_tabs = [ws.title for ws in workbook.worksheets()]

    for tab_name, headers in REQUIRED_TABS.items():
        if tab_name not in existing_tabs:
            ws = workbook.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
            ws.append_row(headers)
        else:
            ws = workbook.worksheet(tab_name)
            existing_headers = ws.row_values(1)

            if not existing_headers:
                ws.append_row(headers)
            else:
                missing_headers = [h for h in headers if h not in existing_headers]
                if missing_headers:
                    final_headers = existing_headers + missing_headers
                    ws.update("1:1", [final_headers])


def read_tab(tab_name):
    setup_database()
    sheet = get_sheet().worksheet(tab_name)
    data = sheet.get_all_records()
    return pd.DataFrame(data)


def append_row(tab_name, row):
    setup_database()
    sheet = get_sheet().worksheet(tab_name)
    sheet.append_row(row)


def create_user():
    st.subheader("Create User ID")

    name = st.text_input("Your name")
    pin = st.text_input("Create PIN", type="password")
    confirm_pin = st.text_input("Confirm PIN", type="password")

    if st.button("Create Account", use_container_width=True):
        if not name.strip():
            st.error("Enter your name.")
            return

        if not pin:
            st.error("Enter a PIN.")
            return

        if pin != confirm_pin:
            st.error("PIN and confirm PIN do not match.")
            return

        users = read_tab("users")

        if not users.empty and name.strip().lower() in users["name"].astype(str).str.lower().tolist():
            st.error("This name already exists. Use another name.")
            return

        user_id = "U_" + uuid.uuid4().hex[:6]
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        append_row("users", [
            user_id,
            name.strip(),
            pin,
            created_at
        ])

        st.success(f"User created successfully. Your User ID: {user_id}")


def login():
    st.title("Expense Tracker")

    setup_database()
    users = read_tab("users")

    tab1, tab2 = st.tabs(["Login", "Create User"])

    with tab1:
        if users.empty:
            st.info("No users found. Create your first user.")
        else:
            name = st.selectbox("Who are you?", users["name"].tolist())
            pin = st.text_input("PIN", type="password")

            if st.button("Login", use_container_width=True):
                user = users[
                    (users["name"].astype(str) == str(name)) &
                    (users["pin"].astype(str) == str(pin))
                ]

                if len(user) == 1:
                    st.session_state["user_id"] = user.iloc[0]["user_id"]
                    st.session_state["name"] = user.iloc[0]["name"]
                    st.rerun()
                else:
                    st.error("Wrong PIN")

    with tab2:
        create_user()


def add_expense():
    st.header("Add Expense")

    users = read_tab("users")

    if len(users) < 2:
        st.warning("Create at least 2 users to use split features.")

    current_user = st.session_state["user_id"]
    friend_options = users[users["user_id"] != current_user]

    paid_by_name = st.selectbox("Paid by", users["name"].tolist())
    paid_by = users[users["name"] == paid_by_name].iloc[0]["user_id"]

    total_amount = st.number_input("Total paid amount", min_value=0.0, step=10.0)
    note = st.text_input("Bill note")

    st.subheader("Items")

    item_count = st.number_input("Number of items", min_value=1, max_value=10, value=3)

    items = []

    for i in range(item_count):
        st.markdown(f"### Item {i + 1}")

        category = st.selectbox(
            "Category",
            ["Breakfast", "Lunch", "Snacks", "Groceries", "Household", "Petrol", "Bike Wash", "Travel", "Gift", "Subscription", "Other"],
            key=f"cat_{i}"
        )

        item_name = st.text_input("Item name", key=f"name_{i}")
        amount = st.number_input("Amount", min_value=0.0, step=10.0, key=f"amt_{i}")

        split_type = st.selectbox(
            "Who is this for?",
            ["Only me", "Only friend", "Shared equally"],
            key=f"split_{i}"
        )

        friend_id = ""
        visible_to = current_user

        if split_type in ["Only friend", "Shared equally"]:
            if friend_options.empty:
                st.error("No friend user available. Create another user first.")
                return

            friend_name = st.selectbox(
                "Friend",
                friend_options["name"].tolist(),
                key=f"friend_{i}"
            )
            friend_id = friend_options[friend_options["name"] == friend_name].iloc[0]["user_id"]
            visible_to = f"{current_user},{friend_id}"

        split_map = {
            "Only me": "private_me",
            "Only friend": "private_friend",
            "Shared equally": "shared_equal"
        }

        items.append([
            category,
            item_name,
            amount,
            split_map[split_type],
            visible_to,
            friend_id
        ])

    entered_total = sum(x[2] for x in items)
    st.info(f"Items total: ₹{entered_total:.2f}")

    if st.button("Save Expense", use_container_width=True):
        if round(entered_total, 2) != round(total_amount, 2):
            st.error("Total amount and item total are not matching.")
            return

        expense_id = "E_" + uuid.uuid4().hex[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today = datetime.now().strftime("%Y-%m-%d")

        append_row("expenses", [
            expense_id,
            today,
            paid_by,
            total_amount,
            note,
            now
        ])

        for item in items:
            item_id = "I_" + uuid.uuid4().hex[:8]
            append_row("expense_items", [
                item_id,
                expense_id,
                item[0],
                item[1],
                item[2],
                item[3],
                item[4],
                item[5]
            ])

        st.success("Expense saved")


def balances():
    st.header("Balances")

    current_user = st.session_state["user_id"]

    expenses = read_tab("expenses")
    items = read_tab("expense_items")
    settlements = read_tab("settlements")
    users = read_tab("users")

    if expenses.empty or items.empty:
        st.info("No expenses yet.")
        return

    df = items.merge(expenses, on="expense_id", how="left")
    balance = {}

    for _, row in df.iterrows():
        paid_by = row["paid_by"]
        amount = float(row["amount"])
        split_type = row["split_type"]
        friend = row["friend_user_id"]

        if split_type == "private_friend":
            if friend and paid_by == current_user:
                balance[friend] = balance.get(friend, 0) + amount

        elif split_type == "shared_equal":
            if friend:
                friend_share = amount / 2

                if paid_by == current_user:
                    balance[friend] = balance.get(friend, 0) + friend_share
                elif paid_by == friend:
                    balance[friend] = balance.get(friend, 0) - friend_share

    if not settlements.empty:
        for _, row in settlements.iterrows():
            from_user = row["from_user"]
            to_user = row["to_user"]
            amount = float(row["amount"])

            if to_user == current_user:
                balance[from_user] = balance.get(from_user, 0) - amount
            elif from_user == current_user:
                balance[to_user] = balance.get(to_user, 0) + amount

    if not balance:
        st.info("No pending balances.")
        return

    for friend_id, amt in balance.items():
        friend_row = users[users["user_id"] == friend_id]

        if friend_row.empty:
            friend_name = friend_id
        else:
            friend_name = friend_row.iloc[0]["name"]

        if amt > 0:
            st.success(f"{friend_name} owes you ₹{amt:.2f}")
        elif amt < 0:
            st.warning(f"You owe {friend_name} ₹{abs(amt):.2f}")
        else:
            st.info(f"Settled with {friend_name}")


def settle_up():
    st.header("Settle Up")

    users = read_tab("users")
    current_user = st.session_state["user_id"]

    if len(users) < 2:
        st.warning("Create at least 2 users first.")
        return

    from_name = st.selectbox("Who paid settlement?", users["name"].tolist())
    to_name = st.selectbox("Who received?", users["name"].tolist())

    from_user = users[users["name"] == from_name].iloc[0]["user_id"]
    to_user = users[users["name"] == to_name].iloc[0]["user_id"]

    amount = st.number_input("Settlement amount", min_value=0.0, step=10.0)
    note = st.text_input("Settlement note", placeholder="GPay / cash / monthly close")

    if st.button("Save Settlement", use_container_width=True):
        if from_user == to_user:
            st.error("Settlement payer and receiver cannot be same.")
            return

        settlement_id = "S_" + uuid.uuid4().hex[:8]
        today = datetime.now().strftime("%Y-%m-%d")
        month_key = datetime.now().strftime("%Y-%m")

        append_row("settlements", [
            settlement_id,
            today,
            from_user,
            to_user,
            amount,
            note,
            month_key
        ])

        st.success("Settlement saved")


def dashboard():
    st.header("My Dashboard")

    current_user = st.session_state["user_id"]
    expenses = read_tab("expenses")
    items = read_tab("expense_items")

    if expenses.empty or items.empty:
        st.info("No data yet.")
        return

    df = items.merge(expenses, on="expense_id", how="left")
    df["amount"] = df["amount"].astype(float)

    visible_df = df[df["visible_to"].astype(str).str.contains(current_user, na=False)]

    st.metric("Visible tracked amount", f"₹{visible_df['amount'].sum():.2f}")

    cat = visible_df.groupby("category")["amount"].sum().reset_index()

    if not cat.empty:
        st.bar_chart(cat, x="category", y="amount")


def main():
    setup_database()

    if "user_id" not in st.session_state:
        login()
        return

    st.sidebar.success(f"Logged in as {st.session_state['name']}")

    page = st.sidebar.radio(
        "Menu",
        ["Add Expense", "Balances", "Settle Up", "Dashboard"]
    )

    if page == "Add Expense":
        add_expense()
    elif page == "Balances":
        balances()
    elif page == "Settle Up":
        settle_up()
    elif page == "Dashboard":
        dashboard()

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()


main()
