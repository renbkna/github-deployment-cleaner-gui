import os
import requests
import logging
import asyncio
import httpx
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkinter.font import Font
import webbrowser
from datetime import datetime
import json
from dotenv import load_dotenv
import sys

# Load the .env file from one directory above the current file's directory (root of the project)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Use environment variable for token; GitHub user and repo will be entered dynamically
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Color scheme
COLORS = {
    "primary": "#3584e4",      # Primary blue
    "secondary": "#f6f5f4",    # Light gray background
    "success": "#2ec27e",      # Green for success
    "warning": "#e5a50a",      # Yellow for warnings
    "error": "#e01b24",        # Red for errors
    "info": "#1c71d8",         # Blue for info
    "accent": "#9141ac",       # Purple for accent
    "dark": "#241f31",         # Dark gray for text
    "light": "#ffffff",        # White
    "border": "#deddda",       # Light gray for borders
}

# Theme settings
THEME = {
    "bg": COLORS["light"],
    "fg": COLORS["dark"],
    "active": COLORS["primary"],
    "font_family": "Segoe UI" if os.name == "nt" else "Helvetica",
    "button_bg": COLORS["primary"],
    "button_fg": COLORS["light"],
    "border_color": COLORS["border"],
}

# Asynchronous function to fetch the latest status for a deployment
async def fetch_status_async(statuses_url: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(statuses_url, headers=HEADERS)
            if response.status_code == 200:
                statuses = response.json()
                if statuses:
                    return statuses[0].get("state", "pending")
                else:
                    return "pending"
            else:
                logger.error(
                    f"Error fetching status from {statuses_url}: {response.status_code}"
                )
                return "unknown"
    except Exception as e:
        logger.error(f"Exception fetching status from {statuses_url}: {e}")
        return "unknown"


def run_async_tasks(tasks):
    """Run asynchronous tasks using a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(asyncio.gather(*tasks))
        return results
    finally:
        loop.close()


def list_deployments(base_url: str = None):
    """
    List all deployments along with their latest status fetched asynchronously.
    If base_url is not provided, it falls back to a default value.
    """
    if base_url is None:
        messagebox.showerror("Error", "Repository URL is not defined.")
        return []
    
    try:
        response = requests.get(base_url, headers=HEADERS, params={"per_page": 100})
        if response.status_code != 200:
            error_msg = f"Failed to fetch deployments: {response.status_code}"
            try:
                error_detail = response.json().get("message", "No details available")
                error_msg += f" - {error_detail}"
            except:
                pass
            logger.error(error_msg)
            return {"error": error_msg}
        
        deployments = response.json()
        
        if not deployments:
            return []

        tasks = []
        deployments_with_tasks = []
        for deployment in deployments:
            statuses_url = deployment.get("statuses_url")
            if statuses_url:
                tasks.append(fetch_status_async(statuses_url))
                deployments_with_tasks.append(deployment)
            else:
                deployment["state"] = "unknown"

        if tasks:
            states = run_async_tasks(tasks)
            # Assign fetched state to each corresponding deployment
            for deployment, state in zip(deployments_with_tasks, states):
                deployment["state"] = state

        return deployments
    except Exception as e:
        logger.error(f"Error listing deployments: {str(e)}")
        return {"error": f"Failed to list deployments: {str(e)}"}


def mark_inactive(deployment_id, base_url: str = None):
    """
    Mark a deployment as inactive.
    """
    if base_url is None:
        messagebox.showerror("Error", "Repository URL is not defined.")
        return False
    url = f"{base_url}/{deployment_id}/statuses"
    payload = {"state": "inactive"}
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code == 201:
        logger.info(f"Deployment {deployment_id} marked as inactive.")
        return True
    else:
        logger.error(
            f"Failed to mark deployment {deployment_id} as inactive: {response.status_code}"
        )
        return False


def delete_deployment(deployment_id, base_url: str = None):
    """
    Delete a deployment.
    """
    if base_url is None:
        messagebox.showerror("Error", "Repository URL is not defined.")
        return False
    url = f"{base_url}/{deployment_id}"
    response = requests.delete(url, headers=HEADERS)
    if response.status_code == 204:
        logger.info(f"Deployment {deployment_id} deleted successfully.")
        return True
    else:
        logger.error(
            f"Failed to delete deployment {deployment_id}: {response.status_code}"
        )
        return False


class ImprovedGitHubDeploymentGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GitHub Deployment Cleaner")
        self.geometry("1200x800")
        self.minsize(900, 600)
        
        # Set application icon
        try:
            self.iconbitmap(os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "icon.png"))
        except:
            pass  # Skip if icon is not available
        
        # Dictionary to store full deployment data keyed by Treeview row ID
        self.tree_data = {}
        
        # Load recent repositories
        self.recent_repos = self.load_recent_repos()
        
        # Set theme colors
        self.configure(bg=THEME["bg"])
        self.option_add("*background", THEME["bg"])
        self.option_add("*foreground", THEME["fg"])
        
        # Create custom styles
        self.create_styles()
        
        # Create main GUI layout
        self.create_layout()
        
        # Bind events
        self.bind_events()
        
        # Load last used repo
        self.load_last_used_repo()
    
    def create_styles(self):
        """Create custom styles for widgets"""
        # Configure ttk styles
        self.style = ttk.Style(self)
        
        # Define fonts
        self.title_font = Font(family=THEME["font_family"], size=14, weight="bold")
        self.subtitle_font = Font(family=THEME["font_family"], size=12, weight="bold")
        self.normal_font = Font(family=THEME["font_family"], size=10)
        self.small_font = Font(family=THEME["font_family"], size=9)
        self.code_font = Font(family="Courier New", size=10)
        
        # Configure Treeview styles
        self.style.configure("Treeview", 
                             background=THEME["bg"],
                             foreground=THEME["fg"],
                             rowheight=30,
                             fieldbackground=THEME["bg"],
                             font=self.normal_font)
        
        self.style.configure("Treeview.Heading", 
                             font=self.normal_font,
                             background=COLORS["secondary"],
                             foreground=THEME["fg"])
        
        # Button styles
        self.style.configure("Primary.TButton", 
                             background=THEME["button_bg"],
                             foreground=THEME["button_fg"],
                             font=self.normal_font)
        
        self.style.configure("Secondary.TButton", 
                             background=COLORS["secondary"],
                             foreground=THEME["fg"],
                             font=self.normal_font)
        
        self.style.configure("Danger.TButton", 
                             background=COLORS["error"],
                             foreground=COLORS["light"],
                             font=self.normal_font)
        
        # Frame styles
        self.style.configure("Card.TFrame", 
                             background=THEME["bg"],
                             borderwidth=1,
                             relief="solid")
        
        # Label styles
        self.style.configure("Title.TLabel", 
                             font=self.title_font,
                             background=THEME["bg"],
                             foreground=THEME["fg"])
        
        self.style.configure("Subtitle.TLabel", 
                             font=self.subtitle_font,
                             background=THEME["bg"],
                             foreground=THEME["fg"])
        
        self.style.configure("Info.TLabel", 
                             font=self.small_font,
                             background=THEME["bg"],
                             foreground=COLORS["info"])
    
    def create_layout(self):
        """Create the main GUI layout"""
        # Create main container with padding
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create top frame with title and logo
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            top_frame, 
            text="GitHub Deployment Cleaner",
            style="Title.TLabel"
        )
        title_label.pack(side=tk.LEFT)
        
        version_label = ttk.Label(
            top_frame,
            text="v2.0",
            style="Info.TLabel"
        )
        version_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # GitHub link
        github_button = ttk.Button(
            top_frame,
            text="View on GitHub",
            style="Secondary.TButton",
            command=lambda: webbrowser.open("https://github.com/renbkna/github-deployment-cleaner")
        )
        github_button.pack(side=tk.RIGHT)
        
        # Create repository configuration frame
        self.create_repo_config_frame(main_frame)
        
        # Create main content area with tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Deployments tab
        self.deployments_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.deployments_tab, text="Deployments")
        self.create_deployments_tab()
        
        # Activity log tab
        self.activity_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.activity_tab, text="Activity Log")
        self.create_activity_tab()
        
        # Create status bar at bottom
        self.status_bar = ttk.Frame(main_frame, relief=tk.SUNKEN, padding=(5, 2))
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
        # Add current repository info to status bar
        self.repo_status_label = ttk.Label(self.status_bar, text="")
        self.repo_status_label.pack(side=tk.RIGHT)
    
    def create_repo_config_frame(self, parent):
        """Create the repository configuration panel"""
        config_frame = ttk.LabelFrame(parent, text="Repository Configuration", padding=10)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Recent repositories dropdown
        recent_frame = ttk.Frame(config_frame)
        recent_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(recent_frame, text="Recent Repositories:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.combo_recent = ttk.Combobox(recent_frame, width=40, state="readonly")
        self.combo_recent.pack(side=tk.LEFT, padx=(0, 10))
        self.update_repo_combobox()
        
        ttk.Button(
            recent_frame, 
            text="Load",
            style="Secondary.TButton",
            command=self.load_selected_repo
        ).pack(side=tk.LEFT)
        
        # Input fields for username and repo
        input_frame = ttk.Frame(config_frame)
        input_frame.pack(fill=tk.X)
        
        # Username field
        username_frame = ttk.Frame(input_frame)
        username_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Label(username_frame, text="GitHub Username/Organization:").pack(anchor=tk.W)
        self.entry_username = ttk.Entry(username_frame)
        self.entry_username.pack(fill=tk.X, pady=5)
        
        # Repository field
        repo_frame = ttk.Frame(input_frame)
        repo_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        ttk.Label(repo_frame, text="Repository Name:").pack(anchor=tk.W)
        self.entry_repo = ttk.Entry(repo_frame)
        self.entry_repo.pack(fill=tk.X, pady=5)
        
        # Button frame with List Deployments and Open in Browser buttons
        button_frame = ttk.Frame(config_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.btn_list = ttk.Button(
            button_frame, 
            text="List Deployments", 
            style="Primary.TButton",
            command=self.list_deployments
        )
        self.btn_list.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_browser = ttk.Button(
            button_frame, 
            text="Open in Browser", 
            style="Secondary.TButton",
            command=self.open_in_browser
        )
        self.btn_browser.pack(side=tk.LEFT)
    
    def create_deployments_tab(self):
        """Create the deployments tab content"""
        tab_frame = ttk.Frame(self.deployments_tab, padding=10)
        tab_frame.pack(fill=tk.BOTH, expand=True)
        
        # Filter frame
        filter_frame = ttk.Frame(tab_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var)
        self.filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.filter_var.trace("w", self.filter_deployments)
        
        # Status filter
        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=(10, 5))
        self.status_filter = ttk.Combobox(filter_frame, width=15, state="readonly")
        self.status_filter['values'] = ["All", "Active", "Inactive", "Success", "Pending", "Failure"]
        self.status_filter.current(0)
        self.status_filter.pack(side=tk.LEFT)
        self.status_filter.bind("<<ComboboxSelected>>", self.filter_deployments)
        
        # Clear filter button
        self.btn_clear = ttk.Button(
            filter_frame, 
            text="Clear Filter", 
            style="Secondary.TButton",
            command=self.clear_filter
        )
        self.btn_clear.pack(side=tk.LEFT, padx=(10, 0))
        
        # Batch actions frame
        batch_frame = ttk.Frame(tab_frame)
        batch_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(batch_frame, text="Batch Actions:").pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            batch_frame, 
            text="Mark All Inactive", 
            style="Secondary.TButton",
            command=self.mark_all_inactive
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            batch_frame, 
            text="Delete All Inactive", 
            style="Danger.TButton",
            command=self.delete_all_inactive
        ).pack(side=tk.LEFT)
        
        # Treeview for showing deployments
        tree_frame = ttk.Frame(tab_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Ref", "Environment", "Status", "Created At", "Actions"),
            show="headings",
            selectmode="browse"
        )
        
        # Configure scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Configure columns
        self.tree.heading("ID", text="ID", command=lambda: self.sort_treeview("ID", False))
        self.tree.heading("Ref", text="Branch/Reference", command=lambda: self.sort_treeview("Ref", False))
        self.tree.heading("Environment", text="Environment", command=lambda: self.sort_treeview("Environment", False))
        self.tree.heading("Status", text="Status", command=lambda: self.sort_treeview("Status", False))
        self.tree.heading("Created At", text="Created At", command=lambda: self.sort_treeview("Created At", False))
        self.tree.heading("Actions", text="Actions")
        
        self.tree.column("ID", width=80, minwidth=80)
        self.tree.column("Ref", width=200, minwidth=150)
        self.tree.column("Environment", width=150, minwidth=100)
        self.tree.column("Status", width=100, minwidth=80)
        self.tree.column("Created At", width=180, minwidth=150)
        self.tree.column("Actions", width=180, minwidth=150)
        
        # Pack the treeview and scrollbars
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_activity_tab(self):
        """Create the activity log tab content"""
        tab_frame = ttk.Frame(self.activity_tab, padding=10)
        tab_frame.pack(fill=tk.BOTH, expand=True)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(tab_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # Control buttons
        control_frame = ttk.Frame(tab_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            control_frame,
            text="Clear Log",
            style="Secondary.TButton",
            command=self.clear_log
        ).pack(side=tk.RIGHT)
    
    def bind_events(self):
        """Bind all event handlers"""
        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)
        self.bind("<F5>", lambda e: self.list_deployments())
        self.bind("<Control-r>", lambda e: self.list_deployments())
    
    def load_recent_repos(self):
        """Load previously used repositories from a config file"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "recent_repos.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as file:
                    data = json.load(file)
                    return data.get("repos", [])
            return []
        except Exception as e:
            logger.error(f"Failed to load recent repos: {e}")
            return []
    
    def save_recent_repos(self):
        """Save recent repositories to a config file"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "recent_repos.json")
            with open(config_path, 'w') as file:
                json.dump({"repos": self.recent_repos[:10]}, file)  # Keep only the 10 most recent
        except Exception as e:
            logger.error(f"Failed to save recent repos: {e}")
    
    def add_to_recent_repos(self, username, repo):
        """Add a repository to the recent list"""
        if not username or not repo:
            return
            
        repo_string = f"{username}/{repo}"
        # Remove if already exists to avoid duplicates
        if repo_string in self.recent_repos:
            self.recent_repos.remove(repo_string)
        
        # Add to the beginning of the list
        self.recent_repos.insert(0, repo_string)
        
        # Update the combobox
        self.update_repo_combobox()
        
        # Save to file
        self.save_recent_repos()
    
    def update_repo_combobox(self):
        """Update the repository combobox with recent repositories"""
        self.combo_recent['values'] = self.recent_repos
        if self.recent_repos:
            self.combo_recent.current(0)
    
    def load_last_used_repo(self):
        """Load the last used repository"""
        if self.recent_repos:
            parts = self.recent_repos[0].split('/')
            if len(parts) == 2:
                self.entry_username.delete(0, tk.END)
                self.entry_username.insert(0, parts[0])
                
                self.entry_repo.delete(0, tk.END)
                self.entry_repo.insert(0, parts[1])
                
                # Update status bar
                self.update_repo_status()
    
    def load_selected_repo(self):
        """Load the selected repository from the combobox"""
        selected = self.combo_recent.get()
        if not selected:
            return
            
        parts = selected.split('/')
        if len(parts) == 2:
            self.entry_username.delete(0, tk.END)
            self.entry_username.insert(0, parts[0])
            
            self.entry_repo.delete(0, tk.END)
            self.entry_repo.insert(0, parts[1])
            
            # Update status bar
            self.update_repo_status()
    
    def update_status(self, message):
        """Update the status label with a timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_label.config(text=f"[{timestamp}] {message}")
        
        # Also log to the text area
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def update_repo_status(self):
        """Update repository info in status bar"""
        username = self.entry_username.get().strip()
        repo = self.entry_repo.get().strip()
        
        if username and repo:
            self.repo_status_label.config(text=f"Repository: {username}/{repo}")
        else:
            self.repo_status_label.config(text="")
    
    def get_base_url(self):
        username = self.entry_username.get().strip()
        repo = self.entry_repo.get().strip()
        if not username or not repo:
            messagebox.showerror(
                "Error", "Please enter both GitHub username and repository name."
            )
            return None
        
        # Add to recent repos
        self.add_to_recent_repos(username, repo)
        
        # Update status bar
        self.update_repo_status()
        
        return f"https://api.github.com/repos/{username}/{repo}/deployments"
    
    def open_in_browser(self):
        """Open the repository in browser"""
        username = self.entry_username.get().strip()
        repo = self.entry_repo.get().strip()
        if not username or not repo:
            messagebox.showerror(
                "Error", "Please enter both GitHub username and repository name."
            )
            return
        
        url = f"https://github.com/{username}/{repo}/deployments"
        webbrowser.open(url)
    
    def filter_deployments(self, *args):
        """Filter the displayed deployments based on filter text and status"""
        filter_text = self.filter_var.get().lower()
        status_filter = self.status_filter.get().lower()
        
        # Clear current display
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Re-add items that match the filter
        for row_id, dep in self.tree_data.items():
            dep_id = str(dep.get("id", ""))
            dep_ref = str(dep.get("ref", "")).lower()
            dep_env = str(dep.get("environment", "")).lower()
            dep_status = str(dep.get("state", "")).lower()
            
            # Check if it matches the text filter
            text_match = (filter_text in dep_id or 
                      filter_text in dep_ref or 
                      filter_text in dep_env or 
                      filter_text in dep_status)
            
            # Check if it matches the status filter
            status_match = True
            if status_filter != "all":
                if status_filter == "active":
                    status_match = dep_status != "inactive"
                else:
                    status_match = dep_status.lower() == status_filter.lower()
            
            if text_match and status_match:
                self.display_deployment(dep)
        
        # Update count in status
        visible_count = len(self.tree.get_children())
        total_count = len(self.tree_data)
        self.update_status(f"Showing {visible_count} of {total_count} deployments")
    
    def clear_filter(self):
        """Clear all filters"""
        self.filter_var.set("")
        self.status_filter.current(0)  # Set to "All"
        self.filter_deployments()
    
    def sort_treeview(self, column, reverse):
        """Sort treeview data when clicking on column headers"""
        column_index = {
            "ID": 0, 
            "Ref": 1, 
            "Environment": 2, 
            "Status": 3, 
            "Created At": 4
        }
        
        if column not in column_index:
            return
        
        data = []
        for item_id in self.tree.get_children(''):
            values = self.tree.item(item_id, 'values')
            data.append((values, item_id))
        
        # Sort data
        data.sort(key=lambda x: x[0][column_index[column]], reverse=reverse)
        
        # Rearrange items in treeview
        for index, (values, item_id) in enumerate(data):
            self.tree.move(item_id, '', index)
        
        # Reverse sort next time
        self.tree.heading(
            column, 
            command=lambda col=column: self.sort_treeview(col, not reverse)
        )
    
    def display_deployment(self, dep):
        """Display a single deployment in the treeview"""
        dep_id = dep.get("id")
        dep_ref = dep.get("ref")
        dep_env = dep.get("environment", "")
        dep_status = dep.get("state", "unknown")
        
        try:
            created_at = datetime.strptime(dep.get("created_at", ""), "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")
        except:
            created_at = dep.get("created_at", "")
        
        # Format actions based on status
        if dep_status == "inactive":
            actions = "Delete"
        else:
            actions = "Mark Inactive | Delete"
        
        # Insert into tree with tag for status color
        row_id = self.tree.insert(
            "",
            "end",
            values=(
                dep_id,
                dep_ref,
                dep_env,
                dep_status,
                created_at,
                actions,
            ),
            tags=(dep_status,)
        )
        
        # Store the full deployment data for this row
        self.tree_data[row_id] = dep
        
        # Configure tag colors
        if dep_status == "success":
            self.tree.tag_configure("success", background="#d4edda")
        elif dep_status == "failure" or dep_status == "error":
            self.tree.tag_configure("failure", background="#f8d7da")
            self.tree.tag_configure("error", background="#f8d7da")
        elif dep_status == "inactive":
            self.tree.tag_configure("inactive", background="#e2e3e5")
        else:
            self.tree.tag_configure(dep_status, background="#fff3cd")

    def list_deployments(self):
        base_url = self.get_base_url()
        if not base_url:
            return

        def task():
            self.update_status("Fetching deployments...")
            self.btn_list.config(state=tk.DISABLED)
            
            # Clear existing data
            self.tree.delete(*self.tree.get_children())
            self.tree_data.clear()
            
            deployments = list_deployments(base_url=base_url)
            
            # Check for errors
            if isinstance(deployments, dict) and "error" in deployments:
                self.update_status(f"Error: {deployments['error']}")
                messagebox.showerror("Error", deployments["error"])
                self.btn_list.config(state=tk.NORMAL)
                return
            
            # Process deployments
            for dep in deployments:
                self.display_deployment(dep)
            
            # Update status with count
            count = len(deployments)
            self.update_status(f"Fetched {count} deployments.")
            self.btn_list.config(state=tk.NORMAL)
            
            # Update status filter dropdown with available statuses
            statuses = set(["All", "Active", "Inactive"])
            for dep in deployments:
                if "state" in dep and dep["state"]:
                    statuses.add(dep["state"].capitalize())
            
            self.status_filter['values'] = sorted(list(statuses))

        threading.Thread(target=task).start()

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        
        if not row_id:
            return

        dep = self.tree_data.get(row_id)
        if not dep:
            return

        deployment_id = dep.get("id")
        current_status = dep.get("state")
        base_url = self.get_base_url()
        if not base_url:
            return

        # If the user clicks on the "Actions" column
        if col == "#6":  # Actions column
            # Show a context menu with available actions
            context_menu = tk.Menu(self, tearoff=0)
            
            # Add "View in Browser" option
            context_menu.add_command(
                label="View in Browser", 
                command=lambda: self.open_deployment_in_browser(deployment_id)
            )
            
            context_menu.add_separator()
            
            # Add "Mark Inactive" option if not already inactive
            if current_status != "inactive":
                context_menu.add_command(
                    label="Mark as Inactive", 
                    command=lambda: self.threaded_mark_inactive(deployment_id, base_url)
                )
            
            # Add "Delete" option
            context_menu.add_command(
                label="Delete Deployment", 
                command=lambda: self.threaded_delete_deployment(deployment_id, base_url)
            )
            
            # Display the menu
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

    def open_deployment_in_browser(self, deployment_id):
        """Open the deployment in GitHub"""
        username = self.entry_username.get().strip()
        repo = self.entry_repo.get().strip()
        if not username or not repo:
            return
            
        url = f"https://github.com/{username}/{repo}/deployments/{deployment_id}"
        webbrowser.open(url)

    def threaded_mark_inactive(self, deployment_id, base_url):
        def task():
            self.update_status(f"Marking deployment {deployment_id} as inactive...")
            success = mark_inactive(deployment_id, base_url=base_url)
            if success:
                messagebox.showinfo(
                    "Success", f"Deployment {deployment_id} marked as inactive."
                )
            else:
                messagebox.showerror(
                    "Error", f"Failed to mark deployment {deployment_id} as inactive."
                )
            self.update_status("Operation complete.")
            self.list_deployments()

        threading.Thread(target=task).start()

    def threaded_delete_deployment(self, deployment_id, base_url):
        if not messagebox.askyesno(
            "Confirm", f"Are you sure you want to delete deployment {deployment_id}?\nThis action cannot be undone."
        ):
            return

        def task():
            self.update_status(f"Deleting deployment {deployment_id}...")
            success = delete_deployment(deployment_id, base_url=base_url)
            if success:
                messagebox.showinfo(
                    "Success", f"Deployment {deployment_id} deleted successfully."
                )
            else:
                messagebox.showerror(
                    "Error", f"Failed to delete deployment {deployment_id}."
                )
            self.update_status("Operation complete.")
            self.list_deployments()

        threading.Thread(target=task).start()
    
    def mark_all_inactive(self):
        """Mark all active deployments as inactive"""
        base_url = self.get_base_url()
        if not base_url:
            return
            
        # Count active deployments
        active_deployments = [dep for _, dep in self.tree_data.items() 
                             if dep.get("state") != "inactive"]
        
        if not active_deployments:
            messagebox.showinfo("Info", "No active deployments to mark as inactive.")
            return
            
        if not messagebox.askyesno(
            "Confirm", 
            f"Are you sure you want to mark all {len(active_deployments)} active deployments as inactive?"
        ):
            return
            
        def task():
            self.update_status(f"Marking {len(active_deployments)} deployments as inactive...")
            
            success_count = 0
            fail_count = 0
            
            for dep in active_deployments:
                deployment_id = dep.get("id")
                success = mark_inactive(deployment_id, base_url=base_url)
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                self.update_status(f"Processed {success_count + fail_count} of {len(active_deployments)}")
            
            # Final report
            message = f"Operation complete. {success_count} deployments marked as inactive."
            if fail_count > 0:
                message += f" {fail_count} operations failed."
                
            messagebox.showinfo("Operation Complete", message)
            self.update_status(message)
            self.list_deployments()
            
        threading.Thread(target=task).start()
    
    def delete_all_inactive(self):
        """Delete all inactive deployments"""
        base_url = self.get_base_url()
        if not base_url:
            return
            
        # Count inactive deployments
        inactive_deployments = [dep for _, dep in self.tree_data.items() 
                               if dep.get("state") == "inactive"]
        
        if not inactive_deployments:
            messagebox.showinfo("Info", "No inactive deployments to delete.")
            return
            
        if not messagebox.askyesno(
            "Confirm", 
            f"Are you sure you want to delete all {len(inactive_deployments)} inactive deployments?\n" +
            "This action cannot be undone!"
        ):
            return
            
        def task():
            self.update_status(f"Deleting {len(inactive_deployments)} inactive deployments...")
            
            success_count = 0
            fail_count = 0
            
            for dep in inactive_deployments:
                deployment_id = dep.get("id")
                success = delete_deployment(deployment_id, base_url=base_url)
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                self.update_status(f"Processed {success_count + fail_count} of {len(inactive_deployments)}")
            
            # Final report
            message = f"Operation complete. {success_count} deployments deleted."
            if fail_count > 0:
                message += f" {fail_count} operations failed."
                
            messagebox.showinfo("Operation Complete", message)
            self.update_status(message)
            self.list_deployments()
            
        threading.Thread(target=task).start()
    
    def clear_log(self):
        """Clear the log text area"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.update_status("Log cleared")

if __name__ == "__main__":
    # Check if token is configured
    if not TOKEN:
        print("WARNING: GitHub token is not configured. Set GITHUB_TOKEN in .env file.")
        if not messagebox.askokcancel(
            "GitHub Token Missing", 
            "GitHub token is not configured. Some features may not work properly.\n\n" +
            "Do you want to continue anyway?"
        ):
            sys.exit(1)
    
    app = ImprovedGitHubDeploymentGUI()
    app.mainloop()
