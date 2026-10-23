"""Right pane: ordered session (drag / ▲▼ / ✕, version chips), generate options, Generate PDFs…"""
import sys
import threading
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from psyset.config import save_config
from psyset.convert import ConversionError, NoConverter, OutputError, find_converters, generate
from psyset.i18n import t
from psyset.library import Instrument, natural_key
from psyset.pdf import PdfReadError, estimate
from psyset.platform import open_path, reveal_path
from psyset.session import Entry, crfs_for, default_filename, default_versions, missing, \
    plan_outputs, sheets_for
from psyset.ui.theme import C

KINDS = ("sheets", "crfs", "merged")
OUT_KEYS = {"sheets": "out_sheets", "crfs": "out_crfs", "merged": "out_merged"}
DEFAULT_OUTPUTS = {"sheets": True, "crfs": True, "merged": False}
MODES = ("by_test", "sheets_first")


# ------------------------------------------------------------- pure helpers --
def reorder(items: list, src: int, insert_at: int) -> list:
    """Move items[src] to the gap `insert_at` (0 = above the first row, len = below the last)."""
    out = list(items)
    item = out.pop(src)
    out.insert(insert_at - 1 if insert_at > src else insert_at, item)
    return out


def toggle_version(chosen: list[str], label: str, labels: list[str]) -> list[str]:
    """Flip `label`; the last chosen version cannot be switched off."""
    if label not in labels:
        return list(chosen)
    new = set(chosen) ^ {label}
    return sorted(new, key=natural_key) if new else list(chosen)


def count_text(lang: str, n_tests: int, pages: int | None, n_word: int) -> str:
    """"(2 tests · 6 p.)", "(1 test · 4 p. + 1 Word)"; pages=None means a PDF is unreadable."""
    if not n_tests:
        return ""
    tests = t(lang, "count_test_one" if n_tests == 1 else "count_test_many", n=n_tests)
    size = t(lang, "count_pages", n="?" if pages is None else pages)
    if n_word:
        word = t(lang, "count_word", n=n_word)
        size = f"{size} + {word}" if pages != 0 else word
    return f"({tests} · {size})"


def warning_lines(lang: str, session: list[Entry]) -> list[str]:
    gaps = missing(session)
    lines = [t(lang, key, names=", ".join(gaps[kind]))
             for kind, key in (("no_sheet", "warn_no_sheet"), ("no_crf", "warn_no_crf"))
             if gaps[kind]]
    lines += [t(lang, "warn_unsupported", file=f"{inst.name}/{f.name}")
              for inst, _ in session for f in inst.unsupported]
    return lines


def kinds_to_save(plan: dict[str, list[Path]], outputs: dict[str, bool]) -> list[str]:
    return [k for k in KINDS if outputs.get(k) and plan[k]]


def build_jobs(plan: dict[str, list[Path]], chosen: dict[str, Path]) -> dict[Path, list[Path]]:
    """{destination: docs}; ValueError(path) if one file was chosen for two outputs."""
    jobs, seen = {}, set()
    for kind, dest in chosen.items():
        same = Path(dest).resolve()
        if same in seen:
            raise ValueError(Path(dest).resolve())
        seen.add(same)
        jobs[Path(dest)] = plan[kind]
    return jobs


def _non_pdfs(jobs: dict[Path, list[Path]]) -> list[Path]:
    return [d for docs in jobs.values() for d in docs if Path(d).suffix.lower() != ".pdf"]


def needs_word_prompt(jobs: dict[Path, list[Path]], cfg: dict, platform: str = sys.platform,
                      converters=find_converters) -> bool:
    """macOS asks once before an app may script Word: explain it before the first conversion."""
    return (platform == "darwin" and not cfg.get("word_prompt_explained")
            and bool(_non_pdfs(jobs)) and "word" in converters())


def _shown(path: Path, library: Path) -> str:
    try:
        return Path(path).relative_to(library).as_posix()
    except ValueError:
        return str(path)


def error_text(lang: str, exc: BaseException, jobs: dict[Path, list[Path]], library: Path) -> str:
    if isinstance(exc, ConversionError):
        return t(lang, "err_conversion", file=_shown(exc.path, library), reason=exc.reason)
    if isinstance(exc, PdfReadError):
        return t(lang, "err_pdf_read", file=_shown(exc.path, library), reason=exc.reason)
    if isinstance(exc, NoConverter):
        first = next(iter(_non_pdfs(jobs)), Path("?"))
        return t(lang, "err_no_converter", file=_shown(first, library))
    if isinstance(exc, OutputError):
        return t(lang, "err_output", file=str(exc.path), reason=exc.reason)
    return t(lang, "err_generic", reason=str(exc) or type(exc).__name__)


