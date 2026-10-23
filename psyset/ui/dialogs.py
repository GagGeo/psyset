"""Dialogs: first launch / library choice, test form (add / edit), assign role, remove."""
import os
import sys
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from psyset import manage
from psyset.config import save_config
from psyset.i18n import t
from psyset.library import (SUPPORTED, Instrument, LibraryMissing, list_domains, parse_role,
                             scan_library)
from psyset.manage import AlreadyExists, InvalidName, _key, holds_role, sanitize_folder_name
from psyset.ui.theme import C, Fonts, setup_styles

# role -> (title key, several files allowed); test/rating files carry version labels
SECTIONS = {"test": ("f_sheets", True), "rating": ("f_crfs", True),
            "instructions": ("f_instr", False), "norms": ("f_norms", True)}
LABELLED = ("test", "rating")
_DOC_TYPES = [("PDF, Word, ODT", " ".join(f"*{e}" for e in sorted(SUPPORTED)))]


# ----------------------------------------------------------------- pure logic --
def next_label(used) -> str:
    """First free version label: A…Z, then 1, 2, …"""
    taken = {u.strip().casefold() for u in used}
    for c in map(chr, range(ord("A"), ord("Z") + 1)):
        if c.casefold() not in taken:
            return c
    n = 1
    while str(n) in taken:
        n += 1
    return str(n)


def trash_word(lang: str, platform: str = sys.platform) -> str:
    return t(lang, "trash_win" if platform == "win32" else "trash")


def library_problem(cfg: dict) -> str | None:
    """None: the configured library scans. "": none configured. Else the path (+ OS reason)."""
    lib = cfg.get("library")
    if not (isinstance(lib, str) and lib):
        return ""
    try:
        scan_library(Path(lib))
    except LibraryMissing:
        return lib
    except OSError as e:  # e.g. offline OneDrive or external drive
        return f"{lib}\n{e.strerror or e}"
    return None


def form_error(lang: str, name: str, domain: str) -> str | None:
    """Validation message for the test form's name and domain, or None."""
    if not name.strip():
        return t(lang, "err_name_empty")
    if not domain.strip():
        return t(lang, "err_domain_empty")
    try:
        sanitize_folder_name(name)
        sanitize_folder_name(domain)
    except InvalidName:
        return t(lang, "err_name_invalid")
    return None


def role_labels(files, role: str) -> list[str]:
    """Version labels that `files` hold for `role` ("" = unlabelled)."""
    return [found[1] for f in files if (found := parse_role(f.stem)) and found[0] == role]


def _clean(label: str) -> str:
    try:
        return sanitize_folder_name(label) if label else ""
    except InvalidName:
        return label


def plan_files(lang: str, role: str, rows: list[dict], others: list[Path]):
    """What saving does to one role's files, decided before anything is written.
    rows: {"path": existing file | None, "src": picked file | None, "current": its label on
    disk, "label": label typed}. others: files of the test folder the form does not list.
    Returns (ops, error): ops are ("put", src, label, replaced file | None) and
    ("rename", path, label); error is the message that must stop the save, or None."""
    labelled, n = role in LABELLED, len(rows)

    def final_label(r: dict) -> str:
        if not labelled:
            return ""
        typed = r["label"].strip()
        # untouched (the entry shows a stray space stripped): keep the label on disk
        return r["current"] if n <= 1 or typed == r["current"].strip() else typed
    finals = [final_label(r) for r in rows]
    keys = []
    for f in finals:
        try:
            keys.append(_key(sanitize_folder_name(f)) if f else "")  # manage's rule
        except InvalidName:
            keys.append(None)
    title = t(lang, SECTIONS[role][0])
    ops = []
    for i, (r, final) in enumerate(zip(rows, finals)):
        relabel = labelled and (r["path"] is None or final != r["current"])
        if relabel:  # only labels that change are checked: an odd existing state never blocks
            if n > 1 and not final:
                return [], t(lang, "err_label_empty", role=title)
            if keys[i] is None:
                return [], t(lang, "err_label_invalid", label=final)
            if keys[i] in keys[:i] + keys[i + 1:]:
                return [], t(lang, "err_label_dup", label=final, role=title)
        if (relabel or r["src"]) and role != "norms":  # norms never replace anything
            clash = next((o for o in others if holds_role(o, role, _clean(final))), None)
            if clash:
                return [], t(lang, "err_hidden_file", file=clash.name)
        if role == "instructions" and r["src"]:  # replaces only its own row's file
            target = _key("instructions" + r["src"].suffix.lower())
            clash = next((o["path"] for o in rows if o is not r and o["path"]
                          and _key(o["path"].name) == target), None)
            if clash:
                return [], t(lang, "err_file_exists", file=clash.name)
        if r["src"]:
            ops.append(("put", r["src"], final, r["path"]))
        elif r["path"] and final != r["current"]:
            ops.append(("rename", r["path"], final))
    return ops, None


