"""PsyDocs look: palette, fonts, ttk styles, and the role Tag chip."""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# PsyDocs palette (dos-pat/new_patient.py), plus the CRF clay and the tag backgrounds.
C = {
    "bg":            "#F4EFE6",
    "panel":         "#EFE9DC",
    "border":        "#D6CDB8",
    "field":         "#FBF8F1",
    "chip":          "#E9E1D2",
    "ink":           "#1F2A26",
    "text":          "#2E3F39",
    "muted":         "#7B8580",
    "faint":         "#B0A88F",
    "green":         "#2D5249",
    "green_hover":   "#26463E",
    "teal":          "#4F8B7A",
    "preview_bg":    "#EAF0EC",
    "preview_bd":    "#CFE0D6",
    "warn_bg":       "#F6EEDC",
    "warn_bd":       "#E6D4A8",
    "warn_dot":      "#D5A24D",
    "red":           "#B85847",
    "clay":          "#C97B5C",
    "clay_bg":       "#F3E2D8",
    "clay_ink":      "#9A5A40",  # clay text on clay_bg (mockup), legible where clay is not
    "sage_bg":       "#E3EDE7",
}


class Fonts:
    """Brand fonts when installed, else system equivalents (PsyDocs' picking)."""

    def __init__(self, root: tk.Misc):
        fams = set(tkfont.families(root))
        pick = lambda prefs, fb: next((f for f in prefs if f in fams), fb)
        self.serif = pick(["Newsreader", "Georgia", "Palatino"], "Times New Roman")
        self.sans = pick(["DM Sans", "Helvetica Neue", "Segoe UI"], "Helvetica")
        self.mono = pick(["JetBrains Mono", "Menlo", "Consolas"], "Courier New")