# ------------------------------------------------------------------- widget --
class SessionPane(ttk.Frame):
    def __init__(self, master, main):
        super().__init__(master, style="Session.TFrame")
        self.main, self.cfg = main, main.cfg
        self.fonts = main.fonts
        self._items: list[list] = []  # [Instrument, chosen versions]
        self._running = False
        self._drag: int | None = None
        self._drop_at = 0
        self.done_dialog = None

        outs = self.cfg.get("outputs") if isinstance(self.cfg.get("outputs"), dict) else {}
        self.out_vars = {k: tk.BooleanVar(self, value=bool(outs.get(k, DEFAULT_OUTPUTS[k])))
                         for k in KINDS}
        self.mode = self.cfg.get("merge_mode") if self.cfg.get("merge_mode") in MODES else MODES[0]
        self.duplex_var = tk.BooleanVar(self, value=self.cfg.get("duplex") is True)

        self.pack(fill="both", expand=True)
        main.tick_listeners.append(lambda inst, on: self.add(inst) if on else self.remove(inst))
        main.lang_listeners.append(lambda _lang: self._build())
        self._build()

    # ------------------------------------------------------------ state --
    @property
    def lang(self) -> str:
        return self.main.lang

    def _t(self, key: str, **fmt) -> str:
        return t(self.lang, key, **fmt)

    def _key(self, inst: Instrument) -> str:
        return inst.key(self.main.library)

    def _index(self, inst: Instrument) -> int | None:
        key = self._key(inst)
        return next((n for n, (i, _) in enumerate(self._items) if self._key(i) == key), None)

    def _remembered(self) -> dict:
        if not isinstance(self.cfg.get("versions"), dict):
            self.cfg["versions"] = {}
        return self.cfg["versions"]

    def _initial_versions(self, inst: Instrument) -> list[str]:
        saved = self._remembered().get(self._key(inst))
        return default_versions(inst, saved if isinstance(saved, list) else None)

    def entries(self) -> list[Entry]:
        return [(i, list(v)) for i, v in self._items]

    def add(self, inst: Instrument) -> None:
        if self._index(inst) is None:
            self._items.append([inst, self._initial_versions(inst)])
            self._render()

    def remove(self, inst: Instrument) -> None:
        n = self._index(inst)
        if n is not None:
            del self._items[n]
            self._render()

    def refresh(self) -> None:
        """Re-sync with main.ticked (fresh Instrument objects after a rescan) and redraw."""
        fresh = {self._key(i): i for i in self.main.ticked}
        items = []
        for inst, chosen in self._items:
            new = fresh.pop(self._key(inst), None)
            if new is not None:
                kept = [v for v in chosen if v in new.versions()]
                items.append([new, kept or self._initial_versions(new)])
        items += [[i, self._initial_versions(i)] for i in fresh.values()]
        self._items = items
        self._render()

    def _save_prefs(self) -> None:
        self.cfg["outputs"] = {k: v.get() for k, v in self.out_vars.items()}
        self.cfg["merge_mode"] = self.mode
        self.cfg["duplex"] = self.duplex_var.get()
        save_config(self.cfg)
        self._update()

    # ------------------------------------------------------------ build --
    def _build(self) -> None:
        for w in self.winfo_children():
            w.destroy()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        ttk.Label(self, text=self._t("session_title"), style="SessionTitle.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(self, text=self._t("session_sub").upper(), style="SessionSub.TLabel").grid(
            row=1, column=0, sticky="w", pady=(0, 8))

        box = tk.Frame(self, bg=C["field"], highlightbackground=C["border"], highlightthickness=1)
        box.grid(row=2, column=0, sticky="nsew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(box, bg=C["field"], highlightthickness=0, bd=0, yscrollincrement=1)
        self._bar = ttk.Scrollbar(box, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._bar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)
        self.rows_frame = tk.Frame(self.canvas, bg=C["field"])
        win = self.canvas.create_window(0, 0, window=self.rows_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: (self.canvas.itemconfigure(win, width=e.width),
                                                   self._fit_scroll()))
        self.rows_frame.bind("<Configure>", lambda _e: self._fit_scroll())

        gen = ttk.Frame(self, style="Session.TFrame")
        gen.grid(row=3, column=0, sticky="we", pady=(12, 0))
        gen.columnconfigure(1, weight=1)
        ttk.Label(gen, text=self._t("generate_label"), style="SessionField.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.count_labels = {}
        for n, kind in enumerate(KINDS, start=1):
            ttk.Checkbutton(gen, text=self._t(OUT_KEYS[kind]), variable=self.out_vars[kind],
                            style="Session.TCheckbutton", takefocus=0,
                            command=self._save_prefs).grid(row=n, column=0, sticky="w")
            self.count_labels[kind] = ttk.Label(gen, style="SessionCount.TLabel")
            self.count_labels[kind].grid(row=n, column=1, sticky="w", padx=(6, 0))
        self.seg = tk.Frame(gen, bg=C["border"])
        self.seg.grid(row=4, column=0, columnspan=2, sticky="w", padx=(24, 0), pady=(2, 6))
        self.seg_labels = {}
        for mode, key in zip(MODES, ("mode_by_test", "mode_sheets_first")):
            lbl = tk.Label(self.seg, text=self._t(key), font=(self.fonts.sans, 10, "bold"),
                           padx=8, pady=3, cursor="hand2")
            lbl.pack(side="left", padx=(1 if mode == MODES[0] else 0, 1), pady=1)
            lbl.bind("<Button-1>", lambda _e, m=mode: self._set_mode(m))
            self.seg_labels[mode] = lbl
        dup = ttk.Frame(gen, style="Session.TFrame")
        dup.grid(row=5, column=0, columnspan=2, sticky="we")
        ttk.Checkbutton(dup, variable=self.duplex_var, style="Session.TCheckbutton", takefocus=0,
                        command=self._save_prefs).pack(side="left", anchor="n")
        dup_text = ttk.Label(dup, text=self._t("duplex"), style="SessionText.TLabel",
                             justify="left", cursor="hand2")
        dup_text.pack(side="left", fill="x", expand=True, pady=(2, 0))
        dup_text.bind("<Button-1>", lambda _e: (self.duplex_var.set(not self.duplex_var.get()),
                                                self._save_prefs()))

        self.warn = tk.Frame(self, bg=C["warn_bg"], highlightbackground=C["warn_bd"],
                             highlightthickness=1)
        tk.Label(self.warn, text="●", bg=C["warn_bg"], fg=C["warn_dot"],
                 font=(self.fonts.sans, 8)).pack(side="left", anchor="n", padx=(10, 6), pady=7)
        self.warn_text = ttk.Label(self.warn, style="Warn.TLabel", justify="left")
        self.warn_text.pack(side="left", fill="x", expand=True, pady=7, padx=(0, 10))

        self.button = ttk.Button(self, style="Accent.TButton", command=self.generate)
        self.button.grid(row=5, column=0, sticky="we", pady=(12, 0))
        self.bind("<Configure>", lambda e: (dup_text.configure(wraplength=max(e.width - 40, 80)),
                                            self.warn_text.configure(
                                                wraplength=max(e.width - 50, 80))))
        self._render()

    def _fit_scroll(self) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all") or (0, 0, 0, 0))
        if self.rows_frame.winfo_reqheight() > self.canvas.winfo_height() > 1:
            self._bar.grid(row=0, column=1, sticky="ns")
        else:
            self._bar.grid_remove()
            self.canvas.yview_moveto(0)

    # ------------------------------------------------------------- rows --
    def _render(self) -> None:
        for w in self.rows_frame.winfo_children():
            w.destroy()
        self._rows = []
        if not self._items:
            ttk.Label(self.rows_frame, text=self._t("session_empty"), style="SessionEmpty.TLabel",
                      wraplength=260, justify="left").pack(anchor="w", padx=6, pady=8)
        for n, (inst, chosen) in enumerate(self._items):
            if n:
                tk.Frame(self.rows_frame, bg=C["border"], height=1).pack(fill="x")
            self._rows.append(self._row(n, inst, chosen))
        self._line = tk.Frame(self.rows_frame, bg=C["green"], height=2)
        self._update()

    def _row(self, n: int, inst: Instrument, chosen: list[str]) -> tk.Frame:
        bg = C["field"]
        row = tk.Frame(self.rows_frame, bg=bg)
        row.pack(fill="x")
        handle = tk.Label(row, text="⋮⋮", bg=bg, fg=C["faint"], cursor="fleur",
                          font=(self.fonts.sans, 12))
        handle.pack(side="left", padx=(4, 4), pady=5)
        handle.bind("<ButtonPress-1>", lambda _e: self._drag_start(n))
        handle.bind("<B1-Motion>", self._drag_move)
        handle.bind("<ButtonRelease-1>", self._drag_end)
        tk.Label(row, text=str(n + 1), bg=bg, fg=C["green"], width=2, anchor="w",
                 font=(self.fonts.mono, 10, "bold")).pack(side="left")
        for text, tip, fn in (("✕", "remove_from_session", lambda: self._unticked(inst)),
                              ("▼", "move_down", lambda: self._move(n, n + 2)),
                              ("▲", "move_up", lambda: self._move(n, n - 1))):
            b = tk.Label(row, text=text, bg=bg, fg=C["muted"], cursor="hand2",
                         font=(self.fonts.sans, 10))
            b.pack(side="right", padx=(0, 6) if text == "✕" else (0, 2))
            b.bind("<Button-1>", lambda _e, fn=fn: fn())
            b.bind("<Enter>", lambda _e, b=b: b.configure(fg=C["green"]))
            b.bind("<Leave>", lambda _e, b=b: b.configure(fg=C["muted"]))
        labels = inst.versions()
        if labels:
            chips = tk.Frame(row, bg=bg)
            chips.pack(side="right", padx=(4, 8))
            for label in labels:
                on = label in chosen
                chip = tk.Label(chips, text=label, padx=5, pady=0, cursor="hand2",
                                font="PsyTag", bg=C["green"] if on else C["chip"],
                                fg=C["bg"] if on else C["muted"])
                chip.pack(side="left", padx=(3, 0))
                chip.bind("<Button-1>", lambda _e, lb=label: self._toggle(inst, lb))
        tk.Label(row, text=inst.name, bg=bg, fg=C["text"], anchor="w",
                 font=(self.fonts.sans, 12)).pack(side="left", fill="x", expand=True)
        return row

    def _move(self, src: int, insert_at: int) -> None:
        if 0 <= insert_at <= len(self._items):
            self._items = reorder(self._items, src, insert_at)
            self._render()

    def _unticked(self, inst: Instrument) -> None:
        self.remove(inst)
        self.main.on_tick(inst, False)

    def _toggle(self, inst: Instrument, label: str) -> None:
        n = self._index(inst)
        if n is None:
            return
        chosen = toggle_version(self._items[n][1], label, inst.versions())
        self._items[n][1] = chosen
        self._remembered()[self._key(inst)] = chosen
        save_config(self.cfg)
        self._render()

    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        self._save_prefs()

    # ------------------------------------------------------------- drag --
    def _drag_start(self, n: int) -> None:
        self._drag, self._drop_at = n, n

    def _drag_move(self, e) -> None:
        # ponytail: no auto-scroll while dragging past the visible rows; ▲▼ cover long lists
        if self._drag is None or not self._rows:
            return
        y = e.y_root - self.rows_frame.winfo_rooty()
        self._drop_at = sum(1 for r in self._rows if r.winfo_y() + r.winfo_height() / 2 < y)
        last = self._rows[-1]
        line_y = (self._rows[self._drop_at].winfo_y() if self._drop_at < len(self._rows)
                  else last.winfo_y() + last.winfo_height())
        self._line.place(x=0, y=max(line_y - 1, 0), relwidth=1)
        self._line.lift()

    def _drag_end(self, _e) -> None:
        src, self._drag = self._drag, None
        self._line.place_forget()
        if src is not None and self._drop_at not in (src, src + 1):
            self._move(src, self._drop_at)

    # ---------------------------------------------------- options/counts --
    def _update(self) -> None:
        session = self.entries()
        plan = plan_outputs(session, self.mode)
        duplex = self.duplex_var.get()
        tests = {"sheets": sum(1 for i, v in session if sheets_for(i, v)),
                 "crfs": sum(1 for i, v in session if crfs_for(i, v)),
                 "merged": sum(1 for i, v in session if sheets_for(i, v) or crfs_for(i, v))}
        for kind in KINDS:
            try:
                pages, others = estimate(plan[kind], duplex)
            except PdfReadError:
                pages, others = None, sum(1 for d in plan[kind] if d.suffix.lower() != ".pdf")
            self.count_labels[kind].configure(
                text=count_text(self.lang, tests[kind], pages, others))
        for mode, lbl in self.seg_labels.items():
            on = mode == self.mode
            lbl.configure(bg=C["green"] if on else C["field"], fg=C["bg"] if on else C["muted"])
        lines = warning_lines(self.lang, session)
        if lines:
            self.warn_text.configure(text="\n".join(lines))
            self.warn.grid(row=4, column=0, sticky="we", pady=(10, 0))
        else:
            self.warn.grid_remove()
        ready = bool(kinds_to_save(plan, {k: v.get() for k, v in self.out_vars.items()}))
        self.button.configure(text=self._t("generating" if self._running else "generate_btn"),
                              state="normal" if ready and not self._running else "disabled")

    # --------------------------------------------------------- generate --
    def _save_dir(self) -> str:
        d = self.cfg.get("last_save_dir")
        return d if isinstance(d, str) and Path(d).is_dir() else str(Path.home())

    def generate(self) -> None:
        if self._running:
            return
        plan = plan_outputs(self.entries(), self.mode)
        kinds = kinds_to_save(plan, {k: v.get() for k, v in self.out_vars.items()})
        if not kinds:
            return
        chosen = {}
        for kind in kinds:
            path = filedialog.asksaveasfilename(
                parent=self.main.root, title=self._t("save_title", kind=self._t(OUT_KEYS[kind])),
                initialdir=self._save_dir(),
                initialfile=default_filename(kind, self.lang, date.today()),
                defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
            if not path:  # one cancel aborts the whole generation
                return
            chosen[kind] = Path(path)
            self.cfg["last_save_dir"] = str(Path(path).parent)
        save_config(self.cfg)
        try:
            jobs = build_jobs(plan, chosen)
        except ValueError as e:
            messagebox.showerror(self._t("err_title"), self._t("err_same_file", file=e.args[0]),
                                 parent=self.main.root)
            return
        if needs_word_prompt(jobs, self.cfg):
            messagebox.showinfo(self._t("word_prompt_title"), self._t("word_prompt_msg"),
                                parent=self.main.root)
            self.cfg["word_prompt_explained"] = True
            save_config(self.cfg)
        self._start(jobs, self.duplex_var.get())

    def _start(self, jobs: dict[Path, list[Path]], duplex: bool) -> None:
        result: dict = {}

        def work():  # no Tk in here: the main thread polls `result`
            try:
                result["pages"] = generate(jobs, duplex)
            except Exception as e:
                result["error"] = e

        self._running = True
        self._update()
        # Not a daemon: quitting mid-run still lets generate() remove its temp files.
        thread = threading.Thread(target=work, name="psyset-generate")
        thread.start()
        self.after(100, self._poll, thread, result, jobs)

    def _poll(self, thread: threading.Thread, result: dict, jobs) -> None:
        if thread.is_alive():
            self.after(100, self._poll, thread, result, jobs)
            return
        self._running = False
        self._update()
        if "error" in result:
            messagebox.showerror(self._t("err_title"),
                                 error_text(self.lang, result["error"], jobs, self.main.library),
                                 parent=self.main.root)
        else:
            self._done(result["pages"])

    def _done(self, pages: dict[Path, int]) -> None:
        files = "\n".join(f"{p.name} ({self._t('count_pages', n=n)})" for p, n in pages.items())
        msg = self._t("done_msg_one" if len(pages) == 1 else "done_msg_many",
                      n=len(pages), files=files)
        top = self.done_dialog = tk.Toplevel(self.main.root, bg=C["bg"])
        top.title(self._t("done_title"))
        top.transient(self.main.root)
        top.resizable(False, False)
        body = ttk.Frame(top, padding=(22, 18))
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=self._t("done_title"), style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(body, text=msg, justify="left").pack(anchor="w", pady=(6, 14))
        btns = ttk.Frame(body)
        btns.pack(anchor="e")
        outputs = list(pages)
        folders = list(dict.fromkeys(p.parent for p in outputs))
        reveal = "btn_reveal_finder" if sys.platform == "darwin" else "btn_reveal_explorer"
        ttk.Button(btns, text=self._t("btn_open"), style="Accent.TButton",
                   command=lambda: [self.main._os_open(open_path, p) for p in outputs]
                   ).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text=self._t(reveal), style="Small.TButton",
                   command=lambda: [self.main._os_open(
                       reveal_path, next(p for p in outputs if p.parent == f)) for f in folders]
                   ).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text=self._t("btn_close"), style="Small.TButton",
                   command=top.destroy).pack(side="left")
        top.bind("<Escape>", lambda _e: top.destroy())
