# Prompt Injection Firewall

## Overview
This repository contains the implementation of a prompt injection firewall to secure AI-driven systems from malicious prompt manipulation attacks. It ensures robust input sanitation, request parsing, and integrates with third-party services like OpenAI.

## Installation
to install dependencies, run:
```
pip install -r requirements.txt
```

## Usage
Run the firewall proxy using:
```
python -m app
```

Ensure necessary environment variables such as API keys are configured properly.

## Tests
To run the tests:
```
pytest tests/ -v
```

## Project Structure
- `app/` - Core implementation.
- `tests/` - Unit tests.

## Contributing
Contributions are welcome! Open an issue or a pull request if you'd like to make improvements.