from gi.repository import Gtk, Gio, Adw, GObject

from pathlib import Path
from os import access, W_OK

from .desktop_entry import DesktopEntryFolder, DesktopEntry, Field

@Gtk.Template(resource_path='/com/github/fabrialberio/pinapp/file_view.ui')
class FileView(Gtk.Box):
    __gtype_name__ = 'FileView'

    window_title = Gtk.Template.Child('title_widget')
    back_button = Gtk.Template.Child('back_button')
    save_button = Gtk.Template.Child('save_button')
    delete_button = Gtk.Template.Child('delete_button')

    scrolled_window = Gtk.Template.Child('scrolled_window')
    main_view = Gtk.Template.Child('main_box')

    app_icon = Gtk.Template.Child('app_icon')
    banner_box = Gtk.Template.Child('name_comment_box')
    
    localized_group = Gtk.Template.Child('localized_group')
    strings_group = Gtk.Template.Child('strings_group')
    bools_group = Gtk.Template.Child('bools_group')

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.file = None

        GObject.type_register(FileView)
        GObject.signal_new('file-back', FileView, GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ())
        GObject.signal_new('file-save', FileView, GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ())
        GObject.signal_new('file-delete', FileView, GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ())
        GObject.signal_new('file-edit', FileView, GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ())
        GObject.signal_new('add-string-field', FileView, GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ())
        GObject.signal_new('add-bool-field', FileView, GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ())

        self.back_button.connect('clicked', lambda _: self.emit('file-back'))
        self.save_button.connect('clicked', lambda _: self.save_file())
        self.delete_button.connect('clicked', lambda _: self.delete_file())
        self.strings_group.get_header_suffix().connect('clicked', lambda _: self._add_key())
        self.bools_group.get_header_suffix().connect('clicked', lambda _: self._add_key(is_bool=True))

    def is_visible(self):
        return isinstance(self.get_parent().get_visible_child(), FileView)

    def delete_file(self):
        builder = Gtk.Builder.new_from_resource('/com/github/fabrialberio/pinapp/file_view_dialogs.ui')
        
        dialog = builder.get_object('confirm_delete_dialog')

        def callback(widget, resp):
            if resp == 'delete':
                self.file.delete()
                self.emit('file-delete')

        dialog.connect('response', callback)
        dialog.set_transient_for(self.get_root())
        dialog.present()

    def load_file(self, file: DesktopEntry):
        self.file = file
        
        if self.file.path.exists():
            self.file.load()

        self.scrolled_window.set_vadjustment(Gtk.Adjustment.new(0, 0, 0, 0, 0, 0))

        while self.banner_box.get_first_child():
            self.banner_box.remove(self.banner_box.get_first_child())

        app_name_row = StringRow(self.file.appsection.Name)
        app_name_row.add_css_class('title-2')
        app_comment_row = StringRow(self.file.appsection.Comment)
        
        self.banner_box.append(app_name_row)
        self.banner_box.append(app_comment_row)

        self.window_title.set_subtitle(self.file.filename)
        self.save_button.set_sensitive(True)

        if access(self.file.path, W_OK):
            self.delete_button.set_visible(True)
        else:
            self.delete_button.set_visible(False)

        self.update_file()

    def update_file(self):
        file_dict: dict = self.file.appsection.as_dict()

        icon_name = self.file.appsection.Icon.get()
        if icon_name == None:
            self.app_icon.set_from_icon_name('image-missing')
        elif Path(icon_name).exists():
            self.app_icon.set_from_file(icon_name)
        else:
            self.app_icon.set_from_icon_name(icon_name)

        file_dict.pop('Name', '')
        file_dict.pop('Comment', '')

        localized_rows = LocaleStringRow.list_from_field_list(list(self.file.appsection.values()))
        self._update_preferences_group(self.localized_group, localized_rows)

        string_rows = StringRow.list_from_field_list(file_dict.values())
        self._update_preferences_group(self.strings_group, string_rows, Adw.ActionRow(
            title=_('No string values present'),
            title_lines=1,
            css_classes=['dim-label'],
            halign=Gtk.Align.CENTER))

        bool_rows = BoolRow.list_from_field_list(file_dict.values())
        self._update_preferences_group(self.bools_group, bool_rows, Adw.ActionRow(
            title=_('No boolean values present'),
            title_lines=1,
            css_classes=['dim-label'],
            halign=Gtk.Align.CENTER))

        if localized_rows:
            self.localized_group.set_visible(True)
        else:
            self.localized_group.set_visible(False)

    def save_file(self):
        if not self.is_visible(): 
            return

        def callback():
            self.emit('file-save')

        try:
            self.file.save()
            callback()
        except OSError:
            self._save_to_user_folder(callback)


    def _save_to_user_folder(self, on_success_callback: callable):
        builder = Gtk.Builder.new_from_resource('/com/github/fabrialberio/pinapp/file_view_dialogs.ui')
        
        dialog = builder.get_object('save_local_dialog')

        def callback(widget, resp):
            if resp == 'yes':
                self.file.save(Path(DesktopEntryFolder.USER_APPLICATIONS)/self.file.filename)
                on_success_callback()

        dialog.connect('response', callback)
        dialog.set_transient_for(self.get_root())
        dialog.present()

    def _add_key(self, is_bool=False):
        builder = Gtk.Builder.new_from_resource('/com/github/fabrialberio/pinapp/file_view_dialogs.ui')

        add_key_dialog = builder.get_object('add_key_dialog')
        key_entry = builder.get_object('key_entry')

        key_entry.connect('changed', lambda _: add_key_dialog.set_response_enabled(
            'add', 
            bool(key_entry.get_text())))

        def callback(widget, resp):
            if resp == 'add':
                self.file.appsection.add_entry(key_entry.get_text(), False if is_bool else '')
                self.update_file()

        add_key_dialog.connect('response', callback)
        add_key_dialog.set_transient_for(self.get_root())
        add_key_dialog.present()


    def _update_preferences_group(self, preferences_group: Adw.PreferencesGroup, new_children: list[Gtk.Widget], empty_state: Gtk.Widget = None):
        '''Removes all present children of the group and adds the new ones'''

        listbox = (
            preferences_group
            .get_first_child()  # Main group GtkBox
            .get_last_child()   # GtkBox containing the listbox
            .get_first_child()) # GtkListbox

        while (row := listbox.get_first_child()) != None:
            preferences_group.remove(row)

        if len(new_children) > 0:
            for c in new_children:
                preferences_group.add(c)
        elif empty_state != None:
            preferences_group.add(empty_state)


