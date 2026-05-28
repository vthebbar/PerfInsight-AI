#  PerfInsight AI — Autonomous Performance Engineering Agent

PerfInsight AI is an intelligent, autonomous performance testing agent built with **Streamlit** and **Python**. It orchestrates **Apache JMeter** load-testing runs, monitors system behavior against strict SLA thresholds, and acts as an on-demand virtual performance engineer to analyze telemetry logs and generating engineering analysis summaries using Local or Cloud AI engines.

It is an automated performance engineering pipeline built with **Streamlit** and **Python**. It simplifies the load-testing lifecycle by orchestrating **Apache JMeter** tests (both local and distributed multi-node architectures).

---

## Features

* **Dual JMeter Architecture Support:** Seamlessly switch between local `Standalone` execution and multi-node distributed `Master-Worker` testing.
* **Native HTML Dashboards:** Automatically compiles and cleans raw CSV execution logs into interactive, graphic-heavy JMeter HTML reporting dashboards inside your workspace.
* **Automated SLA Verification:** Instantly alerts you if average response times, max peak outliers, or error percentages breach your strict threshold metrics.
* **Cognitive AI Reporting:** Interacts directly with Google Gemini, OpenAI, or local Ollama engines to produce narrative, production-ready diagnostic bottlenecks and scaling recommendations without conversational fluff.
* **Persistent Settings Panel:** Save and update system path variables, API keys, and SLA rules to a cleanly formatted, commented local `.env` file right from the UI dashboard.
---
## How to Download, Install, and Use (End-to-End Guide)

PerfInsight AI is designed to run out-of-the-box with zero global system installation headaches. Follow this step-by-step guide to download, configure, and execute the full pipeline.

---

###  Step 1: Get the Project Files

Choose **one** of the following two options to bring the project onto your local machine:

#### Option A: Direct Archive Download (Easiest & Recommended)
1. Navigate to the **Releases** section on the right side of this GitHub repository page.
2. Select the latest stable version and download the package matching your operating system under **Assets**:
   * **🪟 Windows Users:** Click and download the **`Source code (zip)`** file.
   * **🍏 macOS / Linux Users:** Click and download the **`Source code (tar.gz)`** file.
3. Extract (unzip) the downloaded folder completely to a working directory on your computer (e.g., your Desktop or Documents folder).

#### Option B: Clone via Git Terminal
1. Create a folder ( e.g your_folder_name)
2. Open your terminal or command prompt
3. Navigate to to folder in command line ( cd your_folder_name)
4. Run the one of the following command to clone the repository:

   HTTPS:   git clone https://github.com/vthebbar/PerfInsight-AI.git
   or
   SSH :    git clone git@github.com:vthebbar/PerfInsight-AI.git


### ⚙️ Step 2: Provide Your JMeter Script

Take your target JMeter script file (your .jmx file) that you intend to test.

Copy and paste it right into this project's root directory.

Rename the file to exactly **Test_plan.jmx** so the application targets it automatically.


### Step 3: Launching the Application Engine
Run the launcher script corresponding to your operating system sitting inside the project root directory. You do not need to manually install anything.

🪟 On Windows: Double-click the  **start_windows.bat** file.

🍏 On macOS / Linux: Open your terminal inside this project root directory and execute below command:
    
  **chmod +x start_mac_linux.sh && ./start_mac_linux.sh**
   

   ⚙️ What happens automatically: The terminal script safely provisions a sandboxed local copy of Python, builds an isolated virtual workspace (venv/), resolves all code package dependencies cleanly, and launches the app engine without modifying your global system settings.


### ⚙️ Step 4: Prepare Your Workspace Configurations

1. Find the visible template file named **`env.example`** in the project's root folder.
2. Rename that file to exactly **`env`** (simply remove the `.example` extension).
3. Open this `env` file using any standard text editor (like Notepad, TextEdit, or VS Code).

Modify the values as below, depending on AI model you use: 
You do not need to modify inside this file directly, It can done through UI as well once application is launched.

### =================================
### AI Engine Configuration Settings (Modify through UI or directly in env file)
### ==================================

