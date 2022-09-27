from gi.repository import Gtk, Gio, Adw, GObject
from pathlib import Path

from .desktop_entry import DesktopEntry, DesktopEntryFolder


class AppRow(Adw.ActionRow):
    __gtype_name__ = 'AppRow'

    def __init__(self, file: DesktopEntry):
        self.file = file
        self.file.load()
        
        super().__init__(
            title = self.file.appsection.Name.get(),
            subtitle = self.file.appsection.Comment.get(),
            activatable = True,)

        icon = Gtk.Image(
            pixel_size=32,
            margin_top=6,
            margin_bottom=6,
            css_classes=['icon-dropshadow'])
        
        icon_name = file.appsection.Icon.get()
        if icon_name == None:
            icon.set_from_icon_name('image-missing')
        elif Path(icon_name).exists():
            icon.set_from_file(icon_name)
        else:
            icon.set_from_icon_name(icon_name)

        self.add_prefix(icon)

        self.add_suffix(Gtk.Image(
            icon_name='go-next-symbolic',
            opacity=.6))

        self.connect('activated', lambda _: self.emit('file-open', file))

@Gtk.Template(resource_path='/io/github/fabrialberio/pinapp/apps_view.ui')
class AppsView(Gtk.Box):
    __gtype_name__ = 'AppsView'

    new_file_button = Gtk.Template.Child('new_file_button')

    folder_chooser_box = Gtk.Template.Child('folder_chooser_box')
    user_button = Gtk.Template.Child('user_button')
    spinner_button = Gtk.Template.Child('spinner_button')

    user_group = Gtk.Template.Child('user_group')
    system_group = Gtk.Template.Child('system_group')
    flatpak_group = Gtk.Template.Child('flatpak_group')

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

        GObject.type_register(AppsView)
        GObject.signal_new('file-open', AppsView, GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,))

        GObject.type_register(AppRow)
        GObject.signal_new('file-open', AppRow, GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,))

        self.new_file_button.connect('clicked', lambda _: self.new_file())

        self.user_folder = DesktopEntryFolder(DesktopEntryFolder.USER_APPLICATIONS)
        self.system_folder = DesktopEntryFolder(DesktopEntryFolder.SYSTEM_APPLICATIONS)
        self.flatpak_folder = DesktopEntryFolder(DesktopEntryFolder.FLATPAK_SYSTEM_APPLICATIONS)

        self.is_loading = False
        self.update_all_apps()

    def is_visible(self):
        return isinstance(self.get_parent().get_visible_child(), AppsView)

    def new_file(self):
        if not self.is_visible():
            return

        builder = Gtk.Builder.new_from_resource('/io/github/fabrialberio/pinapp/apps_view_dialogs.ui')
        dialog = builder.get_object('filename_dialog')
        name_entry = builder.get_object('name_entry')

        def path_is_valid() -> bool:
            path = name_entry.get_text()
            if '/' in path:
                return False
            else:
                return True

        name_entry.connect('changed', lambda _: dialog.set_response_enabled(
            'create',
            path_is_valid()))

        def callback(widget, resp):
            if resp == 'create':
                path = DesktopEntryFolder.USER_APPLICATIONS / Path(f'{Path(name_entry.get_text())}.desktop')
                file = DesktopEntry.new_with_defaults(path)

                self.emit('file-open', file)

        dialog.connect('response', callback)
        dialog.set_transient_for(self.get_root())
        dialog.show()

    def update_user_apps(self):
        """Exposed function used by other classes"""
        self._update_apps(self.user_group, self.user_folder)

    def update_all_apps(self):        
        self.update_user_apps()
        self._update_apps(
            self.system_group, 
            self.system_folder)
        self._update_apps(
            self.flatpak_group, 
            self.flatpak_folder)

    def _update_apps(self, preferences_group, folder: DesktopEntryFolder):
        self._set_loading(True)
        self._clear_preferences_group(preferences_group)

        def fill_group():
            app_rows = []
            for file in folder.files:
                row = AppRow(file)
                row.connect('file_open', lambda _, f: self.emit('file-open', f))
                app_rows.append(row)
    
            for row in app_rows:
                preferences_group.add(row)

            self._set_loading(False)

        folder.get_files_async(callback=fill_group)

    def _set_loading(self, state: bool):
        if self.is_loading == state:
            return

        if state:
            self.spinner_button.set_active(True)
            self.folder_chooser_box.set_sensitive(False)
            self.is_loading = True
        else:
            self.folder_chooser_box.set_sensitive(True)
            self.user_button.set_active(True)
            self.is_loading = False

    def _clear_preferences_group(self, preferences_group):
        listbox = (
            preferences_group
            .get_first_child()  # Main group GtkBox
            .get_last_child()   # GtkBox containing the listbox
            .get_first_child()) # GtkListbox
    
        
        while (row := listbox.get_first_child()) != None:
            preferences_group.remove(row)
