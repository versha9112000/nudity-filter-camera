import os
import cv2
import json
import shutil
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw
from datetime import datetime, date, timedelta

# ---------------- CONFIG ----------------
FOLDER = r"C:/Users/Misha/PycharmProjects/PythonProject"
BIN_FOLDER = os.path.join(FOLDER, ".bin")
FAV_FILE = os.path.join(FOLDER, "favorites.json")

os.makedirs(FOLDER, exist_ok=True)
os.makedirs(BIN_FOLDER, exist_ok=True)

# Memory Management & Global Controls
THUMB_CACHE = {}
TK_CACHE = []
current_tab = "photos"
current_subfolder = ""
dark_mode = False
search_text = ""
group_by_var = None

# Interactive Selection Tracking State
SELECTED_FILES = set()
CARD_WIDGETS = {}

PLACEHOLDER_IMG = Image.new("RGB", (130, 130), color="#222222")
PLACEHOLDER_VID = Image.new("RGB", (130, 130), color="#1a3a5f")
PLACEHOLDER_DIR = Image.new("RGB", (130, 130), color="#e9ecef")

draw = ImageDraw.Draw(PLACEHOLDER_DIR)
draw.rectangle([20, 40, 110, 100], fill="#ffc107")
draw.rectangle([20, 25, 60, 40], fill="#ffc107")


# ---------------- FAVORITES ----------------
def load_favs():
    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()


def save_favs():
    with open(FAV_FILE, "w") as f:
        json.dump(list(FAV), f)


FAV = load_favs()


# ---------------- VIDEO DURATION TRACKER ----------------
def get_video_duration(path):
    try:
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        if fps > 0:
            sec = int(frames / fps)
            return f"{sec // 60}:{sec % 60:02d}"
    except:
        pass
    return "0:00"


# ---------------- SCAN ENGINE ----------------
def scan_files_and_folders():
    files = []
    folders = []
    search_lower = search_text.strip().lower()
    MEDIA_EXTENSIONS = (".jpg", ".jpeg", ".png", ".mp4", ".avi", ".mkv")

    try:
        if current_tab == "bin":
            target_dir = BIN_FOLDER
        elif current_subfolder:
            target_dir = os.path.join(FOLDER, current_subfolder)
        else:
            target_dir = FOLDER

        if not os.path.exists(target_dir):
            return [], []

        dir_list = os.listdir(target_dir)
    except Exception as e:
        print(f"Error scanning directory: {e}")
        return [], []

    for f in dir_list:
        if f == ".bin" or f == "favorites.json":
            continue

        path = os.path.join(target_dir, f)
        f_lower = f.lower()

        # Handle Subdirectory Filtering
        if os.path.isdir(path):
            if current_tab == "folders" and not current_subfolder:
                if not search_lower or search_lower in f_lower:
                    try:
                        sub_contents = os.listdir(path)
                        has_media = any(sf.lower().endswith(MEDIA_EXTENSIONS) for sf in sub_contents)
                        if has_media:
                            folders.append(path)
                    except:
                        pass
            continue

        if search_lower and search_lower not in f_lower:
            continue

        if current_subfolder:
            if f_lower.endswith(MEDIA_EXTENSIONS):
                files.append(path)
        else:
            if current_tab == "photos" and f_lower.endswith((".jpg", ".jpeg", ".png")):
                files.append(path)
            elif current_tab == "videos" and f_lower.endswith((".mp4", ".avi", ".mkv")):
                files.append(path)
            elif current_tab == "favorites" and path in FAV:
                files.append(path)
            elif current_tab == "bin":
                if f_lower.endswith(MEDIA_EXTENSIONS):
                    files.append(path)

    try:
        return sorted(files, key=os.path.getmtime, reverse=True), sorted(folders)
    except:
        return files, sorted(folders)


# ---------------- SELECTION INTERACTIVE SYSTEM ----------------
def toggle_select_file(path, card_widget):
    if current_tab == "bin":
        return

    if path in SELECTED_FILES:
        SELECTED_FILES.remove(path)
        card_widget.config(highlightbackground="#e1e1e1" if not dark_mode else "#111111",
                           highlightcolor="#e1e1e1" if not dark_mode else "#111111", highlightthickness=1)
    else:
        SELECTED_FILES.add(path)
        card_widget.config(highlightbackground="#007bff", highlightcolor="#007bff", highlightthickness=3)


