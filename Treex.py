import sys
import enum
import weakref

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, GLib, Gio, Gtk

CHR = ord('A')

class TreexNode:
    def __init__(self, parent = None, offset = 0, data = 0, size = 2, comment = ""):
        global CHR
        self._offset = offset
        self._data = data
        self._comment = chr(CHR)
        CHR += 1
        self._size = size
        self._notify_func = None
        self.parent = parent
        self._children = []
    def __repr__(self):
        return '<TreexNode ' + self._comment + '>'
    @property
    def data(self):
        return self._data
    @property
    def comment(self):
        return self._comment
    @property
    def size(self):
        return self._size
    @property
    def offset(self):
        return self._offset
    
    @data.setter
    def data(self, value):
        self._data = value
        self.notify()
    @comment.setter
    def comment(self, value):
        self._comment = value
        self.notify()
    @size.setter
    def size(self, value):
        self._size = value
        self.notify()
    @offset.setter
    def offset(self, value):
        self._offset = value
        self.notify()
    
    def get_nth_child(self, n):
        return None if n >= len(self._children) else self._children[n]
    def get_child_pos(self, child):
        return self._children.index(child)
    def get_next_child(self, child):
        try:
            index = self.get_child_pos(child)
        except ValueError:
            return None
        else:
            return self.get_nth_child(index+1)
    def get_previous_child(self, child):
        try:
            index = self.get_child_pos(child)
        except ValueError:
            return None
        else:
            return self.get_nth_child(index-1) if index > 1 else None
    def get_n_children(self):
        return len(self._children)
    def set_parent(self, parent):
        self.parent = parent
    def set_notify(self, func):
        self._notify_func = func
    def append(self, child):
        self._children.append(child)
        child.set_parent(self)
    def insert_after(self, sibling, child):
        if sibling is not None:
            index = self.get_child_pos(sibling)
        else:
            index = -1
        self._children.insert(index+1, child)
        child.set_parent(self)
    def remove(self, child):
        self._children.remove(child)
        child.set_parent(None)
    
    def notify(self):
        if self._notify_func:
            self._notify_func(self)

