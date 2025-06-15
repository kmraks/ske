import streamlit as st
import pandas as pd

def show(conn, c):
    st.title("Recharge Catalogue")

    # --- Add New Plan ---
    with st.expander("➕ Add New Recharge Plan"):
        with st.form(key="add_plan_form_main"):
            name = st.text_input("Plan Name")
            operator = st.selectbox("Operator", ["Airtel", "Jio", "Vi", "BSNL"])
            price = st.number_input("Price", min_value=0.0)
            validity = st.number_input("Validity (days)", min_value=1)
            data = st.text_input("Data")
            voice = st.text_input("Voice")
            sms = st.text_input("SMS")
            description = st.text_area("Description")
            submitted = st.form_submit_button("Add Plan")
            if submitted:
                c.execute(
                    "INSERT INTO recharge_plans (name, data, voice, sms, validity, operator, price, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (name, data, voice, sms, validity, operator, price, description)
                )
                conn.commit()
                st.success("Plan added!")

    # --- Operator Tabs ---
    operator_tabs = st.tabs(["Airtel", "Jio", "Vi", "BSNL"])
    operators = ["Airtel", "Jio", "Vi", "BSNL"]

    for idx, operator in enumerate(operators):
        with operator_tabs[idx]:
            plans_df = pd.read_sql_query(
                "SELECT id, name, data, voice, sms, validity, operator, price, description FROM recharge_plans WHERE operator=?",
                conn, params=(operator,)
            )
            if plans_df.empty:
                st.info(f"No plans found for {operator}.")
            else:
                st.dataframe(plans_df)

    # --- Edit/Delete Section ---
    st.markdown("#### Edit or Delete a Recharge Plan")
    plans_df = pd.read_sql_query("SELECT * FROM recharge_plans", conn)
    if not plans_df.empty:
        plan_id = st.number_input("Enter Plan ID to Edit/Delete", min_value=1, step=1, key="edit_plan_id")
        selected_plan = plans_df[plans_df['id'] == plan_id]
        if not selected_plan.empty:
            plan = selected_plan.iloc[0]
            with st.form("edit_plan_form"):
                name = st.text_input("Plan Name", value=plan['name'])
                operator = st.selectbox("Operator", ["Airtel", "Jio", "Vi", "BSNL"], index=["Airtel", "Jio", "Vi", "BSNL"].index(plan['operator']))
                price = st.number_input("Price", min_value=0.0, value=plan['price'])
                validity = st.number_input("Validity (days)", min_value=1, value=plan['validity'])
                data = st.text_input("Data", value=plan['data'])
                voice = st.text_input("Voice", value=plan['voice'])
                sms = st.text_input("SMS", value=plan['sms'])
                description = st.text_area("Description", value=plan['description'])
                submitted = st.form_submit_button("Update Plan")
                if submitted:
                    c.execute(
                        "UPDATE recharge_plans SET name=?, data=?, voice=?, sms=?, validity=?, operator=?, price=?, description=? WHERE id=?",
                        (name, data, voice, sms, validity, operator, price, description, plan_id)
                    )
                    conn.commit()
                    st.success("Plan updated!")
            if st.button("Delete Plan"):
                c.execute("DELETE FROM recharge_plans WHERE id=?", (plan_id,))
                conn.commit()
                st.success("Plan deleted!")
    else:
        st.info("No recharge plans found.")