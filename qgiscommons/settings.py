from utils import _callerName, _callerPath
from PyQt4.QtCore import *
import os
import json
from collections import defaultdict
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import iface

#Types to use in the settings.json file

BOOL = "bool"
STRING = "string"
TEXT = "text" # a multile string
NUMBER = "number"
FILE = "file"
FOLDER = "folder"
CHOICE  ="choice"
CRS = "crs"

def setPluginSetting(name, value, namespace = None):
    '''
    Sets the value of a plugin setting.

    :param name: the name of the setting. It is not the full path, but just the last name of it
    :param value: the value to set for the plugin setting 
    :param namespace: The namespace. If not passed or None, the namespace will be inferred from 
    the caller method. Normally, this should not be passed, since it suffices to let this function 
    find out the plugin from where it is being called, and it will automatically use the 
    corresponding plugin namespace
    '''
    namespace = namespace or _callerName().split(".")[0]
    QSettings().setValue(namespace + "/" + name, value)

def pluginSetting(name, namespace = None):
    '''
    Returns the value of a plugin setting.
    
    :param name: the name of the setting. It is not the full path, but just the last name of it
    :param namespace: The namespace. If not passed or None, the namespace will be inferred from 
    the caller method. Normally, this should not be passed, since it suffices to let this function 
    find out the plugin from where it is being called, and it will automatically use the 
    corresponding plugin namespace
    '''    
    namespace = namespace or _callerName().split(".")[0]
    full_name = namespace + "/" + name
    if QSettings().contains(full_name):
        v = QSettings().value(full_name, None)
        if isinstance(v, QPyNullVariant):
            v = None
        return v
    else:        
        for setting in _settings[namespace]:
            if setting["name"] == name:
                return setting["default"]        
        return None

_settings = {}

def readSettings():
    '''
    Reads the settings corresponding to the plugin from where the method is called.
    This function has to be called in the __init__ method of the plugin class.
    Settings are stored in a settings.json file in the plugin folder.
    Here is an eample of such a file:

    [
    {"name":"mysetting",
     "label": "My setting",
     "description": "A setting to customize my plugin",
     "type": "string",
     "default": "dummy string",
     "group": "Group 1"
    },
    {"name":"anothersetting",
      "label": "Another setting",
     "description": "Another setting to customize my plugin",
     "type": "number",
     "default": 0,
     "group": "Group 2"
    },
    {"name":"achoicesetting",
     "label": "A choice setting",
     "description": "A setting to select from a set of possible options",
     "type": "choice",
     "default": "option 1",
     "options":["option 1", "option 2", "option 3"],
     "group": "Group 2"
    }
    ]

    Available types for settings are: string, bool, number, choice, crs and text (a multiline string)
    '''

    namespace = _callerName().split(".")[0]
    path = os.path.join(os.path.dirname(_callerPath()), "settings.json")
    with open(path) as f:
        _settings[namespace] = json.load(f)

_settingActions = {}
def addSettingsMenu(menuName, parentMenuFunction = None):
    '''
    Adds a 'open settings...' menu to the plugin menu.
    This method should be called from the initGui() method of the plugin

    :param menuName: The name of the plugin menu in which the settings menu is to be added
    :param parentMenuFunction: a function from QgisInterface to indicate where to put the container plugin menu.
    If not passed, it uses addPluginToMenu
    '''

    parentMenuFunction = parentMenuFunction or iface.addPluginToMenu
    namespace = _callerName().split(".")[0]
    settingsIcon = QgsApplication.getThemeIcon('/mActionHelpAPI.png')
    settingsAction = QAction(settingsIcon, "Settings...", iface.mainWindow())
    settingsAction.setObjectName(namespace + "settings")
    settingsAction.triggered.connect(lambda: openSettingsDialog(namespace))
    parentMenuFunction(menuName, settingsAction)
    global _settingActions
    _settingActions[menuName] = settingsAction


def removeSettingsMenu(menuName):
    iface.removePluginWebMenu(menuName, _settingActions[menuName])

def openSettingsDialog(namespace):
    '''
    Opens the settings dialog for the passed namespace.
    Instead of calling this function directly, consider using addSettingsMenu()
    '''    
    dlg = ConfigDialog(namespace)
    dlg.exec_()

