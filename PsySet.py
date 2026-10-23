"""PsySet entry point (PyInstaller target)."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from psyset.config import load_config, save_config
from psyset.i18n import t
from psyset.ui.main_window import MainWindow


def main() -> None:
    root = tk.Tk()
    cfg = load_config()
    lib = cfg.get("library")
    if not (isinstance(lib, str) and lib and Path(lib).is_dir()):
        # ponytail: temporary fallback until Task 10's first-launch screen
        root.withdraw()
        lib = filedialog.askdirectory(parent=root, mustexist=True,
                                      title=t(cfg.get("lang", "fr"), "fl_pick_folder"))
        if not lib:
            root.destroy()
            return
        cfg["library"] = str(lib)
        save_config(cfg)
        root.deiconify()
    MainWindow(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()
