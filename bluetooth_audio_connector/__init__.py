from .app import App


def main():
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = App()
    app.run()
