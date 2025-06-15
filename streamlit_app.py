import streamlit as st
import sqlite3
import pandas as pd
import random
from datetime import datetime
import os
from PIL import Image
import base64
import json
from tabs.recharge_catalogue_tab import show as show_recharge_catalogue
from tabs.products_tab import show as show_products
from tabs.about_us import show as show_about_us
from db import get_connection

# Set page config BEFORE any other Streamlit commands
st.set_page_config(page_title="Sri Kailash Electronics", layout="wide")

# --- DB Setup ---
conn, c = get_connection(db_path="recharge.db")


def get_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


# --- Logo Setup ---
def set_logo():
    logo_path = "ske.svg"  # Replace with the correct logo file name
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            .logo {{
                position: fixed;
                top: 20px;
                left: 20px;
                width: 150px;
                z-index: 1000;
            }}
            </style>
            <div class="logo">
                <img src="data:image/jpeg;base64,{logo_base64}" alt="SKE">
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.error(f"Logo image not found at {logo_path}")

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

# --- Load password from config.json ---
APP_PASSWORD = config.get("app_password", "")

# --- Simple Login Page ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login")
    password = st.text_input("Enter password", type="password")
    if st.button("Login"):
        if password == APP_PASSWORD:
            st.session_state.logged_in = True
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# Call the function to set the logo
set_logo()

# --- Navigation Menu ---
st.title("Sri Kailash Electronics")

tab_names = [
    "Dashboard", "Clients", "Recharge Catalogue", "Recharge Orders",
    "Product Catalogue", "Product Orders", "WhatsApp Ads", "WhatsApp Alerts",
    "Lucky Draw", "About Us"
]
tabs = st.tabs(tab_names)

with tabs[0]:
    # --- Dashboard ---
    st.title("📊 Dashboard Overview")
    total_clients = pd.read_sql_query("SELECT COUNT(*) as cnt FROM clients", conn).iloc[0]['cnt']
    total_orders = pd.read_sql_query("SELECT COUNT(*) as cnt FROM orders", conn).iloc[0]['cnt']
    
    # Only sum commission for 'Recharged' orders
    commission_df = pd.read_sql_query(
        "SELECT amount, discount FROM orders WHERE status='Recharged'", conn
    )
    if not commission_df.empty:
        commission_df['commission'] = (commission_df['amount'] * 0.05) - commission_df['discount']
        commission_df['commission'] = commission_df['commission'].clip(lower=0)
        total_commission = commission_df['commission'].sum()
    else:
        total_commission = 0

    due_clients = pd.read_sql_query(
        f"SELECT * FROM clients WHERE recharge_day={datetime.today().day}", conn
    )
    due_count = len(due_clients)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Clients", total_clients)
    col2.metric("Total Recharge Orders", total_orders)
    col3.metric("Total Commission (₹)", f"{total_commission:.2f}")
    col4.metric("Recharges Due Today", due_count)
    
    st.markdown("---")
    st.markdown("### Pending Recharge Orders")
    pending_orders = pd.read_sql_query("SELECT * FROM orders WHERE status='Pending'", conn)
    if not pending_orders.empty:
        pending_orders['commission'] = (pending_orders['amount'] * 0.05) - pending_orders['discount']
        pending_orders['commission'] = pending_orders['commission'].clip(lower=0)
        st.dataframe(pending_orders[['id', 'client_id', 'amount', 'discount', 'commission', 'status', 'created_at']])
    else:
        st.info("No pending recharge orders.")
    
    st.markdown("### Pending Product Orders")
    pending_product = pd.read_sql_query("SELECT * FROM product_orders WHERE status='Pending' ORDER BY created_at DESC", conn)
    if not pending_product.empty:
        st.dataframe(pending_product)
    else:
        st.info("No pending product orders.")

    # --- Pending Due Recharges ---
    st.markdown("### Pending Due Recharges")

    today_day = datetime.today().day
    this_month = datetime.today().strftime("%Y-%m")

    # Get clients whose recharge_day is today
    due_clients = pd.read_sql_query(
        f"SELECT * FROM clients WHERE recharge_day={today_day}", conn
    )

    if not due_clients.empty:
        # Find clients who do NOT have a 'Recharged' order this month
        due_clients['has_recharged'] = due_clients['id'].apply(
            lambda cid: pd.read_sql_query(
                "SELECT COUNT(*) as cnt FROM orders WHERE client_id=? AND status='Recharged' AND strftime('%Y-%m', created_at)=?",
                conn, params=(cid, this_month)
            ).iloc[0]['cnt'] > 0
        )
        pending_due = due_clients[~due_clients['has_recharged']]
        if not pending_due.empty:
            st.dataframe(
                pending_due[['id', 'name', 'phone', 'operator', 'plan_amount', 'recharge_day']]
                .rename(columns={
                    'id': 'Client ID',
                    'name': 'Name',
                    'phone': 'Phone',
                    'operator': 'Operator',
                    'plan_amount': 'Plan Amount',
                    'recharge_day': 'Due Day'
                })
            )
        else:
            st.info("No pending due recharges for today.")
    else:
        st.info("No clients with recharge due today.")

