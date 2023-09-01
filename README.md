# DataTalksClub-Projects


## Table of Contents

- [Introduction](#introduction)
- [Folder Structure](#folder-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
    - [Clone the Repository](#clone-the-repository)
    - [Environment Setup](#environment-setup)
    - [Environment Variables](#environment-variables)
- [Makefile Usage](#makefile-usage)
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
├── Data/          # Data files
├── src/           # Python source files
├── tests/         # Test files (TBD)
├── utils/         # Utility files
├── .gitignore     # Git ignore rules
├── LICENSE        # License file
├── Makefile       # Makefile for automation
├── Pipfile        # Pipfile for dependencies
├── Pipfile.lock   # Locked dependencies
├── README.md      # This file
└── pyproject.toml # Build settings
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
pip install pipenv
pipenv install --dev
pipenv shell
```

### Environment Variables

To run this project, you'll need to add a `.env` file in your project root. Replace your_openai_api_key_here and your_github_access_token_here with your actual OpenAI API key and GitHub access token, respectively.

## Makefile Usage

### Run tests (TBD):

```bash
make test
```

### Quality Checks

```bash
make quality_checks
```

### Scrape Data

```bash
make scrape
```

### Generate Titles

```bash
make titles
```

### Check Deployments

```bash
make deploy
```

### Run All Tasks

```bash
make all
```

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