def clear_all_selections():
    global SELECTED_FILES
    if not SELECTED_FILES:
        return
    SELECTED_FILES.clear()
    render()


def create_folder_from_selection():
    if not SELECTED_FILES:
        messagebox.showwarning("No Selection", "Please Right-Click on images/videos to select them first!")
        return

    folder_name = simpledialog.askstring("Create Folder", "Enter custom folder name for selected media:")
    if not folder_name or not folder_name.strip():
        return

    clean_name = folder_name.replace(":", "-").replace("/", "-").strip()
    target_dir = os.path.join(FOLDER, clean_name)

    if os.path.exists(target_dir):
        if not messagebox.askyesno("Folder Exists", f"Folder '{clean_name}' already exists. Merge files into it?"):
            return
    else:
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to instantiate custom directory: {e}")
            return

    moved_count = 0
    for old_path in list(SELECTED_FILES):
        try:
            if os.path.exists(old_path):
                name = os.path.basename(old_path)
                new_path = os.path.join(target_dir, name)
                shutil.move(old_path, new_path)

                if old_path in THUMB_CACHE: THUMB_CACHE[new_path] = THUMB_CACHE.pop(old_path)
                if old_path in FAV:
                    FAV.remove(old_path)
                    FAV.add(new_path)
                moved_count += 1
        except Exception as e:
            print(f"Failed to migrate file: {e}")

    SELECTED_FILES.clear()
    save_favs()
    messagebox.showinfo("Success", f"Custom folder created! Moved {moved_count} items securely.")
    render()


# ---------------- FILE & DIRECTORY MANIPULATION ----------------
def move_to_bin(path):
    try:
        name = os.path.basename(path)
        dest = os.path.join(BIN_FOLDER, name)
        if os.path.exists(dest):
            base, ext = os.path.splitext(name)
            dest = os.path.join(BIN_FOLDER, f"{base}_old{ext}")
        shutil.move(path, dest)
        if path in THUMB_CACHE: del THUMB_CACHE[path]
    except Exception as e:
        print(f"Error transferring item to bin: {e}")


def restore_from_bin(path):
    try:
        name = os.path.basename(path)
        dest = os.path.join(FOLDER, name)
        shutil.move(path, dest)
        if path in THUMB_CACHE: del THUMB_CACHE[path]
    except Exception as e:
        print(f"Error restoring file: {e}")


def hard_delete(path):
    try:
        if path in FAV:
            FAV.remove(path)
            save_favs()
        os.remove(path)
        if path in THUMB_CACHE: del THUMB_CACHE[path]
    except Exception as e:
        print(f"Error deleting file permanently: {e}")


def rename_file(old_path, win):
    try:
        old_name = os.path.basename(old_path)
        base, ext = os.path.splitext(old_name)
        new_base = simpledialog.askstring("Rename File", f"Enter new name for '{base}':", parent=win)
        if not new_base: return old_path

        new_name = new_base.strip() + ext
        new_path = os.path.join(os.path.dirname(old_path), new_name)

        if os.path.exists(new_path):
            messagebox.showerror("Error", "A file with that name already exists!", parent=win)
            return old_path

        os.rename(old_path, new_path)
        if old_path in THUMB_CACHE: THUMB_CACHE[new_path] = THUMB_CACHE.pop(old_path)
        if old_path in FAV:
            FAV.remove(old_path)
            FAV.add(new_path)
            save_favs()
        win.destroy()
        render()
        return new_path
    except Exception as e:
        messagebox.showerror("Error", f"Failed to rename file: {e}", parent=win)
        return old_path


def create_folder_from_group(group_name, file_paths):
    if current_tab == "bin":
        messagebox.showwarning("Action Blocked", "You cannot organize files while browsing the Trash Bin!")
        return

    clean_name = group_name.replace(":", "-").replace("/", "-").replace(".", "").replace("🖼️ ", "").replace("🎬 ",
                                                                                                            "").strip()
    target_dir = os.path.join(FOLDER, clean_name)

    if os.path.exists(target_dir):
        if not messagebox.askyesno("Folder Exists",
                                   f"Folder '{clean_name}' already exists. Move selected files into it?"):
            return
    else:
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not build operating directory: {e}")
            return

    moved_count = 0
    for old_path in file_paths:
        try:
            if os.path.exists(old_path):
                name = os.path.basename(old_path)
                new_path = os.path.join(target_dir, name)
                shutil.move(old_path, new_path)
                if old_path in THUMB_CACHE: THUMB_CACHE[new_path] = THUMB_CACHE.pop(old_path)
                if old_path in FAV:
                    FAV.remove(old_path)
                    FAV.add(new_path)
                moved_count += 1
        except Exception as e:
            print(f"Failed to migrate object token: {e}")

    save_favs()
    messagebox.showinfo("Success", f"Successfully built folder and migrated {moved_count} items!")
    render()