class TreexTreeModel(GObject.GObject, Gtk.TreeModel):
    COLUMNS = (str, str, str)
    
    COL_OFFSET = 0
    COL_DATA = 1
    COL_COMMENT = 2
    
    def __init__(self):
        super().__init__()
        self.tree = TreexNode()
        self.node_refs = weakref.WeakValueDictionary()
        for i in range(4):
            obj = TreexNode(self.tree, 0, 4, 2)
            self.tree.append(obj)
            self.register_node(obj)
    
    def do_get_flags(self):
        return Gtk.TreeModelFlags.ITERS_PERSIST
    
    def do_get_iter(self, path):
        indices = path.get_indices()
        print("get iter:", indices)
        it = iter(indices)
        node = self.tree.get_nth_child(next(it))
        if not node:
            return (False, None)
        for indice in it:
            node = node.get_nth_child(indice)
            if not node:
                return (False, None)
        print("get iter ->", node)
        return (True, self.get_node_iter(node))
    
    def do_iter_next(self, iter_):
        node = self.get_node(iter_)
        print("next from:", node)
        if not node:
            return (False, None)
        sibling = node.parent.get_next_child(node)
        print("next from ->", sibling)
        if not sibling:
            return (False, None)
        return (True, self.get_node_iter(sibling))
    
    def do_iter_previous(self, iter_):
        node = self.get_node(iter_)
        print("previous from:", node)
        if not node:
            return (False, None)
        sibling = node.parent.get_previous_child(node)
        print("previous from ->", sibling)
        if not sibling:
            return (False, None)
        return (True, self.get_node_iter(sibling))
    
    def do_iter_has_child(self, iter_):
        assert iter_ is not None
        node = self.get_node(iter_)
        print("has child:", node)
        if not node:
            return False
        else:
            return (node.get_n_children() > 0)
    
    def do_iter_n_children(self, iter_):
        if iter_ is None:
            node = self.tree
        else:
            node = self.get_node(iter_)
        print("n children:", node)
        return node.get_n_children()
    
    def do_iter_nth_child(self, iter_, n):
        parent = self.get_node(iter_)
        if not parent:
            parent = self.tree
        node = parent.get_nth_child(n)
        if not node:
            return (False, None)
        citer_ = Gtk.TreeIter()
        citer_.user_data = id(node)
        return (True, citer_)
    
    def do_iter_parent(self, iter_):
        node = self.get_node(iter_)
        print("parent of", node)
        if not node:
            return (False, None)
        parent = node.parent
        if parent is self.tree:
            return (False, None) # top level
        return (True, self.get_node_iter(parent))
    
    def do_iter_children(self, iter_):
        if iter_ is None:
            parent = self.tree
        else:
            parent = self.get_node(iter_)
        child = parent.get_nth_child(0)
        if child is None:
            return (False, None)
        return (True, self.get_node_iter(child))
    
    def do_get_path(self, iter_):
        node = self.get_node(iter_)
        print("path of:", node)
        if not node:
            raise RuntimeError("cannot get path of invalid iter")
        parent = node.parent
        indices = []
        while parent is not None:
            indices.insert(0, parent.get_child_pos(node))
            node = parent
            parent = node.parent
        print("path of ->", indices)
        return Gtk.TreePath(tuple(indices))
    
    def do_get_n_columns(self):
        return len(self.COLUMNS)
    
    def do_get_column_type(self, column):
        return self.COLUMNS[column]
    
    def do_get_value(self, iter_, column):
        node = self.get_node(iter_)
        print("value of", column, node)
        if not node:
            return None
        return (
            self._get_col_offset,
            self._get_col_data,
            self._get_col_comment
        )[column](node)
    
    def _get_col_offset(self, node):
        return "{:08x}".format(node.offset)
    
    def _get_col_data(self, node):
        return "{1:0{0}X}".format(node.size*2, node.data)
    
    def _get_col_comment(self, node):
        return node.comment
    
    def get_node(self, iter_):
        if iter_ is None:
            return None
        node = self.node_refs.get(iter_.user_data, None)
        print("Node of", iter_.user_data, node)
        return node
    
    def register_node(self, node):
        self.node_refs[id(node)] = node
    
    def get_node_iter(self, node):
        if not id(node) in self.node_refs:
            raise RuntimeError("Node is not registered")
        iter_ = Gtk.TreeIter()
        iter_.user_data = id(node)
        return iter_
    
    def append(self, parent, node):
        if parent is None:
            parent = self.tree
        was_alone = parent.get_n_children() == 0
        parent.append(node)
        self.register_node(node)
        node.set_notify(self._node_changed_cb)
        iter_ = self.get_node_iter(node)
        path = self.get_path(iter_)
        print("==== Appended", node, path.get_indices())
        if was_alone:
            piter = self.get_node_iter(parent)
            ppath = self.get_path(piter)
            self.row_has_child_toggled(ppath, piter)
        self.row_inserted(path, iter_)
        return iter_
    
    def insert_after(self, sibling, node):
        if sibling is None:
            parent = self.tree
        else:
            parent = sibling.parent
        was_alone = parent.get_n_children() == 0
        parent.insert_after(sibling, node)
        self.register_node(node)
        node.set_notify(self._node_changed_cb)
        iter_ = self.get_node_iter(node)
        path = self.get_path(iter_)
        print("==== Inserted", node, path.get_indices())
        if was_alone:
            piter = self.get_node_iter(parent)
            ppath = self.get_path(piter)
            self.row_has_child_toggled(ppath, piter)
        self.row_inserted(path, iter_)
        return iter_
    
    def remove(self, node):
        iter_ = self.get_node_iter(node)
        path = self.get_path(iter_)
        parent = node.parent
        was_alone = parent.get_n_children() == 0
        parent.remove(node)
        is_alone = parent.get_n_children() == 0
        node.set_notify(None)
        if (not was_alone) and is_alone:
            piter = self.get_node_iter(parent)
            ppath = self.get_path(piter)
            self.row_has_child_toggled(ppath, piter)
        self.row_deleted(path)
    
    def _node_changed_cb(self, node):
        iter_ = self.get_node_iter(node)
        path = self.get_path(iter_)
        self.row_changed(path, iter_)

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
        self.builder.connect_signals(self)
        
        self.model = TreexTreeModel()
        self.treeview.set_model(self.model)
    
    def on_tb_add_root_clicked(self, widget):
        model, treeiter = self.selection.get_selected()
        if treeiter != None:
            sibling = self.model.get_node(treeiter)
        else:
            sibling = None
        node = TreexNode()
        node_iter = self.model.insert_after(sibling, node)
        self.selection.select_iter(node_iter)
    
    def on_tb_add_child_clicked(self, widget):
        model, treeiter = self.selection.get_selected()
        node = TreexNode()
        parent = self.model.get_node(treeiter)
        child_iter = self.model.append(parent, node) # treeiter can be None
        if treeiter != None:
            path = self.model.get_path(treeiter)
            self.treeview.expand_row(path, False)
        self.selection.select_iter(child_iter)
    
    def on_tb_remove_clicked(self, widget):
        model, treeiter = self.selection.get_selected()
        if treeiter != None:
            node = self.model.get_node(treeiter)
            index = node.parent.get_child_pos(node)
            if index == 0:
                previous = node.parent
            else:
                previous = node.parent.get_nth_child(index-1)
            if previous:
                piter = self.model.get_node_iter(previous)
                self.selection.select_iter(piter)
            else:
                self.selection.unselect_all()
            self.model.remove(node)
    
    def on_tvs_selection_data_changed(self, widget):
        model, treeiter = widget.get_selected()
        if treeiter != None:
            node = self.model.get_node(treeiter)
            data = self.model._get_col_data(node)
            self.editor.set_text(data)
        else:
            self.editor.set_text("")
    
    def on_ent_formula_changed(self, widget):
        model, treeiter = self.selection.get_selected()
        if treeiter != None:
            try:
                value = int(self.editor.get_text(), base=16)
            except ValueError:
                pass
            else:
                node = self.model.get_node(treeiter)
                node.data = value
    
    def on_tvcr_data_comment_edited(self, widget, path, new_text):
        treeiter = self.model.get_iter_from_string(path)
        if treeiter != None:
            node = self.model.get_node(treeiter)
            node.comment = new_text
    
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
