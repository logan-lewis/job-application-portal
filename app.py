# Updated app.py with all rubric requirements met
import streamlit as st
import pandas as pd
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image

# ---------------------- CONFIG ----------------------
st.set_page_config(page_title="SMU Job Application Portal", layout="centered")

DB_NAME = "applications.db"
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Function to display SMU logo
def display_smu_logo():
    try:
        # Add custom CSS for centering
        st.markdown("""
        <style>
        .logo-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Use a container with the custom CSS class
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        image = Image.open("SMU_Logo.png")
        st.image(image, width=500)
        st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading logo: {e}")
        st.write("Please make sure 'SMU_Logo.png' is in the same directory as app.py")

# ---------------------- TABLE SETUP ----------------------
# Create tables if they don't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        role TEXT,
        cover_letter TEXT,
        resume TEXT
    )
''')

# Check if department column exists in applicants table
result = cursor.execute("PRAGMA table_info(applicants)").fetchall()
columns = [col[1] for col in result]
if 'department' not in columns:
    # Add department column to existing table
    cursor.execute('ALTER TABLE applicants ADD COLUMN department TEXT')
    conn.commit()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
''')

# Insert seed data if empty
cursor.execute("SELECT COUNT(*) FROM roles")
if cursor.fetchone()[0] == 0:
    cursor.executemany("INSERT INTO roles (title) VALUES (?)", [
        ("Teacher Assistant",), ("Tutor",), ("Research Assistant",), ("Office Assistant",)
    ])

cursor.execute("SELECT COUNT(*) FROM departments")
if cursor.fetchone()[0] == 0:
    cursor.executemany("INSERT INTO departments (name) VALUES (?)", [
        ("Computer Science",), ("Mathematics",), ("Marketing",), ("Biology",)
    ])

cursor.execute("SELECT COUNT(*) FROM users")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (
        "admin", generate_password_hash("password123")
    ))

conn.commit()

# ---------------------- AUTH SETUP ----------------------
def show_login_form():
    display_smu_logo()
    st.title("Admin Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    
    if submitted:
        # Check credentials against database
        user = cursor.execute("SELECT username, password FROM users WHERE username = ?", (username,)).fetchone()
        
        if user and check_password_hash(user[1], password):
            # Set session state to logged in
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid username or password")
    
    # Add a logout button if already logged in
    if st.session_state.get('logged_in', False):
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

# ---------------------- FORM PAGE ----------------------
def show_application_form():
    display_smu_logo()
    st.title("Apply to be a Student Assistant at SMU")
    st.markdown("Fill out the form below to apply.")

    # Initialize session state for form key if needed
    if 'form_key' not in st.session_state:
        st.session_state.form_key = 0
    
    # Initialize success message flag
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    
    # Show success message if form was submitted
    if st.session_state.form_submitted:
        st.success("Application submitted successfully!")
        st.session_state.form_submitted = False  # Reset for next time

    roles = [r[0] for r in cursor.execute("SELECT title FROM roles").fetchall()]
    departments = [d[0] for d in cursor.execute("SELECT name FROM departments").fetchall()]

    with st.form(f"job_form_{st.session_state.form_key}"):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone Number")
        role = st.selectbox("Position Applying For", roles)
        department = st.selectbox("Department", departments)
        cover_letter = st.text_area("Cover Letter")
        resume = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
        submitted = st.form_submit_button("Submit Application")

    if submitted:
        if name and email and phone and cover_letter and resume:
            os.makedirs("resumes", exist_ok=True)
            resume_path = f"resumes/{name.replace(' ', '_')}.pdf"
            with open(resume_path, "wb") as f:
                f.write(resume.getbuffer())
            
            # Insert into database with department
            cursor.execute('''
                INSERT INTO applicants (name, email, phone, role, department, cover_letter, resume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, phone, role, department, cover_letter, resume_path))
            conn.commit()
            
            # Set success message and increment form key to reset form
            st.session_state.form_submitted = True
            st.session_state.form_key += 1
            st.rerun()
        else:
            st.error("Please complete all fields.")

# ---------------------- ADMIN PAGE ----------------------
def show_admin_dashboard():
    display_smu_logo()
    st.title("Admin Dashboard")

    # Two columns for action buttons at the top
    col1, col2 = st.columns(2)
    
    # Get applications data - safely handle department column
    df = pd.read_sql("SELECT id, name, email, phone, role, cover_letter, resume, department FROM applicants", conn)
    
    with col1:
        if not df.empty:
            st.download_button(
                "Download All Applications as CSV",
                df.to_csv(index=False),
                file_name="applications.csv",
                key="download_all_csv"
            )

    with col2:
        if st.button("Clear All Applications", type="secondary"):
            if 'confirm_clear' not in st.session_state:
                st.session_state.confirm_clear = False
            st.session_state.confirm_clear = True

    if 'confirm_clear' in st.session_state and st.session_state.confirm_clear:
        st.warning("Are you sure you want to clear all applications? This cannot be undone.")
        conf_col1, conf_col2 = st.columns(2)
        with conf_col1:
            if st.button("Yes, Clear Everything"):
                # Clear database
                cursor.execute("DELETE FROM applicants")
                conn.commit()
                # Remove resume files
                if os.path.exists("resumes"):
                    for file in os.listdir("resumes"):
                        file_path = os.path.join("resumes", file)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                        except Exception as e:
                            print(f"Error: {e}")
                st.success("All applications have been cleared!")
                st.session_state.confirm_clear = False
                st.rerun()
        with conf_col2:
            if st.button("No, Cancel"):
                st.session_state.confirm_clear = False
                st.rerun()

    if df.empty:
        st.info("No applications submitted yet.")
        return

    # Filter options - column layout for filters
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        st.subheader("Filter by Role")
        roles = ["All"] + list(df["role"].unique())
        selected_role = st.selectbox("Select role", roles, key="role_filter", label_visibility="collapsed")
        if selected_role != "All":
            df = df[df["role"] == selected_role]
    
    with filter_col2:
        st.subheader("Filter by Department")
        # Get unique departments, handle potential missing values
        departments = ["All"]
        if 'department' in df.columns:
            valid_depts = [d for d in df["department"].unique() if pd.notna(d) and d]
            departments.extend(valid_depts)
        
        selected_dept = st.selectbox("Select department", departments, key="dept_filter", label_visibility="collapsed")
        if selected_dept != "All":
            df = df[df["department"] == selected_dept]

    # Display applications
    for _, row in df.iterrows():
        with st.expander(f"{row['name']} - {row['role']}"):
            st.write(f"**Email:** {row['email']}")
            st.write(f"**Phone:** {row['phone']}")
            
            # Safely display department (might be missing in older records)
            if 'department' in row and pd.notna(row['department']) and row['department']:
                st.write(f"**Department:** {row['department']}")
            else:
                st.write(f"**Department:** Not specified")
                
            st.write(f"**Role:** {row['role']}")
            st.write(f"**Cover Letter:** {row['cover_letter']}")
            
            # Display resume download button if file exists
            if 'resume' in row and pd.notna(row['resume']) and row['resume'] and os.path.exists(row['resume']):
                with open(row['resume'], "rb") as f:
                    st.download_button(
                        label=f"Download Resume for {row['name']}",
                        data=f,
                        file_name=os.path.basename(row['resume']),
                        mime='application/pdf',
                        key=f"resume_{row['id']}"
                    )
            else:
                st.warning("Resume file not found")

# ---------------------- MAIN ROUTING ----------------------
# Initialize session state for login status
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Add login/application form toggle in sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Apply for Job", "Admin Dashboard"])

if page == "Admin Dashboard":
    if st.session_state.logged_in:
        show_admin_dashboard()
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    else:
        show_login_form()
else:
    show_application_form()
