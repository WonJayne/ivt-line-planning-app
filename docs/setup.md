# Environment Setup

This project requires **Python 3.10** or newer. We recommend using a virtual environment so that Python packages used for the exercises do not interfere with other projects.

## Creating a Virtual Environment

1. Install Python (version 3.10 or newer).
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: .\venv\Scripts\activate
   ```

## Installing Dependencies

All required Python packages are listed in `requirements.txt`. Install them with

```bash
pip install -r requirements.txt
```

Alternatively you can install the published package directly from PyPI:

```bash
pip install openbus-light
```

To use the optional OR-Tools solver backend run

```bash
pip install ortools
```

Afterwards run the tests to ensure that your environment is ready:

```bash
pytest
```