class ParkedFiles(Exception):
    """Saving failed and these files of the test folder could not get their name back."""

    def __init__(self, names: list[str]):
        self.names = names
        super().__init__(", ".join(names))


def apply_plans(folder: Path, plans: dict[str, list]) -> None:
    """Edit mode, after the info step (`folder` may have moved). Relabelled files wait under
    visible temp names while files are put, so labels can swap and never meet a stale file;
    a leftover (crash) shows up as an unclassified file, never hidden. ParkedFiles if a
    failure leaves some of them under their temp name."""
    moved = lambda p: folder / p.name
    parked = []  # (temp, role, label, original)
    try:
        for role, ops in plans.items():
            for op in ops:
                if op[0] == "rename":
                    tmp = folder / f"psyset-parked-{uuid.uuid4().hex[:8]}-{op[1].name}"
                    os.rename(moved(op[1]), tmp)
                    parked.append((tmp, role, op[2], moved(op[1])))
        for role, ops in plans.items():
            for op in ops:
                if op[0] == "put":
                    _, src, label, old = op
                    dest = manage.put_file(folder, role, src, label,
                                           replaces=moved(old) if old else None)
                    if old and moved(old) != dest and moved(old).exists():
                        manage.remove_file(moved(old))  # replaced under another name
        while parked:
            tmp, role, label, _ = parked[0]
            manage.assign_role(tmp, role, label)
            parked.pop(0)
    finally:
        lost = []
        for tmp, _, _, original in parked:  # a failure must not leave a file renamed
            try:
                os.rename(tmp, original if not original.exists()
                          else original.with_name("restored-" + original.name))
            except OSError:
                lost.append(tmp.name)
        if lost:
            raise ParkedFiles(lost)


# -------------------------------------------------------------------- helpers --
def _modal(top: tk.Toplevel, master: tk.Misc) -> None:
    top.resizable(False, False)
    if master.winfo_viewable():  # transient to a withdrawn root would hide the dialog
        top.transient(master)
        top.geometry(f"+{master.winfo_rootx() + 80}+{master.winfo_rooty() + 60}")
    try:
        top.wait_visibility()
        top.grab_set()
    except tk.TclError:
        pass


def _error(parent, lang: str, msg: str) -> None:
    messagebox.showerror(t(lang, "err_title"), msg, parent=parent)


