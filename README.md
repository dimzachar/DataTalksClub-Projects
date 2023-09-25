# DataTalksClub-Projects

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://datatalksclub-projects.streamlit.app/)



https://github.com/dimzachar/DataTalksClub-Projects/assets/113017737/c3c3235c-951c-47e8-aa6a-a6dffa159e46


## Table of Contents

- [Introduction](#introduction)
- [Folder Structure](#folder-structure)
- [Getting Started](#getting-started)
    - [Clone the Repository](#clone-the-repository)
    - [Environment Setup](#environment-setup)
    - [Environment Variables](#environment-variables)
- [Makefile Usage](#makefile-usage)
- [CI/CD Pipeline](#cicd-pipeline)
- [Configuration Files](#configuration-files)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Introduction

DataTalksClub-Projects is a Python repository aimed at automating the analysis of projects from [DataTalksClub](https://github.com/DataTalksClub) courses. It focuses on data from [ML Zoomcamp](https://github.com/DataTalksClub/machine-learning-zoomcamp), [MLOps Zoomcamp](https://github.com/DataTalksClub/mlops-zoomcamp) and [DE Zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp) for the years of 2021-2023. The repository includes Python scripts for tasks like web scraping, data handling, and API interactions. The `Data/` folder contains all the datasets I have generated for the courses. It also aims to implement comprehensive tests and data visualizations.


> **Note**: Titles for projects are generated using OpenAI and may require refinement. Future course iterations should include project titles for easier processing.


## Folder Structure

```
.
├── Data/               # Data files
├── src/                # Python source files
├── tests/              # Test files (TBD)
├── utils/              # Utility files
├── .env                # Environment variables
├── .gitignore          # Git ignore rules
├── LICENSE             # License file
├── Makefile            # Makefile for automation
├── README.md           # This file
├── app.py              # Streamlit app
├── help.log            # Unknown titles
├── pyproject.toml      # Build settings
└── requirements.txt    # Dependency list
```

## Getting Started

### Clone the Repository

```bash
git clone https://github.com/yourusername/DataTalksClub-Projects.git
cd DataTalksClub-Projects
```

### Environment Setup

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Environment Variables

To run this project, you'll need to add a `.env` file in your project root. Replace `your_openai_api_key_here` and `your_github_access_token_here` with your actual OpenAI API key and GitHub access token, respectively.

## Makefile Usage

The Makefile included in this repository provides a convenient way to run various tasks. Below are the commands you can use:

### Run tests (TBD)

This command will run all the unit tests and integration tests for the project.

```bash
make test
```

### Quality Checks

Run this command to perform code quality checks. It includes isort, black and pylint.

```bash
make quality_checks
```

### Scrape Data

Use this command to scrape data from specified sources. The data will be saved in the appropriate format and location.

```bash
make scrape
```

### Generate Titles

This command will generate titles for the projects using OpenAI's API.

```bash
make titles
```

### Check Deployments

Run this command to check the deployment status of project services such as web, batch or streaming.

```bash
make deploy
```

### Run All Tasks

This command is a shortcut to run all of the above tasks in sequence. It's a quick way to ensure that everything is set up correctly.

```bash
make all
```

### Streamlit app

Run the Streamlit app using the Makefile

```bash
make streamlit
```

## CI/CD Pipeline (TBD)

This repository includes a Continuous Integration (CI) workflow that automatically builds and tests the Python project upon each push or pull request. This ensures that the codebase remains stable and free of errors as new changes are integrated.

The CI workflow is configured to perform the following tasks:

- Code quality checks
- Unit tests
- Integration tests

## Configuration Files

- `.gitignore`: Specifies files and folders to ignore in Git.
- `LICENSE`: Contains the license information.
- `Pipfile` & `Pipfile.lock`: Manage project dependencies.
- `pyproject.toml`: Contains build-related settings.

## Contributing (Coming soon)

1. Fork the repository.
2. Create a new feature branch.
3. Make changes.
4. Run tests (TBD).
5. Submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact

For inquiries, connect with me on [Linkedin](https://www.linkedin.com/in/zacharenakis/)

## Support this project

[![Donate with PayPal](https://www.paypalobjects.com/digitalassets/c/website/marketing/apac/C2/logos-buttons/optimize/26_Yellow_PayPal_Pill_Button.png)](https://www.paypal.com/donate/?hosted_button_id=LR3PQYHZY4CJ4)
