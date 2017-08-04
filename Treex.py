import sys
import enum

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk

ModelColumn = enum.IntEnum(
    "ModelColumn",
    "OFFSET SIZE DATA FORMULA COMMENT",
    start = 0
)
MODEL_COL_TYPES = [int, int, int, str, str]

DEFAULT_ROW = [0, 2, 0, "", ""]

FilterColumn = enum.IntEnum(
    "FilterColumn",
    "OFFSET DATA COMMENT",
    start = 0
)
FILTER_COL_TYPES = [str, str, str]

class AppWindowWrapper:
    __UIFILE__ = "main.ui"
    
    def __init__(self, app):
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.__UIFILE__)
        self.window = self.builder.get_object("win_main")
        self.editor = self.builder.get_object("ent_formula")
        self.selection = self.builder.get_object("tvs_selection_data")
        self.treeview = self.builder.get_object("tv_data")
        
        self.window.set_title("Treex")
        self.window.set_application(app)
        self.create_model()
        self.builder.connect_signals(self)
    
    def create_model(self):
        self.model = Gtk.TreeStore(*MODEL_COL_TYPES)
        self.model_filter = self.model.filter_new()
        self.model_filter.set_modify_func(
            FILTER_COL_TYPES,
            self.filter_model
        )
        self.treeview.set_model(self.model_filter)
    
    def filter_model(self, model_filter, treeiter_filter, column):
        treeiter = model_filter.convert_iter_to_child_iter(treeiter_filter)
        if column == FilterColumn.OFFSET:
            return "{:08x}".format(self.model[treeiter][ModelColumn.OFFSET])
        elif column == FilterColumn.DATA:
            return "{1:0{0}X}".format(self.model[treeiter][ModelColumn.SIZE]*2, self.model[treeiter][ModelColumn.DATA])
        elif column == FilterColumn.COMMENT:
            return self.model[treeiter][ModelColumn.COMMENT]
        else:
            return "Failed"
    
    def on_tb_add_root_clicked(self, widget):
        fmodel, ftreeiter = self.selection.get_selected()
        if ftreeiter != None:
            treeiter = fmodel.convert_iter_to_child_iter(ftreeiter)
            parent = self.model.iter_parent(treeiter) # parent can be None
        else:
            parent = None
            treeiter = None
        child = self.model.insert_after(parent, treeiter, DEFAULT_ROW)
        _, fchild = fmodel.convert_child_iter_to_iter(child)
        self.selection.select_iter(fchild)
    
    def on_tb_add_child_clicked(self, widget):
        fmodel, ftreeiter = self.selection.get_selected()
        treeiter = fmodel.convert_iter_to_child_iter(ftreeiter)
        child = self.model.append(treeiter, DEFAULT_ROW) # treeiter can be None
        if ftreeiter != None:
            fpath = fmodel.get_path(ftreeiter)
            self.treeview.expand_row(fpath, False)
        _, fchild = fmodel.convert_child_iter_to_iter(child)
        self.selection.select_iter(fchild)
    
    def on_tb_remove_clicked(self, widget):
        fmodel, ftreeiter = self.selection.get_selected()
        if ftreeiter != None:
            treeiter = fmodel.convert_iter_to_child_iter(ftreeiter)
            previous = self.model.iter_previous(treeiter)
            if previous == None:
                previous = self.model.iter_parent(treeiter)
            if previous:
                _, fprevious = fmodel.convert_child_iter_to_iter(previous)
                self.selection.select_iter(fprevious)
            else:
                self.selection.unselect_all()
            self.model.remove(treeiter)
    
    def on_tvs_selection_data_changed(self, widget):
        model, treeiter = widget.get_selected()
        if treeiter != None:
            self.editor.set_text(self.model_filter[treeiter][FilterColumn.DATA])
        else:
            self.editor.set_text("")
    
    def on_ent_formula_changed(self, widget):
        fmodel, ftreeiter = self.selection.get_selected()
        print("Pout")
        if ftreeiter != None:
            treeiter = fmodel.convert_iter_to_child_iter(ftreeiter)
            try:
                value = int(self.editor.get_text(), base=16)
            except ValueError:
                pass
            else:
                self.model[treeiter][ModelColumn.DATA] = value
    
    def on_tvcr_data_comment_edited(self, widget, path, new_text):
        treeiter = self.model.get_iter_from_string(path)
        if treeiter != None:
            self.model[treeiter][ModelColumn.COMMENT] = new_text
    
    def present(self):
        self.window.present()

class Application(Gtk.Application):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="org.cilyan.treex", **kwargs)
        self.window = None
        self.builder = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

    def do_activate(self):
        # We only allow a single window and raise any existing ones
        if not self.window:
            self.window = AppWindowWrapper(self)
        self.window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        self.activate()
        return 0

    def on_about(self, action, param):
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()

    def on_quit(self, action, param):
        self.quit()

if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)
