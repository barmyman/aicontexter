import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import time
import traceback # Import traceback for better error logging
from pathlib import Path # Use pathlib for modern path handling

class FileCollectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Collector")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Variables
        self.source_folder = tk.StringVar()
        self.output_file = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready")

        # --- File type filter variables ---
        self.use_all_files = tk.BooleanVar(value=True) # Default to True (filters disabled)

        # Common file types to include (defaults don't matter much when use_all_files=True initially)
        self.include_php = tk.BooleanVar(value=False)
        self.include_py = tk.BooleanVar(value=True) # Default some common ones
        self.include_xml = tk.BooleanVar(value=False)
        self.include_js = tk.BooleanVar(value=True)
        self.include_css = tk.BooleanVar(value=True)
        self.include_yml = tk.BooleanVar(value=False)
        self.include_vcl = tk.BooleanVar(value=False)

        # Custom file types
        self.custom_include = tk.StringVar()
        self.custom_exclude = tk.StringVar(value="png,jpg,jpeg,gif,webp,ico,pdf,zip,rar,exe,dll,obj,bin,svg,woff,woff2,ttf,eot") # Added more common binary/font types

        # Cache for file type sets (optimization)
        self._include_ext_set = set()
        self._exclude_ext_set = set()

        # Create UI
        self.create_widgets()
        # Set initial state correctly *after* all widgets are created
        self.update_file_type_state()

    def create_widgets(self):
        # Create a tabbed interface
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create Main tab
        self.main_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.main_tab, text="Main")

        # Create File Types tab
        self.file_types_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.file_types_tab, text="File Types")

        # Build the tabs
        self.create_main_tab()
        self.create_file_types_tab() # This now calls update_file_type_state internally at the end

    def create_main_tab(self):
        # --- Prompt ---
        prompt_frame = ttk.LabelFrame(self.main_tab, text="Task Prompt", padding=10)
        prompt_frame.pack(fill=tk.X, expand=False, pady=(0, 10))

        prompt_scrollbar = ttk.Scrollbar(prompt_frame, orient=tk.VERTICAL)
        self.prompt_text_area = tk.Text(
            prompt_frame, height=5, width=70, wrap=tk.WORD,
            yscrollcommand=prompt_scrollbar.set, undo=True
        )
        prompt_scrollbar.config(command=self.prompt_text_area.yview)
        prompt_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.prompt_text_area.pack(fill=tk.BOTH, expand=True)

        desc_label = ttk.Label(
            prompt_frame,
            text="Enter a description of your task here. This will be included at the beginning of the output file.",
            wraplength=700, justify=tk.LEFT # Make text wrap nicely
        )
        desc_label.pack(anchor=tk.W, pady=(5, 0))

        # --- Source Folder ---
        source_frame = ttk.Frame(self.main_tab)
        source_frame.pack(fill=tk.X, pady=10)
        ttk.Label(source_frame, text="Source Folder:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(source_frame, textvariable=self.source_folder, width=60).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(source_frame, text="Browse...", command=self.browse_source).pack(side=tk.LEFT) # Changed side

        # --- Output File ---
        output_frame = ttk.Frame(self.main_tab)
        output_frame.pack(fill=tk.X, pady=10)
        ttk.Label(output_frame, text="Output File:").pack(side=tk.LEFT, padx=(0, 16)) # Align label better
        ttk.Entry(output_frame, textvariable=self.output_file, width=60).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(output_frame, text="Browse...", command=self.browse_output).pack(side=tk.LEFT) # Changed side

        # --- File Type Settings Summary ---
        file_type_frame = ttk.LabelFrame(self.main_tab, text="File Types", padding=10)
        file_type_frame.pack(fill=tk.X, expand=False, pady=10)

        # This checkbox controls the state of the File Types tab
        self.process_all_files_cb = ttk.Checkbutton(
            file_type_frame,
            text="Process all files (ignore filters on 'File Types' tab)",
            variable=self.use_all_files,
            command=self.update_file_type_state # Command links checkbox to state update
        )
        self.process_all_files_cb.pack(anchor=tk.W)

        ttk.Label(
            file_type_frame,
            text="Uncheck the box above to enable and configure specific file type filters on the 'File Types' tab."
        ).pack(anchor=tk.W, pady=(5, 0))

        # --- Progress & Status ---
        progress_status_frame = ttk.Frame(self.main_tab)
        progress_status_frame.pack(fill=tk.X, pady=(15, 5))

        ttk.Label(progress_status_frame, text="Progress:").pack(side=tk.LEFT)
        self.progress_bar = ttk.Progressbar(progress_status_frame, variable=self.progress_var, length=400, mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Status label (using grid for better potential alignment)
        status_frame = ttk.Frame(self.main_tab)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground="blue", anchor=tk.W)
        self.status_label.pack(fill=tk.X)

        # --- Generate Button ---
        self.generate_button = ttk.Button(self.main_tab, text="Generate Combined File", command=self.generate_file)
        self.generate_button.pack(pady=20)

    def create_file_types_tab(self):
        # --- UX Improvement: Add a status label ---
        self.file_type_status_label = ttk.Label(
            self.file_types_tab,
            text="", # Text will be set by update_file_type_state
            foreground="darkorange",
            font=("Helvetica", 10, "italic")
        )
        self.file_type_status_label.pack(anchor=tk.W, pady=(0, 10))

        # --- Include Frame ---
        include_frame = ttk.LabelFrame(self.file_types_tab, text="Include File Types", padding=10)
        include_frame.pack(fill=tk.X, expand=False, pady=5)

        common_types_frame = ttk.Frame(include_frame)
        common_types_frame.pack(fill=tk.X, pady=5)

        common_file_types = [
            ("PHP (*.php)", self.include_php),
            ("Python (*.py)", self.include_py),
            ("XML (*.xml)", self.include_xml),
            ("JavaScript (*.js)", self.include_js),
            ("CSS (*.css)", self.include_css),
            ("YAML (*.yml, *.yaml)", self.include_yml),
            ("VCL (*.vcl)", self.include_vcl)
            # Add more common types if needed
        ]

        self.file_type_checkbuttons = [] # Store references
        cols = 3 # Grid columns
        for i, (text, var) in enumerate(common_file_types):
            cb = ttk.Checkbutton(common_types_frame, text=text, variable=var)
            cb.grid(row=i // cols, column=i % cols, sticky=tk.W, padx=10, pady=2)
            self.file_type_checkbuttons.append(cb)

        ttk.Label(include_frame, text="Additional file types to include (comma separated, e.g. 'html,txt,md'):").pack(anchor=tk.W, pady=(15, 2))
        self.include_entry = ttk.Entry(include_frame, textvariable=self.custom_include, width=70)
        self.include_entry.pack(fill=tk.X, pady=(0, 5))

        # --- Exclude Frame ---
        exclude_frame = ttk.LabelFrame(self.file_types_tab, text="Exclude File Types (these are always excluded)", padding=10)
        exclude_frame.pack(fill=tk.X, expand=False, pady=10)

        ttk.Label(exclude_frame, text="File types to exclude (comma separated, e.g. 'jpg,png,pdf'):").pack(anchor=tk.W, pady=5)
        self.exclude_entry = ttk.Entry(exclude_frame, textvariable=self.custom_exclude, width=70)
        self.exclude_entry.pack(fill=tk.X, pady=5)

        # --- Help Text ---
        help_frame = ttk.LabelFrame(self.file_types_tab, text="How Filters Work", padding=10)
        help_frame.pack(fill=tk.X, expand=False, pady=10)

        help_text = ("• On the 'Main' tab, uncheck 'Process all files' to enable these filters.\n"
                     "• Included types: Check common types and/or add custom extensions.\n"
                     "• Excluded types: These extensions will *always* be skipped, even if listed in 'Include'.\n"
                     "• Enter extensions without the dot (e.g., 'py', not '.py').")
        ttk.Label(help_frame, text=help_text, justify=tk.LEFT).pack(anchor=tk.W)

        # Ensure initial state is set (though it's also called from __init__ after creation)
        # self.update_file_type_state() # Can be called here or after all widgets in __init__

    def update_file_type_state(self):
        """Update the state of the file type filter widgets based on the 'use_all_files' checkbox"""
        use_filters = not self.use_all_files.get()
        new_state = tk.NORMAL if use_filters else tk.DISABLED

        # Update the status label on the File Types tab
        if hasattr(self, 'file_type_status_label'): # Check if label exists
             if use_filters:
                 self.file_type_status_label.config(text="") # Clear message when enabled
             else:
                 self.file_type_status_label.config(text="Filters disabled (using 'Process all files' option on Main tab)")

        # Enable/disable Checkbuttons
        if hasattr(self, 'file_type_checkbuttons'):
            for cb in self.file_type_checkbuttons:
                 if cb.winfo_exists(): # Check if widget is valid
                    cb.config(state=new_state)

        # Enable/disable Entry fields
        if hasattr(self, 'include_entry') and self.include_entry.winfo_exists():
            self.include_entry.config(state=new_state)

        if hasattr(self, 'exclude_entry') and self.exclude_entry.winfo_exists():
            # Exclude entry might arguably remain enabled, but disabling is consistent
            self.exclude_entry.config(state=new_state)

        # Rebuild filter sets when state changes *to* using filters
        if use_filters:
            self._build_filter_sets()
        else:
            self._include_ext_set.clear()
            self._exclude_ext_set = self._parse_extensions(self.custom_exclude.get()) # Keep exclude list even if processing all files? Debatable, let's clear it for consistency.
            self._exclude_ext_set.clear() # Let's clear both for simplicity when "all files" is checked.


    def _parse_extensions(self, ext_string):
        """Helper to parse comma-separated extensions into a lowercase set."""
        if not ext_string:
            return set()
        return {ext.strip().lower().lstrip('.') for ext in ext_string.split(',') if ext.strip()}

    def _build_filter_sets(self):
        """Builds the internal sets of included and excluded extensions."""
        # Excluded types (always take precedence)
        self._exclude_ext_set = self._parse_extensions(self.custom_exclude.get())

        # Included types
        include_types = set()
        # Add checked common file types
        if self.include_php.get(): include_types.add("php")
        if self.include_py.get(): include_types.add("py")
        if self.include_xml.get(): include_types.add("xml")
        if self.include_js.get(): include_types.add("js")
        if self.include_css.get(): include_types.add("css")
        if self.include_yml.get(): include_types.update(["yml", "yaml"])
        if self.include_vcl.get(): include_types.add("vcl")

        # Add custom include types
        custom_includes = self._parse_extensions(self.custom_include.get())
        include_types.update(custom_includes)

        self._include_ext_set = include_types


    def browse_source(self):
        folder_path = filedialog.askdirectory(title="Select Source Folder", initialdir=Path.home())
        if folder_path:
            self.source_folder.set(folder_path)

    def browse_output(self):
        # Suggest a filename based on the source folder name if possible
        source_name = Path(self.source_folder.get()).name
        initial_filename = f"{source_name}_collected.txt" if source_name else "collected_files.txt"

        file_path = filedialog.asksaveasfilename(
            title="Save Output File As...",
            initialdir=Path.home(),
            initialfile=initial_filename,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.output_file.set(file_path)

    def should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed based on the file type filters"""
        if self.use_all_files.get():
            return True # Process all if checkbox is ticked

        # Get the file extension (lowercase, without the dot)
        # file_path.suffix handles cases like '.tar.gz' returning '.gz'
        ext = file_path.suffix[1:].lower() if file_path.suffix else ""
        if not ext: # No extension
             return False # Or decide if you want to include extensionless files

        # Check exclude list first (using the pre-built set)
        if ext in self._exclude_ext_set:
            return False

        # Check include list (using the pre-built set)
        # If include list is empty, arguably nothing should be included unless 'Process All' is checked
        if not self._include_ext_set:
             return False # No includes defined means include nothing

        return ext in self._include_ext_set


    def generate_file(self):
        source_str = self.source_folder.get()
        output_str = self.output_file.get()
        prompt = self.prompt_text_area.get("1.0", tk.END).strip()

        if not source_str:
            messagebox.showerror("Error", "Please select a source folder.", parent=self.root)
            return
        source_path = Path(source_str)
        if not source_path.is_dir():
            messagebox.showerror("Error", f"Source folder not found or is not a directory:\n{source_path}", parent=self.root)
            return

        if not output_str:
            messagebox.showerror("Error", "Please specify an output file path.", parent=self.root)
            return
        output_path = Path(output_str)

        # Basic check if output is inside source (can lead to infinite loops if not careful)
        try:
            if output_path.resolve().is_relative_to(source_path.resolve()):
                 if not messagebox.askyesno("Warning", "The output file is inside the source folder. This might cause issues if re-run.\nContinue anyway?", parent=self.root):
                     return
        except Exception: # Handle potential errors during path resolution
             pass

        # Disable button while running
        self.generate_button.config(state=tk.DISABLED)
        self.status_var.set("Starting collection...")
        self.progress_var.set(0)
        self.status_label.config(foreground="blue")

        # Rebuild filter sets just before starting, ensuring they reflect current UI state
        if not self.use_all_files.get():
            self._build_filter_sets()
        else:
            self._include_ext_set.clear()
            self._exclude_ext_set.clear() # Ensure exclude is also cleared if processing all


        # Start the file collection process in a separate thread
        threading.Thread(
            target=self.collect_files_thread,
            args=(source_path, output_path, prompt),
            daemon=True # Allows app to exit even if thread is running
        ).start()

    def collect_files_thread(self, source_path: Path, output_path: Path, prompt: str):
        try:
            self.status_var.set("Scanning folders and filtering files...")

            # Use pathlib's rglob for efficient recursive search
            # Note: This gets all files first, then filters. For *massive* directories,
            # walking might be slightly more memory efficient if filtering early.
            # But rglob is often cleaner and faster for typical projects.
            all_files = list(source_path.rglob("*.*")) # Get all files first
            # Filter based on `should_process_file`
            files_to_process = [p for p in all_files if p.is_file() and self.should_process_file(p)]

            total_files = len(files_to_process)

            if total_files == 0:
                # Schedule GUI update from the main thread
                self.root.after(0, lambda: messagebox.showwarning(
                    "No Files Found",
                    "No files matching the criteria were found in the source folder.\n"
                    "Please check the folder contents and your file type filters.",
                    parent=self.root
                ))
                self.status_var.set("Ready (No matching files)")
                self.root.after(0, lambda: self.generate_button.config(state=tk.NORMAL)) # Re-enable button
                return

            processed_files = 0
            encodings_to_try = ['utf-8', 'latin-1', 'cp1252'] # Common text encodings

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as out_file:
                # --- Write Header ---
                out_file.write(f"Source Folder: {source_path.resolve()}\n")
                if prompt:
                    out_file.write(f"Task Prompt:\n---\n{prompt}\n---\n\n")
                else:
                    out_file.write("Task Prompt: (Not provided)\n\n")
                out_file.write("Collected Files:\n")
                out_file.write("=" * 80 + "\n\n")

                # --- Write Files ---
                for file_path in files_to_process:
                    relative_path = file_path.relative_to(source_path)
                    self.status_var.set(f"Processing: {relative_path}")

                    file_ext = file_path.suffix[1:].lower() if file_path.suffix else "unknown"

                    out_file.write(f"==== FILE: {relative_path} [{file_ext}] ====\n\n")

                    content = None
                    error_msg = None
                    for enc in encodings_to_try:
                        try:
                            with open(file_path, 'r', encoding=enc) as f:
                                content = f.read()
                            # If successful, break the encoding loop
                            break
                        except UnicodeDecodeError:
                            error_msg = f"[Read Error: Failed to decode with {enc}]"
                            continue # Try next encoding
                        except Exception as e:
                            error_msg = f"[Read Error: {type(e).__name__} - {e}]"
                            # Stop trying encodings if a different error occurs (e.g., permissions)
                            break

                    if content is not None:
                        out_file.write(content)
                    elif error_msg:
                         out_file.write(error_msg + "\n")
                    else:
                         # This case should ideally not happen if encodings_to_try is not empty
                         out_file.write("[Read Error: Unknown issue reading file]\n")

                    out_file.write("\n\n" + "=" * 80 + "\n\n")

                    # --- Update Progress ---
                    processed_files += 1
                    progress_percentage = (processed_files / total_files) * 100
                    # Update GUI thread-safely via the Tkinter variable
                    self.progress_var.set(progress_percentage)
                    # No need for time.sleep(), variable updates trigger GUI refresh

            # --- Final Status Update (Scheduled for GUI thread) ---
            final_message = (f"File collection complete!\n\n"
                             f"Processed {processed_files} files.\n"
                             f"Output saved to:\n{output_path.resolve()}")
            self.root.after(0, lambda: messagebox.showinfo("Success", final_message, parent=self.root))
            self.status_var.set("Ready")
            self.status_label.config(foreground="green") # Indicate success visually


        except Exception as e:
            # Log the full traceback for debugging
            print("--- ERROR DURING FILE COLLECTION ---")
            traceback.print_exc()
            print("------------------------------------")
            # Show error message in GUI (scheduled for GUI thread)
            error_details = f"An error occurred during file collection:\n\n{type(e).__name__}: {e}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_details, parent=self.root))
            self.status_var.set("Error occurred (See console for details)")
            self.status_label.config(foreground="red")

        finally:
             # Ensure the button is re-enabled in the GUI thread, regardless of success/failure
             self.root.after(0, lambda: self.generate_button.config(state=tk.NORMAL))


if __name__ == "__main__":
    root = tk.Tk()

    # Apply a more modern theme if available
    style = ttk.Style()
    available_themes = style.theme_names()
    # Prefer modern themes if available
    if 'clam' in available_themes:
        style.theme_use('clam')
    elif 'vista' in available_themes: # Windows
        style.theme_use('vista')
    elif 'aqua' in available_themes: # macOS
         style.theme_use('aqua')

    # Configure styles for better appearance (optional)
    style.configure('TButton', font=('Segoe UI', 10), padding=5)
    style.configure('TLabel', font=('Segoe UI', 10))
    style.configure('TEntry', font=('Segoe UI', 10), padding=3)
    style.configure('TCheckbutton', font=('Segoe UI', 10))
    style.configure('TFrame', background=style.lookup('TFrame', 'background')) # Ensure frame bg matches theme
    style.configure('TLabelframe', font=('Segoe UI', 10, 'bold'), padding=10)
    style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
    style.configure('TNotebook.Tab', font=('Segoe UI', 10), padding=[10, 5])

    app = FileCollectorApp(root)
    root.mainloop()