def setup_styles(root: tk.Misc, fonts: Fonts) -> None:
    s = ttk.Style(root)
    s.theme_use("clam")
    sans, mono, serif = fonts.sans, fonts.mono, fonts.serif

    # --- PsyDocs styles, verbatim
    s.configure("TFrame", background=C["bg"])
    s.configure("Panel.TFrame", background=C["panel"])
    s.configure("Preview.TFrame", background=C["preview_bg"])
    s.configure("Warn.TFrame", background=C["warn_bg"])

    s.configure("TLabel", background=C["bg"], foreground=C["text"], font=(sans, 12))
    s.configure("Title.TLabel", background=C["bg"], foreground=C["ink"], font=(serif, 26))
    s.configure("Tagline.TLabel", background=C["bg"], foreground=C["muted"],
                font=(mono, 9, "bold"))
    s.configure("Field.TLabel", background=C["bg"], foreground=C["muted"],
                font=(mono, 9, "bold"))
    s.configure("PanelTitle.TLabel", background=C["bg"], foreground=C["ink"],
                font=(serif, 14, "italic"))
    s.configure("Note.TLabel", background=C["bg"], foreground=C["muted"],
                font=(serif, 11, "italic"))
    s.configure("Warn.TLabel", background=C["warn_bg"], foreground=C["text"], font=(sans, 10))
    s.configure("PreviewTitle.TLabel", background=C["preview_bg"], foreground=C["ink"],
                font=(serif, 14, "italic"))
    s.configure("PreviewSub.TLabel", background=C["preview_bg"], foreground=C["teal"],
                font=(mono, 8, "bold"))
    s.configure("Count.TLabel", background=C["green"], foreground=C["bg"],
                font=(mono, 9, "bold"), padding=(8, 2))
    s.configure("CountNote.TLabel", background=C["preview_bg"], foreground=C["muted"],
                font=(sans, 10))

    s.configure("TEntry", fieldbackground=C["field"], foreground=C["text"],
                bordercolor=C["border"], lightcolor=C["border"], darkcolor=C["border"],
                insertcolor=C["text"], padding=(8, 7))
    s.map("TEntry", bordercolor=[("focus", C["teal"])],
          lightcolor=[("focus", C["teal"])], darkcolor=[("focus", C["teal"])])

    s.configure("TCombobox", fieldbackground=C["field"], background=C["chip"],
                foreground=C["text"], bordercolor=C["border"], lightcolor=C["border"],
                darkcolor=C["border"], arrowcolor=C["muted"], padding=(8, 6))
    s.map("TCombobox", fieldbackground=[("readonly", C["field"])],
          bordercolor=[("focus", C["teal"])])

    s.configure("Panel.TCheckbutton", background=C["panel"], foreground=C["text"],
                font=(sans, 12), indicatorbackground=C["field"],
                indicatorforeground=C["bg"], padding=(2, 3))
    s.map("Panel.TCheckbutton",
          background=[("active", C["panel"])],
          indicatorbackground=[("selected", C["green"]), ("!selected", C["field"])],
          indicatorforeground=[("selected", C["bg"])])

    s.configure("Accent.TButton", background=C["green"], foreground=C["bg"],
                bordercolor=C["green"], lightcolor=C["green"], darkcolor=C["green"],
                focuscolor=C["green"], font=(sans, 12, "bold"), padding=(20, 10))
    s.map("Accent.TButton",
          background=[("active", C["green_hover"]), ("pressed", C["green_hover"])])

    s.configure("Small.TButton", background=C["chip"], foreground=C["text"],
                bordercolor=C["border"], lightcolor=C["chip"], darkcolor=C["chip"],
                focuscolor=C["chip"], font=(sans, 12), padding=(10, 6))
    s.map("Small.TButton", background=[("active", C["border"])])

    s.configure("Lang.TButton", background=C["chip"], foreground=C["muted"],
                bordercolor=C["border"], lightcolor=C["chip"], darkcolor=C["chip"],
                focuscolor=C["chip"], font=(mono, 9, "bold"), padding=(7, 3))
    s.map("Lang.TButton", background=[("active", C["border"])])
    s.configure("LangActive.TButton", background=C["green"], foreground=C["bg"],
                bordercolor=C["green"], lightcolor=C["green"], darkcolor=C["green"],
                focuscolor=C["green"], font=(mono, 9, "bold"), padding=(7, 3))
    s.map("LangActive.TButton", background=[("active", C["green"])])

    # --- PsySet additions
    s.configure("TaglineOn.TLabel", background=C["bg"], foreground=C["green"],
                font=(mono, 9, "bold"))
    s.configure("Group.TLabel", background=C["panel"], foreground=C["green"],
                font=(mono, 9, "bold"))
    s.configure("Empty.TLabel", background=C["panel"], foreground=C["muted"],
                font=(serif, 12, "italic"))
    # dialogs (Task 10): file rows inside panels, the assign-role radio buttons
    s.configure("Panel.TLabel", background=C["panel"], foreground=C["text"], font=(sans, 12))
    s.configure("TRadiobutton", background=C["bg"], foreground=C["text"], font=(sans, 12),
                indicatorbackground=C["field"], padding=(2, 3))
    s.map("TRadiobutton", background=[("active", C["bg"])],
          indicatorbackground=[("selected", C["green"]), ("!selected", C["field"])])
    # test rows: a ticked row is lifted onto the field colour
    for name, bg in (("Row", C["panel"]), ("RowOn", C["field"])):
        s.configure(f"{name}.TCheckbutton", background=bg, indicatorbackground=C["field"],
                    indicatorforeground=C["bg"], padding=(2, 1))
        s.map(f"{name}.TCheckbutton", background=[("active", bg)],
              indicatorbackground=[("selected", C["green"]), ("!selected", C["field"])],
              indicatorforeground=[("selected", C["bg"])])
    s.configure("Vertical.TScrollbar", background=C["chip"], troughcolor=C["panel"],
                bordercolor=C["panel"], lightcolor=C["chip"], darkcolor=C["chip"],
                arrowcolor=C["muted"])
    # detail box (field-coloured card under the tests list)
    s.configure("Detail.TFrame", background=C["field"])
    s.configure("DetailHead.TLabel", background=C["field"], foreground=C["muted"],
                font=(mono, 9, "bold"))
    s.configure("DetailRef.TLabel", background=C["field"], foreground=C["text"],
                font=(serif, 13, "italic"))
    s.configure("DetailNone.TLabel", background=C["field"], foreground=C["faint"],
                font=(serif, 13, "italic"))
    s.configure("DetailFile.TLabel", background=C["field"], foreground=C["faint"],
                font=(sans, 11))
    # session pane (Task 9): same family as PsyDocs' preview column
    s.configure("Session.TFrame", background=C["preview_bg"])
    s.configure("SessionTitle.TLabel", background=C["preview_bg"], foreground=C["ink"],
                font=(serif, 16, "italic"))
    s.configure("SessionSub.TLabel", background=C["preview_bg"], foreground=C["teal"],
                font=(mono, 8, "bold"))
    s.configure("SessionField.TLabel", background=C["preview_bg"], foreground=C["muted"],
                font=(mono, 9, "bold"))
    s.configure("SessionText.TLabel", background=C["preview_bg"], foreground=C["text"],
                font=(sans, 12))
    s.configure("SessionCount.TLabel", background=C["preview_bg"], foreground=C["muted"],
                font=(sans, 11))
    s.configure("SessionEmpty.TLabel", background=C["field"], foreground=C["muted"],
                font=(serif, 12, "italic"))
    s.configure("Session.TCheckbutton", background=C["preview_bg"], foreground=C["text"],
                font=(sans, 12), indicatorbackground=C["field"],
                indicatorforeground=C["bg"], padding=(0, 2))
    s.map("Session.TCheckbutton", background=[("active", C["preview_bg"])],
          indicatorbackground=[("selected", C["green"]), ("!selected", C["field"])],
          indicatorforeground=[("selected", C["bg"])])
    s.map("Accent.TButton", background=[("disabled", C["faint"]), ("active", C["green_hover"]),
                                        ("pressed", C["green_hover"])],
          foreground=[("disabled", C["field"])])

    # named fonts for the Tag chips (tk.Label: ttk cannot strike text through)
    for name, overstrike in (("PsyTag", False), ("PsyTagX", True)):
        try:
            tkfont.Font(root, name=name, family=mono, size=8, weight="bold",
                        overstrike=overstrike)
        except tk.TclError:  # already created by an earlier call
            tkfont.nametofont(name, root).configure(family=mono)


