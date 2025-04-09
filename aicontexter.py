import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import traceback # For detailed error logging
from pathlib import Path # Modern way to handle file paths

class FileCollectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Collector")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        self.source_folder = tk.StringVar()
        self.output_file = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready")

        # If True, filters on the "File Types" tab are ignored.
        self.use_all_files = tk.BooleanVar(value=True)

        # Checkboxes for common file types (initial state less important when use_all_files=True)
        self.include_php = tk.BooleanVar(value=False)
        self.include_py = tk.BooleanVar(value=True)
        self.include_xml = tk.BooleanVar(value=False)
        self.include_js = tk.BooleanVar(value=True)
        self.include_css = tk.BooleanVar(value=True)
        self.include_yml = tk.BooleanVar(value=False)
        self.include_vcl = tk.BooleanVar(value=False)

        # User-defined include/exclude extensions
        self.custom_include = tk.StringVar()
        # Start with a sensible list of common binary, archive, and metadata files to exclude.
        self.custom_exclude = tk.StringVar(value="png,jpg,jpeg,gif,webp,ico,pdf,zip,rar,exe,dll,obj,bin,svg,woff,woff2,ttf,eot,gz,tar,bz2,7z,mp3,mp4,mov,avi,doc,docx,xls,xlsx,ppt,pptx,iso,img,ds_store")

        # Internal sets for efficient filtering, populated by _build_filter_sets
        self._include_ext_set = set()
        self._exclude_ext_set = set()

        self.create_widgets()
        # Ensure the UI state matches the initial variable values after widgets are created.
        self.update_file_type_state()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.main_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.main_tab, text="Main")

        self.file_types_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.file_types_tab, text="File Types")

        self.create_main_tab()
        self.create_file_types_tab()

    def create_main_tab(self):
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
             # Ensure prompt description wraps nicely within the frame.
            wraplength=700, justify=tk.LEFT
        )
        desc_label.pack(anchor=tk.W, pady=(5, 0))

        source_frame = ttk.Frame(self.main_tab)
        source_frame.pack(fill=tk.X, pady=10)
        ttk.Label(source_frame, text="Source Folder:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(source_frame, textvariable=self.source_folder, width=60).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(source_frame, text="Browse...", command=self.browse_source).pack(side=tk.LEFT)

        output_frame = ttk.Frame(self.main_tab)
        output_frame.pack(fill=tk.X, pady=10)
        ttk.Label(output_frame, text="Output File:").pack(side=tk.LEFT, padx=(0, 16))
        ttk.Entry(output_frame, textvariable=self.output_file, width=60).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(output_frame, text="Browse...", command=self.browse_output).pack(side=tk.LEFT)

        file_type_frame = ttk.LabelFrame(self.main_tab, text="File Types", padding=10)
        file_type_frame.pack(fill=tk.X, expand=False, pady=10)

        # This checkbox controls whether the detailed filters on the "File Types" tab are used.
        self.process_all_files_cb = ttk.Checkbutton(
            file_type_frame,
            text="Process all files (ignore filters on 'File Types' tab)",
            variable=self.use_all_files,
            # Update the enabled/disabled state of the other tab when this changes.
            command=self.update_file_type_state
        )
        self.process_all_files_cb.pack(anchor=tk.W)

        ttk.Label(
            file_type_frame,
            text="Uncheck the box above to enable and configure specific file type filters on the 'File Types' tab."
        ).pack(anchor=tk.W, pady=(5, 0))

        progress_status_frame = ttk.Frame(self.main_tab)
        progress_status_frame.pack(fill=tk.X, pady=(15, 5))

        ttk.Label(progress_status_frame, text="Progress:").pack(side=tk.LEFT)
        self.progress_bar = ttk.Progressbar(progress_status_frame, variable=self.progress_var, length=400, mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        status_frame = ttk.Frame(self.main_tab)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground="blue", anchor=tk.W)
        self.status_label.pack(fill=tk.X)

        self.generate_button = ttk.Button(self.main_tab, text="Generate Combined File", command=self.generate_file)
        self.generate_button.pack(pady=20)

    def create_file_types_tab(self):
        # Display a message indicating if these filters are currently active or not.
        self.file_type_status_label = ttk.Label(
            self.file_types_tab, text="", foreground="darkorange",
            font=("Helvetica", 10, "italic")
        )
        self.file_type_status_label.pack(anchor=tk.W, pady=(0, 10))

        include_frame = ttk.LabelFrame(self.file_types_tab, text="Include File Types", padding=10)
        include_frame.pack(fill=tk.X, expand=False, pady=5)

        common_types_frame = ttk.Frame(include_frame)
        common_types_frame.pack(fill=tk.X, pady=5)

        common_file_types = [
            ("PHP (*.php)", self.include_php), ("Python (*.py)", self.include_py),
            ("XML (*.xml)", self.include_xml), ("JavaScript (*.js)", self.include_js),
            ("CSS (*.css)", self.include_css), ("YAML (*.yml, *.yaml)", self.include_yml),
            ("VCL (*.vcl)", self.include_vcl)
        ]

        self.file_type_checkbuttons = [] # Keep references to easily enable/disable them later
        cols = 3
        for i, (text, var) in enumerate(common_file_types):
            cb = ttk.Checkbutton(common_types_frame, text=text, variable=var)
            cb.grid(row=i // cols, column=i % cols, sticky=tk.W, padx=10, pady=2)
            self.file_type_checkbuttons.append(cb)

        ttk.Label(include_frame, text="Additional file types to include (comma separated, e.g. 'html,txt,md'):").pack(anchor=tk.W, pady=(15, 2))
        self.include_entry = ttk.Entry(include_frame, textvariable=self.custom_include, width=70)
        self.include_entry.pack(fill=tk.X, pady=(0, 5))

        exclude_frame = ttk.LabelFrame(self.file_types_tab, text="Exclude File Types (these are always excluded)", padding=10)
        exclude_frame.pack(fill=tk.X, expand=False, pady=10)

        ttk.Label(exclude_frame, text="File types to exclude (comma separated, e.g. 'jpg,png,pdf'):").pack(anchor=tk.W, pady=5)
        self.exclude_entry = ttk.Entry(exclude_frame, textvariable=self.custom_exclude, width=70)
        self.exclude_entry.pack(fill=tk.X, pady=5)

        help_frame = ttk.LabelFrame(self.file_types_tab, text="How Filters Work", padding=10)
        help_frame.pack(fill=tk.X, expand=False, pady=10)

        # Provide clear instructions on how the filtering options interact.
        help_text = ("• On the 'Main' tab, uncheck 'Process all files' to enable these filters.\n"
                     "• Included types: Check common types and/or add custom extensions.\n"
                     "• Excluded types: These extensions will *always* be skipped, even if listed in 'Include'.\n"
                     "• Enter extensions without the dot (e.g., 'py', not '.py').\n"
                     "• Files without extensions (like 'Dockerfile') are included only if 'Process all files' is checked (and they aren't explicitly excluded).")
        ttk.Label(help_frame, text=help_text, justify=tk.LEFT).pack(anchor=tk.W)

    def update_file_type_state(self):
        """Enable or disable the file type filter widgets based on the 'use_all_files' checkbox."""
        use_filters = not self.use_all_files.get()
        new_state = tk.NORMAL if use_filters else tk.DISABLED

        # Update the status label on the File Types tab to reflect the current state.
        if hasattr(self, 'file_type_status_label'): # Check widget exists
             if use_filters:
                 self.file_type_status_label.config(text="")
             else:
                 self.file_type_status_label.config(text="Filters disabled (using 'Process all files' option on Main tab)")

        # Enable/disable the individual filter widgets.
        if hasattr(self, 'file_type_checkbuttons'):
            for cb in self.file_type_checkbuttons:
                 if cb.winfo_exists():
                    cb.config(state=new_state)
        if hasattr(self, 'include_entry') and self.include_entry.winfo_exists():
            self.include_entry.config(state=new_state)
        if hasattr(self, 'exclude_entry') and self.exclude_entry.winfo_exists():
            self.exclude_entry.config(state=new_state)

        # Rebuild the internal filter sets to match the current UI state.
        # The exclude set is always needed, include set only matters if filters are active.
        self._build_filter_sets()

    def _parse_extensions(self, ext_string):
        """Convert a comma-separated string of extensions into a lowercase set, removing dots."""
        if not ext_string:
            return set()
        return {ext.strip().lower().lstrip('.') for ext in ext_string.split(',') if ext.strip()}

    def _build_filter_sets(self):
        """Update the internal sets of included and excluded extensions based on UI."""
        # Always parse the exclude list from the UI.
        self._exclude_ext_set = self._parse_extensions(self.custom_exclude.get())
        # Force-add .DS_Store to ensure it's always ignored, regardless of user input.
        self._exclude_ext_set.add("ds_store")

        # Only build the include set if the filters are actually enabled.
        if not self.use_all_files.get():
            include_types = set()
            if self.include_php.get(): include_types.add("php")
            if self.include_py.get(): include_types.add("py")
            if self.include_xml.get(): include_types.add("xml")
            if self.include_js.get(): include_types.add("js")
            if self.include_css.get(): include_types.add("css")
            if self.include_yml.get(): include_types.update(["yml", "yaml"])
            if self.include_vcl.get(): include_types.add("vcl")

            custom_includes = self._parse_extensions(self.custom_include.get())
            include_types.update(custom_includes)
            self._include_ext_set = include_types
        else:
             # If processing all files, the include set is irrelevant.
             self._include_ext_set.clear()

    def browse_source(self):
        folder_path = filedialog.askdirectory(title="Select Source Folder", initialdir=Path.home())
        if folder_path:
            self.source_folder.set(folder_path)

    def browse_output(self):
        # Suggest a reasonable output filename based on the source folder's name.
        source_name = Path(self.source_folder.get()).name
        initial_filename = f"{source_name}_collected.txt" if source_name else "collected_files.txt"

        file_path = filedialog.asksaveasfilename(
            title="Save Output File As...",
            initialdir=Path.home(), initialfile=initial_filename,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.output_file.set(file_path)

    def should_process_file(self, file_path: Path) -> bool:
        """Check if a given file should be included in the output based on current settings."""
        ext_lower = file_path.suffix[1:].lower() if file_path.suffix else ""

        # --- RULE 1: Always check the exclude list first. ---
        # This applies whether "Process all files" is checked or not.
        if ext_lower in self._exclude_ext_set:
            return False
        # Also exclude extensionless files if they match an "exclude" rule (e.g., user added 'LICENSE' to exclude)
        # Note: This requires the user to add the *exact* filename without extension to the exclude list.
        if not ext_lower and file_path.name in self._exclude_ext_set:
             return False

        # --- RULE 2: If "Process all files" is checked, include everything not excluded above. ---
        if self.use_all_files.get():
            return True # It wasn't excluded, so include it.

        # --- RULE 3: Filters are active ("Process all files" is unchecked). ---
        # Skip files without extensions when filters are active.
        if not ext_lower:
             return False

        # If the include list is empty, nothing passes the filter (except when "Process all" is on).
        if not self._include_ext_set:
             return False

        # Include the file only if its extension is in the specific include list.
        return ext_lower in self._include_ext_set


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

        # Safety check: Prevent selecting the output file *inside* the source directory,
        # as this could lead to infinite loops or unexpected behavior on re-runs.
        try:
            resolved_output = output_path.resolve()
            resolved_source = source_path.resolve()
            if resolved_output == resolved_source or resolved_output.is_relative_to(resolved_source):
                 if not messagebox.askyesno("Warning", "The output file is inside the source folder. This could lead to processing the output file itself on subsequent runs.\n\nContinue anyway?", parent=self.root, icon='warning'):
                     return
        except OSError as e:
             # This might happen if paths are invalid or permissions are wrong. Warn but continue.
             print(f"Warning: Could not resolve paths for safety check - {e}")
        except Exception as e:
             print(f"Warning: Could not perform output/source path check - {e}")

        self.generate_button.config(state=tk.DISABLED)
        self.status_var.set("Starting collection...")
        self.progress_var.set(0)
        self.status_label.config(foreground="blue")

        # Ensure filter sets are up-to-date before starting the thread.
        self._build_filter_sets()

        # Run the potentially long file operation in a background thread to keep the UI responsive.
        threading.Thread(
            target=self.collect_files_thread,
            args=(source_path, output_path, prompt),
            daemon=True # Allows the app to exit even if this thread hangs.
        ).start()

    def collect_files_thread(self, source_path: Path, output_path: Path, prompt: str):
        try:
            self.status_var.set("Scanning folders...")

            # Use rglob("*") to find EVERYTHING recursively (files, dirs, links, etc.).
            # We'll filter down to just the files we want next.
            all_potential_items = source_path.rglob("*")

            self.status_var.set("Filtering files...")
            files_to_process = []
            # Resolve the output path once to efficiently check against it later.
            resolved_output_path = None
            try:
                resolved_output_path = output_path.resolve()
            except Exception: # Handle cases where output might not exist yet or other errors.
                pass

            # Iterate through all found items and keep only the files that match our criteria.
            for item_path in all_potential_items:
                # Important: Skip processing the output file itself if it's inside the source.
                if resolved_output_path and item_path.resolve() == resolved_output_path:
                    continue

                # Check if it's a file and passes the include/exclude rules.
                if item_path.is_file() and self.should_process_file(item_path):
                    files_to_process.append(item_path)

            total_files = len(files_to_process)

            if total_files == 0:
                # Inform the user via the main thread's event loop.
                self.root.after(0, lambda: messagebox.showwarning(
                    "No Files Found",
                    "No files matching the criteria were found in the source folder.\n"
                    "Please check the folder contents and your file type filters (including excludes).",
                    parent=self.root
                ))
                self.status_var.set("Ready (No matching files)")
                self.root.after(0, lambda: self.generate_button.config(state=tk.NORMAL))
                return

            processed_files = 0
            # Attempt common text encodings. Add more if needed for specific project files.
            encodings_to_try = ['utf-8', 'latin-1', 'cp1252']

            # Make sure the directory for the output file exists.
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Open the output file; use 'replace' for encoding errors during writing (less likely but safe).
            with open(output_path, 'w', encoding='utf-8', errors='replace') as out_file:
                out_file.write(f"Source Folder: {source_path.resolve()}\n")
                if prompt:
                    out_file.write(f"Task Prompt:\n---\n{prompt}\n---\n\n")
                else:
                    out_file.write("Task Prompt: (Not provided)\n\n")
                out_file.write(f"Collected {total_files} files matching criteria:\n")
                out_file.write("=" * 80 + "\n\n")

                for file_path in files_to_process:
                    relative_path = file_path.relative_to(source_path)
                    self.status_var.set(f"Processing ({processed_files+1}/{total_files}): {relative_path}")

                    file_ext_display = file_path.suffix[1:].lower() if file_path.suffix else "no extension"
                    out_file.write(f"==== FILE: {relative_path} [{file_ext_display}] ====\n\n")

                    content = None
                    error_msg = None
                    processed_successfully = False
                    try:
                        # Try reading the file using different encodings.
                        read_error = None
                        for enc in encodings_to_try:
                            try:
                                with open(file_path, 'r', encoding=enc) as f:
                                    content = f.read()
                                processed_successfully = True
                                break # Found a working encoding.
                            except UnicodeDecodeError:
                                read_error = f"Failed to decode with {enc}"
                                continue # Try the next encoding.
                            except Exception as e:
                                # Catch other file read issues (e.g., permissions).
                                read_error = f"{type(e).__name__} - {e}"
                                break # No point trying other encodings for this type of error.

                        if not processed_successfully:
                            error_msg = f"[Read Error: Could not read file as text ({read_error or 'Unknown text read issue'})]"

                    except Exception as e:
                         # Catch errors happening even before trying to open/read.
                         error_msg = f"[Read Error: Pre-open error - {type(e).__name__} - {e}]"

                    if content is not None:
                        out_file.write(content)
                    elif error_msg:
                         out_file.write(error_msg + "\n")
                    else:
                         out_file.write("[Read Error: Unknown issue reading file]\n") # Should be rare.

                    out_file.write("\n\n" + "=" * 80 + "\n\n")

                    processed_files += 1
                    progress_percentage = (processed_files / total_files) * 100
                    # Update the progress bar via the Tkinter variable (thread-safe).
                    self.progress_var.set(progress_percentage)

            # Report success back to the user on the main GUI thread.
            final_message = (f"File collection complete!\n\n"
                             f"Processed {processed_files} files.\n"
                             f"Output saved to:\n{output_path.resolve()}")
            self.root.after(0, lambda: messagebox.showinfo("Success", final_message, parent=self.root))
            self.status_var.set(f"Ready (Completed: {processed_files} files)")
            self.status_label.config(foreground="green")

        except Exception as e:
            # Log the full error details for debugging.
            print("--- ERROR DURING FILE COLLECTION ---")
            traceback.print_exc()
            print("------------------------------------")
            # Show a user-friendly error message on the main GUI thread.
            error_details = f"An error occurred during file collection:\n\n{type(e).__name__}: {e}\n\n(Check console output for more details)"
            self.root.after(0, lambda: messagebox.showerror("Error", error_details, parent=self.root))
            self.status_var.set("Error occurred (See console for details)")
            self.status_label.config(foreground="red")

        finally:
             # Crucial: Always re-enable the button on the main thread, whether success or error.
             self.root.after(0, lambda: self.generate_button.config(state=tk.NORMAL))


if __name__ == "__main__":
    root = tk.Tk()

    # Try to apply a more modern theme if available on the system.
    style = ttk.Style()
    available_themes = style.theme_names()
    if 'clam' in available_themes: style.theme_use('clam')
    elif 'vista' in available_themes: style.theme_use('vista')
    elif 'aqua' in available_themes: style.theme_use('aqua')

    # Use a common modern font like Segoe UI if available, otherwise fall back.
    default_font_family = 'Segoe UI'
    default_font_size = 10
    try:
        import tkinter.font
        # Check if the font exists to avoid errors.
        tkinter.font.Font(family=default_font_family, size=default_font_size)
        default_font = (default_font_family, default_font_size)
    except tk.TclError:
        default_font = (None, default_font_size) # Use system default font family.

    # Apply some basic styling for consistency.
    style.configure('TButton', font=default_font, padding=5)
    style.configure('TLabel', font=default_font)
    style.configure('TEntry', font=default_font, padding=3)
    style.configure('TCheckbutton', font=default_font)
    style.configure('TFrame', background=style.lookup('TFrame', 'background'))
    style.configure('TLabelframe', font=(default_font[0], default_font[1], 'bold'), padding=10)
    style.configure('TLabelframe.Label', font=(default_font[0], default_font[1], 'bold'))
    style.configure('TNotebook.Tab', font=default_font, padding=[10, 5])

    app = FileCollectorApp(root)
    root.mainloop()
