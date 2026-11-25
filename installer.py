"""Helpers for installing, moving and uninstalling tar.gz applications."""

import os
import shutil
import tarfile
import subprocess


def safe_extract(tar, dest):
    """Extract tar safely (prevent path traversal)."""
    for member in tar.getmembers():
        member_path = os.path.join(dest, member.name)
        abs_dest = os.path.abspath(dest)
        abs_member = os.path.abspath(member_path)
        if not (abs_member == abs_dest or abs_member.startswith(abs_dest + os.sep)):
            raise ValueError(f"Unsafe path in archive: {member.name}")
    tar.extractall(dest)


def inspect_tarball(path):
    """Return list of top-level entries in the tarball."""
    with tarfile.open(path, "r:*") as tar:
        tops = set()
        for m in tar.getmembers():
            # top-level component
            first = m.name.split("/")[0]
            if first and first not in (".",):
                tops.add(first)
        return sorted(tops)


def extract_tarball(tarball, target_parent):
    """Extract tarball into target_parent. Returns path to the extracted top-level dir (if single)."""
    os.makedirs(target_parent, exist_ok=True)
    before = set(os.listdir(target_parent))
    with tarfile.open(tarball, "r:*") as tar:
        safe_extract(tar, target_parent)
    after = set(os.listdir(target_parent))
    new_entries = after - before
    # If a single new top-level dir was created, return it
    if len(new_entries) == 1:
        new = new_entries.pop()
        full = os.path.join(target_parent, new)
        if os.path.isdir(full):
            return full
    # Otherwise return target_parent (extraction dumped files directly)
    return target_parent


def find_executables(directory):
    """Find likely executable files in directory, best candidates first."""
    result = []
    for root, dirs, files in os.walk(directory):
        depth = root[len(directory):].count(os.sep)
        if depth > 3:
            dirs[:] = []
            continue
        for fn in files:
            fp = os.path.join(root, fn)
            if os.access(fp, os.X_OK) and not fn.endswith((".so", ".pyc", ".desktop")):
                result.append((depth, fp, fn))
    # sort: shallower first; prefer name matching dir name; avoid helpers
    base = os.path.basename(directory).lower()
    def key(item):
        depth, fp, fn = item
        name = fn.lower()
        # penalty for helper-ish names
        helper_penalty = 0
        for h in ("crash", "helper", "updater", "crashhelper", "plugin", "sandbox"):
            if h in name:
                helper_penalty += 5
        match_bonus = 0
        if base and (base in name or name in base):
            match_bonus = -10
        # prefer bin/ or root
        return (depth + helper_penalty + match_bonus, name)
    result.sort(key=key)
    return [fp for (_, fp, _) in result]


def find_desktop_files(directory):
    result = []
    for root, dirs, files in os.walk(directory):
        depth = root[len(directory):].count(os.sep)
        if depth > 3:
            dirs[:] = []
            continue
        for fn in files:
            if fn.endswith(".desktop"):
                result.append(os.path.join(root, fn))
    return result