# --------------------------------------------------------------- first launch --
class LibraryDialog(tk.Toplevel):
    """FR/EN first, then use an existing tests folder or create a starter library."""

    def __init__(self, master, cfg: dict, change: bool = False):
        super().__init__(master, bg=C["bg"])
        self.cfg, self.change, self.ok = cfg, change, False
        self.lang = cfg.get("lang") if cfg.get("lang") in ("fr", "en") else "fr"
        self.problem = library_problem(cfg)
        self.fonts = Fonts(self)
        self._body = None
        self._build()
        _modal(self, master)

    def _t(self, key: str, **fmt) -> str:
        return t(self.lang, key, **fmt)

    def set_lang(self, lang: str) -> None:
        self.lang = lang
        self._build()

    def _build(self) -> None:
        if self._body is not None:
            self._body.destroy()
        self.title(self._t("settings_change_lib" if self.change else "fl_title"))
        b = self._body = ttk.Frame(self, padding=(26, 20, 26, 22))
        b.pack(fill="both", expand=True)
        b.columnconfigure(0, weight=1)
        head = ttk.Frame(b)
        head.grid(row=0, column=0, sticky="we", pady=(0, 12))
        head.columnconfigure(0, weight=1)
        ttk.Label(head, text="PsySet", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        langs = ttk.Frame(head)
        langs.grid(row=0, column=1, sticky="ne")
        for code in ("fr", "en"):
            ttk.Button(langs, text=code.upper(), width=3,
                       style="LangActive.TButton" if self.lang == code else "Lang.TButton",
                       command=lambda c=code: self.set_lang(c)).pack(side="left", padx=(0, 3))
        ttk.Label(b, text=self._t("fl_title"), style="PanelTitle.TLabel").grid(
            row=1, column=0, sticky="w")
        if self.problem:
            warn = tk.Frame(b, bg=C["warn_bg"], highlightbackground=C["warn_bd"],
                            highlightthickness=1)
            warn.grid(row=2, column=0, sticky="we", pady=(10, 0))
            tk.Label(warn, text="●", bg=C["warn_bg"], fg=C["warn_dot"],
                     font=(self.fonts.sans, 8)).pack(side="left", padx=(10, 6), pady=7)
            ttk.Label(warn, text=self._t("fl_missing", path=self.problem), style="Warn.TLabel",
                      wraplength=400, justify="left").pack(side="left", pady=7, padx=(0, 10))
        ttk.Label(b, text=self._t("fl_intro")).grid(row=3, column=0, sticky="w", pady=(14, 10))
        ttk.Button(b, text=self._t("fl_use_existing"), style="Accent.TButton",
                   command=self.use_existing).grid(row=4, column=0, sticky="we")
        ttk.Button(b, text=self._t("fl_create_new"), style="Small.TButton",
                   command=self.create_new).grid(row=5, column=0, sticky="we", pady=(8, 0))
        ttk.Button(b, text=self._t("btn_cancel" if self.change else "fl_quit"),
                   style="Small.TButton", command=self.destroy).grid(
            row=6, column=0, sticky="e", pady=(18, 0))

    def use_existing(self) -> None:
        folder = filedialog.askdirectory(parent=self, mustexist=True,
                                         title=self._t("fl_pick_folder"))
        if not folder:
            return
        self.problem = library_problem({"library": folder})
        if self.problem is None:
            self._finish(Path(folder))
        else:
            self._build()

    def create_new(self) -> None:
        parent = filedialog.askdirectory(parent=self, mustexist=True,
                                         title=self._t("fl_pick_parent"))
        if not parent:
            return
        name = simpledialog.askstring(self._t("fl_create_new"), self._t("fl_new_name"),
                                      initialvalue=self._t("fl_default_name"), parent=self)
        if name is None:
            return
        try:
            target = Path(parent) / sanitize_folder_name(name)
        except InvalidName:
            return _error(self, self.lang, self._t("err_name_invalid"))
        if target.exists():
            return _error(self, self.lang, self._t("err_lib_exists", path=str(target)))
        try:
            manage.create_starter_library(target, self.lang)
        except OSError as e:
            return _error(self, self.lang, self._t("err_save", reason=e))
        self._finish(target)

    def _finish(self, library: Path) -> None:
        self.cfg["lang"] = self.lang
        self.cfg["library"] = str(library)
        save_config(self.cfg)
        self.ok = True
        self.destroy()


def first_launch(root: tk.Tk, cfg: dict, change: bool = False) -> bool:
    """Choose (or create) the library; saves `lang` and `library`. False if the user quits."""
    if not change:  # the main window has not styled the app yet
        setup_styles(root, Fonts(root))
    dlg = LibraryDialog(root, cfg, change)
    root.wait_window(dlg)
    return dlg.ok


# ------------------------------------------------------------- assign / remove --
def ask_role(master, lang: str, filename: str = "") -> tuple[str, str] | None:
    """(role, label) for an unclassified file, or None if cancelled."""
    top = tk.Toplevel(master, bg=C["bg"])
    top.title(t(lang, "assign_title"))
    body = ttk.Frame(top, padding=(22, 18))
    body.pack(fill="both", expand=True)
    ttk.Label(body, text=t(lang, "assign_prompt", file=filename), style="PanelTitle.TLabel",
              wraplength=380, justify="left").pack(anchor="w", pady=(0, 8))
    role, label = tk.StringVar(top, value="test"), tk.StringVar(top)
    entry = ttk.Entry(body, textvariable=label, width=8)
    sync = lambda: entry.configure(state="normal" if role.get() in LABELLED else "disabled")
    for value, key in (("test", "role_sheet"), ("rating", "role_crf"),
                       ("instructions", "role_instr"), ("norms", "role_norms")):
        ttk.Radiobutton(body, text=t(lang, key), value=value, variable=role,
                        command=sync).pack(anchor="w")
    ttk.Label(body, text=t(lang, "assign_label"), style="Field.TLabel").pack(
        anchor="w", pady=(10, 3))
    entry.pack(anchor="w")
    result = []

    def ok():
        result.append((role.get(), label.get().strip() if role.get() in LABELLED else ""))
        top.destroy()

    btns = ttk.Frame(body)
    btns.pack(anchor="e", pady=(16, 0))
    ttk.Button(btns, text=t(lang, "btn_cancel"), style="Small.TButton",
               command=top.destroy).pack(side="left", padx=(0, 6))
    ttk.Button(btns, text=t(lang, "btn_ok"), style="Accent.TButton", command=ok).pack(side="left")
    top.bind("<Escape>", lambda _e: top.destroy())
    _modal(top, master)
    master.wait_window(top)
    return result[0] if result else None


def assign_file_role(master, lang: str, path: Path) -> bool:
    """Ask the role of an unclassified file and rename it. True if the library changed."""
    choice = ask_role(master, lang, path.name)
    if not choice:
        return False
    role, label = choice
    try:
        manage.assign_role(path, role, label)
    except AlreadyExists as e:
        _error(master, lang, t(lang, "err_file_exists", file=e))
    except InvalidName:
        _error(master, lang, t(lang, "err_label_invalid", label=label))
    except OSError as e:
        _error(master, lang, t(lang, "err_save", reason=e))
    else:
        return True
    return False


def remove_test(master, lang: str, inst: Instrument) -> bool:
    """Confirm, then move the test folder to the Trash. True if it was moved."""
    if not messagebox.askyesno(t(lang, "confirm_title"),
                               t(lang, "confirm_remove_test", name=inst.name,
                                 trash=trash_word(lang)), parent=master):
        return False
    try:
        manage.remove_test(inst.folder)
    except OSError as e:
        _error(master, lang, t(lang, "err_save", reason=e))
        return False
    return True


# ------------------------------------------------------------------ test form --
class TestForm(tk.Toplevel):
    """Add a test (`instrument` None) or edit one. After it closes: `result` is the saved
    test folder (or None) and `changed` tells whether the library changed on disk."""

    def __init__(self, master, root_dir: Path, lang: str, instrument: Instrument | None,
                 domain: str | None = None):
        super().__init__(master, bg=C["bg"])
        self.root_dir, self.lang, self.inst = Path(root_dir), lang, instrument
        self.result: Path | None = None
        self.changed = False
        self.fonts = Fonts(self)
        try:
            domains, insts = list_domains(self.root_dir), scan_library(self.root_dir)
        except (LibraryMissing, OSError):
            domains, insts = [], []
        self._subdomains: dict[str, set[str]] = {}
        for i in insts:
            if i.subdomain:
                self._subdomains.setdefault(_key(i.domain), set()).add(i.subdomain)

        inst = instrument
        self.name_var = tk.StringVar(self, value=inst.name if inst else "")
        self.domain_var = tk.StringVar(self, value=inst.domain if inst else (
            domain if domain in domains else (domains[0] if domains else "")))
        self.sub_var = tk.StringVar(self, value=inst.subdomain if inst else "")
        # one row per file: existing `path` and/or picked `src`, version `label` (+ its `current`)
        self.rows: dict[str, list[dict]] = {role: [] for role in SECTIONS}
        # labels held by files the form does not list (unsupported formats, duplicates)
        self._hidden = {role: role_labels([*inst.unsupported, *inst.duplicates], role) if inst
                        else [] for role in LABELLED}
        if inst:
            for role, files in (("test", inst.sheets), ("rating", inst.crfs)):
                self.rows[role] = [self._row(p, None, lbl) for lbl, p in files.items()]
            self.rows["instructions"] = [self._row(p, None) for p in inst.instructions]
            self.rows["norms"] = [self._row(p, None) for p in inst.norms]

        self.title(self._t("form_title_edit", name=inst.name) if inst
                   else self._t("form_title_add"))
        self._build(domains)
        self.bind("<Escape>", lambda _e: self.destroy())
        _modal(self, master)

    def _t(self, key: str, **fmt) -> str:
        return t(self.lang, key, **fmt)

    def _row(self, path: Path | None, src: Path | None, label: str = "") -> dict:
        return {"path": path, "src": src, "label": tk.StringVar(self, value=label),
                "current": label if path else ""}  # the label on disk

    # ------------------------------------------------------------ build --
    def _build(self, domains: list[str]) -> None:
        b = ttk.Frame(self, padding=(26, 20, 26, 22))
        b.pack(fill="both", expand=True)
        b.columnconfigure((0, 1), weight=1, uniform="cols")
        mono, sans = self.fonts.mono, self.fonts.sans

        def field(text, row, col=0, span=2):
            ttk.Label(b, text=self._t(text).upper(), style="Field.TLabel").grid(
                row=row, column=col, columnspan=span, sticky="w", pady=(0, 3))

        field("f_name", 0)
        name = ttk.Entry(b, textvariable=self.name_var, width=50, font=(mono, 12))
        name.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 12))
        field("f_reference", 2)
        self.ref_text = tk.Text(b, height=4, width=50, wrap="word", bd=0, bg=C["field"],
                                fg=C["text"], insertbackground=C["text"], font=(sans, 12),
                                highlightbackground=C["border"], highlightcolor=C["teal"],
                                highlightthickness=1, padx=8, pady=6)
        self.ref_text.grid(row=3, column=0, columnspan=2, sticky="we", pady=(0, 12))
        if self.inst:
            self.ref_text.insert("1.0", self.inst.reference)
        field("f_domain", 4, 0, 1)
        field("f_subdomain", 4, 1, 1)
        ttk.Combobox(b, textvariable=self.domain_var, values=domains, font=(sans, 12)).grid(
            row=5, column=0, sticky="we", padx=(0, 6), pady=(0, 12))
        self.sub_box = ttk.Combobox(b, textvariable=self.sub_var, font=(sans, 12))
        self.sub_box.grid(row=5, column=1, sticky="we", padx=(6, 0), pady=(0, 12))
        self.domain_var.trace_add("write", lambda *_: self._sync_subdomains())
        self._sync_subdomains()

        self._frames, self._add_btns = {}, {}
        for n, (role, (key, _multi)) in enumerate(SECTIONS.items()):
            r, c = 6 + n // 2 * 2, n % 2
            ttk.Label(b, text=self._t(key), style="PanelTitle.TLabel").grid(
                row=r, column=c, sticky="w", pady=(2, 3))
            panel = tk.Frame(b, bg=C["panel"], highlightbackground=C["border"],
                             highlightthickness=1)
            panel.grid(row=r + 1, column=c, sticky="nsew", pady=(0, 12),
                       padx=(0, 6) if c == 0 else (6, 0))
            inner = ttk.Frame(panel, style="Panel.TFrame")
            inner.pack(fill="both", expand=True, padx=10, pady=7)
            self._frames[role] = ttk.Frame(inner, style="Panel.TFrame")
            self._frames[role].pack(fill="x")
            self._add_btns[role] = ttk.Button(inner, text=self._t("f_add_file"),
                                              style="Small.TButton",
                                              command=lambda r=role: self.add_files(r))
            self._add_btns[role].pack(anchor="w", pady=(4, 0))
            self._render(role)

        btns = ttk.Frame(b)
        btns.grid(row=10, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(btns, text=self._t("btn_cancel"), style="Small.TButton",
                   command=self.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text=self._t("btn_save"), style="Accent.TButton",
                   command=self.save).pack(side="left")
        name.focus_set()

    def _sync_subdomains(self) -> None:
        subs = self._subdomains.get(_key(self.domain_var.get().strip()), set())
        self.sub_box.configure(values=sorted(subs, key=str.casefold))

    def _render(self, role: str) -> None:
        frame = self._frames[role]
        for w in frame.winfo_children():
            w.destroy()
        rows = self.rows[role]
        for r in rows:
            line = ttk.Frame(frame, style="Panel.TFrame")
            line.pack(fill="x", pady=2)
            if role in LABELLED and len(rows) > 1:
                ttk.Entry(line, textvariable=r["label"], width=4,
                          font=(self.fonts.mono, 11)).pack(side="left", padx=(0, 8))
            text = r["path"].name if r["path"] else r["src"].name
            if r["path"] and r["src"]:
                text += f"  ←  {r['src'].name}"
            ttk.Label(line, text=text, style="Panel.TLabel").pack(side="left", fill="x",
                                                                  expand=True)
            ttk.Button(line, text=self._t("f_remove"), style="Small.TButton",
                       command=lambda r=r: self.remove_row(role, r)).pack(side="right")
            if r["path"]:
                ttk.Button(line, text=self._t("f_replace"), style="Small.TButton",
                           command=lambda r=r: self.replace(role, r)).pack(
                    side="right", padx=(0, 6))
        single = not SECTIONS[role][1]
        self._add_btns[role].configure(state="disabled" if single and rows else "normal")

    # ---------------------------------------------------------- file rows --
    def _ask(self, role: str, several: bool) -> list[Path]:
        kw = {"parent": self, "title": self._t("f_pick_file")}
        if role in LABELLED:
            kw["filetypes"] = _DOC_TYPES
        if several:
            picked = filedialog.askopenfilenames(**kw)
        else:
            picked = [filedialog.askopenfilename(**kw)]
        return [Path(p) for p in picked or () if p]

    def add_files(self, role: str) -> None:
        rows = self.rows[role]
        used = lambda: [*(r["label"].get() for r in rows), *self._hidden.get(role, [])]
        for src in self._ask(role, SECTIONS[role][1]):
            if role in LABELLED and len(rows) == 1 and not rows[0]["label"].get():
                rows[0]["label"].set(next_label(used()))  # a version is added: label the lone file
            rows.append(self._row(None, src, next_label(used()) if role in LABELLED else ""))
        self._render(role)

    def replace(self, role: str, row: dict) -> None:
        picked = self._ask(role, False)
        if picked:
            row["src"] = picked[0]
            self._render(role)

    def remove_row(self, role: str, row: dict) -> None:
        if row["path"] is not None:  # an existing file: to the Trash, now
            if not messagebox.askyesno(
                    self._t("confirm_title"),
                    self._t("confirm_remove_file", file=row["path"].name,
                            trash=trash_word(self.lang)), parent=self):
                return
            try:
                manage.remove_file(row["path"])
            except OSError as e:
                return _error(self, self.lang, self._t("err_save", reason=e))
            self.changed = True
        self.rows[role].remove(row)
        self._render(role)

    def _plain(self, row: dict) -> dict:
        return {**row, "label": row["label"].get()}

    def _others(self) -> list[Path]:
        """Files of the test folder that the form does not list."""
        if self.inst is None:
            return []
        listed = {r["path"] for rows in self.rows.values() for r in rows}
        try:
            return [f for f in self.inst.folder.iterdir() if f.is_file() and f not in listed]
        except OSError:
            return []

    # --------------------------------------------------------------- save --
    def save(self) -> None:
        name, domain = self.name_var.get().strip(), self.domain_var.get().strip()
        subdomain, reference = self.sub_var.get().strip(), self.ref_text.get("1.0", "end-1c").strip()
        err, plans = form_error(self.lang, name, domain), {}
        others = self._others()
        for role in SECTIONS:
            if err:
                break
            plans[role], err = plan_files(self.lang, role,
                                          [self._plain(r) for r in self.rows[role]], others)
        if err:
            return _error(self, self.lang, err)
        folder = None
        try:
            if self.inst is None:
                put = {role: [(label, src) for _, src, label, _ in ops] for role, ops in plans.items()}
                folder = manage.add_test(
                    self.root_dir, domain, name, reference, subdomain, put["test"], put["rating"],
                    put["instructions"][0][1] if put["instructions"] else None,
                    [src for _, src in put["norms"]])
            else:
                folder = manage.update_info(self.inst.folder, self.root_dir, name, reference,
                                            subdomain, domain)
                apply_plans(folder, plans)
        except manage.FolderBusy as e:  # nothing was copied or deleted: keep the form
            self.changed |= e.path != self.inst.folder  # left under its temp name: rescan
            return _error(self, self.lang, self._t("err_folder_busy", path=str(e.path),
                                                   reason=e.reason))
        except ParkedFiles as e:
            _error(self, self.lang, self._t("err_parked", files=", ".join(e.names)))
        except AlreadyExists as e:
            if folder is None:  # nothing written yet: let the user fix the name
                return _error(self, self.lang, self._t("err_exists", domain=domain))
            _error(self, self.lang, self._t("err_file_exists", file=e))
        except InvalidName:
            if folder is None:
                return _error(self, self.lang, self._t("err_name_invalid"))
            _error(self, self.lang, self._t("err_save", reason=self._t("err_name_invalid")))
        except OSError as e:
            _error(self, self.lang, self._t("err_save", reason=e))
            if folder is None:
                return  # nothing written (add_test cleans up after itself): keep the form
        self.result = folder
        self.changed = True
        self.destroy()
