"""Main screen: header, domains pane, tests pane (tags, detail box), session pane."""
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from psyset.config import save_config
from psyset.i18n import t
from psyset.library import Instrument, LibraryMissing, list_domains, scan_library
from psyset.platform import asset_path, open_path, reveal_path
from psyset.ui.session_pane import SessionPane
from psyset.ui.theme import C, Fonts, Tag, setup_styles

# role -> (string key, chip kind)
ROLES = {"sheet": ("tag_sheet", "sheet"), "crf": ("tag_crf", "crf"),
         "instr": ("tag_instr", "ref"), "norms": ("tag_norms", "ref")}


def role_files(inst: Instrument, role: str) -> list[Path]:
    return {"sheet": list(inst.sheets.values()), "crf": list(inst.crfs.values()),
            "instr": inst.instructions, "norms": inst.norms}[role]


def matches(inst: Instrument, query: str) -> bool:
    q = query.casefold()
    return any(q in s.casefold() for s in (inst.name, inst.subdomain, inst.reference))


def group(insts: list[Instrument], with_domain: bool) -> list[tuple[str, list[Instrument]]]:
    """Consecutive runs of (domain ›) subdomain; scan_library already sorts no-subdomain last."""
    groups = []
    for i in insts:
        header = " › ".join(([i.domain] if with_domain else []) + ([i.subdomain] if i.subdomain else []))
        if groups and groups[-1][0].casefold() == header.casefold():
            groups[-1][1].append(i)
        else:
            groups.append((header, [i]))
    return groups


def wheel_notches(delta: int, windowing: str, tk_version: float) -> float:
    """MouseWheel %D -> notches (positive = up). Only Tk 8.6 on macOS sends raw deltas;
    Windows, X11 and Tk 9 everywhere send 120 per notch, with partial deltas from smooth wheels."""
    return float(delta) if windowing == "aqua" and tk_version < 9 else delta / 120