def _fade(color: str, base: str, alpha: float) -> str:
    """`color` at `alpha` opacity over `base` (Tk has no alpha)."""
    a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(base[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * alpha + y * (1 - alpha)):02X}" for x, y in zip(a, b))


TAG_COLORS = {  # kind -> (background, foreground)
    "sheet": (C["sage_bg"], C["green"]),
    "crf": (C["clay_bg"], C["clay_ink"]),
    "ref": (C["chip"], C["muted"]),
}


class Tag(tk.Label):
    """Role chip: SHEET / CRF / INSTR / NORMS. Missing -> faded, struck through, inert."""

    def __init__(self, master, text: str, kind: str, present: bool, count: int = 0,
                 command=None, width: int = 0):
        bg, fg = TAG_COLORS[kind]
        if not present:
            bg, fg = _fade(bg, C["panel"], 0.35), _fade(fg, C["panel"], 0.35)
        if count > 1:
            text = f"{text} ×{count}"
        super().__init__(master, text=text, bg=bg, fg=fg, width=width,
                         font="PsyTag" if present else "PsyTagX", padx=5, pady=1, bd=0,
                         highlightthickness=1, highlightbackground=bg,
                         cursor="hand2" if present and command else "")
        self.present = present
        if present and command:
            self.bind("<Button-1>", lambda _e: command())
            self.bind("<Enter>", lambda _e: self.configure(highlightbackground=C["teal"]))
            self.bind("<Leave>", lambda _e: self.configure(highlightbackground=bg))
