# LexiconError product media

These are captures of the compiled local Tauri application, not mockups or generated interface
concepts.

- `lexiconerror-catalog.png`: initial offline catalog and root-cause inspector.
- `lexiconerror-command-palette.png`: command palette after querying Rust `E0382`.
- `lexiconerror-diagnostic-detail.png`: selected `E0382` record after pressing Enter.
- `lexiconerror-search-demo.gif`: optimized animated README preview.
- `lexiconerror-search-demo.mp4`: H.264 version of the same interaction at 1120×700 and 10 fps.

Regenerate on Windows after building the desktop executable:

~~~powershell
npm.cmd run desktop:build
python scripts\capture_readme_media.py
~~~

The capture script launches only `src-tauri/target/release/lexicon-error.exe`, drives its visible
command palette, writes the five named media files, and terminates only the process it started. It
requires Pillow, NumPy, ImageIO, and ImageIO-FFmpeg.