with tabs[1]:
    # --- Clients ---
    st.title("👥 Clients Management")
    search_term = st.text_input("Search Clients (Name or Phone)")
    if search_term:
        query = f"""
        SELECT c.*, 
          (SELECT COUNT(*) FROM orders WHERE client_id = c.id) AS total_recharge_orders,
          (SELECT COUNT(*) FROM product_orders WHERE client_id = c.id) AS total_product_orders
        FROM clients AS c
        WHERE name LIKE '%{search_term}%' OR phone LIKE '%{search_term}%'
        """
    else:
        query = """
        SELECT c.*, 
          (SELECT COUNT(*) FROM orders WHERE client_id = c.id) AS total_recharge_orders,
          (SELECT COUNT(*) FROM product_orders WHERE client_id = c.id) AS total_product_orders
        FROM clients AS c
        """
    df_clients = pd.read_sql_query(query, conn)
    st.dataframe(df_clients)
    
    selected_client_id = st.number_input("Enter Client ID to View Details", min_value=0, step=1)
    if selected_client_id > 0:
        client_df = pd.read_sql_query(f"SELECT * FROM clients WHERE id={selected_client_id}", conn)
        if not client_df.empty:
            client = client_df.iloc[0]
            st.markdown(f"### Client Profile: {client['name']} (ID: {client['id']})")
            st.write(f"**Phone:** {client['phone']}")
            st.write(f"**Group:** {client['group_name']}")
            st.write(f"**Operator:** {client['operator']}")
            st.write(f"**Plan Amount:** ₹{client['plan_amount']}")
            st.write(f"**Recharge Day:** {client['recharge_day']}")
            st.write(f"**Premium:** {'Yes' if client['premium'] else 'No'}")
            st.write(f"**Lucky Draw Wins:** {client.get('lucky_draw_wins', 0)}")
            st.write(f"**Referred:** {'Yes' if client.get('referred') else 'No'}")
            st.write(f"**Referred By:** {client.get('referred_by_name', '')} ({client.get('referred_by_phone', '')})")
            st.write(f"**Notes:** {client.get('notes', '')}")
            
            orders = pd.read_sql_query(f"SELECT * FROM orders WHERE client_id={selected_client_id} ORDER BY created_at DESC", conn)
            if orders.empty:
                st.info("No recharge orders for this client.")
            else:
                st.subheader("Recharge History")
                st.dataframe(orders)
        else:
            st.error("Client not found.")
    
    with st.expander("Add New Client"):
        with st.form("add_client"):
            name = st.text_input("Name")
            phone = st.text_input("Phone")
            group_options = ["Family", "Friends", "Colleagues", "VIP", "Others"]
            group_name = st.selectbox("Group", group_options)
            if group_name == "Others":
                custom_group = st.text_input("Enter Custom Group")
                final_group = custom_group
            else:
                final_group = group_name
            operator = st.text_input("Operator")
            plan_amount = st.number_input("Plan Amount", min_value=0.0, step=1.0)
            recharge_day = st.number_input("Recharge Day", min_value=1, max_value=31, step=1)
            is_premium = st.selectbox("Premium?", ["No", "Yes"])
            lucky_draw_wins = st.number_input("Lucky Draw Wins", min_value=0, step=1)
            referred = st.selectbox("Referred?", ["No", "Yes"])
            referred_by_name = st.text_input("Referred By Name") if referred == "Yes" else ""
            referred_by_phone = st.text_input("Referred By Phone") if referred == "Yes" else ""
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Add Client")
            if submitted:
                premium_val = 1 if is_premium == "Yes" else 0
                referred_val = 1 if referred == "Yes" else 0
                if not name or not phone or not final_group:
                    st.error("Name, Phone, and Group are required.")
                else:
                    try:
                        c.execute(
                            "INSERT INTO clients (name, phone, group_name, operator, plan_amount, recharge_day, premium, lucky_draw_wins, referred, referred_by_name, referred_by_phone, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (name, phone, final_group, operator, plan_amount, recharge_day, premium_val, lucky_draw_wins, referred_val, referred_by_name, referred_by_phone, notes)
                        )
                        conn.commit()
                        st.success("Client added successfully!")
                    except sqlite3.IntegrityError:
                        st.error("Phone number already exists.")
    
    with st.expander("Edit / Delete Client"):
        edit_client_id = st.number_input("Enter Client ID", key="edit_client_id")
        if st.button("Fetch Client Data", key="fetch_client"):
            edit_client_df = pd.read_sql_query("SELECT * FROM clients WHERE id=?", conn, params=(edit_client_id,))
            if edit_client_df.empty:
                st.error("Client not found.")
            else:
                st.session_state.edit_client = edit_client_df.iloc[0].to_dict()
                st.success("Client data fetched!")
        if "edit_client" in st.session_state and isinstance(st.session_state.edit_client, dict):
            data = st.session_state.edit_client
            with st.form("update_client"):
                new_name = st.text_input("Name", value=data["name"])
                new_phone = st.text_input("Phone", value=data["phone"])
                group_options = ["Family", "Friends", "Colleagues", "VIP", "Others"]
                group_name = st.selectbox("Group", group_options,
                                          index=group_options.index(data["group_name"]) if data["group_name"] in group_options else 0)
                if group_name == "Others":
                    custom_group = st.text_input("Custom Group", value=data["group_name"])
                    final_group = custom_group
                else:
                    final_group = group_name
                new_operator = st.text_input("Operator", value=data.get("operator", ""))
                new_plan_amount = st.number_input("Plan Amount", min_value=0.0, step=1.0, value=float(data.get("plan_amount", 0)))
                new_recharge_day = st.number_input("Recharge Day", min_value=1, max_value=31, step=1, value=int(data.get("recharge_day", 1)))
                is_premium = st.selectbox("Premium?", ["No", "Yes"], index=1 if data.get("premium") else 0)
                new_lucky_draw_wins = st.number_input("Lucky Draw Wins", min_value=0, step=1, value=int(data.get("lucky_draw_wins", 0)))
                referred = st.selectbox("Referred?", ["No", "Yes"], index=1 if data.get("referred") else 0)
                new_referred_by_name = st.text_input("Referred By Name", value=data.get("referred_by_name", ""))
                new_referred_by_phone = st.text_input("Referred By Phone", value=data.get("referred_by_phone", ""))
                new_notes = st.text_area("Notes", value=data.get("notes", ""))
                update_client = st.form_submit_button("Update Client")
                if update_client:
                    premium_val = 1 if is_premium == "Yes" else 0
                    referred_val = 1 if referred == "Yes" else 0
                    try:
                        c.execute(
                            """UPDATE clients SET name=?, phone=?, group_name=?, operator=?, plan_amount=?, recharge_day=?, 
                            premium=?, lucky_draw_wins=?, referred=?, referred_by_name=?, referred_by_phone=?, notes=? WHERE id=?""",
                            (new_name, new_phone, final_group, new_operator, new_plan_amount, new_recharge_day,
                             premium_val, new_lucky_draw_wins, referred_val, new_referred_by_name, new_referred_by_phone, new_notes, data["id"])
                        )
                        conn.commit()
                        st.success("Client updated successfully!")
                        del st.session_state.edit_client
                    except sqlite3.IntegrityError as e:
                        st.error("Update failed: " + str(e))
            st.markdown("### Delete Client")
            confirm_del = st.checkbox("Confirm deletion", key="confirm_del")
            if st.button("Delete Client", key="delete_client"):
                if confirm_del:
                    try:
                        c.execute("DELETE FROM clients WHERE id=?", (data["id"],))
                        conn.commit()
                        st.success("Client deleted successfully!")
                        del st.session_state.edit_client
                    except Exception as e:
                        st.error("Deletion failed: " + str(e))
                else:
                    st.error("Please confirm deletion by checking the box.")
        else:
            st.info("Fetch a client to edit or delete.")

