import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import subprocess
import sys
from pathlib import Path
import time
import re
import json

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def find_ffmpeg():
    """Find ffmpeg executable"""
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    ffmpeg_paths = [
        os.path.join(script_dir, "ffmpeg.exe"),
        get_resource_path("ffmpeg.exe"),
        "ffmpeg.exe",
        "C:\\ffmpeg\\bin\\ffmpeg.exe",
    ]
    
    for path in ffmpeg_paths:
        if os.path.exists(path):
            return path
    return "ffmpeg"

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("600x800")
        self.root.resizable(True, True)
        
        # Variables
        self.download_thread = None
        self.is_downloading = False
        self.current_process = None
        self.current_video = 0
        self.total_videos = 0
        self.playlist_videos = []
        self.selected_videos = []
        self.video_vars = []
        
        # Find ffmpeg
        self.ffmpeg_path = find_ffmpeg()
        
        # Create GUI elements
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Set window icon
        try:
            icon_path = get_resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
        
        # URL Section
        url_frame = ttk.LabelFrame(main_frame, text="Video URL", padding="10")
        url_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        url_frame.columnconfigure(0, weight=1)
        
        ttk.Label(url_frame, text="YouTube URL (video or playlist):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.url_entry = ttk.Entry(url_frame, font=("Arial", 9))
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        self.url_entry.insert(0, "https://www.youtube.com/watch?v=VIDEO_ID")
        
        self.fetch_btn = ttk.Button(url_frame, text="Fetch Videos", command=self.fetch_playlist)
        self.fetch_btn.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Download Settings Frame
        settings_frame = ttk.LabelFrame(main_frame, text="Download Settings", padding="10")
        settings_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        
        # Download Type
        ttk.Label(settings_frame, text="Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.download_type = tk.StringVar(value="audio")
        type_frame = ttk.Frame(settings_frame)
        type_frame.grid(row=0, column=1, columnspan=2, sticky=tk.W)
        ttk.Radiobutton(type_frame, text="Audio (MP3)", variable=self.download_type, 
                       value="audio", command=self.toggle_quality_options).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(type_frame, text="Video (MP4)", variable=self.download_type, 
                       value="video", command=self.toggle_quality_options).pack(side=tk.LEFT)
        
        # Quality Selection
        ttk.Label(settings_frame, text="Quality:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.quality_var = tk.StringVar(value="best")
        
        self.audio_qualities = ["best", "320", "256", "192", "128", "96", "worst"]
        self.video_qualities = ["best", "2160p", "1440p", "1080p", "720p", "480p", "360p", "worst"]
        
        self.quality_menu = ttk.Combobox(settings_frame, textvariable=self.quality_var, 
                                         values=self.audio_qualities, state="readonly", width=20)
        self.quality_menu.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Thumbnail option
        self.include_thumb = tk.BooleanVar(value=True)
        self.thumb_check = ttk.Checkbutton(settings_frame, text="Include Thumbnail", variable=self.include_thumb)
        self.thumb_check.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Video Selection Frame
        video_frame = ttk.LabelFrame(main_frame, text="Video Selection", padding="10")
        video_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(1, weight=1)
        
        # Video list with scrollbar
        self.video_list_outer = ttk.Frame(video_frame)
        self.video_list_outer.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.video_list_frame = ttk.Frame(self.video_list_outer)
        self.video_list_frame.pack(fill="both", expand=True)
        
        # Create canvas with scrollbar
        self.canvas = tk.Canvas(self.video_list_frame, height=150, bg="white", 
                                highlightthickness=1, highlightbackground="#cccccc", 
                                relief="sunken", bd=2)
        self.scrollbar = ttk.Scrollbar(self.video_list_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="white")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
        
        # Selection buttons
        select_frame = ttk.Frame(video_frame)
        select_frame.grid(row=1, column=0, columnspan=2, pady=(0, 5))
        
        ttk.Button(select_frame, text="Select All", command=self.select_all_videos).pack(side=tk.LEFT, padx=5)
        ttk.Button(select_frame, text="Deselect All", command=self.deselect_all_videos).pack(side=tk.LEFT, padx=5)
        
        # Range selection
        self.range_frame = ttk.Frame(video_frame)
        self.range_frame.grid(row=2, column=0, columnspan=2, pady=5)
        
        ttk.Label(self.range_frame, text="Range:").pack(side=tk.LEFT, padx=(0, 5))
        self.range_start = ttk.Entry(self.range_frame, width=8)
        self.range_start.pack(side=tk.LEFT, padx=2)
        self.range_start.insert(0, "1")
        ttk.Label(self.range_frame, text="to").pack(side=tk.LEFT, padx=5)
        self.range_end = ttk.Entry(self.range_frame, width=8)
        self.range_end.pack(side=tk.LEFT, padx=2)
        self.range_end.insert(0, "1")
        ttk.Button(self.range_frame, text="Select Range", command=self.select_range).pack(side=tk.LEFT, padx=10)
        
        # Output directory
        output_frame = ttk.LabelFrame(main_frame, text="Output Settings", padding="10")
        output_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        
        ttk.Label(output_frame, text="Save to:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.dir_frame = ttk.Frame(output_frame)
        self.dir_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.dir_frame.columnconfigure(0, weight=1)
        
        self.dir_entry = ttk.Entry(self.dir_frame, font=("Arial", 9))
        self.dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.dir_entry.insert(0, str(Path.home() / "Downloads" / "YouTube Downloads"))
        
        ttk.Button(self.dir_frame, text="Browse", command=self.browse_folder).grid(row=0, column=1)
        
        # Status and Progress Section
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        
        # Counter label
        self.counter_label = ttk.Label(status_frame, text="", foreground="blue", font=("Arial", 9))
        self.counter_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # Current video label
        self.current_video_label = ttk.Label(status_frame, text="", foreground="blue", font=("Arial", 9))
        self.current_video_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Status label
        self.status_label = ttk.Label(status_frame, text="Ready", foreground="gray", font=("Arial", 9))
        self.status_label.grid(row=3, column=0, columnspan=2, sticky=tk.W)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.download_btn = ttk.Button(button_frame, text="Download", command=self.start_download, state="disabled")
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.cancel_download, state="disabled")
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Configure weights
        main_frame.rowconfigure(2, weight=1)
        
    def toggle_quality_options(self):
        if self.download_type.get() == "audio":
            self.quality_menu['values'] = self.audio_qualities
            self.quality_var.set("best")
        else:
            self.quality_menu['values'] = self.video_qualities
            self.quality_var.set("best")
    
    def fetch_playlist(self):
        """Fetch playlist videos and display them with checkboxes"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL first")
            return
        
        # Reset progress bar and status
        self.progress_var.set(0)
        self.status_label.config(text="Fetching videos...", foreground="blue")
        self.current_video_label.config(text="")
        self.fetch_btn.config(state="disabled")
        self.download_btn.config(state="disabled")
        
        def fetch_thread():
            try:
                # Check if it's a playlist or single video
                if self.is_playlist(url):
                    cmd = ['yt-dlp', '--flat-playlist', '--dump-json', url]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    self.playlist_videos = []
                    for line in result.stdout.splitlines():
                        if line.strip():
                            try:
                                video_info = json.loads(line)
                                self.playlist_videos.append(video_info)
                            except:
                                pass
                else:
                    # Single video - get info
                    cmd = ['yt-dlp', '--dump-json', '--no-playlist', url]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    try:
                        video_info = json.loads(result.stdout)
                        self.playlist_videos = [video_info]
                    except:
                        self.playlist_videos = []
                
                self.total_videos = len(self.playlist_videos)
                
                # Update UI in main thread
                self.root.after(0, self.display_video_list)
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Found {self.total_videos} video(s)", foreground="green"))
                # Update range end default to total videos
                self.root.after(0, lambda: self.range_end.delete(0, tk.END))
                self.root.after(0, lambda: self.range_end.insert(0, str(self.total_videos)))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch: {str(e)}"))
                self.root.after(0, lambda: self.status_label.config(text="Ready", foreground="gray"))
            finally:
                self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
        
        thread = threading.Thread(target=fetch_thread)
        thread.daemon = True
        thread.start()
    
    def display_video_list(self):
        """Display video list with checkboxes"""
        # Clear existing checkboxes
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.video_vars = []
        self.selected_videos = list(range(len(self.playlist_videos)))
        
        # Create checkboxes for each video
        for i, video in enumerate(self.playlist_videos):
            var = tk.BooleanVar(value=True)  # Pre-checked
            self.video_vars.append(var)
            
            title = video.get("title", f"Video {i+1}")
            if len(title) > 60:
                title = title[:57] + "..."
            
            # Alternate background colors
            bg_color = "#f0f0f0" if i % 2 == 0 else "white"
            
            item_frame = tk.Frame(self.scrollable_frame, bg=bg_color, padx=5, pady=2)
            item_frame.pack(fill=tk.X, expand=True)
            
            cb = tk.Checkbutton(item_frame, text=f"{i+1}. {title}", variable=var, 
                               command=self.update_selected_count, bg=bg_color, anchor=tk.W, 
                               selectcolor=bg_color, activebackground=bg_color)
            cb.pack(fill=tk.X, expand=True)
        
        # Enable download button if there are videos
        if self.playlist_videos:
            self.update_selected_count()
        else:
            self.download_btn.config(state="disabled")
    
    def update_selected_count(self):
        """Update the selected videos count"""
        if not self.video_vars:
            self.download_btn.config(state="disabled")
            return
        
        selected_count = sum(1 for var in self.video_vars if var.get())
        self.selected_videos = [i for i, var in enumerate(self.video_vars) if var.get()]
        
        if selected_count == 0:
            self.counter_label.config(text="0 videos selected")
            self.download_btn.config(state="disabled")
        elif selected_count == len(self.video_vars):
            self.counter_label.config(text=f"{selected_count} videos selected (all)")
            self.download_btn.config(state="normal")
        else:
            self.counter_label.config(text=f"{selected_count} of {len(self.video_vars)} videos selected")
            self.download_btn.config(state="normal")
    
    def select_all_videos(self):
        """Select all videos"""
        for var in self.video_vars:
            var.set(True)
        self.selected_videos = list(range(len(self.playlist_videos)))
        self.update_selected_count()
    
    def deselect_all_videos(self):
        """Deselect all videos"""
        for var in self.video_vars:
            var.set(False)
        self.selected_videos = []
        self.update_selected_count()
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            self.canvas.yview_scroll(1, "units")
    
    def select_range(self):
        """Select a range of videos"""
        try:
            start = int(self.range_start.get()) - 1
            end = int(self.range_end.get()) - 1
            
            if start < 0 or end >= len(self.video_vars) or start > end:
                messagebox.showerror("Error", "Invalid range")
                return
            
            # First deselect all
            for var in self.video_vars:
                var.set(False)
            
            # Then select the range
            for i in range(start, end + 1):
                self.video_vars[i].set(True)
            
            self.update_selected_count()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")
    
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, folder)
    
    def is_playlist(self, url):
        return 'playlist' in url.lower() or 'list=' in url.lower()
    
    def get_playlist_count(self, url):
        """Get total number of videos in playlist"""
        try:
            cmd = ['yt-dlp', '--flat-playlist', '--dump-json', url]
            result = subprocess.run(cmd, capture_output=True, text=True)
            count = 0
            for line in result.stdout.splitlines():
                if line.strip():
                    count += 1
            return count
        except:
            return 0
    
    def build_command(self):
        """Build the yt-dlp command"""
        url = self.url_entry.get().strip()
        if not url:
            return None
        
        output_dir = self.dir_entry.get()
        if not output_dir:
            output_dir = str(Path.home() / "Downloads" / "YouTube Downloads")
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        cmd = ['yt-dlp']
        
        # Output template
        cmd.extend(['-o', os.path.join(output_dir, '%(title)s.%(ext)s')])
        
        # Add playlist options if it's a playlist
        if self.is_playlist(url):
            cmd.append('--yes-playlist')
            cmd.append('--ignore-errors')
            
            # Add playlist items if videos are selected
            if self.playlist_videos and self.video_vars:
                selected_indices = [i+1 for i, var in enumerate(self.video_vars) if var.get()]
                if selected_indices:
                    items_str = ','.join(map(str, selected_indices))
                    cmd.extend(['--playlist-items', items_str])
                else:
                    return None  # No videos selected
        else:
            # Single video
            cmd.append('--ignore-errors')
        
        # Progress output
        cmd.append('--newline')
        cmd.append('--progress')
        cmd.append('--no-warnings')
        
        # Configure based on download type
        if self.download_type.get() == "audio":
            quality = self.quality_var.get()
            
            if quality == "best":
                cmd.extend(['-f', 'bestaudio/best'])
            elif quality == "worst":
                cmd.extend(['-f', 'worstaudio/worst'])
            else:
                cmd.extend(['-f', 'bestaudio/best'])
            
            cmd.extend(['--extract-audio', '--audio-format', 'mp3'])
            
            if quality == "best":
                cmd.extend(['--audio-quality', '0'])
            elif quality == "worst":
                cmd.extend(['--audio-quality', '9'])
            else:
                try:
                    bitrate = int(quality)
                    quality_val = max(0, min(9, int(9 - ((bitrate - 64) / 256) * 9)))
                    cmd.extend(['--audio-quality', str(quality_val)])
                except:
                    cmd.extend(['--audio-quality', '5'])
            
            if self.include_thumb.get():
                cmd.append('--embed-thumbnail')
                
        else:
            quality = self.quality_var.get()
            
            if quality == "best":
                cmd.extend(['-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'])
            elif quality == "worst":
                cmd.extend(['-f', 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst'])
            elif quality == "2160p":
                cmd.extend(['-f', f'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]/best'])
            elif quality == "1440p":
                cmd.extend(['-f', f'bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best[height<=1440]/best'])
            elif quality == "1080p":
                cmd.extend(['-f', f'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'])
            elif quality == "720p":
                cmd.extend(['-f', f'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best'])
            elif quality == "480p":
                cmd.extend(['-f', f'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best'])
            elif quality == "360p":
                cmd.extend(['-f', f'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]/best'])
            else:
                cmd.extend(['-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'])
            
            if self.include_thumb.get():
                cmd.append('--embed-thumbnail')
        
        # Specify ffmpeg location
        if os.path.exists(self.ffmpeg_path):
            cmd.extend(['--ffmpeg-location', os.path.dirname(self.ffmpeg_path)])
        
        cmd.append(url)
        
        return cmd
    
    def download_playlist(self):
        """Download using subprocess"""
        url = self.url_entry.get().strip()
        if not url:
            self.root.after(0, lambda: messagebox.showerror("Error", "Please enter a URL"))
            self.download_complete()
            return
        
        # Get total video count for playlist
        if self.is_playlist(url) and self.total_videos == 0:
            self.root.after(0, lambda: self.status_label.config(text="Counting videos...", foreground="blue"))
            self.total_videos = self.get_playlist_count(url)
            if self.total_videos > 0:
                self.root.after(0, lambda: self.counter_label.config(text=f"Found {self.total_videos} videos"))
        elif not self.is_playlist(url):
            self.total_videos = 1
        
        cmd = self.build_command()
        if not cmd:
            self.download_complete()
            return
        
        try:
            self.root.after(0, lambda: self.status_label.config(text="Starting download...", foreground="blue"))
            
            # Start the subprocess
            if sys.platform == "win32":
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
            
            # Read output line by line
            for line in self.current_process.stdout:
                if not self.is_downloading:
                    break
                
                # Parse progress and counter
                if '[download]' in line:
                    # Check for playlist counter
                    match = re.search(r'Downloading item (\d+) of (\d+)', line)
                    if match:
                        self.current_video = int(match.group(1))
                        self.total_videos = int(match.group(2))
                        self.root.after(0, lambda c=self.current_video, t=self.total_videos: 
                                      self.counter_label.config(text=f"Video {c} of {t}"))
                    
                    # Check for destination filename
                    if 'Destination:' in line:
                        title = line.split('Destination:')[-1].strip()
                        title = os.path.basename(title)
                        title = os.path.splitext(title)[0][:50]
                        self.root.after(0, lambda t=title: self.current_video_label.config(text=f"Downloading: {t}"))
                    
                    # Parse percentage
                    percent_match = re.search(r'(\d+(?:\.\d+)?)%', line)
                    if percent_match:
                        percent = float(percent_match.group(1))
                        self.root.after(0, lambda p=percent: self.progress_var.set(p))
                        self.root.after(0, lambda p=percent: self.status_label.config(text=f"Downloading... {p:.1f}%"))
                
                elif '100%' in line and 'of' in line:
                    self.root.after(0, lambda: self.status_label.config(text="Processing..."))
            
            if self.current_process and self.is_downloading:
                return_code = self.current_process.wait()
                
                if return_code == 0:
                    self.root.after(0, lambda: self.status_label.config(text="Download completed successfully!", foreground="green"))
                    self.root.after(0, lambda: self.current_video_label.config(text=""))
                    self.root.after(0, lambda: self.counter_label.config(text=""))
                    self.root.after(0, lambda: messagebox.showinfo("Success", "Download completed successfully!"))
                elif return_code != 0:
                    self.root.after(0, lambda: self.status_label.config(text="Download failed", foreground="red"))
            
        except Exception as e:
            if self.is_downloading:
                self.root.after(0, lambda: self.status_label.config(text=f"Error: {str(e)[:100]}", foreground="red"))
        
        finally:
            self.current_process = None
            self.download_complete()
    
    def start_download(self):
        if self.is_downloading:
            return
        
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
        
        # Check if it's a playlist with selected videos
        if self.video_vars and self.playlist_videos:
            selected_count = sum(1 for var in self.video_vars if var.get())
            if selected_count == 0:
                messagebox.showerror("Error", "Please select at least one video to download")
                return
            self.total_videos = selected_count
        elif self.is_playlist(url):
            self.total_videos = 0
        else:
            self.total_videos = 1
        
        self.current_video = 0
        self.counter_label.config(text="")
        
        self.is_downloading = True
        self.download_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress_var.set(0)
        self.status_label.config(text="Starting download...", foreground="blue")
        self.current_video_label.config(text="")
        
        self.download_thread = threading.Thread(target=self.download_playlist)
        self.download_thread.daemon = True
        self.download_thread.start()
    
    def cancel_download(self):
        """Kill the subprocess immediately"""
        if not self.is_downloading:
            return
        
        self.status_label.config(text="Cancelling download...", foreground="orange")
        self.cancel_btn.config(state="disabled")
        
        # Kill the process
        if self.current_process:
            try:
                if sys.platform == "win32":
                    self.current_process.terminate()
                    time.sleep(0.3)
                    if self.current_process.poll() is None:
                        self.current_process.kill()
                else:
                    self.current_process.terminate()
                    time.sleep(0.3)
                    if self.current_process.poll() is None:
                        self.current_process.kill()
            except:
                pass
        
        self.is_downloading = False
        self.current_process = None
        self.progress_var.set(0)
        self.status_label.config(text="Download cancelled by user", foreground="orange")
        self.current_video_label.config(text="")
        self.counter_label.config(text="")
        self.download_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
    
    def download_complete(self):
        """Reset UI after download completes"""
        self.is_downloading = False
        self.current_process = None
        self.download_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        
        current_text = self.status_label.cget("text")
        if current_text not in ["Download completed successfully!", "Download cancelled by user", "Cancelling download..."] and "Error" not in current_text:
            self.status_label.config(text="Ready", foreground="gray")
            self.current_video_label.config(text="")

def main():
    root = tk.Tk()
    
    try:
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except:
        pass
    
    app = YouTubeDownloader(root)
    root.mainloop()

if __name__ == "__main__":
    main()
