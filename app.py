import streamlit as st
import duckdb
import sqlite3
import pandas as pd
import os 
from datetime import datetime
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Ollama

# -----------------------------------------------------------------------------
# 1. DATABASE INIT & DATA LAYERING
# -----------------------------------------------------------------------------
def init_duckdb():
    """Dynamically parses and loads CSV, JSON, or Excel data into your local agent."""
    conn = duckdb.connect(":memory:")
    
    # Clean out older demo tables to prevent schema mixing
    conn.execute("DROP TABLE IF EXISTS Customer;")
    conn.execute("DROP TABLE IF EXISTS Invoice;")
    conn.execute("DROP TABLE IF EXISTS my_custom_table;")
    
    # -------------------------------------------------------------------------
    # CONFIGURATION: Put your file name here (Supports .csv, .json, .xlsx)
    # -------------------------------------------------------------------------
    target_file = "/Users/vamsikrishnakumar/Downloads/Local SQL Agent/sql_agt/datasets/Walmart_Sales.csv"  # Change this to "data.json" or "records.xlsx"
    # -------------------------------------------------------------------------
    
    # Fallback to demo tables if file isn't dropped in yet
    if not os.path.exists(target_file):
        st.warning(f"'{target_file}' not found in directory. Using sample dataset layout instead.")
        conn.execute("CREATE TABLE IF NOT EXISTS my_custom_table (CustomerId INT, FirstName TEXT, Total NUMERIC);")
        conn.execute("INSERT INTO my_custom_table VALUES (1, 'Vamsi', 250.00);")
        return conn

    # Extract file extension
    _, ext = os.path.splitext(target_file.lower())
    
    try:
        if ext == ".csv":
            # Auto-detects row parameters, headers, and schemas from CSV
            # Change your existing CSV execution line to this:
            conn.execute(f"CREATE TABLE my_custom_table AS SELECT * FROM read_csv_auto('{target_file}', ignore_errors=true);")
            st.success(f"Successfully mounted CSV dataset: '{target_file}' as 'my_custom_table'")
            
        elif ext == ".json":
            # Shreds nested JSON arrays or structured records directly into rows
            conn.execute(f"CREATE TABLE my_custom_table AS SELECT * FROM read_json_auto('{target_file}');")
            st.success(f"Successfully mounted JSON dataset: '{target_file}' as 'my_custom_table'")
            
        elif ext == ".xlsx":
            # Configures embedded Excel plugin to query spreadsheets inline
            conn.execute("INSTALL excel; LOAD excel;")
            # Adjust sheet name parameter if your target data isn't on 'Sheet1'
            conn.execute(f"CREATE TABLE my_custom_table AS SELECT * FROM read_xlsx('{target_file}', sheet='Sheet1');")
            st.success(f"Successfully mounted Excel worksheet: '{target_file}' as 'my_custom_table'")
            
    except Exception as error:
        st.error(f"Error parsing file structural properties: {str(error)}")
        
    return conn

def get_duckdb_schema(conn):
    """Dynamically parses and structures schemas from the internal engine."""
    tables = conn.execute("SHOW TABLES;").fetchall()
    schema_details = ""
    
    for table_tuple in tables:
        table_name = table_tuple[0]
        schema_details += f"Table: {table_name}\n"
        columns = conn.execute(f"PRAGMA table_info('{table_name}');").fetchall()
        for col in columns:
            schema_details += f"- {col[1]}: {col[2]}\n"
        schema_details += "\n"
    return schema_details

# -----------------------------------------------------------------------------
# 2. LOCAL TRANSACTION LOGGING (SQLite)
# -----------------------------------------------------------------------------
def init_logging_db():
    """Builds the tracking mechanism for local operation logs."""
    conn = sqlite3.connect("logs.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS query_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        question TEXT,
        sql_query TEXT,
        status TEXT,
        error_message TEXT
    );
    """)
    conn.commit()
    conn.close()

def log_transaction(question, sql_query, status, error_message=""):
    """Appends complete workflow transactions straight into local storage."""
    conn = sqlite3.connect("logs.db")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO query_logs (timestamp, question, sql_query, status, error_message)
    VALUES (?, ?, ?, ?, ?);
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), question, sql_query, status, error_message))
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# 3. LLM INFERENCE PIPELINE
# -----------------------------------------------------------------------------
def generate_sql(question, schema):
    """Invokes local LangChain to process structured query code strings."""
    template = """You are an expert data analyst. Use the following database schema to write a SQL query that answers the user's question.

