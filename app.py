"""Main GTK4 application for Gear Lever for Tar."""

import os
import threading
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from registry import load_registry, save_registry, new_id, now_iso, data_dir
from installer import (
    extract_tarball, find_executables, find_desktop_files,
    parse_desktop_name, parse_desktop_exec, open_in_file_manager, launch, move_dir, remove_dir,
    register_desktop, unregister_desktop, find_icon_files,
)

INSTALL_BASE = os.path.expanduser("~/applications/tarlever")


def ensure_install_base():
    os.makedirs(INSTALL_BASE, exist_ok=True)
    return INSTALL_BASE


class GearLeverForTarApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.example.TarLauncher")
        try:
            Gtk.Window.set_default_icon_name("tarlauncher")
        except Exception:
            pass
        self.entries = load_registry()
        self.win = None

    def do_activate(self):
        if not self.win:
            self.win = MainWindow(self)
        self.win.present()

    def save(self):
        save_registry(self.entries)


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.app = app
        self.set_title("TarLauncher – Gear Lever für Tar Archive")
        self.set_default_size(900, 600)
        try:
            icon_theme = Gtk.IconTheme.get_for_display(self.get_display())
            icon_theme.add_search_path(os.path.dirname(os.path.abspath(__file__)))
            self.set_icon_name("tarlauncher")
        except Exception:
            pass

        header = Adw.HeaderBar()
        title = Adw.WindowTitle(title="TarLauncher", subtitle="Gear Lever für Tar Archive")
        header.set_title_widget(title)

        install_btn = Gtk.Button(label="Installieren")
        install_btn.connect("clicked", self.on_install)
        header.pack_start(install_btn)

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.connect("clicked", lambda b: self.refresh_list())
        header.pack_end(refresh_btn)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.connect("row-activated", self.on_row_activated)
        self.list_box.connect("row-selected", self.on_row_selected)
        scrolled.set_child(self.list_box)
        box.append(scrolled)

        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_bar.set_margin_top(8)
        action_bar.set_margin_bottom(8)
        action_bar.set_margin_start(8)
        action_bar.set_margin_end(8)

        self.open_btn = Gtk.Button(label="Öffnen")
        self.open_btn.connect("clicked", self.on_open)
        self.open_folder_btn = Gtk.Button(label="Ordner öffnen")
        self.open_folder_btn.connect("clicked", self.on_open_folder)
        self.edit_btn = Gtk.Button(label="Bearbeiten")
        self.edit_btn.connect("clicked", self.on_edit)
        self.uninstall_btn = Gtk.Button(label="Deinstallieren")
        self.uninstall_btn.connect("clicked", self.on_uninstall)
        self.uninstall_btn.add_css_class("destructive-action")

        action_bar.append(self.open_btn)
        action_bar.append(self.open_folder_btn)
        action_bar.append(self.edit_btn)
        action_bar.append(self.uninstall_btn)
        box.append(action_bar)

        self.set_content(box)

        self.refresh_list()

    def refresh_list(self):
        while True:
            row = self.list_box.get_row_at_index(0)
            if row is None:
                break
            self.list_box.remove(row)

        for entry in self.app.entries:
            row = self._make_row(entry)
            self.list_box.append(row)

    def _icon_for_entry(self, entry):
        img = Gtk.Image()
        # try icon_source
        src = entry.get("icon_source", "")
        if src and os.path.exists(src):
            try:
                img.set_from_file(src)
                img.set_pixel_size(32)
                return img
            except Exception:
                pass
        # try hicolor installed icon name
        name = entry.get("icon", "")
        if name and not os.path.isabs(name):
            try:
                img.set_from_icon_name(name)
                img.set_pixel_size(32)
                return img
            except Exception:
                pass
        # try icon file in install dir / hicolor path
        if name and os.path.isabs(name) and os.path.exists(name):
            try:
                img.set_from_file(name)
                img.set_pixel_size(32)
                return img
            except Exception:
                pass
        # find any icon in install dir
        try:
            from installer import find_icon_files
            icons = find_icon_files(entry.get("install_dir", ""))
            if icons:
                img.set_from_file(icons[0])
                img.set_pixel_size(32)
                return img
        except Exception:
            pass
        img.set_from_icon_name("application-x-executable-symbolic")
        img.set_pixel_size(32)
        return img

    def _make_row(self, entry):
        row = Adw.ActionRow()
        row.set_title(entry.get("name", "Unbekannt"))
        p = entry.get("install_dir", "")
        typ = ""
        if p:
            # detect type from tarball or dir
            tb = entry.get("tarball", "")
            if tb:
                low = tb.lower()
                if low.endswith((".tar.gz", ".tgz")):
                    typ = "tar.gz"
                elif low.endswith((".tar.xz", ".txz")):
                    typ = "tar.xz"
                elif low.endswith((".tar.bz2", ".tbz2")):
                    typ = "tar.bz2"
                elif low.endswith(".zip"):
                    typ = "zip"
                elif low.endswith(".tar"):
                    typ = "tar"
                else:
                    typ = os.path.splitext(tb)[1].lstrip(".") or "Verzeichnis"
            else:
                typ = "Verzeichnis"
        sub = p
        if typ:
            sub = f"{p}  [{typ}]"
        row.set_subtitle(sub)
        icon = self._icon_for_entry(entry)
        row.add_prefix(icon)
        row.entry_id = entry.get("id")
        return row

    def on_row_selected(self, listbox, row):
        if row is None:
            return
        # avoid reopening if already open
        entry = None
        for e in self.app.entries:
            if e.get("id") == getattr(row, "entry_id", None):
                entry = e
                break
        if entry is None:
            return
        # only open if no detail window already for this entry
        for w in getattr(self, "detail_windows", []):
            if getattr(w, "entry", None) is entry:
                try:
                    w.present()
                except Exception:
                    pass
                return
        win = AppDetailWindow(self, entry)
        self.detail_windows = getattr(self, "detail_windows", [])
        self.detail_windows.append(win)
        win.connect("close-request", lambda w: self.detail_windows.remove(w) if w in self.detail_windows else None)
        win.present()

    def on_row_activated(self, listbox, row):
        self.on_row_selected(listbox, row)
        self.detail_windows = getattr(self, "detail_windows", [])
        self.detail_windows.append(win)
        win.connect("close-request", lambda w: self.detail_windows.remove(w) if w in self.detail_windows else None)
        win.present()

    def _selected_entry(self):
        row = self.list_box.get_selected_row()
        if row is None:
            return None
        for e in self.app.entries:
            if e.get("id") == getattr(row, "entry_id", None):
                return e
        return None

    # ---------- Install flow ----------

    def on_install(self, btn):
        dialog = Adw.MessageDialog(transient_for=self, heading="Was möchtest du installieren?")
        dialog.set_body("Wähle eine Datei (tar.gz, tar.xz, ...) oder ein Verzeichnis.")
        dialog.add_response("file", "Datei auswählen")
        dialog.add_response("dir", "Verzeichnis auswählen")
        dialog.add_response("cancel", "Abbrechen")
        dialog.set_response_appearance("file", Adw.ResponseAppearance.SUGGESTED)

        def on_resp(d, resp):
            d.close()
            if resp == "file":
                self._pick_file()
            elif resp == "dir":
                self._pick_dir()

        dialog.connect("response", on_resp)
        dialog.present()

    def _pick_file(self):
        dialog = Gtk.FileDialog()
        dialog.set_title("Datei auswählen")
        f = Gtk.FileFilter()
        f.set_name("Archive (tar.*, gz, xz, zip)")
        for pat in ("*.tar", "*.tar.gz", "*.tgz", "*.tar.xz", "*.txz", "*.tar.bz2", "*.tbz2", "*.zip"):
            f.add_pattern(pat)
        f2 = Gtk.FileFilter()
        f2.set_name("Alle Dateien")
        f2.add_pattern("*")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f2)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self, None, self._on_file_chosen)

    def _on_file_chosen(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except Exception:
            return
        if file is None:
            return
        self._install_file(file.get_path())

    def _install_file(self, tarball):
        ensure_install_base()
        # show loading
        loading = self._show_loading("Extrahiere Archiv...")
        def work():
            try:
                installed_dir = extract_tarball(tarball, INSTALL_BASE)
                GLib.idle_add(self._finish_file_install, tarball, installed_dir, loading)
            except Exception as e:
                GLib.idle_add(self._loading_error, loading, f"Extraktion fehlgeschlagen: {e}")
        threading.Thread(target=work, daemon=True).start()

    def _finish_file_install(self, tarball, installed_dir, loading):
        self._close_loading(loading)
        name = os.path.basename(installed_dir.rstrip(os.sep))
        desktops = find_desktop_files(installed_dir)
        if desktops:
            dn = parse_desktop_name(desktops[0])
            if dn:
                name = dn
        elif tarball:
            base = os.path.basename(tarball)
            for ext in (".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2", ".tar", ".zip"):
                if base.lower().endswith(ext):
                    base = base[: -len(ext)]
                    break
            # strip version-like suffix
            import re
            base = re.sub(r"[-_]?v?\d+(\.\d+)*$", "", base)
            if base:
                name = base
        execs = find_executables(installed_dir)
        if desktops:
            de = parse_desktop_exec(desktops[0])
            if de:
                cand = de if os.path.isabs(de) else os.path.join(installed_dir, de)
                if os.path.exists(cand) and cand not in execs:
                    execs.insert(0, cand)
                elif cand in execs:
                    execs.remove(cand)
                    execs.insert(0, cand)
        self._show_install_confirm(tarball, installed_dir, name, execs, desktops)
        return False

    def _pick_dir(self):
        dialog = Gtk.FileDialog()
        dialog.set_title("Verzeichnis auswählen")
        dialog.select_folder(self, None, self._on_dir_chosen)

    def _on_dir_chosen(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except Exception:
            return
        if folder is None:
            return
        self._install_dir(folder.get_path())

    def _install_dir(self, src_dir):
        ensure_install_base()
        loading = self._show_loading("Verschiebe Verzeichnis...")
        def work():
            try:
                new_dir = move_dir(src_dir, INSTALL_BASE)
                GLib.idle_add(self._finish_dir_install, src_dir, new_dir, loading)
            except Exception as e:
                GLib.idle_add(self._loading_error, loading, f"Verschieben fehlgeschlagen: {e}")
        threading.Thread(target=work, daemon=True).start()

    def _finish_dir_install(self, src_dir, new_dir, loading):
        self._close_loading(loading)
        name = os.path.basename(new_dir.rstrip(os.sep))
        desktops = find_desktop_files(new_dir)
        if desktops:
            dn = parse_desktop_name(desktops[0])
            if dn:
                name = dn
        execs = find_executables(new_dir)
        if desktops:
            de = parse_desktop_exec(desktops[0])
            if de:
                cand = de if os.path.isabs(de) else os.path.join(new_dir, de)
                if os.path.exists(cand) and cand not in execs:
                    execs.insert(0, cand)
                elif cand in execs:
                    execs.remove(cand)
                    execs.insert(0, cand)
        self._show_install_confirm("", new_dir, name, execs, desktops)
        return False

    def _show_install_confirm(self, tarball, installed_dir, name, execs, desktops):
        dialog = Adw.MessageDialog(transient_for=self, heading="Installation bestätigen")
        dialog.set_body(f"App: {name}\nOrdner: {installed_dir}")

        name_entry = Gtk.Entry()
        name_entry.set_text(name)

        exec_strings = [os.path.relpath(e, installed_dir) for e in execs] if execs else [""]
        model = Gtk.StringList.new(exec_strings)
        exec_combo = Gtk.DropDown()
        exec_combo.set_model(model)
        if execs:
            exec_combo.set_selected(0)

        choose_exec_btn = Gtk.Button(label="Ausführungsdatei wählen...")
        chosen_exec = {"path": execs[0] if execs else ""}

        def on_choose_exec(b):
            fd = Gtk.FileDialog()
            fd.set_title("Ausführungsdatei wählen")
            fd.open(self, None, lambda d, r: _on_exec_chosen(d, r))

        def _on_exec_chosen(d, r):
            try:
                f = d.open_finish(r)
            except Exception:
                return
            if f is None:
                return
            p = f.get_path()
            chosen_exec["path"] = p
            # add to combo model? just store; update exec_strings display
            rel = os.path.relpath(p, installed_dir) if p.startswith(installed_dir) else p
            if rel not in exec_strings:
                exec_strings.append(rel)
                m2 = Gtk.StringList.new(exec_strings)
                exec_combo.set_model(m2)
                exec_combo.set_selected(len(exec_strings) - 1)

        choose_exec_btn.connect("clicked", on_choose_exec)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(8)
        nl = Gtk.Label(label="Name:")
        nl.set_halign(Gtk.Align.START)
        box.append(nl)
        box.append(name_entry)
        el = Gtk.Label(label="Startdatei (optional):")
        el.set_halign(Gtk.Align.START)
        box.append(el)
        box.append(exec_combo)
        info = Gtk.Label(label=f"Gefundene Startdateien: {len(execs)}")
        info.set_halign(Gtk.Align.START)
        info.add_css_class("dim-label")
        box.append(info)
        box.append(choose_exec_btn)
        reg_check = Gtk.CheckButton(label="Im System registrieren (Desktop-Entry)")
        reg_check.set_active(True)
        box.append(reg_check)
        dialog.set_extra_child(box)

        dialog.add_response("cancel", "Abbrechen")
        dialog.add_response("install", "Installieren")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)

        def on_resp(d, resp):
            if resp != "install":
                d.close()
                return
            chosen_name = name_entry.get_text().strip() or name
            sel = exec_combo.get_selected()
            exec_rel = exec_strings[sel] if exec_strings and sel < len(exec_strings) else ""
            if chosen_exec["path"]:
                exec_path = chosen_exec["path"]
            elif exec_rel and exec_rel != "":
                exec_path = os.path.join(installed_dir, exec_rel)
            else:
                exec_path = ""
            entry = {
                "id": new_id(),
                "name": chosen_name,
                "tarball": tarball,
                "install_dir": installed_dir,
                "executable": exec_path,
                "desktop_file": desktops[0] if desktops else "",
                "installed_at": now_iso(),
            }
            self.app.entries.append(entry)
            if reg_check.get_active():
                try:
                    register_desktop(entry)
                except Exception as e:
                    print("register failed", e)
            self.app.save()
            self.refresh_list()
            d.close()

        dialog.connect("response", on_resp)
        dialog.present()

    # ---------- Loading ----------

    def _show_loading(self, msg):
        dialog = Adw.MessageDialog(transient_for=self, heading=msg)
        spinner = Gtk.Spinner()
        spinner.start()
        spinner.set_size_request(32, 32)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_halign(Gtk.Align.CENTER)
        box.append(spinner)
        dialog.set_extra_child(box)
        dialog.present()
        return dialog

    def _close_loading(self, dialog):
        try:
            dialog.close()
        except Exception:
            pass

    def _loading_error(self, loading, msg):
        self._close_loading(loading)
        self._show_error(msg)
        return False

    # ---------- Actions ----------

    def on_open(self, btn):
        entry = self._selected_entry()
        if entry is None:
            self._show_error("Bitte eine App auswählen.")
            return
        exec_path = entry.get("executable", "")
        target = exec_path if (exec_path and os.path.exists(exec_path)) else entry.get("install_dir", "")
        if not launch(target):
            self._show_error("Konnte nicht öffnen.")

    def on_open_folder(self, btn):
        entry = self._selected_entry()
        if entry is None:
            self._show_error("Bitte eine App auswählen.")
            return
        d = entry.get("install_dir", "")
        if d and os.path.exists(d):
            if not open_in_file_manager(d):
                self._show_error("Konnte Ordner nicht öffnen.")
        else:
            self._show_error("Ordner nicht gefunden.")

    def on_uninstall_entry(self, entry):
        dialog = Adw.MessageDialog(transient_for=self, heading="Deinstallieren?")
        dialog.set_body(f"{entry.get('name')} und Ordner {entry.get('install_dir')} werden gelöscht.")
        dialog.add_response("cancel", "Abbrechen")
        dialog.add_response("del", "Deinstallieren")
        dialog.set_response_appearance("del", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_resp(d, resp):
            if resp != "del":
                d.close()
                return
            loading = self._show_loading("Lösche...")
            def work():
                try:
                    unregister_desktop(entry)
                except Exception:
                    pass
                remove_dir(entry.get("install_dir", ""))
                GLib.idle_add(self._finish_uninstall, entry, loading)
            threading.Thread(target=work, daemon=True).start()
            d.close()

        dialog.connect("response", on_resp)
        dialog.present()

    def on_uninstall(self, btn):
        entry = self._selected_entry()
        if entry is None:
            self._show_error("Bitte eine App auswählen.")
            return
        self.on_uninstall_entry(entry)

    def _finish_uninstall(self, entry, loading):
        self._close_loading(loading)
        self.app.entries = [e for e in self.app.entries if e.get("id") != entry.get("id")]
        self.app.save()
        self.refresh_list()
        return False

    def on_edit(self, btn):
        entry = self._selected_entry()
        if entry is None:
            self._show_error("Bitte eine App auswählen.")
            return
        dialog = Adw.MessageDialog(transient_for=self, heading="App bearbeiten")
        name_entry = Gtk.Entry()
        name_entry.set_text(entry.get("name", ""))
        desc_entry = Gtk.Entry()
        desc_entry.set_text(entry.get("description", ""))
        version_entry = Gtk.Entry()
        version_entry.set_text(entry.get("version", ""))
        exec_entry = Gtk.Entry()
        exec_entry.set_text(entry.get("executable", ""))
        icon_entry = Gtk.Entry()
        icon_entry.set_text(entry.get("icon", "") or entry.get("icon_source", ""))
        cat_entry = Gtk.Entry()
        cat_entry.set_text(entry.get("categories", "Utility;Application;"))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(8)
        for lbl, w in [("Name:", name_entry), ("Beschreibung:", desc_entry), ("Version:", version_entry), ("Startdatei:", exec_entry), ("Icon (Name/Pfad):", icon_entry), ("Kategorien:", cat_entry)]:
            l = Gtk.Label(label=lbl)
            l.set_halign(Gtk.Align.START)
            box.append(l)
            box.append(w)

        reload_btn = Gtk.Button(label="Metadaten neu laden")
        def _reload(b):
            self.on_reload_metadata_for(entry)
            name_entry.set_text(entry.get("name", ""))
            desc_entry.set_text(entry.get("description", ""))
            version_entry.set_text(entry.get("version", ""))
            exec_entry.set_text(entry.get("executable", ""))
            icon_entry.set_text(entry.get("icon", "") or entry.get("icon_source", ""))
            cat_entry.set_text(entry.get("categories", "Utility;Application;"))
        reload_btn.connect("clicked", _reload)
        box.append(reload_btn)

        # icon picker
        def pick_icon(b):
            fd = Gtk.FileDialog()
            fd.set_title("Icon auswählen")
            f = Gtk.FileFilter()
            f.set_name("Bilder")
            for pat in ("*.png", "*.svg", "*.xpm", "*.ico"):
                f.add_pattern(pat)
            f2 = Gtk.FileFilter()
            f2.set_name("Alle Dateien")
            f2.add_pattern("*")
            filters = Gio.ListStore.new(Gtk.FileFilter)
            filters.append(f2)
            filters.append(f)
            fd.set_filters(filters)
            fd.open(self, None, lambda d, r: _on_icon(d, r))

        def _on_icon(d, r):
            try:
                f = d.open_finish(r)
            except Exception:
                return
            if f is None:
                return
            src = f.get_path()
            # copy into app dir so it stays portable
            try:
                import shutil
                ext = os.path.splitext(src)[1].lower() or ".png"
                target = os.path.join(entry.get("install_dir", ""), "app-icon" + ext)
                shutil.copy2(src, target)
                entry["icon_source"] = target
                icon_entry.set_text(target)
            except Exception:
                icon_entry.set_text(src)

        ib = Gtk.Button(label="Icon-Datei wählen…")
        ib.connect("clicked", pick_icon)
        box.append(ib)

        reg_check = Gtk.CheckButton(label="Im System registriert")
        reg_check.set_active(bool(entry.get("desktop_entry")))
        box.append(reg_check)

        dialog.set_extra_child(box)
        dialog.add_response("cancel", "Abbrechen")
        dialog.add_response("save", "Speichern")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)

        def on_resp(d, resp):
            if resp != "save":
                d.close()
                return
            entry["name"] = name_entry.get_text().strip() or entry.get("name", "")
            entry["description"] = desc_entry.get_text().strip()
            entry["version"] = version_entry.get_text().strip()
            entry["executable"] = exec_entry.get_text().strip()
            ic = icon_entry.get_text().strip()
            if ic and os.path.exists(ic):
                entry["icon_source"] = ic
                entry["icon"] = ""
            else:
                entry["icon"] = ic
                entry["icon_source"] = ""
            entry["categories"] = cat_entry.get_text().strip() or "Utility;Application;"
            # update system registration
            if reg_check.get_active():
                try:
                    register_desktop(entry)
                except Exception as e:
                    print("register failed", e)
            else:
                try:
                    unregister_desktop(entry)
                except Exception:
                    pass
                entry["desktop_entry"] = ""
            self.app.save()
            self.refresh_list()
            d.close()

        dialog.connect("response", on_resp)
        dialog.present()

    def on_update_entry(self, entry):
        # open method chooser for given entry
        dialog = Adw.MessageDialog(transient_for=self, heading="App aktualisieren")
        dialog.set_body("Wähle die Aktualisierungsmethode.")
        dialog.add_response("file", "Aus Datei")
        dialog.add_response("dir", "Aus Verzeichnis")
        dialog.add_response("cancel", "Abbrechen")
        dialog.set_response_appearance("file", Adw.ResponseAppearance.SUGGESTED)

        def on_resp(d, resp):
            d.close()
            if resp == "file":
                self._pick_update_file(entry)
            elif resp == "dir":
                self._pick_update_dir(entry)

        dialog.connect("response", on_resp)
        dialog.present()

    def on_update(self, btn):
        entry = self._selected_entry()
        if entry is None:
            self._show_error("Bitte eine App auswählen.")
            return
        self.on_update_entry(entry)
        if entry is None:
            self._show_error("Bitte eine App auswählen.")
            return
        dialog = Adw.MessageDialog(transient_for=self, heading="App aktualisieren")
        dialog.set_body("Wähle die Aktualisierungsmethode.")
        dialog.add_response("file", "Aus Datei")
        dialog.add_response("dir", "Aus Verzeichnis")
        dialog.add_response("cancel", "Abbrechen")
        dialog.set_response_appearance("file", Adw.ResponseAppearance.SUGGESTED)

        def on_resp(d, resp):
            d.close()
            if resp == "file":
                self._pick_update_file(entry)
            elif resp == "dir":
                self._pick_update_dir(entry)

        dialog.connect("response", on_resp)
        dialog.present()

    def _pick_update_file(self, entry):
        dialog = Gtk.FileDialog()
        dialog.set_title("Neue Datei auswählen")
        f = Gtk.FileFilter()
        f.set_name("Alle Dateien")
        f.add_pattern("*")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self, None, lambda dd, res: self._on_update_file_chosen(dd, res, entry))

    def _on_update_file_chosen(self, dialog, result, entry):
        try:
            file = dialog.open_finish(result)
        except Exception:
            return
        if file is None:
            return
        self._do_update_file(entry, file.get_path())

    def _do_update_file(self, entry, tarball):
        import tempfile, shutil
        loading = self._show_loading("Aktualisiere...")
        def work():
            try:
                tmp_parent = tempfile.mkdtemp(prefix="tv_upd_")
                new_dir = extract_tarball(tarball, tmp_parent)
                old_dir = entry["install_dir"]
                if os.path.exists(old_dir):
                    shutil.rmtree(old_dir)
                if new_dir == tmp_parent:
                    os.makedirs(old_dir, exist_ok=True)
                    for item in os.listdir(tmp_parent):
                        shutil.move(os.path.join(tmp_parent, item), os.path.join(old_dir, item))
                else:
                    shutil.move(new_dir, old_dir)
                shutil.rmtree(tmp_parent, ignore_errors=True)
                GLib.idle_add(self._finish_update, entry, tarball, loading)
            except Exception as e:
                GLib.idle_add(self._loading_error, loading, f"Aktualisierung fehlgeschlagen: {e}")
        threading.Thread(target=work, daemon=True).start()

    def _pick_update_dir(self, entry):
        dialog = Gtk.FileDialog()
        dialog.set_title("Neues Verzeichnis auswählen")
        dialog.select_folder(self, None, lambda dd, res: self._on_update_dir_chosen(dd, res, entry))

    def _on_update_dir_chosen(self, dialog, result, entry):
        try:
            folder = dialog.select_folder_finish(result)
        except Exception:
            return
        if folder is None:
            return
        self._do_update_dir(entry, folder.get_path())

    def _do_update_dir(self, entry, src_dir):
        import tempfile, shutil
        loading = self._show_loading("Aktualisiere...")
        def work():
            try:
                tmp_parent = tempfile.mkdtemp(prefix="tv_upd_")
                new_dir = os.path.join(tmp_parent, os.path.basename(src_dir.rstrip(os.sep)))
                shutil.copytree(src_dir, new_dir)
                old_dir = entry["install_dir"]
                if os.path.exists(old_dir):
                    shutil.rmtree(old_dir)
                shutil.move(new_dir, old_dir)
                shutil.rmtree(tmp_parent, ignore_errors=True)
                GLib.idle_add(self._finish_update, entry, "", loading)
            except Exception as e:
                GLib.idle_add(self._loading_error, loading, f"Aktualisierung fehlgeschlagen: {e}")
        threading.Thread(target=work, daemon=True).start()

    def _finish_update(self, entry, tarball, loading):
        self._close_loading(loading)
        if tarball:
            entry["tarball"] = tarball
        self.on_reload_metadata_for(entry)
        if entry.get("desktop_entry"):
            try:
                register_desktop(entry)
            except Exception:
                pass
        self.app.save()
        self.refresh_list()
        self._refresh_detail_windows()
        return False

    def on_reload_metadata(self, btn):
        entry = self._selected_entry()
        if entry is None:
            self._show_error("Bitte eine App auswählen.")
            return
        self.on_reload_metadata_for(entry)
        if entry.get("desktop_entry"):
            try:
                register_desktop(entry)
            except Exception:
                pass
        self.app.save()
        self.refresh_list()

    def on_reload_metadata_for(self, entry):
        d = entry.get("install_dir", "")
        desktops = find_desktop_files(d)
        if desktops:
            dn = parse_desktop_name(desktops[0])
            if dn:
                entry["name"] = dn
            de = parse_desktop_exec(desktops[0])
            if de:
                cand = de if os.path.isabs(de) else os.path.join(d, de)
                if os.path.exists(cand):
                    entry["executable"] = cand
            entry["desktop_file"] = desktops[0]
        else:
            execs = find_executables(d)
            if execs:
                entry["executable"] = execs[0]
        icons = find_icon_files(d)
        if icons and not entry.get("icon_source"):
            entry["icon_source"] = icons[0]
        entry["installed_at"] = now_iso()

    def _refresh_detail_windows(self):
        for w in getattr(self, "detail_windows", []):
            try:
                w._reload_fields()
            except Exception:
                pass

    def _show_error(self, msg):
        dialog = Adw.MessageDialog(transient_for=self, heading="Fehler")
        dialog.set_body(msg)
        dialog.add_response("ok", "OK")
        dialog.present()