# ---------------- INTERACTIVE NAVIGATION SCOPES ----------------
def open_folder_scope(folder_path):
    global current_subfolder
    current_subfolder = os.path.basename(folder_path)
    render()


def exit_subfolder_scope():
    global current_subfolder
    current_subfolder = ""
    render()


# ---------------- ASYNC THUMBNAIL WORKER ----------------
def load_thumbnail_worker(path, btn, is_video):
    if path in THUMB_CACHE:
        img = THUMB_CACHE[path]
    else:
        try:
            if not is_video:
                img = Image.open(path).convert("RGB")
            else:
                cap = cv2.VideoCapture(path)
                ok, fr = cap.read()
                cap.release()
                if not ok: return
                fr = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(fr)

            img.thumbnail((130, 130))
            THUMB_CACHE[path] = img
        except:
            return

    def update_ui():
        try:
            photo = ImageTk.PhotoImage(img)
            TK_CACHE.append(photo)
            btn.config(image=photo)
        except:
            pass

    root.after(0, update_ui)


# ---------------- ACTION MODAL WINDOWS ----------------
def open_media(path):
    win = tk.Toplevel(root)
    win.geometry("900x780")
    win.title("Media Viewer")

    ctrl_frame = tk.Frame(win, pady=10)
    ctrl_frame.pack(side="top", fill="x")

    if current_tab == "bin":
        def bin_restore():
            restore_from_bin(path)
            win.destroy()
            render()

        def bin_wipe():
            hard_delete(path)
            win.destroy()
            render()

        tk.Button(ctrl_frame, text="♻️ Restore File", command=bin_restore, bg="#28a745", fg="white",
                  font=("Arial", 11, "bold"), padx=10).pack(side="left", padx=15)
        tk.Button(ctrl_frame, text="❌ Delete Permanently", command=bin_wipe, bg="#dc3545", fg="white",
                  font=("Arial", 11, "bold"), padx=10).pack(side="right", padx=15)

    else:
        def fav():
            if path in FAV:
                FAV.remove(path)
            else:
                FAV.add(path)
            save_favs()
            render()

        def soft_delete():
            move_to_bin(path)
            win.destroy()
            render()

        tk.Button(ctrl_frame, text="❤️ Favorite", command=fav, font=("Arial", 11)).pack(side="left", padx=15)
        tk.Button(ctrl_frame, text="✏️ Rename", command=lambda: rename_file(path, win), font=("Arial", 11)).pack(
            side="left", padx=5)
        tk.Button(ctrl_frame, text="🗑 Move to Bin", command=soft_delete, bg="#ffc107", font=("Arial", 11)).pack(
            side="right", padx=15)

    lbl = tk.Label(win)
    lbl.pack(expand=True, fill="both", pady=10)

    if path.lower().endswith((".jpg", ".jpeg", ".png")):
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((850, 630))
            photo = ImageTk.PhotoImage(img)
            lbl.config(image=photo)
            lbl.image = photo
        except:
            lbl.config(text="Corrupt profile data loaded.")
    else:
        cap = cv2.VideoCapture(path)

        def play():
            if not win.winfo_exists():
                cap.release()
                return
            ok, frame = cap.read()
            if ok:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                img.thumbnail((850, 630))
                photo = ImageTk.PhotoImage(img)
                lbl.config(image=photo)
                lbl.image = photo
                lbl.after(25, play)
            else:
                cap.release()

        play()


# ---------------- UI CANVAS THEMES ----------------
def apply_theme():
    bg = "#111111" if dark_mode else "#ffffff"
    fg = "#ffffff" if dark_mode else "#000000"
    root.configure(bg=bg)
    top.configure(bg=bg)
    canvas_container.configure(bg=bg)
    return bg, fg


def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    render()


