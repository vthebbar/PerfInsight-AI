import os
import shutil
import subprocess
import pandas as pd
import streamlit as st
from google import genai
from openai import OpenAI
from dotenv import load_dotenv

# --- CONFIGURATION & STORAGE HANDLERS ---
ENV_FILE = ".env"

def load_stored_config():
    """Loads configuration parameters from the local .env file safely."""
    load_dotenv(ENV_FILE, override=True)
    return {
        "AI_PROVIDER": os.getenv("AI_PROVIDER", "Google Gemini"),
        "AI_MODEL": os.getenv("AI_MODEL", "gemini-2.5-flash"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "CUSTOM_BASE_URL": os.getenv("CUSTOM_BASE_URL", "http://localhost:11434/v1"),
        "JMETER_PATH": os.getenv("JMETER_PATH", "jmeter"),
        "TEST_PLAN": os.getenv("TEST_PLAN", "your_test_plan.jmx"),
        "RESULT_CSV": os.getenv("RESULT_CSV", "reports/results.csv"),
        "SLA_AVG_RESP": float(os.getenv("SLA_AVG_RESP", "2000")),
        "SLA_ERROR_PERC": float(os.getenv("SLA_ERROR_PERC", "5.0")),
        "SLA_MAX_RESP": float(os.getenv("SLA_MAX_RESP", "5000")),
        "JMETER_MODE": os.getenv("JMETER_MODE", "Standalone (Local)"),
        "WORKER_IPS": os.getenv("WORKER_IPS", ""),
        "EXIT_WORKERS_END": os.getenv("EXIT_WORKERS_END", "True") == "True"
    }

def save_config_to_env(provider, model, gemini_key, openai_key, base_url, jmeter_path, test_plan, result_csv, sla_avg, sla_error, sla_max, jmeter_mode, worker_ips, exit_workers):
    """Saves all UI settings back into a single centralized .env file while preserving structural formatting and comments."""
    
    env_template = f"""# =========================================================================
# AI Engine Configuration Settings
# =========================================================================
# Options: "Google Gemini", "OpenAI", "Local Ollama", "Custom OpenAI-Compatible"
AI_PROVIDER={provider}
AI_MODEL={model}

# API Credentials (Fill in the ones you use; leave others blank)
GEMINI_API_KEY={gemini_key}
OPENAI_API_KEY={openai_key}

# Custom / Local Server Endpoints (Defaults to local Ollama API port)
CUSTOM_BASE_URL={base_url}

# =========================================================================
# JMeter Orchestration & Infrastructure Paths
# =========================================================================
# Options: "Standalone (Local)", "Distributed (Master-Worker)"
JMETER_MODE={jmeter_mode}
WORKER_IPS={worker_ips}

# For distributed testing: whether to cleanly terminate remote slaves when done
EXIT_WORKERS_END={exit_workers}

# File System Workspace Locations
# MAC/Linux Path format: /Users/yourusername/apache-jmeter/bin/jmeter.sh
# Windows Path format: C:\\apache-jmeter\\bin\jmeter.bat
JMETER_PATH={jmeter_path}
TEST_PLAN={test_plan}
RESULT_CSV={result_csv}

# =========================================================================
# Performance Service Level Agreements (SLAs)
# =========================================================================
SLA_AVG_RESP={sla_avg}
SLA_ERROR_PERC={sla_error}
SLA_MAX_RESP={sla_max}
"""

    with open(ENV_FILE, "w") as f:
        f.write(env_template.strip() + "\n")

# Load current active state configurations
config = load_stored_config()

# --- STREAMLIT WEB UI SETUP ---
st.set_page_config(page_title="PerfInsight AI", layout="wide")
st.title("PerfInsight AI — Performance Test Analyzer")
st.caption("Execute JMeter tests, validate SLA rules, and generate engineering summaries using Local or Cloud AI Models")

# Sidebar Configuration Control Panel
st.sidebar.header("🛠️ Configuration Settings")

# --- SECTION 1: AI MODEL SELECTION ---
st.sidebar.subheader("🤖 AI Engine Setup")
provider_choice = st.sidebar.selectbox(
    "Select AI Provider", 
    ["Google Gemini", "OpenAI", "Local Ollama", "Custom OpenAI-Compatible"],
    index=["Google Gemini", "OpenAI", "Local Ollama", "Custom OpenAI-Compatible"].index(config["AI_PROVIDER"])
)

gemini_key = config["GEMINI_API_KEY"]
openai_key = config["OPENAI_API_KEY"]
base_url_val = config["CUSTOM_BASE_URL"]
model_default = config["AI_MODEL"]

if provider_choice == "Google Gemini":
    gemini_key = st.sidebar.text_input("Gemini API Key", value=gemini_key, type="password")
    model_name = st.sidebar.text_input("Model Name", value=model_default if "gemini" in model_default else "gemini-2.5-flash")
elif provider_choice == "OpenAI":
    openai_key = st.sidebar.text_input("OpenAI API Key", value=openai_key, type="password")
    model_name = st.sidebar.text_input("Model Name", value=model_default if "gpt" in model_default else "gpt-4o-mini")
elif provider_choice == "Local Ollama":
    base_url_val = st.sidebar.text_input("Ollama Base URL", value=base_url_val if base_url_val else "http://localhost:11434/v1")
    model_name = st.sidebar.text_input("Model Name (e.g. qwen2.5-coder, llama3)", value=model_default if "gemini" not in model_default and "gpt" not in model_default else "qwen2.5-coder")
    openai_key = "ollama"
else:
    base_url_val = st.sidebar.text_input("Custom Base URL", value=base_url_val)
    openai_key = st.sidebar.text_input("Custom Provider API Key", value=openai_key, type="password")
    model_name = st.sidebar.text_input("Model Name", value=model_default)

# --- SECTION 2: JMETER ENGINE SETUP ---
st.sidebar.markdown("---")
st.sidebar.subheader("🧬 JMeter Orchestration Engine")

jmeter_mode_choice = st.sidebar.radio(
    "JMeter Test Execution Architecture",
    ["Standalone (Local)", "Distributed (Master-Worker)"],
    index=["Standalone (Local)", "Distributed (Master-Worker)"].index(config["JMETER_MODE"])
)

worker_ips_input = config["WORKER_IPS"]
exit_workers_input = config["EXIT_WORKERS_END"]

if jmeter_mode_choice == "Distributed (Master-Worker)":
    worker_ips_input = st.sidebar.text_input(
        "Worker (Slave) Nodes IP List", 
        value=worker_ips_input,
        placeholder="192.168.1.10, 192.168.1.11",
        help="Comma-separated IP addresses or hostnames of running jmeter-server nodes."
    )
    exit_workers_input = st.sidebar.checkbox(
        "Auto-Exit Worker Processes at Test End", 
        value=exit_workers_input,
        help="Instructs remote worker daemons to shut down immediately when execution terminates."
    )

jmeter_path_input = st.sidebar.text_input("JMeter Path/Folder", value=config["JMETER_PATH"])
test_plan_input = st.sidebar.text_input("Test Plan Path (.jmx)", value=config["TEST_PLAN"])
result_csv_input = st.sidebar.text_input("Results CSV Save Path", value=config["RESULT_CSV"])

# --- SECTION 3: SLA THRESHOLDS ---
st.sidebar.markdown("---")
st.sidebar.subheader("🚨 Performance SLA Thresholds")
sla_avg_input = st.sidebar.number_input("Max Avg Response Time (ms)", value=int(config["SLA_AVG_RESP"]), step=100)
sla_error_input = st.sidebar.number_input("Max Allowed Error Rate (%)", value=float(config["SLA_ERROR_PERC"]), step=0.5, format="%.1f")
sla_max_input = st.sidebar.number_input("Max Peak Response Time (ms)", value=int(config["SLA_MAX_RESP"]), step=500)

# Unified Save Configurations Button
if st.sidebar.button("💾 Save Settings to .env", use_container_width=True):
    save_config_to_env(
        provider_choice, model_name, gemini_key, openai_key, base_url_val,
        jmeter_path_input, test_plan_input, result_csv_input,
        sla_avg_input, sla_error_input, sla_max_input,
        jmeter_mode_choice, worker_ips_input, exit_workers_input
    )
    st.sidebar.success("Settings synchronized cleanly to your formatted .env file!")
    st.rerun()

# --- MAIN EXECUTION PIPELINE ---
if st.button("▶️ Run Full Performance Pipeline", type="primary"):
    
    # Validations
    if provider_choice == "Google Gemini" and not gemini_key:
        st.error("Please supply a valid Gemini API Key to run this execution.")
        st.stop()
    if jmeter_mode_choice == "Distributed (Master-Worker)" and not worker_ips_input.strip():
        st.error("Distributed execution mode is active. You must supply at least one Worker Node IP address.")
        st.stop()
    if not os.path.exists(test_plan_input):
        st.error(f"Test plan file (.jmx) not located at: {test_plan_input}")
        st.stop()

    # Dynamic Directory Resolution
    reports_dir = os.path.dirname(result_csv_input) if os.path.dirname(result_csv_input) else "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    html_report_dir = os.path.join(reports_dir, "jmeter_html_report")

    # -------------------------------------------------------------------------
    # STAGE 1: Headless JMeter CLI Execution & HTML Report Compilation
    # -------------------------------------------------------------------------
    st.header("Stage 1: Executing JMeter Load Test")
    
    # Clean up file-system footprint before run
    if os.path.exists(result_csv_input):
        os.remove(result_csv_input)
    if os.path.exists(html_report_dir):
        shutil.rmtree(html_report_dir)

    # Core Execution command string structure
    jmeter_cmd = [jmeter_path_input, "-n", "-t", test_plan_input, "-l", result_csv_input]
    
    if jmeter_mode_choice == "Distributed (Master-Worker)":
        cleaned_ips = ",".join([ip.strip() for ip in worker_ips_input.split(",") if ip.strip()])
        jmeter_cmd.extend(["-R", cleaned_ips])
        if exit_workers_input:
            jmeter_cmd.append("-X")
        st.info(f"Orchestrating distributed execution across Workers: `{cleaned_ips}`")

    with st.spinner("JMeter is running the test script in non-GUI mode... Please wait."):
        try:
            process = subprocess.run(jmeter_cmd, capture_output=True, text=True, check=True)
            st.success("✅ JMeter test execution complete.")
        except subprocess.CalledProcessError as e:
            st.error(f"Execution failed. Error log details:\n{e.stderr}")
            st.stop()
        except FileNotFoundError:
            st.error(f"Could not find JMeter using path reference '{jmeter_path_input}'. Ensure paths are configured properly.")
            st.stop()

    # --- NATIVE JMETER HTML DASHBOARD GENERATION BLOCK ---
    with st.spinner("Compiling native JMeter HTML Graphics Dashboard..."):
        try:
            html_cmd = [jmeter_path_input, "-g", result_csv_input, "-o", html_report_dir]
            subprocess.run(html_cmd, capture_output=True, text=True, check=True)
            st.success(f"📊 Native JMeter HTML dashboard successfully compiled.")
            st.info(f"📁 Open locally: `{os.path.abspath(os.path.join(html_report_dir, 'index.html'))}`")
        except Exception as e:
            st.warning(f"Failed to compile native JMeter HTML dashboard: {e}")

    # -------------------------------------------------------------------------
    # STAGE 2: Metric Parsing & Automated Rule Validation
    # -------------------------------------------------------------------------
    st.header("Stage 2: Metrics Aggregation & SLA Validation")
    
    df = pd.read_csv(result_csv_input)
    total_requests = len(df)
    avg_response = df['elapsed'].mean()
    max_response = df['elapsed'].max()
    errors = df[df['success'] == False].shape[0]
    error_percent = (errors / total_requests) * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Requests (Aggregated)", f"{total_requests}")
    col2.metric("Average Response Time", f"{avg_response:.2f} ms")
    col3.metric("Max Response Time", f"{max_response} ms")
    col4.metric("Error Rate", f"{error_percent:.2f}%")

    st.subheader("⚠️ Rule-Based SLA Verification Alerts")
    is_stable = True
    
    if avg_response > sla_avg_input:
        st.error(f"❌ **High average response time detected:** Mean metric of {avg_response:.2f} ms breaks safety threshold of {sla_avg_input} ms.")
        is_stable = False
    if error_percent > sla_error_input:
        st.error(f"❌ **High error percentage detected:** Failure rate of {error_percent:.2f}% breaches limit boundary of {sla_error_input}%.")
        is_stable = False
    if max_response > sla_max_input:
        st.warning(f"⚠️ **Extreme peak outlier detected:** Worst-case request hit {max_response} ms, breaking your limit of {sla_max_input} ms.")
        is_stable = False
        
    if is_stable:
        st.success("✅ **SLA Verification Passed:** System metrics fall safely within custom rules configurations.")

    # -------------------------------------------------------------------------
    # STAGE 3: Cognitive AI Analysis Engine
    # -------------------------------------------------------------------------
    st.header(f"Stage 3: Performance Analysis Report by AI - ({provider_choice})")
    
    prompt = f"""
    You are a senior performance testing engineer with extensive experience in analyzing JMeter test results and suggesting optimizations.

    Analyze these JMeter test results against our established engineering SLAs. 
    Note that this test was run using a {jmeter_mode_choice} architecture.

    Test Metadata Profile:
    - Total Requests Across Infrastructure: {total_requests}
    - Average Response Time: {avg_response:.2f} ms (Target SLA: < {sla_avg_input} ms)
    - Max Response Time: {max_response} ms (Target SLA: < {sla_max_input} ms)
    - Error Percentage: {error_percent:.2f}% (Target SLA: < {sla_error_input}%)

    Provide:
    1. Performance summary
    2. Possible bottlenecks based on the metrics relative to the targets
    3. Recommendations (incorporate distributed client scaling insights if relevant)
    4. Overall assessment

    STRICT FORMATTING CONSTRAINTS:
    - Do NOT include any conversational preamble, pleasantries, greetings, or meta-commentary.
    - Do NOT write introductions like "As a senior performance testing engineer...", "I have analyzed the results...", or "Here is the report...".
    - Start directly with the first heading section row using standard Markdown headers.
    - Keep the technical assessment factual, objective, and dense with engineering terminology.
    
    """

    with st.spinner(f"Requesting diagnostic engineering report using model '{model_name}'..."):
        try:
            if provider_choice == "Google Gemini":
                client = genai.Client(api_key=gemini_key)
                response = client.models.generate_content(model=model_name, contents=prompt)
                report_content = response.text
            else:
                if provider_choice in ["Local Ollama", "Custom OpenAI-Compatible"]:
                    client = OpenAI(api_key=openai_key, base_url=base_url_val)
                else:
                    client = OpenAI(api_key=openai_key)
                
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}]
                )
                report_content = response.choices[0].message.content
            
            st.markdown("---")
            st.markdown(report_content)
            st.markdown("---")
            
            report_txt_path = os.path.join(reports_dir, "ai_performance_report.txt")
            with open(report_txt_path, "w") as f:
                f.write(report_content)
            st.info(f"💾 Report logged to disk directory storage: `{report_txt_path}`")
            
        except Exception as e:
            st.error(f"Failed transmission execution handling with active AI engine: {e}")