import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import traceback # For detailed error logging
from pathlib import Path

# Define directories to always skip during traversal
DEFAULT_SKIP_DIRS = {'.git', '__pycache__', '.svn', '.hg', '.vscode', '.idea', 'node_modules'} # Added node_modules

# Define file extensions/names to always exclude by default in the UI
DEFAULT_EXCLUDE_ENTRIES = ( # Renamed for clarity (includes names and extensions)
    # Binary/Archives/Media
    "png,jpg,jpeg,gif,webp,ico,pdf,zip,rar,exe,dll,obj,o,so,a,lib,"
    "bin,svg,woff,woff2,ttf,eot,otf,gz,tar,bz2,7z,"
    "mp3,mp4,mov,avi,mkv,flv,wmv,"
    "doc,docx,xls,xlsx,ppt,pptx,odt,ods,odp,"
    "iso,img,dmg,"
    "pyc,pyo,class,"
    # Databases
    "sqlite,sqlite3,db,db3,mdb,accdb,sqlitedb,"
    # Metadata/OS specific - ensure names are lowercase
    "ds_store,thumbs.db,"
    # Common lock files
    "lock, yarn.lock, package-lock.json" # Added common lock files
)


class FileCollectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Collector")
        self.root.geometry("800x650")
        self.root.resizable(True, True)

        self.source_folder = tk.StringVar()
        self.output_file = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready")

        self.use_all_files = tk.BooleanVar(value=True)

        self.include_php = tk.BooleanVar(value=False)
        self.include_py = tk.BooleanVar(value=True)
        self.include_xml = tk.BooleanVar(value=False)
        self.include_js = tk.BooleanVar(value=True)
        self.include_css = tk.BooleanVar(value=True)
        self.include_yml = tk.BooleanVar(value=False)
        self.include_vcl = tk.BooleanVar(value=False)

        self.custom_include = tk.StringVar()
        self.custom_exclude = tk.StringVar(value=DEFAULT_EXCLUDE_ENTRIES)

        self._include_ext_set = set()
        self._exclude_entry_set = set() # Renamed for clarity

        self.create_widgets()
        self.update_file_type_state() # Ensure UI state matches initial vars

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
            yscrollcommand=prompt_scrollbar.set, undo=True,
            font=default_font # Apply font
        )
        prompt_scrollbar.config(command=self.prompt_text_area.yview)
        prompt_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.prompt_text_area.pack(fill=tk.BOTH, expand=True)

        desc_label = ttk.Label(
            prompt_frame,
            text="Enter a description of your task here. This will be included at the beginning of the output file.",
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

        self.process_all_files_cb = ttk.Checkbutton(
            file_type_frame,
            text="Process all text files (ignore 'Include' filters, still apply 'Exclude' filters)",
            variable=self.use_all_files,
            command=self.update_file_type_state
        )
        self.process_all_files_cb.pack(anchor=tk.W)

        ttk.Label(
            file_type_frame,
            text="Uncheck the box above to use specific 'Include' filters. 'Exclude' filters on the next tab always apply."
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
        self.file_type_status_label = ttk.Label(
            self.file_types_tab, text="", foreground="darkorange",
            font=(default_font_family, default_font_size, "italic") # Use defined font
        )
        self.file_type_status_label.pack(anchor=tk.W, pady=(0, 10))

        include_frame = ttk.LabelFrame(self.file_types_tab, text="Include File Types (Only used if 'Process all text files' is UNCHECKED)", padding=10)
        include_frame.pack(fill=tk.X, expand=False, pady=5)

        common_types_frame = ttk.Frame(include_frame)
        common_types_frame.pack(fill=tk.X, pady=5)

        common_file_types = [
            ("PHP (*.php)", self.include_php), ("Python (*.py)", self.include_py),
            ("XML (*.xml)", self.include_xml), ("JavaScript (*.js)", self.include_js),
            ("CSS (*.css)", self.include_css), ("YAML (*.yml, *.yaml)", self.include_yml),
            ("VCL (*.vcl)", self.include_vcl)
        ]

        self.file_type_checkbuttons = []
        cols = 3
        for i, (text, var) in enumerate(common_file_types):
            cb = ttk.Checkbutton(common_types_frame, text=text, variable=var)
            cb.grid(row=i // cols, column=i % cols, sticky=tk.W, padx=10, pady=2)
            self.file_type_checkbuttons.append(cb)

        ttk.Label(include_frame, text="Additional file types to include (comma separated, e.g. 'html,txt,md'):").pack(anchor=tk.W, pady=(15, 2))
        self.include_entry = ttk.Entry(include_frame, textvariable=self.custom_include, width=70)
        self.include_entry.pack(fill=tk.X, pady=(0, 5))

        exclude_frame = ttk.LabelFrame(self.file_types_tab, text="Exclude File Types & Names (These are ALWAYS excluded)", padding=10)
        exclude_frame.pack(fill=tk.X, expand=False, pady=10)

        ttk.Label(exclude_frame, text=f"Comma separated list (e.g. 'jpg,png,pdf,LICENSE'). Also skips directories like {', '.join(sorted(DEFAULT_SKIP_DIRS))}.").pack(anchor=tk.W, pady=5)
        exclude_scrollbar_y = ttk.Scrollbar(exclude_frame, orient=tk.VERTICAL)
        exclude_scrollbar_x = ttk.Scrollbar(exclude_frame, orient=tk.HORIZONTAL)
        self.exclude_text_area = tk.Text(
            exclude_frame, height=4, width=70, wrap=tk.NONE,
            yscrollcommand=exclude_scrollbar_y.set,
            xscrollcommand=exclude_scrollbar_x.set,
            undo=True,
            font=default_font # Apply font
        )
        self.exclude_text_area.insert(tk.END, self.custom_exclude.get())
        self.exclude_text_area.bind("<<Modified>>", self._update_custom_exclude_var)

        exclude_scrollbar_y.config(command=self.exclude_text_area.yview)
        exclude_scrollbar_x.config(command=self.exclude_text_area.xview)
        exclude_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        exclude_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.exclude_text_area.pack(fill=tk.BOTH, expand=True, pady=5)
        self.exclude_text_area.edit_modified(False)

        help_frame = ttk.LabelFrame(self.file_types_tab, text="How Filters Work", padding=10)
        help_frame.pack(fill=tk.X, expand=False, pady=10)

        help_text = ("• On the 'Main' tab:\n"
                     "  - CHECK 'Process all text files' to include most text files (respecting Excludes).\n"
                     "  - UNCHECK it to use the specific 'Include' filters below (still respecting Excludes).\n"
                     "• Included types (tab): Only used when 'Process all text files' is UNCHECKED.\n"
                     "• Excluded types/names (tab): These files/extensions are *always* skipped.\n"
                     f"• Hidden/system directories ({', '.join(sorted(DEFAULT_SKIP_DIRS))}, etc.) are always skipped.\n"
                     "• Enter extensions without the dot (e.g., 'py'). Enter full names for specific files (e.g., 'LICENSE', '.env').\n"
                     "• Files without extensions are included only if 'Process all text files' is checked (and they aren't explicitly excluded by name).")
        ttk.Label(help_frame, text=help_text, justify=tk.LEFT).pack(anchor=tk.W)

    def _update_custom_exclude_var(self, event=None):
        """Update the custom_exclude StringVar when the Text widget changes."""
        if hasattr(self, 'exclude_text_area') and self.exclude_text_area.edit_modified():
             current_text = self.exclude_text_area.get("1.0", tk.END).strip()
             self.custom_exclude.set(current_text)
             self.exclude_text_area.edit_modified(False)
             # Rebuild filters immediately when exclude changes
             self._build_filter_sets()


    def update_file_type_state(self):
        """Enable or disable the file type filter widgets based on the 'use_all_files' checkbox."""
        use_specific_includes = not self.use_all_files.get()
        include_state = tk.NORMAL if use_specific_includes else tk.DISABLED
        exclude_state = tk.NORMAL # Exclude widget is always active

        if hasattr(self, 'file_type_status_label'):
             if use_specific_includes:
                 self.file_type_status_label.config(text="Using specific 'Include' filters below (and 'Exclude' filters).")
             else:
                 self.file_type_status_label.config(text="Ignoring 'Include' filters (using 'Process all text files' option). 'Exclude' filters still apply.")

        if hasattr(self, 'file_type_checkbuttons'):
            for cb in self.file_type_checkbuttons:
                 if cb.winfo_exists():
                    cb.config(state=include_state)
        if hasattr(self, 'include_entry') and self.include_entry.winfo_exists():
            self.include_entry.config(state=include_state)
        if hasattr(self, 'exclude_text_area') and self.exclude_text_area.winfo_exists():
             self.exclude_text_area.config(state=exclude_state) # Ensure exclude text is always editable

        self._build_filter_sets() # Rebuild filters whenever state changes

    def _parse_filter_entries(self, entry_string):
        """Convert a comma-separated string of names/extensions into a lowercase set."""
        if not entry_string:
            return set()
        parsed = set()
        for item in entry_string.split(','):
            cleaned_item = item.strip().lower()
            if cleaned_item:
                 # Store entries exactly as cleaned (e.g., 'ds_store', 'py', 'license', '.env')
                 parsed.add(cleaned_item)
        return parsed


    def _build_filter_sets(self):
        """Update the internal sets of included and excluded entries based on UI."""
        # Build exclude set from the text area (via the StringVar)
        self._exclude_entry_set = self._parse_filter_entries(self.custom_exclude.get())
        # Ensure core OS/Metadata files are always excluded, case-insensitively
        self._exclude_entry_set.update(["ds_store", "thumbs.db"]) # Add specific names known to cause issues

        # Build include set ONLY if specific filters are enabled
        if not self.use_all_files.get():
            include_types = set()
            if self.include_php.get(): include_types.add("php")
            if self.include_py.get(): include_types.add("py")
            if self.include_xml.get(): include_types.add("xml")
            if self.include_js.get(): include_types.add("js")
            if self.include_css.get(): include_types.add("css")
            if self.include_yml.get(): include_types.update(["yml", "yaml"])
            if self.include_vcl.get(): include_types.add("vcl")

            custom_includes = self._parse_filter_entries(self.custom_include.get())
            # Only add extensions from custom includes, not full names
            include_types.update(inc for inc in custom_includes if not os.path.sep in inc and '.' not in inc) # Basic check for extension format
            self._include_ext_set = {ext.lstrip('.') for ext in include_types} # Ensure no leading dots in include set
        else:
             self._include_ext_set.clear()


    def browse_source(self):
        folder_path = filedialog.askdirectory(title="Select Source Folder", initialdir=Path.home())
        if folder_path:
            self.source_folder.set(folder_path)

    def browse_output(self):
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
        """Check if a given file should be included based on exclusion/inclusion rules."""
        file_name_lower = file_path.name.lower()
        # Get extension without dot, or empty string if no extension
        extension_lower = file_path.suffix[1:].lower() if file_path.suffix else ""

        # --- RULE 1: Check Exclusions ---
        # Check if the full filename (lowercase) is explicitly excluded
        if file_name_lower in self._exclude_entry_set:
            # print(f"Excluding '{file_path.name}' based on full name match in exclude set.")
            return False
        # Check if the extension (lowercase, no dot) is explicitly excluded
        if extension_lower and extension_lower in self._exclude_entry_set:
            # print(f"Excluding '{file_path.name}' based on extension '.{extension_lower}' in exclude set.")
            return False

        # --- RULE 2: "Process All Text Files" Mode ---
        if self.use_all_files.get():
            # Include if it wasn't excluded above
            # print(f"Including '{file_path.name}' (Process All Text Files mode).")
            return True

        # --- RULE 3: Specific Include Filters Mode ---
        # In this mode, files MUST have an extension...
        if not extension_lower:
             # print(f"Excluding '{file_path.name}' (no extension in Specific Include mode).")
             return False
        # ...and that extension must be in the include set.
        # The include set (_include_ext_set) is guaranteed to not have leading dots by _build_filter_sets
        if extension_lower in self._include_ext_set:
             # print(f"Including '{file_path.name}' based on extension '.{extension_lower}' in include list.")
             return True
        else:
             # print(f"Excluding '{file_path.name}' (extension '.{extension_lower}' not in include list).")
             return False


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

        # Safety check: Prevent output inside source
        try:
            resolved_output = output_path.resolve()
            resolved_source = source_path.resolve()
            # Use is_relative_to for robust check across OS/mount points if possible
            # Add explicit check for equality too
            if resolved_output == resolved_source or resolved_output.is_relative_to(resolved_source):
                 if not messagebox.askyesno("Warning", "The output file is inside the source folder. This could lead to processing the output file itself on subsequent runs.\n\nContinue anyway?", parent=self.root, icon='warning'):
                     return
        except (OSError, ValueError) as e: # Catch resolution errors or ValueError from is_relative_to (e.g. different drives)
             print(f"Warning: Could not perform output/source path check - {e}")


        self.generate_button.config(state=tk.DISABLED)
        self.status_var.set("Starting collection...")
        self.progress_var.set(0)
        self.status_label.config(foreground="blue")

        # Ensure filter sets are up-to-date before starting thread
        # Force update from text area in case user didn't trigger the <<Modified>> event
        self._update_custom_exclude_var()
        self._build_filter_sets()

        threading.Thread(
            target=self.collect_files_thread,
            args=(source_path, output_path, prompt),
            daemon=True
        ).start()

    def collect_files_thread(self, source_path: Path, output_path: Path, prompt: str):
        try:
            self.status_var.set("Scanning folders...")
            files_to_process = []
            resolved_output_path = None
            try:
                # Resolve needs the file to potentially exist, use absolute() as fallback
                resolved_output_path = output_path.resolve() if output_path.exists() else output_path.absolute()
            except Exception as e:
                 print(f"Warning: Could not resolve output path '{output_path}' for self-check: {e}")
                 resolved_output_path = output_path.absolute()

            skipped_dirs_count = 0
            processed_dirs_count = 0
            # Use os.walk for efficient directory skipping
            for root, dirs, files in os.walk(source_path, topdown=True):
                processed_dirs_count += 1
                current_root_path = Path(root)

                # Modify dirs in-place to prevent os.walk from descending into them
                original_dir_count = len(dirs)
                dirs[:] = [d for d in dirs if d.lower() not in DEFAULT_SKIP_DIRS]
                skipped_dirs_count += (original_dir_count - len(dirs))

                for filename in files:
                    file_path = current_root_path / filename
                    try:
                        # Check for output file collision
                        # Use absolute paths for comparison if resolve fails or paths are tricky
                        if resolved_output_path and file_path.absolute() == resolved_output_path:
                            continue
                    except OSError as e:
                         # Handle potential errors during absolute() call, though less likely
                         print(f"Warning: Error getting absolute path for self-check: {file_path} - {e}")


                    if self.should_process_file(file_path):
                        files_to_process.append(file_path)

            self.status_var.set(f"Scan complete. Found {len(files_to_process)} files to process (scanned {processed_dirs_count} dirs, skipped {skipped_dirs_count} hidden/system dirs).")
            total_files = len(files_to_process)

            if total_files == 0:
                self.root.after(0, lambda: messagebox.showwarning(
                    "No Files Found",
                    "No files matching the criteria were found in the source folder or all were excluded.\n"
                    f"Checked {processed_dirs_count} directories, skipped {skipped_dirs_count} hidden/system directories (like .git).\n"
                    "Please check the folder contents and your file type filters (especially Excludes).",
                    parent=self.root
                ))
                self.status_var.set(f"Ready (No matching files found)")
                self.root.after(0, lambda: self.generate_button.config(state=tk.NORMAL))
                return

            processed_files = 0
            encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8', errors='replace') as out_file:
                out_file.write(f"Source Folder: {source_path.resolve()}\n")
                if prompt:
                    out_file.write(f"Task Prompt:\n---\n{prompt}\n---\n\n")
                else:
                    out_file.write("Task Prompt: (Not provided)\n\n")
                out_file.write(f"Collected {total_files} files matching criteria:\n")
                out_file.write("=" * 80 + "\n\n")

                for file_path in files_to_process:
                    try:
                        relative_path = file_path.relative_to(source_path)
                    except ValueError:
                        relative_path = file_path # Fallback

                    self.status_var.set(f"Processing ({processed_files+1}/{total_files}): {relative_path}")
                    file_ext_display = file_path.suffix[1:].lower() if file_path.suffix else "no extension"
                    out_file.write(f"==== FILE: {relative_path} [{file_ext_display}] ====\n\n")

                    content = None
                    error_msg = None
                    processed_successfully = False

                    try:
                        # Try reading with different encodings, check for null bytes
                        read_error = None
                        for enc in encodings_to_try:
                            try:
                                with open(file_path, 'r', encoding=enc) as f:
                                    chunk = f.read(1024) # Check first 1KB for binary indicator
                                    if '\0' in chunk:
                                         read_error = f"Contains null bytes (likely binary), read attempted with {enc}"
                                         processed_successfully = False
                                         break # Stop trying encodings

                                    content = chunk + f.read()
                                processed_successfully = True
                                break # Success
                            except UnicodeDecodeError:
                                read_error = f"Failed to decode with {enc}"
                                continue
                            except OSError as e:
                                read_error = f"OS Error reading: {e}"
                                break
                            except Exception as e:
                                read_error = f"Unexpected Error reading: {type(e).__name__} - {e}"
                                break

                        if not processed_successfully:
                            # Use the most relevant error message captured
                            error_msg = f"[Read Error: Could not read file as text (Reason: {read_error or 'Unknown issue or binary content'})]"

                    except OSError as e:
                         error_msg = f"[Read Error: Pre-read OS error - {e}]"
                    except Exception as e:
                         error_msg = f"[Read Error: Pre-open error - {type(e).__name__} - {e}]"

                    if content is not None:
                        out_file.write(content)
                    elif error_msg:
                         out_file.write(error_msg + "\n")
                    else:
                         # Should only happen if processed_successfully is False but no error_msg (e.g. null byte hit)
                         out_file.write(f"[Read Error: File skipped (likely binary or encoding issue)]\n")

                    out_file.write("\n\n" + "=" * 80 + "\n\n")
                    processed_files += 1
                    self.progress_var.set((processed_files / total_files) * 100)

            final_message = (f"File collection complete!\n\n"
                             f"Processed {processed_files} files.\n"
                             f"Output saved to:\n{output_path.resolve()}")
            self.root.after(0, lambda: messagebox.showinfo("Success", final_message, parent=self.root))
            self.status_var.set(f"Ready (Completed: {processed_files} files)")
            self.status_label.config(foreground="green")

        except Exception as e:
            print("--- ERROR DURING FILE COLLECTION ---")
            traceback.print_exc()
            print("------------------------------------")
            error_details = f"An error occurred during file collection:\n\n{type(e).__name__}: {e}\n\n(Check console output for more details)"
            self.root.after(0, lambda: messagebox.showerror("Error", error_details, parent=self.root))
            self.status_var.set("Error occurred (See console for details)")
            self.status_label.config(foreground="red")

        finally:
             self.root.after(0, lambda: self.generate_button.config(state=tk.NORMAL))


if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    available_themes = style.theme_names()
    # Prefer more modern themes
    if 'clam' in available_themes: style.theme_use('clam')
    elif 'vista' in available_themes: style.theme_use('vista')
    elif 'aqua' in available_themes: style.theme_use('aqua')
    elif 'gtk' in available_themes: style.theme_use('gtk')
    elif 'winxpnative' in available_themes: style.theme_use('winxpnative')

    default_font_family = 'Segoe UI'
    default_font_size = 10
    try:
        import tkinter.font
        font_families = tkinter.font.families()
        if default_font_family not in font_families:
             # Basic fallback font logic
             if 'Helvetica' in font_families: default_font_family = 'Helvetica'
             elif 'Arial' in font_families: default_font_family = 'Arial'
             else: default_font_family = None

        default_font = (default_font_family, default_font_size)
        bold_font = (default_font_family, default_font_size, 'bold')
    except Exception:
        default_font = (None, default_font_size)
        bold_font = (None, default_font_size, 'bold')

    style.configure('TButton', font=default_font, padding=5)
    style.configure('TLabel', font=default_font)
    style.configure('TEntry', font=default_font, padding=3)
    style.configure('TCheckbutton', font=default_font)
    style.configure('TFrame', background=style.lookup('TFrame', 'background'))
    style.configure('TLabelframe', font=bold_font, padding=10)
    style.configure('TLabelframe.Label', font=bold_font)
    style.configure('TNotebook.Tab', font=default_font, padding=[10, 5])

    app = FileCollectorApp(root)
    root.mainloop()