#########################################

class ConfigDialog(QDialog):

    def __init__(self, namespace):
        self.settings = _settings[namespace]
        self.namespace = namespace
        QDialog.__init__(self)
        self.setupUi()
        if hasattr(self.searchBox, 'setPlaceholderText'):
            self.searchBox.setPlaceholderText(self.tr("Search..."))
        self.searchBox.textChanged.connect(self.filterTree)
        self.fillTree()
        self.tree.expandAll()

    def setupUi(self):
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.resize(640, 450)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setMargin(0)
        self.searchBox = QgsFilterLineEdit(self)
        self.verticalLayout.addWidget(self.searchBox)
        self.tree = QTreeWidget(self)
        self.tree.setAlternatingRowColors(True)
        self.verticalLayout.addWidget(self.tree)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.verticalLayout.addWidget(self.buttonBox)

        self.setWindowTitle("Configuration options")
        self.searchBox.setToolTip("Enter setting name to filter list")
        self.tree.headerItem().setText(0, "Setting")
        self.tree.headerItem().setText(1, "Value")

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)


    def filterTree(self):
        text = unicode(self.searchBox.text())
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            visible = False
            for j in range(item.childCount()):
                subitem = item.child(j)
                itemText = subitem.text(0)
            if (text.strip() == ""):
                subitem.setHidden(False)
                visible = True
            else:
                hidden = text not in itemText
                item.setHidden(hidden)
                visible = visible or not hidden
            item.setHidden(not visible)
            item.setExpanded(visible and text.strip() != "")

    def fillTree(self):
        self.items = {}
        self.tree.clear()

        grouped = defaultdict(list)
        for setting in self.settings:
            grouped[setting["group"]].append(setting)
        for groupName, group in grouped.iteritems():
            item = self._getGroupItem(groupName, group)
            self.tree.addTopLevelItem(item)

        self.tree.setColumnWidth(0, 400)


    def _getGroupItem(self, groupName, params):
        print params
        item = QTreeWidgetItem()
        item.setText(0, groupName)
        icon = QIcon(os.path.join(os.path.dirname(__file__), "setting.png"))
        item.setIcon(0, icon)
        for param in params:
            value = pluginSetting(param["name"], self.namespace)
            subItem = TreeSettingItem(item, self.tree, param, self.namespace, value)
            item.addChild(subItem)
        return item


    def accept(self):
        iterator = QTreeWidgetItemIterator(self.tree)
        value = iterator.value()
        while value:
            if hasattr(value, 'saveValue'):
                try:
                    value.saveValue()
                except WrongValueException:
                    return
            iterator += 1            
            value = iterator.value()

        QDialog.accept(self)


class WrongValueException(Exception):
    pass