with tabs[2]:
    show_recharge_catalogue(conn, c)
    

with tabs[3]:
    # --- Recharge Orders ---
    st.title("⚡ Recharge Orders")
    with st.expander("Add New Recharge Order"):
        with st.form("add_recharge_order"):
            client_id = st.number_input("Client ID", min_value=1, step=1)
            if client_id:
                client_data = pd.read_sql_query("SELECT name FROM clients WHERE id=?", conn, params=(client_id,))
                if not client_data.empty:
                    st.write(f"Client Name: {client_data.iloc[0]['name']}")
                else:
                    st.error("Client ID not found.")
            else:
                st.error("Please enter a valid Client ID.")
            
            
            amount = st.number_input("Amount (₹)", min_value=0.0, step=1.0)
            discount = 0.0
            if amount:
                discount_min = config["discount"]["min"]
                discount_max = config["discount"]["max"]
                discount = round(amount * random.uniform(discount_min, discount_max), 2)
            st.number_input("Discount (%)", value=discount, disabled=True, step=0.01)
            status = st.selectbox("Status", ["Pending", "Recharged", "Failed"])
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            add_order = st.form_submit_button("Add Recharge Order")
            if add_order:
                try:
                    c.execute("INSERT INTO orders (client_id, amount, discount, commission, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                              (client_id, amount, discount, 0.0, status, created_at))
                    conn.commit()
                    st.success("Recharge order added successfully!")
                except Exception as e:
                    st.error("Failed to add recharge order: " + str(e))
    st.markdown("### Recharge Orders List")
    orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC", conn)
    if not orders_df.empty:
        orders_df['commission'] = (orders_df['amount'] * 0.05) - orders_df['discount']
        orders_df['commission'] = orders_df['commission'].clip(lower=0)
        st.dataframe(orders_df[['id', 'client_id', 'amount', 'discount', 'commission', 'status', 'created_at']])
    else:
        st.info("No recharge orders available.")
    with st.expander("Edit / Delete Recharge Order"):
        order_id = st.number_input("Enter Order ID", min_value=1, step=1, key="order_id")
        if st.button("Fetch Order Data", key="fetch_order"):
            order_fetch = pd.read_sql_query("SELECT * FROM orders WHERE id=?", conn, params=(order_id,))
            if order_fetch.empty:
                st.error("Order not found.")
            else:
                st.session_state.order_data = order_fetch.iloc[0].to_dict()
                st.success("Order data fetched!")
        if "order_data" in st.session_state:
            order_data = st.session_state.order_data
            with st.form("update_order_form"):
                new_client_id = st.number_input("Client ID", min_value=1, value=int(order_data["client_id"]))
                new_amount = st.number_input("Amount (₹)", min_value=0.0, step=1.0, value=float(order_data["amount"]))
                new_discount = round(new_amount * random.uniform(0.0025, 0.0175), 2)
                st.number_input("Discount (%)", value=new_discount, disabled=True, step=0.01)
                new_status = st.selectbox("Status", ["Pending", "Recharged", "Failed"],
                                          index=["Pending", "Recharged", "Failed"].index(order_data["status"]))
                update_order = st.form_submit_button("Update Order")
                if update_order:
                    try:
                        c.execute("UPDATE orders SET client_id=?, amount=?, discount=?, status=? WHERE id=?",
                                  (new_client_id, new_amount, new_discount, new_status, order_data["id"]))
                        conn.commit()
                        st.success("Order updated successfully!")
                        del st.session_state.order_data
                    except Exception as e:
                        st.error("Update failed: " + str(e))
            st.markdown("### Delete Order")
            confirm_order_del = st.checkbox("Confirm deletion", key="confirm_order_del")
            if st.button("Delete Order", key="delete_order"):
                if confirm_order_del:
                    try:
                        c.execute("DELETE FROM orders WHERE id=?", (order_data["id"],))
                        conn.commit()
                        st.success("Order deleted successfully!")
                        del st.session_state.order_data
                    except Exception as e:
                        st.error("Deletion failed: " + str(e))
                else:
                    st.error("Please confirm deletion.")

with tabs[4]:
   show_products(conn, c)

with tabs[5]:
    # --- Product Orders ---
    st.title("📦 Product Orders")
    with st.expander("Add New Product Order"):
        with st.form("add_product_order"):
            product_id = st.number_input("Product ID", min_value=1, step=1)
            client_id = st.number_input("Client ID", min_value=1, step=1)
            quantity = st.number_input("Quantity", min_value=1, step=1)
            status = st.selectbox("Status", ["Pending", "Completed", "Cancelled"])
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            add_prod_order = st.form_submit_button("Add Product Order")
            if add_prod_order:
                try:
                    c.execute("INSERT INTO product_orders (product_id, client_id, quantity, status, created_at) VALUES (?, ?, ?, ?, ?)",
                              (product_id, client_id, quantity, status, created_at))
                    conn.commit()
                    st.success("Product order added successfully!")
                except Exception as e:
                    st.error("Failed to add product order: " + str(e))
    st.markdown("### Product Orders List")
    prod_orders_df = pd.read_sql_query("SELECT * FROM product_orders ORDER BY created_at DESC", conn)
    if not prod_orders_df.empty:
        st.dataframe(prod_orders_df)
    else:
        st.info("No product orders available.")
    with st.expander("Edit / Delete Product Order"):
        prod_order_id = st.number_input("Enter Product Order ID", min_value=1, step=1, key="prod_order_id")
        if st.button("Fetch Order Data", key="fetch_prod_order"):
            order_fetch = pd.read_sql_query("SELECT * FROM product_orders WHERE id=?", conn, params=(prod_order_id,))
            if order_fetch.empty:
                st.error("Product order not found.")
            else:
                st.session_state.prod_order = order_fetch.iloc[0].to_dict()
                st.success("Product order data fetched!")
        if "prod_order" in st.session_state:
            order_data = st.session_state.prod_order
            with st.form("update_prod_order_form"):
                new_product_id = st.number_input("Product ID", min_value=1, value=int(order_data["product_id"]))
                new_client_id = st.number_input("Client ID", min_value=1, value=int(order_data["client_id"]))
                new_quantity = st.number_input("Quantity", min_value=1, step=1, value=int(order_data["quantity"]))
                new_status = st.selectbox("Status", ["Pending", "Completed", "Cancelled"],
                                          index=["Pending", "Completed", "Cancelled"].index(order_data["status"]))
                update_order = st.form_submit_button("Update Product Order")
                if update_order:
                    try:
                        c.execute("UPDATE product_orders SET product_id=?, client_id=?, quantity=?, status=? WHERE id=?",
                                  (new_product_id, new_client_id, new_quantity, new_status, order_data["id"]))
                        conn.commit()
                        st.success("Product order updated successfully!")
                        del st.session_state.prod_order
                    except Exception as e:
                        st.error("Update failed: " + str(e))
            st.markdown("### Delete Product Order")
            confirm_prod_order_del = st.checkbox("Confirm deletion", key="confirm_prod_order_del")
            if st.button("Delete Product Order", key="delete_prod_order"):
                if confirm_prod_order_del:
                    try:
                        c.execute("DELETE FROM product_orders WHERE id=?", (order_data["id"],))
                        conn.commit()
                        st.success("Product order deleted successfully!")
                        del st.session_state.prod_order
                    except Exception as e:
                        st.error("Deletion failed: " + str(e))
                else:
                    st.error("Please confirm deletion by checking the box.")

with tabs[6]:
    # --- WhatsApp Ads ---
    st.title("📢 WhatsApp Ads")
    with st.form("send_ads"):
        title = st.text_input("Ad Title")
        message = st.text_area("Message")
        group_name = st.selectbox("Target Group", ["All", "Self", "Father", "Mother", "Wife", "Best Friend", "Premium", "Others"])
        submit_ads = st.form_submit_button("Send Ad")
        if submit_ads:
            c.execute("INSERT INTO ads (title, message, group_name, created_at) VALUES (?, ?, ?, ?)",
                      (title, message, group_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            st.success("Ad saved and queued for sending.")

with tabs[7]:
    # --- WhatsApp Alerts ---
    st.title("📲 WhatsApp Alerts")
    with st.form("send_alerts"):
        alert_message = st.text_area("Alert Message")
        recipient_group = st.selectbox("Recipient Group", ["All", "Self", "Father", "Mother", "Wife", "Best Friend", "Others"])
        submit_alert = st.form_submit_button("Send Alert")
        if submit_alert:
            c.execute("INSERT INTO alerts (message, recipient_group, sent_at) VALUES (?, ?, ?)",
                      (alert_message, recipient_group, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            st.success("Alert saved and queued for sending.")

with tabs[8]:
    # --- Lucky Draw ---
    st.title("🎉 Lucky Draw")
    clients_df = pd.read_sql_query("SELECT id, name, phone, lucky_draw_wins FROM clients", conn)
    if st.button("Pick a Lucky Winner!"):
        if not clients_df.empty:
            winner = clients_df.sample(1).iloc[0]
            st.success(f"Winner: {winner['name']} ({winner['phone']})")
            c.execute("UPDATE clients SET lucky_draw_wins = lucky_draw_wins + 1 WHERE id = ?", (winner['id'],))
            conn.commit()
        else:
            st.warning("No clients available for lucky draw.")
    st.markdown("#### Lucky Draw Winners Count")
    st.dataframe(clients_df[["name", "phone", "lucky_draw_wins"]])

with tabs[9]:
    # --- About Us ---
    show_about_us()


def set_black_background():
    st.markdown(
        """
        <style>
        .stApp {
            background-color: black;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# Call the function to set the black background
set_black_background()

def set_fixed_svg_with_black_background(svg_path):
    if os.path.exists(svg_path):
        with open(svg_path, "r") as f:
            svg_content = f.read()
        encoded_svg = base64.b64encode(svg_content.encode()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-color: black;
                background-image: url("data:image/svg+xml;base64,{encoded_svg}");
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-position: center;
                background-size: 55%;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    else:
        st.error(f"SVG background not found at {svg_path}")

# Call the function to set the fixed SVG background with black base
set_fixed_svg_with_black_background("ske.svg")

def calculate_commission(amount, discount):
    commission = (amount * 0.05) - discount
    return max(commission, 0)  # Ensure commission is not negative

# Example: When adding a new recharge order
def add_recharge_order(client_id, amount, discount, status="Pending"):
    commission = calculate_commission(amount, discount)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO orders (client_id, amount, discount, commission, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (client_id, amount, discount, commission, status, created_at)
    )
    conn.commit()

# Example: When updating an existing recharge order
def update_recharge_order(order_id, amount, discount, status):
    commission = calculate_commission(amount, discount)
    c.execute(
        "UPDATE orders SET amount=?, discount=?, commission=?, status=? WHERE id=?",
        (amount, discount, commission, status, order_id)
    )
    conn.commit()

# Run this ONCE to migrate your table, then remove/comment it out
c.execute("""
    CREATE TABLE IF NOT EXISTS recharge_plans_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        data TEXT,
        voice TEXT,
        sms TEXT,
        validity INTEGER,
        operator TEXT,
        price REAL,
        description TEXT
    )
""")
c.execute("""
    INSERT INTO recharge_plans_new (id, name, data, voice, sms, validity, operator, price, description)
    SELECT id, name, data, voice, sms, validity, operator, price, description FROM recharge_plans
""")
c.execute("DROP TABLE recharge_plans")
c.execute("ALTER TABLE recharge_plans_new RENAME TO recharge_plans")
conn.commit()



