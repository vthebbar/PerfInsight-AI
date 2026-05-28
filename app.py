# PerfInsight AI - A Streamlit Application for JMeter Performance Test Analysis with AI-Driven Insights by Vishwanatha Hebbar
import os
import sys
import shutil
import subprocess
import contextlib
import pandas as pd
import streamlit as st
from google import genai
from openai import OpenAI
from dotenv import load_dotenv

# Try importing anthropic SDK safely if used
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

# --- CONFIGURATION & STORAGE HANDLERS ---
ENV_FILE = "env"

def load_stored_config():
    """Loads configuration parameters from the local env file safely."""
    load_dotenv(ENV_FILE, override=True)
    return {
        "AI_PROVIDER": os.getenv("AI_PROVIDER", "Google Gemini"),
        "AI_MODEL": os.getenv("AI_MODEL", "gemini-2.5-flash"),
        "AI_API_KEY": os.getenv("AI_API_KEY", "key in API key for selected provider"),
        "CUSTOM_BASE_URL": os.getenv("CUSTOM_BASE_URL", "http://localhost:11434/v1"),
        "ANTHROPIC_MODEL": os.getenv("ANTHROPIC_MODEL", ""),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "JMETER_PATH": os.getenv("JMETER_PATH", "path to jmeter.sh(mac) or jmeter.bat(windows)"),
        "TEST_PLAN": os.getenv("TEST_PLAN", "Test_Plan.jmx"),
        "RESULT_CSV": os.getenv("RESULT_CSV", "reports/results.csv"),
        "SLA_AVG_RESP": float(os.getenv("SLA_AVG_RESP", "2000")),
        "SLA_ERROR_PERC": float(os.getenv("SLA_ERROR_PERC", "5.0")),
        "SLA_MAX_RESP": float(os.getenv("SLA_MAX_RESP", "5000")),
        "JMETER_MODE": os.getenv("JMETER_MODE", "Standalone (Local)"),
        "WORKER_IPS": os.getenv("WORKER_IPS", ""),
        "EXIT_WORKERS_END": os.getenv("EXIT_WORKERS_END", "True") == "True"
    }

