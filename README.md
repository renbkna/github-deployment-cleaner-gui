# GitHub Deployment Cleaner GUI

A Python desktop application for managing GitHub deployments. This tool helps you list, mark inactive, and delete GitHub deployments across your repositories.

![GitHub Deployment Cleaner Screenshot](screenshots/main.png)

## Features

- List all deployments for any GitHub repository
- Filter deployments by status and text search
- Mark deployments as inactive
- Delete deployments
- Batch operations: mark all inactive, delete all inactive
- Recent repositories history
- Activity logging
- GitHub API integration

## Requirements

- Python 3.7+
- GitHub Personal Access Token with `repo` permissions

## Installation

1. Clone the repository:

```bash
git clone https://github.com/renbkna/github-deployment-cleaner-gui
cd github-deployment-cleaner-gui
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your GitHub token:

```sh
GITHUB_TOKEN=your_github_personal_access_token_here
```

## Usage

Run the application:

```bash
python gui.py
```

### Basic workflow

1. Enter a GitHub username/organization and repository name
2. Click "List Deployments" to fetch all deployments
3. Use filters to find specific deployments
4. Click on the "Actions" column to see available operations for each deployment
5. Use batch actions for multiple deployments

## Configuration

GitHub API access requires a Personal Access Token with `repo` scope. You can create one in your [GitHub Developer Settings](https://github.com/settings/tokens).

## Development

The application is built using:

- Tkinter for the GUI
- Requests/httpx for API calls
- Threading for non-blocking operations

### Project Structure

- `gui.py` - Main application entry point and GUI
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (GitHub token)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- GitHub API Documentation: <https://docs.github.com/en/rest/deployments>