def parse_desktop_name(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("Name="):
                    return line.strip().split("=", 1)[1]
    except Exception:
        pass
    return None


def parse_desktop_exec(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("Exec="):
                    val = line.strip().split("=", 1)[1]
                    # take first token
                    return val.split()[0]
    except Exception:
        pass
    return None


def open_in_file_manager(path):
    try:
        subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def launch(path):
    if os.path.isdir(path):
        return open_in_file_manager(path)
    try:
        subprocess.Popen([path], cwd=os.path.dirname(path))
        return True
    except Exception:
        try:
            subprocess.Popen(["xdg-open", path])
            return True
        except Exception:
            return False


def move_dir(src, dst_parent):
    os.makedirs(dst_parent, exist_ok=True)
    name = os.path.basename(src.rstrip(os.sep))
    dst = os.path.join(dst_parent, name)
    if os.path.exists(dst):
        # unique name
        i = 1
        base = name
        while os.path.exists(dst):
            dst = os.path.join(dst_parent, f"{base}_{i}")
            i += 1
    shutil.move(src, dst)
    return dst


def remove_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
        return True
    return False


def find_icon_files(directory):
    result = []
    for root, dirs, files in os.walk(directory):
        depth = root[len(directory):].count(os.sep)
        if depth > 4:
            dirs[:] = []
            continue
        for fn in files:
            low = fn.lower()
            if low.endswith((".png", ".svg", ".xpm", ".ico")):
                result.append(os.path.join(root, fn))
    return result


def install_icon(app_id, directory, desktop_icon_hint=None):
    """Install an icon for the app into hicolor theme. Returns icon name (app_id) or path."""
    base = os.path.expanduser("~/.local/share/icons/hicolor")
    candidates = []
    if desktop_icon_hint:
        # could be a path or name
        if os.path.isabs(desktop_icon_hint) and os.path.exists(desktop_icon_hint):
            candidates.append(desktop_icon_hint)
    candidates += find_icon_files(directory)
    if not candidates:
        return None
    # prefer svg, then png, then largest png
    svg = [c for c in candidates if c.lower().endswith(".svg")]
    pngs = [c for c in candidates if c.lower().endswith(".png")]
    chosen = None
    if svg:
        chosen = svg[0]
    elif pngs:
        # pick largest by file size
        chosen = max(pngs, key=lambda p: os.path.getsize(p))
    else:
        chosen = candidates[0]

    if chosen.lower().endswith(".svg"):
        target_dir = os.path.join(base, "scalable", "apps")
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, app_id + ".svg")
    else:
        # determine size by reading? default 256x256
        target_dir = os.path.join(base, "256x256", "apps")
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, app_id + ".png")
    shutil.copy2(chosen, target)
    return app_id


def register_desktop(entry):
    """Register app in ~/.local/share/applications (XDG). Works on GNOME/KDE/Cinnamon/COSMIC."""
    apps_dir = os.path.expanduser("~/.local/share/applications")
    os.makedirs(apps_dir, exist_ok=True)
    app_id = "tarlever-" + entry.get("id", "app")
    icon_name = entry.get("icon")
    # if icon is a path or icon_source provided, (re)install icon
    icon_source = entry.get("icon_source")
    if icon_source and os.path.exists(icon_source):
        icon_name = install_icon(app_id, entry.get("install_dir", ""), icon_source)
        entry["icon"] = icon_name
    elif icon_name and os.path.isabs(icon_name) and os.path.exists(icon_name):
        icon_name = install_icon(app_id, entry.get("install_dir", ""), icon_name)
        entry["icon"] = icon_name
    elif not icon_name:
        icon_name = install_icon(app_id, entry.get("install_dir", ""), entry.get("desktop_file"))
        entry["icon"] = icon_name
    name = entry.get("name", "App")
    exec_path = entry.get("executable", "")
    if not exec_path or not os.path.exists(exec_path):
        exec_path = entry.get("install_dir", "")
    desktop_path = os.path.join(apps_dir, app_id + ".desktop")
    categories = entry.get("categories", "Utility;Application;")
    content = f"""[Desktop Entry]
Type=Application
Name={name}
Exec={exec_path} %U
Icon={icon_name if icon_name else "application-x-executable"}
Categories={categories}
Terminal=false
StartupNotify=true
"""
    with open(desktop_path, "w", encoding="utf-8") as f:
        f.write(content)
    entry["desktop_entry"] = desktop_path
    # update db
    try:
        subprocess.run(["update-desktop-database", apps_dir], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    return desktop_path


def unregister_desktop(entry):
    desktop_path = entry.get("desktop_entry")
    if desktop_path and os.path.exists(desktop_path):
        try:
            os.remove(desktop_path)
        except Exception:
            pass
    icon_name = entry.get("icon")
    if icon_name:
        base = os.path.expanduser("~/.local/share/icons/hicolor")
        for sub in ("scalable/apps", "256x256/apps", "128x128/apps", "64x64/apps", "48x48/apps"):
            for ext in (".svg", ".png"):
                p = os.path.join(base, sub, icon_name + ext)
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
    apps_dir = os.path.expanduser("~/.local/share/applications")
    try:
        subprocess.run(["update-desktop-database", apps_dir], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
