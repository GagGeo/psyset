from psyset.ui.main_window import wheel_notches


def test_wheel_notches_per_platform():
    assert wheel_notches(3, "aqua", 8.6) == 3          # Tk 8.6 macOS: raw delta
    assert wheel_notches(-120, "aqua", 9.0) == -1      # Tk 9 macOS: 120 per notch
    assert wheel_notches(120, "win32", 8.6) == 1
    assert wheel_notches(40, "win32", 8.6) == 40 / 120  # precision touchpad: a third of a notch
    assert wheel_notches(-120, "x11", 8.6) == -1
