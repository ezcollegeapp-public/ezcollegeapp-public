# EZCollegeApp

<div align="center">

**Large Language Models for College Applications**

*A research project exploring AI-powered solutions for college admissions*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## 📖 About

EZCollegeApp is a research project that investigates the application of large language models (LLMs) in the college application process. This project examines how advanced AI technologies can assist students, counselors, and institutions in navigating the complexities of college admissions.

## 🎓 Research Paper

The repository includes a comprehensive research paper documenting the methodology, findings, and implications of using LLMs for college applications:

📄 **`EZCollegeApp__Large_Language_Models_for_College_Applications_submitted.pdf`**

## 🔬 Research Focus

- **AI-Assisted Applications**: Exploring how LLMs can support essay writing, application review, and guidance
- **Educational Technology**: Investigating the intersection of artificial intelligence and higher education
- **Ethical Considerations**: Examining the implications and best practices for AI in admissions

## 📚 Contents

- Research paper (submitted for peer review)
- Documentation and supplementary materials
- License information

## � Getting Started

### Installation

```bash
cd ezcommon-backend
pip install -r requirements.txt
```

### Configuration

Copy the example environment file and add your API key:

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY
```

### Usage

Place your documents (transcripts, test scores, etc.) in `ezcommon-backend/data/`, then run:

```bash
cd ezcommon-backend

# Step 1: Parse documents and store in database
python workflow/parse_documents.py

# Step 2: (Optional) Extract data to JSON
python workflow/export_data.py

# Step 3: Fill application forms
python workflow/fill_forms.py
```

| Script | Description |
|--------|-------------|
| `parse_documents.py` | Parses user documents (OCR/Vision AI) and stores semantic blocks in database |
| `export_data.py` | Extracts stored data to JSON file for inspection |
| `fill_forms.py` | Fills college application forms using parsed data |

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

*For comprehensive details, methodology, and findings, please refer to the research paper.*

</div>