class BoolRow(Adw.ActionRow):
    def __init__(self, field: Field) -> None:
        self.field = field

        self.switch = Gtk.Switch(
            active=field.as_bool(),
            valign=Gtk.Align.CENTER,
        )
        self.switch.connect('state-set', self.on_state_set)

        super().__init__(
            title=field.key,
            activatable_widget=self.switch,
        )
        self.add_suffix(self.switch)

    @staticmethod
    def list_from_field_list(fields: list[Field]):
        return [BoolRow(f) for f in fields if type(f.get()) == bool]

    def on_state_set(self, widget, value):
        self.field.set(value)

class StringRow(Adw.EntryRow):
    def __init__(self, field: Field) -> None:
        self.field = field
        
        super().__init__(title=field.key)
        self.set_text(field.as_str() or '')
        self.connect('changed', self.on_changed)
        
    def add_action(self, icon_name: str, tooltip: str, callback):
        button = Gtk.Button(
                icon_name=icon_name,
                tooltip_text=tooltip,
                valign=Gtk.Align.CENTER,
                css_classes=['flat'])

        button.connect('clicked', callback)
        self.add_suffix(button)


    @staticmethod
    def list_from_field_list(fields: list[Field]):
        return [StringRow(f) for f in fields if ((t := type(f.get())) == str or t == list) and not f.locale]

    def on_changed(self, widget):
        self.field.set(self.get_text())

class LocaleStringRow(Adw.EntryRow):
    def __init__(self, field: Field) -> None:
        self.field = field

        locales = [f.locale for f in self.field.localized_fields]
        self.dropdown = Gtk.DropDown.new_from_strings(sorted(locales))
        self.dropdown.set_valign(Gtk.Align.CENTER)
        self.dropdown.connect('notify', self._on_dropdown_notify)

        super().__init__(title=field.key.capitalize())
        self.add_suffix(self.dropdown)
        self.connect('changed', self._on_changed)

    @staticmethod
    def list_from_field_list(fields: list[Field]):
        if len(fields) > 0:
            # Assumes that all keys are in the same section
            section = fields[0].section
            
            # All keys that have a locale, but stripped of it
            localized_keys = [f.unlocalized_key for f in fields if f.localized_fields]
            # Remove duplicates
            localized_keys = list(dict.fromkeys(localized_keys))

            return [LocaleStringRow(Field(k, section)) for k in localized_keys]
        else:
            return []

    @property
    def selected_locale(self):
        return self.dropdown.get_selected_item().get_string()

    def _on_dropdown_notify(self, widget, value):
        self.set_text(self.field.localize(self.selected_locale).as_str())

    def _on_changed(self, widget):
        self.field.localize(self.selected_locale).set(self.get_text())