CRITICAL RULES:
1. If a column name contains spaces, parentheses, slashes, or special characters (e.g., Temperature (C), Wind Speed (km/h), Precip Type), you MUST wrap that column name in double quotes, exactly like this: "Temperature (C)" or "Wind Speed (km/h)".
2. Do not use double quotes for the table name or standard single-word columns.
3. Return ONLY the raw SQL query. Do not include markdown code blocks, backticks (```sql), or explanations.

Database Schema:
{schema}

Question: {question}
SQL:"""
    
    prompt = PromptTemplate(template=template, input_variables=["schema", "question"])
    
    # Binds directly to the local Ollama daemon service 
    llm = Ollama(model="llama3", temperature=0.0, base_url="http://host.docker.internal:11434")
    chain = prompt | llm
    
    raw_sql = chain.invoke({"schema": schema, "question": question})
    return raw_sql
def heal_sql(broken_sql, error_message, schema):
    """Sends a failed SQL query and its error footprint back to LLaMA3 for automated correction."""
    template = """You are an expert data analyst and SQL debugger. A SQL query you generated failed against a DuckDB database. 
Review the original query, the schema, and the exact database error message below, then generate a corrected, working version of the query.

CRITICAL RULES:
1. Fix the syntax error or column mismatch highlighted in the error log.
2. If column names contain spaces or special characters, remember they MUST be enclosed in double quotes (e.g., "Temperature (C)").
3. Return ONLY the raw corrected SQL query. Do not include markdown formatting or explanations.

Database Schema:
{schema}

Failed Query:
{broken_sql}

Database Error Message:
{error_message}

Corrected SQL:"""

    prompt = PromptTemplate(template=template, input_variables=["schema", "broken_sql", "error_message"])
    llm = Ollama(model="llama3", temperature=0.0, base_url="http://host.docker.internal:11434")
    chain = prompt | llm
    
    corrected_sql = chain.invoke({"schema": schema, "broken_sql": broken_sql, "error_message": error_message})
    return clean_sql_output(corrected_sql)

def clean_sql_output(raw_sql: str) -> str:
    """Strips typical structural artifacts and markdown syntax wrapper boxes."""
    cleaned = raw_sql.replace("```sql", "").replace("```", "")
    return cleaned.strip()

# -----------------------------------------------------------------------------
# 4. STREAMLIT INTERFACE FRAMEWORK
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Local SQL Agent", layout="wide")
st.title("Local Natural Language SQL Analytics Agent")
st.caption("Privacy-Preserving Data Exploration Engine Running Completely Offline")

# Instantiate systems
duckdb_conn = init_duckdb()
init_logging_db()
database_schema = get_duckdb_schema(duckdb_conn)

# Persist application states across layout updates
if "active_sql" not in st.session_state:
    st.session_state.active_sql = ""
if "current_error" not in st.session_state:
    st.session_state.current_error = None

tab_workspace, tab_audit = st.tabs(["Analytics Workspace", "System Execution Logs"])

with tab_workspace:
    st.subheader("Natural Language Data Querying")
    user_query = st.text_input(
        "Enter your question in plain English:",
        placeholder="e.g., Top 5 customers by sales volume"
    )
    
    if st.button("Generate & Execute Query"):
        if user_query:
            with st.spinner("Analyzing schema and generating optimized query text..."):
                try:
                    # Generate the underlying query structure 
                    generated_raw = generate_sql(user_query, database_schema)
                    cleaned_sql = clean_sql_output(generated_raw)
                    st.session_state.active_sql = cleaned_sql
                    st.session_state.current_error = None
                except Exception as e:
                    st.error(f"Failed to communicate with local Ollama engine: {str(e)}")
        else:
            st.warning("Please supply a valid analysis question first.")

    # Render interactive execution container if an active query string exists
    if st.session_state.active_sql:
        st.markdown("### Active SQL Query Target")
        
        # Display editable UI fields to fix any potential execution errors manually
        st.session_state.active_sql = st.text_area(
            "Review or modify the code directly below if execution hits an exception:",
            value=st.session_state.active_sql,
            height=120
        )
        
        if st.button("Run SQL Query Now"):
            with st.spinner("Processing calculations inside DuckDB..."):
                try:
                    # Execute transactions straight into structured DataFrames
                    results_df = duckdb_conn.execute(st.session_state.active_sql).fetchdf()
                    
                    st.success("Query executed successfully!")
                    st.dataframe(results_df, use_container_width=True)
                    
                    # Persist working outcomes down to local files
                    csv_data = results_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Result Dataset as CSV",
                        data=csv_data,
                        file_name="query_results.csv",
                        mime="text/csv"
                    )
                    
                    # --- START OF SMART CHART SUGGESTIONS ---
                    st.markdown("---")
                    st.subheader("Automated Visual Analytics")

                    if not results_df.empty:
                        # Identify numeric and string columns dynamically from the active dataframe
                        numeric_cols = results_df.select_dtypes(include=['number']).columns.tolist()
                        string_cols = results_df.select_dtypes(include=['object', 'category']).columns.tolist()

                        if len(numeric_cols) >= 1:
                            # Scenario A: Categorical axis vs Numeric metric axis (e.g., Summary vs Temperature)
                            if len(string_cols) >= 1:
                                x_axis = string_cols[0]
                                y_axis = numeric_cols[0]
                                
                                st.info(f"Smart Suggestion: Plotting distribution of **{y_axis}** grouped by **{x_axis}**.")
                                
                                # Aggregate data to display a clean bar chart
                                chart_data = results_df.groupby(x_axis)[y_axis].mean().sort_values(ascending=False)
                                st.bar_chart(chart_data)
                                
                            # Scenario B: Purely numeric trends
                            elif len(numeric_cols) >= 2:
                                st.info(f"Smart Suggestion: Plotting relationship trends across numeric vectors.")
                                st.line_chart(results_df[numeric_cols[:2]])
                        else:
                            st.caption("Insufficient numerical metric columns found in the query output to map visual properties.")
                    else:
                        st.warning("The query returned an empty dataset.")
                    # --- END OF SMART CHART SUGGESTIONS ---
                    
                    log_transaction(user_query, st.session_state.active_sql, "SUCCESS")
                    st.session_state.current_error = None
                    
                except Exception as db_error:
                    first_error = str(db_error)
                    st.warning(f"⚠️ Initial query attempt failed: {first_error}. Triggering Self-Healing Agent...")
                    
                    try:
                        # Attempt to heal the broken SQL string automatically
                        with st.spinner("Analyzing error log and rewriting query..."):
                            healed_sql = heal_sql(st.session_state.active_sql, first_error, database_schema)
                            
                        st.info(f"✨ Suggested Correction:\n`{healed_sql}`")
                        
                        # Re-execute the freshly corrected query
                        results_df = duckdb_conn.execute(healed_sql).fetchdf()
                        
                        # Update session state with the working query text
                        st.session_state.active_sql = healed_sql
                        st.success("🎉 Self-healing successful! Query executed cleanly.")
                        st.dataframe(results_df, use_container_width=True)
                        
                        # Render charts and download button for the healed output
                        csv_data = results_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Result Dataset as CSV",
                            data=csv_data,
                            file_name="query_results.csv",
                            mime="text/csv"
                        )
                        
                        log_transaction(user_query, healed_sql, "SUCCESS")
                        st.session_state.current_error = None
                        
                    except Exception as secondary_error:
                        # Fallback if the second attempt fails as well
                        st.session_state.current_error = str(secondary_error)
                        st.error(f"Database Query Exception (Healer Failed): {st.session_state.current_error}")
                        log_transaction(user_query, st.session_state.active_sql, "FAILED", error_message=st.session_state.current_error)

with tab_audit:
    st.subheader("Local Operation Audit Trail")
    st.markdown("This window reads metadata transactions directly out of the local tracking database (`logs.db`).")
    
    if st.button("Refresh Log View"):
        st.rerun()
        
    try:
        log_conn = sqlite3.connect("logs.db")
        logs_df = pd.read_sql_query("SELECT * FROM query_logs ORDER BY id DESC;", log_conn)
        log_conn.close()
        
        if not logs_df.empty:
            st.dataframe(logs_df, use_container_width=True)
        else:
            st.info("No query transaction entries have been registered yet.")
    except Exception as log_read_err:
        st.error(f"Could not load tracking databases: {str(log_read_err)}")