import streamlit as st
import pandas as pd
import os
import json

def show(conn, c):
    st.title("Product Catalogue")

    # --- Add New Product ---
    with st.expander("➕ Add New Product"):
        with st.form(key="add_product_form_main"):
            name = st.text_input("Product Name")
            category = st.text_input("Category")
            subcategory = st.text_input("Subcategory")
            price = st.number_input("Price", min_value=0.0)
            stock = st.number_input("Stock", min_value=0, step=1)
            description = st.text_area("Description")
            image_files = st.file_uploader("Product Images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
            submitted = st.form_submit_button("Add Product")
            if submitted:
                image_paths = []
                if image_files:
                    os.makedirs("product_images", exist_ok=True)
                    for image_file in image_files:
                        image_path = f"product_images/{name}_{image_file.name}"
                        with open(image_path, "wb") as f:
                            f.write(image_file.read())
                        image_paths.append(image_path)
                images_json = json.dumps(image_paths)
                c.execute(
                    "INSERT INTO products (name, category, subcategory, price, stock, description, image_paths) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, category, subcategory, price, stock, description, images_json)
                )
                conn.commit()
                st.success("Product added!")

    # --- Product List ---
    products_df = pd.read_sql_query(
        "SELECT id, name, category, subcategory, price, stock, description, image_paths FROM products",
        conn
    )
    if products_df.empty:
        st.info("No products found.")
    else:
        st.dataframe(products_df)

    # --- Edit/Delete Section ---
    st.markdown("#### Edit or Delete a Product")
    if not products_df.empty:
        product_id = st.number_input("Enter Product ID to Edit/Delete", min_value=1, step=1, key="edit_product_id")
        selected_product = products_df[products_df['id'] == product_id]
        if not selected_product.empty:
            product = selected_product.iloc[0]
            with st.form("edit_product_form"):
                name = st.text_input("Product Name", value=product['name'])
                category = st.text_input("Category", value=product['category'])
                subcategory = st.text_input("Subcategory", value=product['subcategory'])
                price = st.number_input("Price", min_value=0.0, value=product['price'])
                stock = st.number_input("Stock", min_value=0, step=1, value=product['stock'])
                description = st.text_area("Description", value=product['description'])
                image_files = st.file_uploader("Product Images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
                submitted = st.form_submit_button("Update Product")
                if submitted:
                    image_paths = json.loads(product['image_paths']) if product['image_paths'] else []
                    if image_files:
                        os.makedirs("product_images", exist_ok=True)
                        image_paths = []
                        for image_file in image_files:
                            image_path = f"product_images/{name}_{image_file.name}"
                            with open(image_path, "wb") as f:
                                f.write(image_file.read())
                            image_paths.append(image_path)
                    images_json = json.dumps(image_paths)
                    c.execute(
                        "UPDATE products SET name=?, category=?, subcategory=?, price=?, stock=?, description=?, image_paths=? WHERE id=?",
                        (name, category, subcategory, price, stock, description, images_json, product_id)
                    )
                    conn.commit()
                    st.success("Product updated!")
            if st.button("Delete Product"):
                c.execute("DELETE FROM products WHERE id=?", (product_id,))
                conn.commit()
                st.success("Product deleted!")
    else:
        st.info("No products found.")