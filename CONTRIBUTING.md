# Contributing to FragEngine

Thank you for your interest in contributing to **FragEngine**, a subset of the **FragLab Analytics** suite! We welcome contributions to make our telemetry engine faster, more robust, and more accurate.

---

## 🛠️ Getting Started

1. **Fork the Repository**: Create your own copy of the repository on GitHub.
2. **Clone Locally**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/FragEngine.git
   cd FragEngine
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Load the Extension**: Load the `chrome_extension/` folder as an unpacked extension in Google Chrome.

---

## 🌿 Branching Strategy

We use standard git flow conventions:
-   `main` contains the latest stable, tagged release.
-   Create a branch for your work: `git checkout -b feature/your-feature-name` or `bugfix/your-bug-name`.

---

## 📝 Coding Guidelines

-   **Keep it Lightweight**: FragEngine runs alongside active gameplay. Always optimize for CPU, RAM, and GPU constraints.
-   **Python Style**: Follow PEP 8 guidelines. Keep backend code modular.
-   **JavaScript Style**: Decouple visual updates from request logic. Use raw pixel buffers for local diff gating to prevent redundant TCP requests.

---

## 🚀 Submitting a Pull Request

1. Ensure all tests pass.
2. Commit with clear, semantic commit messages (e.g. `feat: add Tesseract OCR fallback` or `fix: resolve cooldown lock boundary`).
3. Push to your branch and create a Pull Request against the `main` branch of `FragLabAnalytics/FragEngine`.
4. Provide a detailed summary of changes, latency impact, and test results in the PR template.