class MainWindow:
    def __init__(self, root: tk.Tk, cfg: dict):
        self.root, self.cfg = root, cfg
        self.lang = cfg.get("lang") if cfg.get("lang") in ("fr", "en") else "fr"
        self.library = Path(cfg.get("library") or "")
        self.fonts = Fonts(root)
        setup_styles(root, self.fonts)
        root.configure(bg=C["bg"])
        root.minsize(1100, 700)
        root.geometry("1180x760")

        self.instruments: list[Instrument] = []
        self.domains: list[str] = []
        self.ticked: list[Instrument] = []  # tick order; the session pane owns the ordering
        # Task 9 subscribes here. Called after every change, whoever caused it (including
        # the session pane itself via on_tick), so listeners must be idempotent.
        self.tick_listeners: list = []   # f(inst, ticked: bool)
        self.lang_listeners: list = []   # f(lang)
        self.domain: str | None = None   # None = all tests
        self.detail_key: str | None = None
        self._vars: dict[str, tk.BooleanVar] = {}
        self._rows: dict = {}
        self._built: list = []
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())

        self._logo = None
        logo = asset_path("logo", "psyset-mark-112.png")
        if logo:
            try:
                self._logo = tk.PhotoImage(file=str(logo)).subsample(2)  # 56 px
            except tk.TclError:
                pass

        self.main = ttk.Frame(root, padding=(26, 20, 26, 18))
        self.main.pack(fill="both", expand=True)
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(1, weight=1)
        self.body = ttk.Frame(self.main)
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.rowconfigure(0, weight=1)
        for col, weight in enumerate((75, 150, 105)):
            self.body.columnconfigure(col, weight=weight, uniform="panes")
        # Session pane area: kept across FR/EN rebuilds.
        box = tk.Frame(self.body, bg=C["preview_bg"], highlightbackground=C["preview_bd"],
                       highlightthickness=1)
        box.grid(row=0, column=2, sticky="nsew", padx=(18, 0))
        self.session_area = ttk.Frame(box, style="Session.TFrame")
        self.session_area.pack(fill="both", expand=True, padx=14, pady=12)

        root.bind_all("<MouseWheel>", self._on_wheel, add="+")
        try:  # Tk 9 on macOS sends trackpad scrolling as its own event
            root.bind_all("<TouchpadScroll>", self._on_touchpad, add="+")
        except tk.TclError:
            pass

        self._scan()
        self._build()
        self.session = SessionPane(self.session_area, self)

    # ------------------------------------------------------------ library --
    def _key(self, inst: Instrument) -> str:
        return inst.key(self.library)

    def _scan(self) -> None:
        try:
            self.instruments = scan_library(self.library)
            self.domains = list_domains(self.library)
        except (LibraryMissing, OSError):
            self.instruments, self.domains = [], []
            messagebox.showerror(t(self.lang, "err_title"),
                                 t(self.lang, "fl_missing", path=str(self.library)),
                                 parent=self.root)
        ticked = {self._key(i) for i in self.ticked}
        self._vars = {self._key(i): tk.BooleanVar(value=self._key(i) in ticked)
                      for i in self.instruments}
        if self.domain not in self.domains:
            self.domain = None

    def reload(self) -> None:
        """Rescan the library; ticks survive by Instrument.key, vanished tests are unticked."""
        old = self.ticked
        self._scan()
        by_key = {self._key(i): i for i in self.instruments}
        self.ticked = [by_key[self._key(i)] for i in old if self._key(i) in by_key]
        for inst in old:
            if self._key(inst) not in by_key:
                for f in self.tick_listeners:
                    f(inst, False)
        self._build()
        self.session.refresh()

    # ---------------------------------------------------------------- ticks --
    def on_tick(self, inst: Instrument, ticked: bool) -> None:
        key = self._key(inst)
        if key in self._vars:
            self._vars[key].set(ticked)
        was = any(self._key(i) == key for i in self.ticked)
        if ticked == was:
            return
        if ticked:
            self.ticked.append(inst)
        else:
            self.ticked = [i for i in self.ticked if self._key(i) != key]
        self._paint_row(key)
        self._paint_domains()
        for f in self.tick_listeners:
            f(inst, ticked)

    # ------------------------------------------------------------- language --
    def set_lang(self, lang: str) -> None:
        if lang == self.lang:
            return
        self.lang = self.cfg["lang"] = lang
        save_config(self.cfg)
        self._build()
        for f in self.lang_listeners:
            f(lang)

    # ---------------------------------------------------------------- build --
    def _t(self, key: str, **fmt) -> str:
        return t(self.lang, key, **fmt)

    def _build(self) -> None:
        for w in self._built:
            w.destroy()
        self.root.title(self._t("window_title"))
        self._built = [self._build_header(), self._build_domains(), self._build_tests(),
                       self._build_footer()]
        self._render_tests()
        self._render_detail()

    def _build_header(self):
        h = ttk.Frame(self.main)
        h.grid(row=0, column=0, sticky="we", pady=(0, 16))
        h.columnconfigure(2, weight=1)
        if self._logo is not None:
            tk.Label(h, image=self._logo, bg=C["bg"], bd=0).grid(
                row=0, column=0, rowspan=2, padx=(0, 12), sticky="w")
        ttk.Label(h, text="PsySet", style="Title.TLabel").grid(row=0, column=1, sticky="w")
        tagline = ttk.Frame(h)
        tagline.grid(row=1, column=1, sticky="w")
        head, sep, tail = self._t("tagline").rpartition("· ")
        ttk.Label(tagline, text=head + sep, style="Tagline.TLabel").pack(side="left")
        ttk.Label(tagline, text=tail, style="TaglineOn.TLabel").pack(side="left")
        langs = ttk.Frame(h)
        langs.grid(row=0, column=2, rowspan=2, sticky="ne")
        for code in ("fr", "en"):
            ttk.Button(langs, text=code.upper(), width=3,
                       style="LangActive.TButton" if self.lang == code else "Lang.TButton",
                       command=lambda c=code: self.set_lang(c)).pack(side="left", padx=(0, 3))
        return h

    def _build_footer(self):
        f = ttk.Label(self.main, text=self._t("footer"), style="Note.TLabel")
        f.grid(row=2, column=0, sticky="w", pady=(12, 0))
        return f

    def _build_domains(self):
        left = ttk.Frame(self.body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        ttk.Label(left, text=self._t("domains_label"), style="Field.TLabel").pack(
            anchor="w", pady=(0, 6))
        self._dom_rows = {}
        for d in (None, *self.domains):
            row = tk.Frame(left, cursor="hand2")
            row.pack(fill="x", pady=1)
            count = tk.Label(row, font=(self.fonts.mono, 9, "bold"))
            count.pack(side="right", padx=(4, 10))
            name = tk.Label(row, text=self._t("all_tests") if d is None else d,
                            font=(self.fonts.sans, 12), anchor="w")
            name.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=6)
            for w in (row, name, count):
                w.bind("<Button-1>", lambda _e, d=d: self.select_domain(d))
            self._dom_rows[d] = (row, name, count)
        ttk.Button(left, text=self._t("add_test"), style="Small.TButton",
                   command=self.add_test).pack(anchor="w", pady=(12, 0))
        return left

    def _paint_domains(self) -> None:
        searching = bool(self.search_var.get().strip())
        ticked = [i.domain for i in self.ticked]
        for d, (row, name, count) in self._dom_rows.items():
            on = d == self.domain and not searching
            bg = C["green"] if on else C["bg"]
            total = sum(1 for i in self.instruments if d is None or i.domain == d)
            n = len(ticked) if d is None else ticked.count(d)
            row.configure(bg=bg)
            name.configure(bg=bg, fg=C["bg"] if on else C["text"])
            count.configure(bg=bg, fg=C["preview_bd"] if on else C["muted"], text=f"{n}/{total}")

    def select_domain(self, d: str | None) -> None:
        self.domain = d
        if self.search_var.get():
            self.search_var.set("")  # the trace re-renders
        else:
            self._render_tests()

    def _build_tests(self):
        mid = ttk.Frame(self.body)
        mid.grid(row=0, column=1, sticky="nsew")
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(1, weight=1)

        search = ttk.Entry(mid, textvariable=self.search_var, font=(self.fonts.mono, 11))
        search.grid(row=0, column=0, sticky="we", pady=(0, 10))
        self._placeholder = tk.Label(search, text="⌕  " + self._t("search_placeholder"),
                                     bg=C["field"], fg=C["faint"], font=(self.fonts.mono, 11),
                                     cursor="xterm")
        self._placeholder.bind("<Button-1>", lambda _e: search.focus_set())
        self._toggle_placeholder()

        panel = tk.Frame(mid, bg=C["panel"], highlightbackground=C["border"], highlightthickness=1)
        panel.grid(row=1, column=0, sticky="nsew")
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(panel, bg=C["panel"], highlightthickness=0, bd=0,
                                yscrollincrement=1)
        bar = ttk.Scrollbar(panel, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=8)
        bar.grid(row=0, column=1, sticky="ns")
        self.list_frame = tk.Frame(self.canvas, bg=C["panel"])
        win = self.canvas.create_window(0, 0, window=self.list_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(win, width=e.width))
        self.list_frame.bind("<Configure>", lambda _e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))

        self.detail = tk.Frame(mid, bg=C["field"], highlightbackground=C["border"],
                               highlightthickness=1)
        return mid

    def _on_search(self) -> None:
        self._toggle_placeholder()
        self._render_tests()

    def _toggle_placeholder(self) -> None:
        if self.search_var.get():
            self._placeholder.place_forget()
        else:
            self._placeholder.place(x=9, rely=0.5, anchor="w")

    # -------------------------------------------------------------- tests list --
    def _render_tests(self) -> None:
        self._paint_domains()
        for w in self.list_frame.winfo_children():
            w.destroy()
        self._rows = {}
        query = self.search_var.get().strip()
        if query:
            insts, with_domain = [i for i in self.instruments if matches(i, query)], True
        elif self.domain is None:
            insts, with_domain = self.instruments, True
        else:
            insts, with_domain = [i for i in self.instruments if i.domain == self.domain], False
        if not insts:
            ttk.Label(self.list_frame, text=self._t("no_results"), style="Empty.TLabel").pack(
                anchor="w", padx=4, pady=6)
        # same chip width per column so the four tags line up from row to row
        texts = {r: [self._chip_text(i, r) for i in insts] for r in ROLES}
        widths = {r: max(map(len, v), default=0) for r, v in texts.items()}
        groups = group(insts, with_domain)
        for n, (header, members) in enumerate(groups):
            if not header and len(groups) > 1:
                header = self._t("group_other")
            if header:
                ttk.Label(self.list_frame, text=header.upper(), style="Group.TLabel").pack(
                    anchor="w", padx=4, pady=(0 if n == 0 else 10, 3))
            for inst in members:
                self._add_row(inst, widths)
        self.canvas.yview_moveto(0)

    def _chip_text(self, inst: Instrument, role: str) -> str:
        n = len(role_files(inst, role))
        return self._t(ROLES[role][0]) + (f" ×{n}" if n > 1 else "")

    def _add_row(self, inst: Instrument, widths: dict) -> None:
        key = self._key(inst)
        var = self._vars[key]
        row = tk.Frame(self.list_frame)
        row.pack(fill="x", pady=1, padx=(0, 6))
        cb = ttk.Checkbutton(row, variable=var, takefocus=0,
                             command=lambda: self.on_tick(inst, var.get()))
        cb.pack(side="left", padx=(4, 4))
        chips = tk.Frame(row)
        chips.pack(side="right", padx=(4, 4))
        for role, (skey, kind) in ROLES.items():
            files = role_files(inst, role)
            Tag(chips, self._t(skey), kind, bool(files), len(files), width=widths[role],
                command=lambda r=role: self.open_role(inst, r)).pack(side="left", padx=(3, 0))
        name = tk.Label(row, text=inst.name, fg=C["text"], font=(self.fonts.sans, 12),
                        anchor="w", cursor="hand2")
        name.pack(side="left", fill="x", expand=True, pady=4)
        name.bind("<Button-1>", lambda _e: self.show_detail(inst))
        self._rows[key] = (row, cb, name, chips)
        self._paint_row(key)

    def _paint_row(self, key: str) -> None:
        if key not in self._rows:
            return
        row, cb, name, chips = self._rows[key]
        on = self._vars[key].get()
        bg = C["field"] if on else C["panel"]
        for w in (row, name, chips):
            w.configure(bg=bg)
        cb.configure(style="RowOn.TCheckbutton" if on else "Row.TCheckbutton")

    # ----------------------------------------------------------------- tags --
    def open_role(self, inst: Instrument, role: str) -> None:
        files = role_files(inst, role)
        if len(files) == 1:
            self._os_open(open_path, files[0])
        elif files:
            menu = tk.Menu(self.root, tearoff=0)
            for f in files:
                menu.add_command(label=f.name, command=lambda f=f: self._os_open(open_path, f))
            x, y = self.root.winfo_pointerxy()
            try:
                menu.tk_popup(x, y)
            finally:
                menu.grab_release()

    def _os_open(self, fn, path: Path) -> None:
        try:
            fn(path)
        except OSError as e:
            messagebox.showerror(self._t("err_title"),
                                 self._t("err_open", file=path.name, reason=e), parent=self.root)

    # --------------------------------------------------------------- detail --
    def show_detail(self, inst: Instrument) -> None:
        self.detail_key = self._key(inst)
        self._render_detail()

    def _render_detail(self) -> None:
        for w in self.detail.winfo_children():
            w.destroy()
        inst = next((i for i in self.instruments if self._key(i) == self.detail_key), None)
        if inst is None:
            self.detail.grid_remove()
            return
        self.detail.grid(row=2, column=0, sticky="we", pady=(10, 0))
        box = ttk.Frame(self.detail, style="Detail.TFrame")
        box.pack(fill="x", padx=12, pady=10)
        where = " › ".join(p for p in (inst.domain, inst.subdomain) if p)
        wrapped = [ttk.Label(box, text=f"{inst.name} · {where}".upper(), justify="left",
                             style="DetailHead.TLabel"),
                   ttk.Label(box, text=inst.reference or self._t("no_reference"), justify="left",
                             style="DetailRef.TLabel" if inst.reference else "DetailNone.TLabel")]
        wrapped[0].pack(anchor="w", fill="x", pady=(0, 4))
        wrapped[1].pack(anchor="w", fill="x")

        others = ([(f, self._t("reason_unclassified")) for f in inst.unclassified]
                  + [(f, self._t("reason_unsupported", ext=f.suffix.lower()))
                     for f in inst.unsupported]
                  + [(f, self._t("reason_duplicate")) for f in inst.duplicates])
        if others:
            ttk.Label(box, text=self._t("detail_files"), style="DetailHead.TLabel").pack(
                anchor="w", pady=(8, 2))
        for f, why in others:
            lbl = ttk.Label(box, text=f"{f.name} · {why}", style="DetailFile.TLabel",
                            justify="left")
            lbl.pack(anchor="w", fill="x")
            if f in inst.unclassified:
                lbl.configure(cursor="hand2")
                lbl.bind("<Button-1>", lambda _e, f=f: self.assign_role(inst, f))
            wrapped.append(lbl)
        box.bind("<Configure>", lambda e: [w.configure(wraplength=max(e.width - 4, 50))
                                           for w in wrapped])

        btns = ttk.Frame(box, style="Detail.TFrame")
        btns.pack(anchor="w", pady=(8, 0))
        ttk.Button(btns, text=self._t("edit_info"), style="Small.TButton",
                   command=lambda: self.edit_info(inst)).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text=self._t("open_folder"), style="Small.TButton",
                   command=lambda: self._os_open(reveal_path, inst.folder)).pack(side="left")

    # ---------------------------------------------------------- scrolling --
    def _scroll_list(self, e, pixels: float) -> None:
        try:
            w = self.root.winfo_containing(e.x_root, e.y_root)
        except (KeyError, tk.TclError):  # e.g. a Combobox popdown: no Python widget
            return
        if w is None or not pixels:
            return
        for canvas in (self.canvas, self.session.canvas):
            c = str(canvas)
            if str(w) == c or str(w).startswith(c + "."):
                canvas.yview_scroll(int(pixels) or (1 if pixels > 0 else -1), "units")
                return

    def _on_wheel(self, e) -> None:
        n = wheel_notches(e.delta, self.root.tk.call("tk", "windowingsystem"), tk.TkVersion)
        self._scroll_list(e, -n * 30)

    def _on_touchpad(self, e) -> None:
        _dx, dy = self.root.tk.call("tk::PreciseScrollDeltas", e.delta)
        self._scroll_list(e, -dy)

    # ------------------------------------------------- dialogs (Task 10) --
    def add_test(self) -> None:
        """Stub: Task 10 opens the add-test form."""

    def edit_info(self, inst: Instrument) -> None:
        """Stub: Task 10 opens the test form pre-filled."""

    def assign_role(self, inst: Instrument, path: Path) -> None:
        """Stub: Task 10 opens the assign-role dialog."""