def set_search(event=None):
    global search_text
    search_text = search_var.get()
    render()


def refresh_gallery():
    global THUMB_CACHE
    THUMB_CACHE.clear()
    render()


# ---------------- CORE RENDERING STAGE ----------------
def render():
    global TK_CACHE, CARD_WIDGETS
    TK_CACHE = []
    CARD_WIDGETS = {}

    for w in canvas_container.winfo_children():
        w.destroy()

    bg, fg = apply_theme()

    if current_subfolder:
        nav_header = tk.Frame(canvas_container, bg=bg, pady=8, padx=10)
        nav_header.pack(side="top", fill="x")
        tk.Button(nav_header, text="⬅️ Back to Custom Folders List", command=exit_subfolder_scope,
                  bg="#28a745", fg="white", font=("Arial", 10, "bold")).pack(side="left")
        tk.Label(nav_header, text=f" Browsing Content: / {current_subfolder}", fg="#007bff", bg=bg,
                 font=("Arial", 11, "bold")).pack(side="left", padx=10)

    canvas = tk.Canvas(canvas_container, bg=bg, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    v_scroll = tk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
    v_scroll.pack(side="right", fill="y")

    for child in root.winfo_children():
        if isinstance(child, tk.Scrollbar) and child.cget("orient") == "horizontal":
            child.destroy()

    h_scroll = tk.Scrollbar(root, orient="horizontal", command=canvas.xview)
    h_scroll.pack(side="bottom", fill="x")
    canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

    inner_frame = tk.Frame(canvas, bg=bg)
    canvas.create_window((0, 0), window=inner_frame, anchor="nw")
    inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    files, custom_folders = scan_files_and_folders()
    ph_img = ImageTk.PhotoImage(PLACEHOLDER_IMG)
    ph_vid = ImageTk.PhotoImage(PLACEHOLDER_VID)
    ph_dir = ImageTk.PhotoImage(PLACEHOLDER_DIR)
    TK_CACHE.extend([ph_img, ph_vid, ph_dir])

    cols = 6

    if current_tab == "folders" and not current_subfolder:
        if custom_folders:
            dir_title_frame = tk.Frame(inner_frame, bg=bg, pady=5)
            dir_title_frame.pack(fill="x", anchor="w", padx=10)
            tk.Label(dir_title_frame, text="📁 My Created Custom Folders", fg="#ffc107", bg=bg,
                     font=("Arial", 13, "bold")).pack(side="left")

            dir_grid_frame = tk.Frame(inner_frame, bg=bg)
            dir_grid_frame.pack(fill="x", padx=10, pady=5)

            for i, folder_path in enumerate(custom_folders):
                f_name = os.path.basename(folder_path)
                if len(f_name) > 18: f_name = f_name[:15] + "..."

                f_card = tk.Frame(dir_grid_frame, bg=bg, bd=0, highlightbackground="#ffc107", highlightthickness=1)
                f_card.grid(row=i // cols, column=i % cols, padx=8, pady=8)

                f_btn = tk.Button(f_card, image=ph_dir, command=lambda p=folder_path: open_folder_scope(p),
                                  relief="flat", bd=0)
                f_btn.pack(pady=2)

                tk.Label(f_card, text=f_name, fg=fg, bg=bg, font=("Arial", 9, "bold")).pack()
                tk.Label(f_card, text="CLICK TO OPEN", fg="#28a745", bg=bg, font=("Arial", 7, "bold")).pack()
        else:
            empty_lbl = tk.Label(inner_frame,
                                 text="No custom folders found.\nSelect media in Photos/Videos tabs and choose 'Create Folder From Selection'.",
                                 fg="gray", bg=bg, font=("Arial", 11, "italic"), justify="center", pady=40)
            empty_lbl.pack(fill="x", padx=20)

    mode = group_by_var.get() if group_by_var else "No Grouping"
    grouped_data = {}

    # Define baseline processing check dates
    today_val = date.today()
    tomorrow_val = today_val + timedelta(days=1)
    yesterday_val = today_val - timedelta(days=1)

    today_str = today_val.strftime("%d-%m-%Y")
    tomorrow_str = tomorrow_val.strftime("%d-%m-%Y")
    yesterday_str = yesterday_val.strftime("%d-%m-%Y")

    for path in files:
        f_lower = path.lower()
        is_video = f_lower.endswith((".mp4", ".avi", ".mkv"))

        try:
            t = os.path.getmtime(path)
            dt = datetime.fromtimestamp(t)
            file_date = dt.date()

            if mode == "Day/Month/Year" or mode == "No Grouping":
                raw_date = dt.strftime("%d-%m-%Y")
                if file_date > tomorrow_val:
                    group_key = f"🗓️ FUTURE ({raw_date})"
                elif raw_date == tomorrow_str:
                    group_key = f"🗓️ TOMORROW ({raw_date})"
                elif raw_date == today_str:
                    group_key = f"🗓️ TODAY ({raw_date})"
                elif raw_date == yesterday_str:
                    group_key = f"🗓️ YESTERDAY ({raw_date})"
                else:
                    group_key = f"🗓️ OLDER IMAGES ({raw_date})"
            elif mode == "Month & Year":
                group_key = dt.strftime("%B %Y")
            elif mode == "Year Only":
                group_key = dt.strftime("%Y")
            elif mode == "File Type":
                group_key = "🎬 Videos" if is_video else "🖼️ Images"
            elif mode == "Extension":
                group_key = os.path.splitext(f_lower)[1].upper() + " Format"
        except:
            group_key = "Unknown Context"

        if group_key not in grouped_data:
            grouped_data[group_key] = []
        grouped_data[group_key].append(path)

    # ADVANCED SORTING: Keep Future -> Tomorrow -> Today -> Yesterday -> Older ordered chronologically
    def sort_groups(key):
        if "FUTURE" in key: return (0, key)
        if "TOMORROW" in key: return (1, key)
        if "TODAY" in key: return (2, key)
        if "YESTERDAY" in key: return (3, key)
        if "OLDER IMAGES" in key: return (4, key)
        return (5, key)

    sorted_keys = sorted(grouped_data.keys(), key=sort_groups,
                         reverse=False if mode in ["Day/Month/Year", "No Grouping"] else True)

    for group_title in sorted_keys:
        paths = grouped_data[group_title]
        header_frame = tk.Frame(inner_frame, bg=bg, pady=10)
        header_frame.pack(fill="x", anchor="w", padx=10)

        # Apply specific unique colors to the headers
        title_color = fg
        if "FUTURE" in group_title:
            title_color = "#9b5de5"
        elif "TOMORROW" in group_title:
            title_color = "#28a745"
        elif "TODAY" in group_title:
            title_color = "#007bff"
        elif "YESTERDAY" in group_title:
            title_color = "#f77f00"
        elif "OLDER IMAGES" in group_title:
            title_color = "gray"

        tk.Label(header_frame, text=f"📂 {group_title} ({len(paths)} items)", fg=title_color, bg=bg,
                 font=("Arial", 12, "bold")).pack(side="left")

        if mode != "No Grouping" and current_tab != "bin":
            tk.Button(header_frame, text="📁 Create Folder From Group",
                      command=lambda g=group_title, p=paths: create_folder_from_group(g, p),
                      bg="#17a2b8", fg="white", font=("Arial", 9, "bold"), bd=0, padx=6, pady=2).pack(side="left",
                                                                                                      padx=15)

        grid_frame = tk.Frame(inner_frame, bg=bg)
        grid_frame.pack(fill="x", padx=10)

        for i, path in enumerate(paths):
            is_vid = path.lower().endswith((".mp4", ".avi", ".mkv"))
            placeholder = ph_vid if is_vid else ph_img

            file_name = os.path.basename(path)
            if len(file_name) > 18: file_name = file_name[:15] + "..."

            try:
                timestamp = os.path.getmtime(path)
                date_str = datetime.fromtimestamp(timestamp).strftime("%d-%m-%Y %H:%M")
            except:
                date_str = "00-00-0000 00:00"

            is_selected = path in SELECTED_FILES
            b_color = "#007bff" if is_selected else ("#e1e1e1" if not dark_mode else "#111111")
            b_thick = 3 if is_selected else 1

            card = tk.Frame(grid_frame, bg=bg, bd=0, highlightbackground=b_color, highlightcolor=b_color,
                            highlightthickness=b_thick)
            card.grid(row=i // cols, column=i % cols, padx=8, pady=8)
            CARD_WIDGETS[path] = card

            btn = tk.Button(card, image=placeholder, command=lambda p=path: open_media(p), relief="flat", bd=0)
            btn.pack(pady=2)

            lbl_name = tk.Label(card, text=file_name, fg=fg, bg=bg, font=("Arial", 9, "bold"))
            lbl_name.pack()
            lbl_date = tk.Label(card, text=date_str, fg="gray", bg=bg, font=("Arial", 8))
            lbl_date.pack()

            for item in (btn, lbl_name, lbl_date, card):
                item.bind("<Button-3>", lambda e, p=path, c=card: toggle_select_file(p, c))
                item.bind("<Control-Button-1>", lambda e, p=path, c=card: toggle_select_file(p, c))

            if is_vid:
                duration_lbl = tk.Label(card, text="⏱ Loading...", fg="#17a2b8", bg=bg, font=("Arial", 8, "italic"))
                duration_lbl.pack()
                duration_lbl.bind("<Button-3>", lambda e, p=path, c=card: toggle_select_file(p, c))
                duration_lbl.bind("<Control-Button-1>", lambda e, p=path, c=card: toggle_select_file(p, c))

                def load_dur(p, lbl):
                    dur = get_video_duration(p)
                    try:
                        root.after(0, lambda: lbl.config(text=f"🎬 {dur}"))
                    except:
                        pass

                threading.Thread(target=load_dur, args=(path, duration_lbl), daemon=True).start()
            else:
                lbl_type = tk.Label(card, text="🖼️ PHOTO", fg="#28a745", bg=bg, font=("Arial", 8))
                lbl_type.pack()
                lbl_type.bind("<Button-3>", lambda e, p=path, c=card: toggle_select_file(p, c))
                lbl_type.bind("<Control-Button-1>", lambda e, p=path, c=card: toggle_select_file(p, c))

            t_thread = threading.Thread(target=load_thumbnail_worker, args=(path, btn, is_vid), daemon=True)
            t_thread.start()


def switch(tab):
    global current_tab, current_subfolder, search_text
    current_tab = tab
    current_subfolder = ""
    search_text = ""
    search_var.set("")
    render()


# ---------------- APPLICATION INITIALIZATION ----------------
root = tk.Tk()
root.title("Pro Gallery Media Suite")
root.geometry("1450x850")

top = tk.Frame(root)
top.pack(fill="x", pady=5)

tk.Button(top, text="Photos", command=lambda: switch("photos"), width=12).pack(side="left", padx=2)
tk.Button(top, text="Videos", command=lambda: switch("videos"), width=12).pack(side="left", padx=2)
tk.Button(top, text="My Folders 📁", command=lambda: switch("folders"), width=14, bg="#ffc107").pack(side="left", padx=2)
tk.Button(top, text="Favorites", command=lambda: switch("favorites"), width=12).pack(side="left", padx=2)
tk.Button(top, text="Bin 🗑", command=lambda: switch("bin"), width=12).pack(side="left", padx=2)

tk.Button(top, text="🔄 Refresh", command=refresh_gallery, bg="#007bff", fg="white", font=("Arial", 9, "bold")).pack(
    side="left", padx=10)
tk.Button(top, text="📁 Create Folder From Selection", command=create_folder_from_selection, bg="#28a745", fg="white",
          font=("Arial", 9, "bold")).pack(side="left", padx=5)
tk.Button(top, text="🧹 Clear Selection", command=clear_all_selections, bg="#6c757d", fg="white",
          font=("Arial", 9, "bold")).pack(side="left", padx=2)

tk.Button(top, text="🌙 Theme", command=toggle_theme).pack(side="right", padx=5)

search_var = tk.StringVar()
search_entry = tk.Entry(top, textvariable=search_var, width=22)
search_entry.pack(side="right", padx=5)
search_entry.bind("<Return>", set_search)
tk.Label(top, text="🔍").pack(side="right")

tk.Label(top, text="Group Basis:").pack(side="right", padx=5)
group_by_var = tk.StringVar(value="No Grouping")
group_dropdown = ttk.Combobox(top, textvariable=group_by_var,
                              values=["No Grouping", "File Type", "Extension", "Day/Month/Year", "Month & Year",
                                      "Year Only"],
                              width=16, state="readonly")
group_dropdown.pack(side="right", padx=5)
group_dropdown.bind("<<ComboboxSelected>>", lambda e: render())

canvas_container = tk.Frame(root)
canvas_container.pack(fill="both", expand=True)

render()
root.mainloop()