# Exclusion Strategy: .gitignore vs .dockerignore

This project uses a layered approach to file exclusion to ensure security, maintainability, and efficiency.

---

## 1. .gitignore (Source Control)

**Tool:** Git  
**Purpose:** Defines what never gets saved to the code history on GitHub.

### **Key Exclusions:**
- **Local Environments:** `.venv/`, `env/` (Prevents hundreds of MBs of local libraries from being committed).
- **Terraform State:** `*.tfstate`, `.terraform/` (State files can contain raw secrets and should only live in the remote S3 backend).
- **Secrets/Env:** `.env`, `*.pem`, `*.key` (CRITICAL: Prevents accidental credential leakage).
- **IDE Junk:** `.vscode/`, `.idea/`, `.DS_Store` (Keeps the repo clean for all developers).

> [!IMPORTANT]
> **.dockerignore is tracked in Git.** We removed `.dockerignore` from the `.gitignore` so that every developer and build server uses the exact same build rules.

---

## 2. .dockerignore (Container Build)

**Tool:** Docker  
**Purpose:** Defines what is **excluded** from the build context sent to the Docker daemon.

### **The Rationale for Refactoring:**
Originally, the build context included the entire 800MB+ project directory. We refactored this to a **"Strict Exclusion"** model.

### **Key Exclusions:**
- **Infrastructure:** `terraform/`, `kubernetes/` (Docker doesn't need IaC code to build a Python app).
- **Docs & Planning:** `project-docs/`, `README.md`, `LICENSE` (Reduces image size and improves security).
- **Test Artifacts:** `tests/`, `.pytest_cache/` (Keeps the production image lean).
- **Local Dev Junk:** `.venv/`, `__pycache__` (Prevents local machine bloat from entering the container).

### **Impact of Optimization:**
- **Build Context Size:** Reduced from **820MB** → **902 Bytes** (55,000x improvement).
- **Security:** Sensitive infrastructure code and local secrets are never "sent" to the Docker daemon.
- **Speed:** Incremental builds take seconds instead of minutes.

---

## Summary Comparison

| Feature | .gitignore | .dockerignore |
| :--- | :--- | :--- |
| **Target** | GitHub / Repo History | Docker Image / Build Process |
| **Logic** | "Don't save this" | "Don't send this to the builder" |
| **Primary Goal** | Security & Repo Hygiene | Build Performance & Image Size |

---

## Usage Tip
If you add a new service (e.g., `frontend/`), ensure you add it to the `.dockerignore` of the `api/` service to keep the API build context clean.