class TreeSettingItem(QTreeWidgetItem):

    comboStyle = '''QComboBox {
                 border: 1px solid gray;
                 border-radius: 3px;
                 padding: 1px 18px 1px 3px;
                 min-width: 6em;
             }

             QComboBox::drop-down {
                 subcontrol-origin: padding;
                 subcontrol-position: top right;
                 width: 15px;
                 border-left-width: 1px;
                 border-left-color: darkgray;
                 border-left-style: solid;
                 border-top-right-radius: 3px;
                 border-bottom-right-radius: 3px;
             }
            '''

    def _addTextBoxWithLink(self, text, func, editable):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.lineEdit = QLineEdit()
        self.lineEdit.setText(self._value)
        self.linkLabel = QLabel()
        self.linkLabel.setText("<a href='#'> %s</a>" % text)
        self.crsLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.lineEdit)
        layout.addWidget(self.linkLabel)
        self.newValue = value
        self.linkLabel.connect(self.label, SIGNAL("linkActivated(QString)"), func)
        w = QWidget()
        w.setLayout(layout)
        self.tree.setItemWidget(self, 1, w)

    def __init__(self, parent, tree, setting, namespace, value):
        QTreeWidgetItem.__init__(self, parent)
        self.parent = parent
        self.namespace = namespace
        self.tree = tree
        self._value = value
        self.name = setting["name"]
        self.labelText = setting["label"]
        self.settingType = setting["type"]
        self.setText(0, self.labelText)
        if self.settingType == CRS:
            def edit():
                selector = QgsGenericProjectionSelector()
                selector.setSelectedAuthId(value)
                if selector.exec_():
                    authId = selector.selectedAuthId()
                    if authId.upper().startswith("EPSG:"):
                        self.newValue = authId
                        self.lineEdit.setText(authId)
            self._addTextBoxWithLink("Edit", edit, False)
        elif self.settingType == FILE:
            def edit():
                f = QFileDialog.getOpenFileNames(None, "Select file", "", "*.*")
                if f:
                    self.newValue = f
                    self.lineEdit.setText(f)
            self._addTextBoxWithLink("Browse", edit, True)
        elif self.settingType == FOLDER:
            def edit():
                f = QFileDialog.getExistingDirectory(parent, "Select folder", "")
                if f:
                    self.newValue = f
                    self.lineEdit.setText(f)
            self._addTextBoxWithLink("Browse", edit, True)
        elif self.settingType == BOOL:
            if value:
                self.setCheckState(1, Qt.Checked)
            else:
                self.setCheckState(1, Qt.Unchecked)
        elif self.settingType == CHOICE:
            self.combo = QComboBox()
            self.combo.setStyleSheet(self.comboStyle)
            for option in setting["options"]:
                self.combo.addItem(option)
            self.tree.setItemWidget(self, 1, self.combo)
            idx = self.combo.findText(str(value))
            self.combo.setCurrentIndex(idx)
        elif self.settingType == TEXT:
            self.label = QLabel()
            self.label.setText("<a href='#'>Edit</a>")
            self.newValue = value
            def edit():
                dlg = TextEditorDialog(unicode(self.newValue))
                dlg.exec_()
                self.newValue = dlg.text
            self.label.connect(self.label, SIGNAL("linkActivated(QString)"), edit)
            self.tree.setItemWidget(self, 1, self.label)
        else:
            self.setFlags(self.flags() | Qt.ItemIsEditable)
            self.setText(1, unicode(value))


    def saveValue(self):
        value = self.value()
        setPluginSetting(self.name, value, self.namespace)

    def value(self):
        self.setBackgroundColor(0, Qt.white)
        self.setBackgroundColor(1, Qt.white)
        try:
            if self.settingType == BOOL:
                return self.checkState(1) == Qt.Checked
            elif self.settingType == NUMBER:
                v = float(self.text(1))
                return 
            elif self.settingType == CHOICE:
                return self.combo.currentText()
            elif self.settingType in [TEXT, CRS, FILE, FOLDER]:
                return self.newValue
            else:
                return self.text(1)
        except:
            self.setBackgroundColor(0, Qt.yellow)
            self.setBackgroundColor(1, Qt.yellow)
            raise WrongValueException()

    def setValue(self, value):
        if self.settingType == BOOL:
            if value:
                self.setCheckState(1, Qt.Checked)
            else:
                self.setCheckState(1, Qt.Unchecked)
        elif self.settingType == CHOICE:
            idx = self.combo.findText(str(value))
            self.combo.setCurrentIndex(idx)
        elif self.settingType == TEXT:
            self.newValue = value
        elif self.settingType in [CRS, FILE, FOLDER]:
            self.newValue = value
            self.lineEdit.setText(value)
        else:
            self.setText(1, unicode(value))

class TextEditorDialog(QDialog):

    def __init__(self, text):
        super(TextEditorDialog, self).__init__()

        self.text = text

        self.resize(600, 350)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowSystemMenuHint |
                                                QtCore.Qt.WindowMinMaxButtonsHint)
        self.setWindowTitle("Editor")

        layout = QVBoxLayout()
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.editor = QTextEdit()
        self.editor.setPlainText(text)
        layout.addWidget(self.editor)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        buttonBox.accepted.connect(self.okPressed)
        buttonBox.rejected.connect(self.cancelPressed)

    def okPressed(self):
        self.text = self.editor.toPlainText()
        self.close()

    def cancelPressed(self):
        self.close()
