# 🚀 TestFlow: Context-Aware BDD Generator

## 📌 Table of Contents
- [Introduction](#introduction)
- [Demo](#demo)
- [Inspiration](#inspiration)
- [What It Does](#what-it-does)
- [How We Built It](#how-we-built-it)
- [Challenges We Faced](#challenges-we-faced)
- [How to Run](#how-to-run)
- [Tech Stack](#tech-stack)
- [Team](#team)

---

## 🎯 Introduction
TestFlow is an intelligent context-aware testing tool that automatically generates Behavior Driven Development (BDD) test cases from Java codebases. Developed for the Context-Aware Testing , it analyzes Spring Boot applications, extracts API endpoints with their full context, and creates comprehensive test suites that understand the relationships between components.

## 🎥 Demo
📹 [Video Demo](artifacts/demo)  
🖼️ Screenshots:



## 💡 Inspiration
Traditional test case creation lacks awareness of the full application context, often leading to fragile tests that break when code changes. TestFlow was inspired by the need to generate tests that understand relationships between components, providing developers with robust test suites that adapt to evolving applications while maintaining comprehensive coverage.

## ⚙️ What It Does
- **Context-Aware Analysis**: Extracts not just API endpoints but their full context including controllers, services, and repositories
- **Dependency Mapping**: Creates detailed dependency graphs showing how components interact
- **Intelligent BDD Generation**: Generates tests that understand business logic and data flow
- **Smart Change Detection**: Identifies affected components when code changes and updates only relevant tests
- **Rich HTML Reports**: Produces detailed reports showing test execution results with context
- **Cross-Platform Compatibility**: Handles system-specific issues like Windows file permissions

## 🛠️ How We Built It
TestFlow combines static code analysis with AI-powered test generation. The system parses Java files to build a complete context model of the application, tracks relationships between components, and leverages LLM technology to generate meaningful test scenarios based on the full application context. When code changes, it intelligently updates only the affected tests.

## 🚧 Challenges We Faced
- **Context Extraction**: Building a complete model of application components and their relationships
- **Intelligent Test Generation**: Creating tests that understand business logic, not just API contracts
- **Change Impact Analysis**: Determining which tests need updates when code changes
- **Cross-Platform Compatibility**: Handling file system differences between operating systems
- **Report Clarity**: Making test results easy to understand in the context of the application

## 🏃 How to Run
1. Clone the repository  
   ```sh
   git clone https://github.com/ewfx/catfe-deep-seekers.git
   
   ```
2. Install dependencies  
   ```sh
   pip install -r requirements.txt
   ```
3. Configure your project  
   ```sh
   # Edit config.json with your repository URL and OpenAI API key
   ```
4. Run the full analysis  
   ```sh
   python generate_artifacts.py
   ```
5. Run BDD tests  
   ```sh
   python run_everything.py
   ```
6. Update after code changes  
   ```sh
   python update_from_git.py
   ```

## 🏗️ Tech Stack
- 🔹 Python: Core application logic
- 🔹 Javalang: Java parsing and static analysis
- 🔹 OpenAI API: Context-aware test generation
- 🔹 Behave: BDD test execution
- 🔹 GitPython: Version control integration


## 👥 Team
- **Kowshik Biradavolu** - [GitHub](#) | [LinkedIn](#)
- **Kishore Kanna K** - [GitHub](#) | [LinkedIn](#)
- **Venkatesh Nachimuthu** - [GitHub](#) | [LinkedIn](#)
- **Sunil Gopa** - [GitHub](#) | [LinkedIn](#)
