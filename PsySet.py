"""PsySet entry point (PyInstaller target)."""
import tkinter as tk

from psyset.config import load_config
from psyset.ui.dialogs import first_launch, library_problem
from psyset.ui.main_window import MainWindow


def main() -> None:
    root = tk.Tk()
    cfg = load_config()
    if library_problem(cfg) is not None:  # never set up, or the folder is gone / offline
        root.withdraw()
        if not first_launch(root, cfg):
            root.destroy()
            return
        root.deiconify()
    MainWindow(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()