class AppDetailWindow(Adw.Window):
    def __init__(self, main_win, entry):
        super().__init__()
        self.main_win = main_win
        self.app = main_win.app
        self.entry = entry
        self.set_title(f"TarLauncher – {entry.get('name', '')}")
        self.set_default_size(700, 720)
        self.set_modal(True)
        self.set_transient_for(main_win)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # icon preview
        icon_img = main_win._icon_for_entry(entry)
        icon_img.set_pixel_size(64)
        icon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        icon_box.set_halign(Gtk.Align.CENTER)
        icon_box.append(icon_img)
        box.append(icon_box)

        # fields
        self.name_entry = Gtk.Entry(); self.name_entry.set_text(entry.get("name", ""))
        self.desc_entry = Gtk.Entry(); self.desc_entry.set_text(entry.get("description", ""))
        self.version_entry = Gtk.Entry(); self.version_entry.set_text(entry.get("version", ""))
        self.exec_entry = Gtk.Entry(); self.exec_entry.set_text(entry.get("executable", ""))
        self.icon_entry = Gtk.Entry(); self.icon_entry.set_text(entry.get("icon", "") or entry.get("icon_source", ""))
        self.cat_entry = Gtk.Entry(); self.cat_entry.set_text(entry.get("categories", "Utility;Application;"))
        self.path_label = Gtk.Label(label=entry.get("install_dir", ""))
        self.path_label.set_wrap(True)
        self.path_label.set_selectable(True)

        for lbl, w in [("Name:", self.name_entry), ("Beschreibung:", self.desc_entry), ("Version:", self.version_entry),
                       ("Startdatei:", self.exec_entry), ("Icon:", self.icon_entry), ("Kategorien:", self.cat_entry)]:
            l = Gtk.Label(label=lbl); l.set_halign(Gtk.Align.START)
            box.append(l); box.append(w)
        pl = Gtk.Label(label="Installationspfad:")
        pl.set_halign(Gtk.Align.START)
        box.append(pl); box.append(self.path_label)

        # system registration toggle
        self.reg_check = Gtk.CheckButton(label="Im System registriert")
        self.reg_check.set_active(bool(entry.get("desktop_entry")))
        box.append(self.reg_check)

        # action buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.CENTER)
        open_btn = Gtk.Button(label="Öffnen")
        open_btn.connect("clicked", lambda b: self._open())
        folder_btn = Gtk.Button(label="Ordner")
        folder_btn.connect("clicked", lambda b: self._open_folder())
        choose_exec_btn = Gtk.Button(label="Startdatei wählen…")
        choose_exec_btn.connect("clicked", lambda b: self._choose_exec())
        reload_btn = Gtk.Button(label="Metadaten neu laden")
        reload_btn.connect("clicked", lambda b: self._reload())
        save_btn = Gtk.Button(label="Speichern")
        save_btn.connect("clicked", lambda b: self._save())
        save_btn.add_css_class("suggested-action")
        uninst_btn = Gtk.Button(label="Deinstallieren")
        uninst_btn.add_css_class("destructive-action")
        uninst_btn.connect("clicked", lambda b: self._uninstall())
        for b in (open_btn, folder_btn, choose_exec_btn, reload_btn, save_btn, uninst_btn):
            btn_box.append(b)
        box.append(btn_box)

        # update buttons
        upd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        upd_box.set_halign(Gtk.Align.CENTER)
        upd_file_btn = Gtk.Button(label="Aktualisieren (Datei)")
        upd_file_btn.connect("clicked", lambda b: self._update_file())
        upd_dir_btn = Gtk.Button(label="Aktualisieren (Verzeichnis)")
        upd_dir_btn.connect("clicked", lambda b: self._update_dir())
        for b in (upd_file_btn, upd_dir_btn):
            upd_box.append(b)
        box.append(upd_box)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(box)
        toolbar.set_content(scrolled)
        self.set_content(toolbar)

    def _open(self):
        exec_path = self.entry.get("executable", "")
        target = exec_path if (exec_path and os.path.exists(exec_path)) else self.entry.get("install_dir", "")
        launch(target)

    def _open_folder(self):
        open_in_file_manager(self.entry.get("install_dir", ""))

    def _choose_exec(self):
        fd = Gtk.FileDialog()
        fd.set_title("Startdatei wählen")
        fd.open(self, None, lambda d, r: self._on_exec_chosen(d, r))

    def _on_exec_chosen(self, d, r):
        try:
            f = d.open_finish(r)
        except Exception:
            return
        if f is None:
            return
        self.exec_entry.set_text(f.get_path())

    def _update_file(self):
        fd = Gtk.FileDialog()
        fd.set_title("Neue Datei auswählen")
        f = Gtk.FileFilter(); f.set_name("Alle Dateien"); f.add_pattern("*")
        filters = Gio.ListStore.new(Gtk.FileFilter); filters.append(f)
        fd.set_filters(filters)
        fd.open(self, None, lambda d, r: self._on_update_file(d, r))

    def _on_update_file(self, d, r):
        try:
            f = d.open_finish(r)
        except Exception:
            return
        if f is None:
            return
        self.main_win._do_update_file(self.entry, f.get_path())

    def _update_dir(self):
        fd = Gtk.FileDialog()
        fd.set_title("Neues Verzeichnis auswählen")
        fd.select_folder(self, None, lambda d, r: self._on_update_dir(d, r))

    def _on_update_dir(self, d, r):
        try:
            folder = d.select_folder_finish(r)
        except Exception:
            return
        if folder is None:
            return
        self.main_win._do_update_dir(self.entry, folder.get_path())

    def _reload_fields(self):
        e = self.entry
        self.name_entry.set_text(e.get("name", ""))
        self.desc_entry.set_text(e.get("description", ""))
        self.version_entry.set_text(e.get("version", ""))
        self.exec_entry.set_text(e.get("executable", ""))
        self.icon_entry.set_text(e.get("icon", "") or e.get("icon_source", ""))
        self.cat_entry.set_text(e.get("categories", "Utility;Application;"))
        self.path_label.set_text(e.get("install_dir", ""))

    def _update(self):
        # delegate to main window update flow for this entry
        self.main_win.on_update_entry(self.entry)

    def _reload(self):
        self.main_win.on_reload_metadata_for(self.entry)
        # refresh fields
        self.name_entry.set_text(self.entry.get("name", ""))
        self.desc_entry.set_text(self.entry.get("description", ""))
        self.version_entry.set_text(self.entry.get("version", ""))
        self.exec_entry.set_text(self.entry.get("executable", ""))
        self.icon_entry.set_text(self.entry.get("icon", "") or self.entry.get("icon_source", ""))
        self.cat_entry.set_text(self.entry.get("categories", "Utility;Application;"))
        self.main_win.app.save()
        self.main_win.refresh_list()

    def _save(self):
        e = self.entry
        e["name"] = self.name_entry.get_text().strip() or e.get("name", "")
        e["description"] = self.desc_entry.get_text().strip()
        e["version"] = self.version_entry.get_text().strip()
        e["executable"] = self.exec_entry.get_text().strip()
        ic = self.icon_entry.get_text().strip()
        if ic and os.path.exists(ic):
            e["icon_source"] = ic
            e["icon"] = ""
        else:
            e["icon"] = ic
            e["icon_source"] = ""
        e["categories"] = self.cat_entry.get_text().strip() or "Utility;Application;"
        if self.reg_check.get_active():
            try:
                register_desktop(e)
            except Exception:
                pass
        else:
            try:
                unregister_desktop(e)
            except Exception:
                pass
            e["desktop_entry"] = ""
        self.main_win.app.save()
        self.main_win.refresh_list()
        self.close()

    def _uninstall(self):
        self.main_win.on_uninstall_entry(self.entry)
        self.close()
