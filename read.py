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
    print("db file name " + db_file)
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
        print("created connection for db file name " + db_file)
        conn.commit()
        conn.close()

# Function to save data to the database
def save_data(db_file, username, user_message_content, response):
    conn = create_connection(db_file)

        # Convert the user message content to a JSON string if it's a list
    if isinstance(user_message_content, list):
        # We only save text content. Images and other objects are discarded for DB storage.
        text_content = " ".join([part for part in user_message_content if isinstance(part, str)])
    else:
        text_content = user_message_content
    if conn:
        try:
            c = conn.cursor()
            c.execute("INSERT INTO chat_log (username, request, response) VALUES (?, ?, ?)",
                      (username, text_content, response))
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
    """Retrieves all chat entries from the database and formats them for Streamlit."""
    conn = create_connection(db_file)
    messages = []
    if conn:
        try:
            c = conn.cursor()
            # Select the request (user message) and response (assistant message)
            c.execute("SELECT request, response FROM chat_log ORDER BY timestamp ASC")
            data = c.fetchall()
            
            # Loop through the fetched data and format it into a list of dictionaries
            for request, response in data:
                # Add the user's message
                if request:  # Ensure the request is not empty
                    messages.append({
                        "role": "user", 
                        "content": request
                    })
                
                # Add the assistant's response
                if response: # Ensure the response is not empty
                    messages.append({
                        "role": "assistant",
                        "content": response
                    })
            
            return messages
            
        except sqlite3.Error as e:
            st.error(f"Error retrieving data from database: {e}")
            return []
        finally:
            if conn:
                conn.close()
    return []


def delete_chat_log(username, db_name):
    """
    Deletes a specific chat log entry from the database by its ID.

    Args:
        log_id (int): The primary key (id) of the log entry to delete.
    """

    conn = None
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Prepare and execute the DELETE statement
        sql = "DELETE FROM chat_log WHERE username = ?"
        cursor.execute(sql, (username,))

        # Commit the changes to the database
        conn.commit()
        
        # Check if any row was actually deleted
        if cursor.rowcount > 0:
            print(f"Successfully deleted chat log with ID: {username}")
        else:
            print(f"No chat log found with ID: {username}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        # Always close the connection
        if conn:
            conn.close()