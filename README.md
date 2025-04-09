# AIContexter - Python File Collector

How many times did you try to get smth from AI chat and realized that it looses your context? With this, you can simply gather all you project file's content into one file, fill the prompt and AI chat will be fully into your context to give you best help.

## Features

- **Collect Files Recursively**: Scan through directories and subdirectories to find all matching files
- **File Type Filtering**: Include or exclude files based on their extensions
- **Common File Types**: Quick selection for common file types (Python, JavaScript, CSS, PHP, XML, YAML, VCL)
- **Custom Extensions**: Add your own custom file extensions to include or exclude
- **Task Description**: Include a descriptive prompt at the beginning of the output file
- **Progress Tracking**: Monitor the collection process with a progress bar
- **Multiple Encodings**: Attempts to read files with different encodings to handle various text formats
- **Modern UI**: Clean tabbed interface with an intuitive design

## Installation

### Requirements
- Python 3.6 or higher
- tkinter (usually comes with Python)

### Steps

1. Clone this repository
2. Run the application:
   ```bash
   python aicontexter.py
   ```

or 

   ```bash
   python3 aicontexter.py
   ```   

## Usage

### Basic Operation

1. **Select Source Folder**: Choose the root directory containing the files you want to collect
2. **Choose Output File**: Select where you want to save the combined output
3. **Add Task Description** (Optional): Enter a description of what you're collecting
4. **Configure File Types** (Optional): 
   - Use the "File Types" tab to specify which file extensions to include/exclude
   - Or check "Process all files" to include everything
5. **Click "Generate Combined File"**: Wait for the process to complete

### File Type Filtering

- **Process All Files**: When checked, all file filters are ignored
- **Include File Types**: Select common file types or add custom extensions
- **Exclude File Types**: Always excludes these extensions, even if listed in Include

## Use Cases

- Collecting code for review or documentation
- Preparing codebases for analysis by LLMs or other tools
- Creating backups of text-based project files
- Generating documentation from code comments
- Preparing code for printing or offline reference

## How It Works

The application:
1. Recursively scans the source directory for files
2. Filters files based on your include/exclude settings
3. Reads each file, attempting different encodings if needed
4. Combines all content into a single output file with clear separators between files
5. Includes file paths and extensions for easy reference

## Troubleshooting

- **No Files Found**: Check that your source directory contains files matching your filter settings
- **Reading Errors**: Some files may not be readable due to encoding issues or binary content
- **Output Inside Source**: Avoid saving the output file inside the source directory to prevent potential issues during re-runs

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with Python and tkinter
- Uses pathlib for modern path handling
- Inspired by the need to collect code for LLM processing
