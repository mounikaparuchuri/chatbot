import sqlite3 # type: ignore
import streamlit as st
import os

# Connect to the database file
def create_connection(db_file):
    """Create a database connection to the SQLite database specified by db_file."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        st.error(f"Error connecting to database: {e}")
    return conn

# Function to set up the database and table
def setup_db(db_file):
    conn = create_connection(db_file)
    if conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS chat_log (
                id INTEGER PRIMARY KEY,
                username TEXT,
                request TEXT,
                response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

# Function to save data to the database
def save_data(db_file, username, request, response):
    conn = create_connection(db_file)
    if conn:
        try:
            c = conn.cursor()
            c.execute("INSERT INTO chat_log (username, request, response) VALUES (?, ?, ?)",
                      (username, request, response))
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Error saving data to database: {e}")
        finally:
            conn.close()


def rename_db_file(old_name, new_name):
    """Renames the SQLite database file."""
    if os.path.exists(old_name):
        try:
            os.rename(old_name, new_name)
            st.success(f"Database file renamed from {old_name} to {new_name}.")
            return True
        except OSError as e:
            st.error(f"Error: {e}. Make sure no other process is using the file.")
            return False
    else:
        st.warning(f"File '{old_name}' not found.")
        return False
    

# Function to retrieve all data from the database
def retrieve_data(db_file):
    """Retrieves all chat entries from the database."""
    conn = create_connection(db_file)
    if conn:
        try:
            c = conn.cursor()
            # The SQL query to select all data
            c.execute("SELECT username, request, response, timestamp FROM chat_log ORDER BY timestamp ASC")
            # Fetch all the results
            data = c.fetchall()
            return data
        except sqlite3.Error as e:
            st.error(f"Error retrieving data from database: {e}")
            return []
        finally:
            conn.close()
    return []