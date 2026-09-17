# -*- coding: utf-8 -*-
"""Notificaciones de escritorio."""

import shutil
import subprocess


def notify(title, message):
    try:
        import gi  # noqa: F401

        gi.require_version("Notify", "0.7")
        from gi.repository import Notify

        Notify.init("Antivinux")
        notification = Notify.Notification.new(title, message, "antivinux")
        notification.set_timeout(6000)
        notification.show()
        return
    except Exception:
        pass

    notify_send = shutil.which("notify-send")
    if notify_send:
        subprocess.Popen([notify_send, "-i", "antivinux", title, message])
        return
    try:
        print("{0}: {1}".format(title, message))
    except Exception:
        pass


__all__ = ["notify"]