def save_config_to_env(updates: dict):
    """Updates key values inside env file while carefully retaining comments, blocks, and original structure."""
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, "w") as f:
            pass

    new_lines = []
    with open(ENV_FILE, "r") as f:
        lines = f.readlines()

    existing_keys = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            key = stripped.split("=")[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                existing_keys.add(key)
                continue
        new_lines.append(line)

    for key, val in updates.items():
        if key not in existing_keys:
            new_lines.append(f"{key}={val}\n")

    with open(ENV_FILE, "w") as f:
        f.writelines(new_lines)


# -------------------------------------------------------------------------
# CORE PERFORMANCE PIPELINE EXECUTION ENGINE
# -------------------------------------------------------------------------
def run_performance_pipeline(run_config: dict, automated_mode: bool = False):
    """Executes the entire end-to-end performance testing pipeline headlessly or via UI."""
    
    # Helper functions for dual-mode logging and lifecycle termination
    def log_header(title):
        if not automated_mode:
            st.header(title)
        else:
            print(f"\n=========================================\n🚀 {title.upper()}\n=========================================")

    def log_info(msg):
        if not automated_mode: st.info(msg)
        else: print(f"[INFO] {msg}")

    def log_success(msg):
        if not automated_mode: st.success(msg)
        else: print(f"✅ [SUCCESS] {msg}")

    def log_warning(msg):
        if not automated_mode: st.warning(msg)
        else: print(f"⚠️ [WARNING] {msg}")

    def log_error(msg):
        if not automated_mode:
            st.error(msg)
            st.stop()
        else:
            print(f"❌ [CRITICAL ERROR] {msg}")
            sys.exit(1)

    @contextlib.contextmanager
    def status_activity(msg):
        if not automated_mode:
            with st.spinner(msg):
                yield
        else:
            print(f"⏳ {msg}...")
            yield

    # Extract configuration variables
    provider_choice = run_config["AI_PROVIDER"]
    model_name = run_config["AI_MODEL"]
    ai_key_val = run_config["AI_API_KEY"]
    base_url_val = run_config["CUSTOM_BASE_URL"]
    anthropic_model_val = run_config["ANTHROPIC_MODEL"]
    anthropic_key_val = run_config["ANTHROPIC_API_KEY"]
    jmeter_mode_choice = run_config["JMETER_MODE"]
    worker_ips_input = run_config["WORKER_IPS"]
    exit_workers_input = run_config["EXIT_WORKERS_END"]
    jmeter_path_input = run_config["JMETER_PATH"]
    test_plan_input = run_config["TEST_PLAN"]
    result_csv_input = run_config["RESULT_CSV"]
    sla_avg_input = float(run_config["SLA_AVG_RESP"])
    sla_error_input = float(run_config["SLA_ERROR_PERC"])
    sla_max_input = float(run_config["SLA_MAX_RESP"])

    # Core Orchestration Validations (Infrastructure checks stay here)
    if jmeter_mode_choice == "Distributed (Master-Worker)" and not worker_ips_input.strip():
        log_error("Distributed execution mode is active. You must supply at least one Worker Node IP address.")
    if not os.path.exists(test_plan_input):
        log_error(f"Test plan file (.jmx) not located at: {test_plan_input}")

    # Dynamic Directory Resolution
    reports_dir = os.path.dirname(result_csv_input) if os.path.dirname(result_csv_input) else "reports"
    os.makedirs(reports_dir, exist_ok=True)
    html_report_dir = os.path.join(reports_dir, "jmeter_html_report")

    # -------------------------------------------------------------------------
    # STAGE 1: Headless JMeter CLI Execution & HTML Report Compilation
    # -------------------------------------------------------------------------
    log_header("Stage 1: Executing JMeter Load Test")
    
    if os.path.exists(result_csv_input):
        os.remove(result_csv_input)
    if os.path.exists(html_report_dir):
        shutil.rmtree(html_report_dir)

    jmeter_cmd = [jmeter_path_input, "-n", "-t", test_plan_input, "-l", result_csv_input]
    
    if jmeter_mode_choice == "Distributed (Master-Worker)":
        cleaned_ips = ",".join([ip.strip() for ip in worker_ips_input.split(",") if ip.strip()])
        jmeter_cmd.extend(["-R", cleaned_ips])
        if exit_workers_input:
            jmeter_cmd.append("-X")
        log_info(f"Orchestrating distributed execution across Workers: `{cleaned_ips}`")

    with status_activity("JMeter is running the test script in non-GUI mode"):
        try:
            subprocess.run(jmeter_cmd, capture_output=True, text=True, check=True)
            log_success("JMeter test execution complete.")
        except subprocess.CalledProcessError as e:
            log_error(f"Execution failed. Error log details:\n{e.stderr}")
        except FileNotFoundError:
            log_error(f"Could not find JMeter using path reference '{jmeter_path_input}'. Ensure paths are configured properly.")

    # --- NATIVE JMETER HTML DASHBOARD GENERATION BLOCK ---
    with status_activity("Compiling native JMeter HTML Graphics Dashboard"):
        try:
            html_cmd = [jmeter_path_input, "-g", result_csv_input, "-o", html_report_dir]
            subprocess.run(html_cmd, capture_output=True, text=True, check=True)
            log_success("Native JMeter HTML dashboard successfully compiled.")
            log_info(f"Open locally: `{os.path.abspath(os.path.join(html_report_dir, 'index.html'))}`")
        except Exception as e:
            log_warning(f"Failed to compile native JMeter HTML dashboard: {e}")

    # -------------------------------------------------------------------------
    # STAGE 2: Advanced Metrics Aggregation & SLA Validation
    # -------------------------------------------------------------------------
    log_header("Stage 2: Metrics Aggregation & SLA Validation")
    
    df = pd.read_csv(result_csv_input)
    
    total_requests = len(df)
    avg_response = df['elapsed'].mean()
    max_response = df['elapsed'].max()
    min_response = df['elapsed'].min()
    p95_response = df['elapsed'].quantile(0.95)
    p99_response = df['elapsed'].quantile(0.99)
    
    avg_connect_time = df['Connect'].mean() if 'Connect' in df.columns else 0
    avg_latency = df['Latency'].mean() if 'Latency' in df.columns else 0
    
    errors = df[df['success'] == False].shape[0]
    error_percent = (errors / total_requests) * 100 if total_requests > 0 else 0
    
    df['timeStamp_parsed'] = pd.to_numeric(df['timeStamp'], errors='coerce')
    
    if df['timeStamp_parsed'].isna().any():
        df['timeStamp_parsed'] = pd.to_datetime(df['timeStamp'], errors='coerce')
        if total_requests > 1:
            test_duration_sec = (df['timeStamp_parsed'].max() - df['timeStamp_parsed'].min()).total_seconds()
        else:
            test_duration_sec = 0
    else:
        if total_requests > 1:
            test_duration_sec = (df['timeStamp_parsed'].max() - df['timeStamp_parsed'].min()) / 1000.0
        else:
            test_duration_sec = 0

    test_duration_sec = max(test_duration_sec, 1.0) if total_requests > 1 else 0
    throughput_rps = total_requests / test_duration_sec if test_duration_sec > 0 else 0

    total_bytes_received = df['bytes'].sum() if 'bytes' in df.columns else 0
    total_bytes_sent = df['sentBytes'].sum() if 'sentBytes' in df.columns else 0
    mb_received = total_bytes_received / (1024 * 1024)
    mb_sent = total_bytes_sent / (1024 * 1024)

    if pd.api.types.is_numeric_dtype(df['timeStamp_parsed']):
        df['relative_time_min'] = (df['timeStamp_parsed'] - df['timeStamp_parsed'].min()) / 60000.0
    else:
        df['relative_time_min'] = (df['timeStamp_parsed'] - df['timeStamp_parsed'].min()).dt.total_seconds() / 60.0
    timeline_summary = []
    
    if total_requests > 10:
        df['time_bucket'] = pd.cut(df['relative_time_min'], bins=min(10, int(df['relative_time_min'].max()) + 1))
        bucket_groups = df.groupby('time_bucket', observed=False)
        for bucket, group in bucket_groups:
            if not group.empty:
                timeline_summary.append({
                    "Window_Min": f"{bucket.left:.1f}m - {bucket.right:.1f}m",
                    "RPS": len(group) / (max((bucket.right - bucket.left) * 60, 1)),
                    "Avg_Response": group['elapsed'].mean(),
                    "Error_Rate": (group[group['success'] == False].shape[0] / len(group)) * 100
                })
    
    endpoint_summary = []
    if 'label' in df.columns:
        endpoint_groups = df.groupby('label')
        for label, group in endpoint_groups:
            endpoint_summary.append({
                "Transaction": label,
                "Count": len(group),
                "Avg_Resp": group['elapsed'].mean(),
                "Error_Rate": (group[group['success'] == False].shape[0] / len(group)) * 100
            })
        endpoint_summary = sorted(endpoint_summary, key=lambda x: x['Avg_Resp'], reverse=True)[:5]

    if not automated_mode:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Requests (Aggregated)", f"{total_requests}")
        col2.metric("Average Throughput", f"{throughput_rps:.2f} req/sec")
        col3.metric("Average Response Time", f"{avg_response:.2f} ms")
        col4.metric("Error Rate", f"{error_percent:.2f}%")

        with st.expander("📊 View Advanced Percentile & Network Telemetry"):
            sub_col1, sub_col2, sub_col3, sub_col4 = st.columns(4)
            sub_col1.metric("95th Percentile (p95)", f"{p95_response:.1f} ms")
            sub_col2.metric("99th Percentile (p99)", f"{p99_response:.1f} ms")
            sub_col3.metric("Data Received (Download)", f"{mb_received:.2f} MB")
            sub_col4.metric("Data Sent (Upload)", f"{mb_sent:.2f} MB")
    else:
        print(f"-> Total Requests Transmitted: {total_requests}")
        print(f"-> Average Throughput:          {throughput_rps:.2f} req/sec")
        print(f"-> Average Response Time:       {avg_response:.2f} ms")
        print(f"-> Error Rate:                  {error_percent:.2f}%")
        print(f"-> 95th Percentile (p95):       {p95_response:.1f} ms")
        print(f"-> 99th Percentile (p99):       {p99_response:.1f} ms")

    is_stable = True
    if avg_response > sla_avg_input:
        is_stable = False
        msg = f"❌ High average response time detected: Mean metric of {avg_response:.2f} ms breaks safety threshold of {sla_avg_input} ms."
        if not automated_mode: st.error(msg)
        else: print(msg)
        
    if error_percent > sla_error_input:
        is_stable = False
        msg = f"❌ High error percentage detected: Failure rate of {error_percent:.2f}% breaches limit boundary of {sla_error_input}%."
        if not automated_mode: st.error(msg)
        else: print(msg)
        
    if max_response > sla_max_input:
        is_stable = False
        log_warning(f"Extreme peak outlier detected: Worst-case request hit {max_response} ms, breaking your limit of {sla_max_input} ms.")
        
    if is_stable:
        log_success("SLA Verification Passed: System metrics fall safely within custom rules configurations.")

    # -------------------------------------------------------------------------
    # STAGE 3: Cognitive AI Analysis Engine
    # -------------------------------------------------------------------------
    active_runtime_model = anthropic_model_val if provider_choice == "Anthropic" else model_name
    log_header(f"Stage 3: Performance Analysis Report by AI Agent ({provider_choice})")
    
    # --- INTERCEPT MISSING API KEYS SPECIFICALLY IN STAGE 3 ---
    if provider_choice == "Google Gemini" and not ai_key_val:
        log_error("Missing API Key: Please supply a valid Gemini API Key to run the AI analysis.")
    if provider_choice == "OpenAI" and not ai_key_val:
        log_error("Missing API Key: Please supply a valid OpenAI API Key to run the AI analysis.")
    if provider_choice == "Custom OpenAI-Compatible" and not ai_key_val:
        log_error("Missing API Key: Please supply a valid Provider API Key to run the AI analysis.")
    if provider_choice == "Anthropic" and not anthropic_key_val:
        log_error("Missing API Key: Please supply a valid Anthropic API Key to run the AI analysis.")

    timeline_str = "\n".join([f"- Window [{t['Window_Min']}]: Throughput={t['RPS']:.1f} RPS, Avg Response={t['Avg_Response']:.1f} ms, Error Rate={t['Error_Rate']:.1f}%" for t in timeline_summary])
    endpoint_str = "\n".join([f"- Transaction [{e['Transaction']}]: Executions={e['Count']}, Avg Response={e['Avg_Resp']:.1f} ms, Error Rate={e['Error_Rate']:.1f}%" for e in endpoint_summary])

    prompt = f"""
    ROLE: Expert Senior Performance Engineer. Provide a concise, high-density diagnostic assessment. Do NOT restate raw metrics or write conversational padding. Start directly with the analysis.

    METADATA PROFILE:
    - Architecture: {jmeter_mode_choice}
    - Total Requests Transmitted: {total_requests}
    - Total Execution Window: {test_duration_sec:.2f} seconds
    - Calculated System Throughput: {throughput_rps:.2f} requests/sec
    - Error Percentage: {error_percent:.2f}% [Target SLA Limit: < {sla_error_input}%]

    RESPONSE TIME TELEMETRY:
    - Minimum Latency: {min_response} ms
    - Average Response Time: {avg_response:.2f} ms [Target SLA Limit: < {sla_avg_input} ms]
    - 95th Percentile (p95): {p95_response:.2f} ms
    - 99th Percentile (p99): {p99_response:.2f} ms
    - Maximum Peak Outlier: {max_response} ms [Target SLA Limit: < {sla_max_input} ms]
    - Network Transfer Footprint: Sent {mb_sent:.2f} MB / Received {mb_received:.2f} MB
    - Average Infrastructure Connection Overhead: {avg_connect_time:.2f} ms (Time spent establishing TCP handshakes)
    - Average Infrastructure Time-To-First-Byte (Latency): {avg_latency:.2f} ms

    CHRONOLOGICAL TELEMETRY:
    {timeline_str if timeline_str else "Data stream consolidated linearly across active execution runtime."}

    TOP DEGRADED TRANSACTIONS:
    {endpoint_str if endpoint_str else "Transactions performed uniformly without isolated code-path drift."}

    REQUIRED OUTPUT SECTIONS (KEEP IT BRIEF & FACTUAL):

    1. Executive Performance Verdict
       - One blunt sentence: Did the system handle the load cleanly or show stress? State the single most critical architectural takeaway.

    2. Bottleneck Analysis & Root Cause
       - Short bullet points interpreting metric correlations (e.g., latency vs. load ramp, throughput plateau vs. error spikes, connection overhead vs. processing delays). Explain what the patterns mean in plain English.

    3. Analytical Key Findings (Provide exactly these 5 tables):

    TABLE 1 — SLA Headroom & Health
    Columns: Metric | Actual | SLA Limit | Headroom (Delta %) | Status (✅ / ⚠️ / ❌)

    TABLE 2 — Timeline Diagnostics & Server Checklist
    Columns: Time Window | Signal Observed | What to Check on Server & Why

    TABLE 3 — Stability Scorecard
    Columns: Dimension | Rating (🟢 Good / 🟡 Moderate / 🔴 Poor) | Core Observation

    TABLE 4 — Prioritized Engineering Actions
    Columns: Priority | Action | Core Issue Addressed
    - Allowed Priorities: 🔴 Fix Now / 🟡 Investigate / 🔵 Before Next Run
    - CRITICAL RULE: If the system performed flawlessly with zero issues, omit all rows and write exactly one single row stating: "No action needed" across all columns.

    TABLE 5 — Test Execution Summary
    Columns: Core Dimension | Configured Target Value

    4. Strategic Recommendations (OPTIONAL SECTION)
       - Include this narrative block ONLY if there are high-value, long-term strategic recommendations based on the observed data. If the test run was clean, SKIP this section completely.

    FORMAT CONSTRAINTS: Shorter, maximum-density output preferred. No conversational intros/outros. Dive straight into Markdown header 1.
    """

    with status_activity(f"Requesting AI analysis via model '{active_runtime_model}'"):
        try:
            if provider_choice == "Google Gemini":
                client = genai.Client(api_key=ai_key_val)
                response = client.models.generate_content(model=active_runtime_model, contents=prompt)
                report_content = response.text
                
            elif provider_choice == "Anthropic":
                if not Anthropic:
                    log_error("The 'anthropic' Python package is not installed.")
                client = Anthropic(api_key=anthropic_key_val)
                response = client.messages.create(
                    model=active_runtime_model,
                    max_tokens=3000,
                    messages=[{"role": "user", "content": prompt}]
                )
                report_content = response.content[0].text
                
            else:
                if provider_choice in ["Local Ollama", "Custom OpenAI-Compatible"]:
                    client = OpenAI(api_key=ai_key_val if ai_key_val else "local", base_url=base_url_val)
                else:
                    client = OpenAI(api_key=ai_key_val)
                
                response = client.chat.completions.create(
                    model=active_runtime_model,
                    messages=[{"role": "user", "content": prompt}]
                )
                report_content = response.choices[0].message.content
            
            # Render output summary
            if not automated_mode:
                st.markdown("---")
                st.markdown(report_content)
                st.markdown("---")
            else:
                print("\n" + report_content + "\n")
            
            report_txt_path = os.path.join(reports_dir, "ai_performance_report.txt")
            with open(report_txt_path, "w") as f:
                f.write(report_content)
            log_success(f"Report logged to disk directory storage: `{report_txt_path}`")
            
        except Exception as e:
            # --- INTERCEPT INVALID/REJECTED API KEYS FROM PROVIDER API RESPONSE ---
            err_msg = str(e).lower()
            auth_keywords = ["api key", "unauthorized", "401", "authentication", "forbidden", "403", "invalid_key", "credentials"]
            
            if any(keyword in err_msg for keyword in auth_keywords):
                log_error(f"Invalid API Key: The provided API key for {provider_choice} was rejected by the server. Please verify your token details.")
            else:
                log_error(f"Failed transmission execution handling with active AI engine: {e}")


# -------------------------------------------------------------------------
# INTERACTIVE STREAMLIT WEB UI LAYOUT
# -------------------------------------------------------------------------
def render_web_ui():
    """Renders the standard interactive Streamlit analytical front-end interface."""
    config = load_stored_config()
    
    st.set_page_config(page_title="PerfInsight AI", layout="wide")
    st.title("PerfInsight AI — Performance Test Analyzer")
    st.caption("Execute JMeter tests, validate SLA rules, and generate engineering summaries using Local or Cloud AI Models")

    st.sidebar.header("🛠️ Configuration Settings")
    st.sidebar.subheader("🤖 AI Engine Setup")
    
    provider_choice = st.sidebar.selectbox(
        "Select AI Provider", 
        ["Google Gemini", "OpenAI", "Local Ollama", "Custom OpenAI-Compatible", "Anthropic"],
        index=["Google Gemini", "OpenAI", "Local Ollama", "Custom OpenAI-Compatible", "Anthropic"].index(config["AI_PROVIDER"]),
        key="widget_ai_provider"
    )

    if provider_choice == "Google Gemini":
        ai_key_val = st.sidebar.text_input("Gemini API Key", value=config["AI_API_KEY"], type="password", key="widget_ai_key_gemini")
        model_name = st.sidebar.text_input("Model Name", value=config["AI_MODEL"] if "gemini" in config["AI_MODEL"] else "gemini-2.5-flash", key="widget_model_gemini")
        base_url_val = config["CUSTOM_BASE_URL"]
        anthropic_model_val = config["ANTHROPIC_MODEL"]
        anthropic_key_val = config["ANTHROPIC_API_KEY"]
    elif provider_choice == "OpenAI":
        ai_key_val = st.sidebar.text_input("OpenAI API Key", value=config["AI_API_KEY"], type="password", key="widget_ai_key_openai")
        model_name = st.sidebar.text_input("Model Name", value=config["AI_MODEL"] if "gpt" in config["AI_MODEL"] else "gpt-4o-mini", key="widget_model_openai")
        base_url_val = config["CUSTOM_BASE_URL"]
        anthropic_model_val = config["ANTHROPIC_MODEL"]
        anthropic_key_val = config["ANTHROPIC_API_KEY"]
    elif provider_choice == "Local Ollama":
        base_url_val = st.sidebar.text_input("Ollama Base URL", value=config["CUSTOM_BASE_URL"] if config["CUSTOM_BASE_URL"] else "http://localhost:11434/v1", key="widget_base_url_ollama")
        model_name = st.sidebar.text_input("Model Name (e.g. qwen2.5-coder, llama3)", value=config["AI_MODEL"] if "gemini" not in config["AI_MODEL"] and "gpt" not in config["AI_MODEL"] else "qwen2.5-coder:7b", key="widget_model_ollama")
        ai_key_val = config["AI_API_KEY"]
        anthropic_model_val = config["ANTHROPIC_MODEL"]
        anthropic_key_val = config["ANTHROPIC_API_KEY"]
    elif provider_choice == "Custom OpenAI-Compatible":
        base_url_val = st.sidebar.text_input("Custom Base URL", value=config["CUSTOM_BASE_URL"], key="widget_base_url_custom")
        ai_key_val = st.sidebar.text_input("Custom Provider API Key", value=config["AI_API_KEY"], type="password", key="widget_ai_key_custom")
        model_name = st.sidebar.text_input("Model Name", value=config["AI_MODEL"], key="widget_model_custom")
        anthropic_model_val = config["ANTHROPIC_MODEL"]
        anthropic_key_val = config["ANTHROPIC_API_KEY"]
    elif provider_choice == "Anthropic":
        anthropic_key_val = st.sidebar.text_input("Anthropic API Key", value=config["ANTHROPIC_API_KEY"], type="password", key="widget_anthropic_key")
        anthropic_model_val = st.sidebar.text_input("Claude Model Name", value=config["ANTHROPIC_MODEL"] if config["ANTHROPIC_MODEL"] else "claude-3-5-sonnet-20241022", key="widget_anthropic_model")
        ai_key_val = config["AI_API_KEY"]
        base_url_val = config["CUSTOM_BASE_URL"]
        model_name = ""

    st.sidebar.markdown("---")
    st.sidebar.subheader("🧬 JMeter Orchestration Engine")

    jmeter_mode_choice = st.sidebar.radio(
        "JMeter Test Execution Architecture",
        ["Standalone (Local)", "Distributed (Master-Worker)"],
        index=["Standalone (Local)", "Distributed (Master-Worker)"].index(config["JMETER_MODE"]),
        key="widget_jmeter_mode"
    )

    if jmeter_mode_choice == "Distributed (Master-Worker)":
        worker_ips_input = st.sidebar.text_input("Worker (Slave) Nodes IP List", value=config["WORKER_IPS"], placeholder="192.168.1.10, 192.168.1.11", key="widget_worker_ips")
        exit_workers_input = st.sidebar.checkbox("Auto-Exit Worker Processes at Test End", value=config["EXIT_WORKERS_END"], key="widget_exit_workers")
    else:
        worker_ips_input = config["WORKER_IPS"]
        exit_workers_input = config["EXIT_WORKERS_END"]

    jmeter_path_input = st.sidebar.text_input("JMeter Path/Folder", value=config["JMETER_PATH"], key="widget_jmeter_path")
    test_plan_input = st.sidebar.text_input("Test Plan Path (.jmx)", value=config["TEST_PLAN"], key="widget_test_plan")
    result_csv_input = st.sidebar.text_input("Results CSV Save Path", value=config["RESULT_CSV"], key="widget_result_csv")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🚨 Performance SLA Thresholds")
    sla_avg_input = st.sidebar.number_input("Max Avg Response Time (ms)", value=int(config["SLA_AVG_RESP"]), step=100, key="widget_sla_avg")
    sla_error_input = st.sidebar.number_input("Max Allowed Error Rate (%)", value=float(config["SLA_ERROR_PERC"]), step=0.5, format="%.1f", key="widget_sla_error")
    sla_max_input = st.sidebar.number_input("Max Peak Response Time (ms)", value=int(config["SLA_MAX_RESP"]), step=500, key="widget_sla_max")

    if st.sidebar.button("💾 Save Settings to env", use_container_width=True):
        updates_payload = {
            "AI_PROVIDER": provider_choice,
            "AI_MODEL": model_name,
            "AI_API_KEY": ai_key_val if provider_choice != "Anthropic" else "",
            "CUSTOM_BASE_URL": base_url_val if provider_choice in ["Local Ollama", "Custom OpenAI-Compatible"] else "",
            "ANTHROPIC_MODEL": anthropic_model_val if provider_choice == "Anthropic" else "",
            "ANTHROPIC_API_KEY": anthropic_key_val if provider_choice == "Anthropic" else "",
            "JMETER_MODE": jmeter_mode_choice,
            "WORKER_IPS": worker_ips_input,
            "EXIT_WORKERS_END": "True" if exit_workers_input else "False",
            "JMETER_PATH": jmeter_path_input,
            "TEST_PLAN": test_plan_input,
            "RESULT_CSV": result_csv_input,
            "SLA_AVG_RESP": str(int(sla_avg_input)),
            "SLA_ERROR_PERC": str(sla_error_input),
            "SLA_MAX_RESP": str(int(sla_max_input))
        }
        save_config_to_env(updates_payload)
        st.sidebar.success("Settings synchronized cleanly!")
        st.rerun()

    ui_runtime_config = {
        "AI_PROVIDER": provider_choice,
        "AI_MODEL": model_name,
        "AI_API_KEY": ai_key_val,
        "CUSTOM_BASE_URL": base_url_val,
        "ANTHROPIC_MODEL": anthropic_model_val,
        "ANTHROPIC_API_KEY": anthropic_key_val,
        "JMETER_MODE": jmeter_mode_choice,
        "WORKER_IPS": worker_ips_input,
        "EXIT_WORKERS_END": exit_workers_input,
        "JMETER_PATH": jmeter_path_input,
        "TEST_PLAN": test_plan_input,
        "RESULT_CSV": result_csv_input,
        "SLA_AVG_RESP": sla_avg_input,
        "SLA_ERROR_PERC": sla_error_input,
        "SLA_MAX_RESP": sla_max_input
    }

    if st.button("▶️ Run Full Performance Pipeline", type="primary"):
        run_performance_pipeline(ui_runtime_config, automated_mode=False)


# -------------------------------------------------------------------------
# DUAL-TRIGGER RECOGNITION ENTRYPOINT GATEWAY
# -------------------------------------------------------------------------
if __name__ == "__main__":
    from streamlit.runtime import exists as streamlit_runtime_exists

    if streamlit_runtime_exists():
        render_web_ui()
    else:
        print("🚀 Launching PerfInsight AI in Headless CI/CD Automation Mode...")
        headless_config = load_stored_config()
        run_performance_pipeline(headless_config, automated_mode=True)