| Provider Choice/KEY | AI_PROVIDER | AI_MODEL | AI_API_KEY | CUSTOM_BASE_URL |
|---|---|---|---|---|
| Google Gemini | Google Gemini | gemini-2.5-flash or gemini-2.5-pro | Your Gemini API Key | Leave Blank |
| OpenAI | OpenAI | gpt-4o-mini or gpt-4o | Your OpenAI API Key | Leave Blank |
| Local Ollama | Local Ollama | qwen2.5-coder:7b or llama3 | Leave Blank | http://localhost:11434/v1 |
| xAI Grok | Custom OpenAI-Compatible | grok-4.3 | Your Grok API Key | https://api.x.ai/v1 |
| DeepSeek | Custom OpenAI-Compatible | deepseek-reasoner or deepseek-chat | Your DeepSeek API Key | https://api.deepseek.com/v1 |
| OpenRouter | Custom OpenAI-Compatible | e.g., meta-llama/llama-3.3-70b | Your OpenRouter Key | https://openrouter.ai/api/v1 |

#### =======================================

Once the setup completes, choose one of the execution methods below to interact with the pipeline:

### Method 1: Interactive Web Dashboard (Standard)
By default, the launcher automatically fires open a visual interface in your default web browser at:
👉 http://localhost:8501
Inside this visual layout, you can adjust configuration inputs on-the-fly, drag SLA toggle bars, save modifications, Click on button **Run Full Performance Pipeline** and watch the automated pipeline execute in real time.

### Method 2: Headless CLI Execution (CI/CD / Terminal Automation)
If you want to execute your pre-configured pipeline completely from your command line or within an automated pipeline (e.g., Jenkins, GitHub Actions, or a cron job) without spinning up a web server, run this command within your activated environment:
  **python app.py**

**Note:** This mode bypasses the Streamlit web server entirely. It reads your latest parameters straight from the local env configuration file, runs the JMeter execution, validates SLAs, saves the AI performance report to disk, and terminates cleanly upon completion.


 ### 🧬 Distributed Architecture Setup (Optional)
If your test scales beyond a single runner and requires a Distributed (Master-Worker) multi-node load configuration:

Verify Versions: Ensure all remote Worker (Slave) machines have the exact same version of Apache JMeter and Java installed as your local Master machine.

Start Worker Daemons: On each remote worker machine, open the terminal, navigate to its jmeter/bin directory, and launch the listener daemon:

Linux/Mac Worker: ./jmeter-server

Windows Worker: jmeter-server.bat

Configure the Dashboard UI: Inside the PerfInsight AI web sidebar panel, switch the JMeter Test Execution Architecture radio button to Distributed (Master-Worker).

Input Node IPs: In the text field that appears, input the comma-separated IP addresses or hostnames of your active workers (e.g., 192.168.1.50, 192.168.1.51). Click Save Settings to .env and run the test.

**📂 Workspace Output Directory Layout:**

Upon executing the pipeline, the project structure isolates outputs cleanly inside a managed workspace layout. Here is where your generated reports reside:

```text

PERF_INSIGHT_AI/
├── start_windows.bat          # Clickable trigger file for Windows
├── start_mac_linux.sh         # Clickable trigger file for Mac/Linux
├── app.py                     # Core pipeline application script
├── .env                       # Active runtime environment parameters
└── reports/                   # AUTO-GENERATED TEST OUTPUTS FOLDER
    ├── results.csv          # Raw aggregated JMeter data tracking log metrics
    ├── ai_performance_report.txt # Raw direct text summary from the AI Engine
    └── jmeter_html_report/    # Compiled native interactive graphics dashboard
        └── index.html         
        #Double-click this file to open visual charts in your browser

```

Open reports/jmeter_html_report/index.html locally in any web browser to see response time distributions and transaction graphs, then open reports/ai_performance_report.txt to read your dense, objective engineering assessment summary.


---
<p align="center">
  <small>🤖 <i>An AI initiative by Vishwanatha Hebbar</i></small>
</p>