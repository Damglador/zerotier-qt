#!/usr/bin/env python

# A Qt front-end for ZeroTier
# Copyright (C) 2023 Tomás Ralph
# Copyright (C) 2026 Vsevolod «Damglador» Stopchanskyi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################
#                                 #
#  Originally created by tralph3  #
#   https://github.com/tralph3    #
#                                 #
#  Qt port by Damglador           #
#   https://github.com/Damglador  #
#                                 #
###################################

from PySide6.QtCore import (
  QStandardPaths, QTimer, Qt,
)
from PySide6.QtGui import (
  QAction, QBrush, QColor, QDesktopServices,
  QIcon, QKeySequence
)
from PySide6.QtWidgets import (
  QApplication, QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
  QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
  QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget
)

import os
import sys
import json
import signal
import shutil
import textwrap
import subprocess as proc
from subprocess import check_call, check_output, STDOUT, CalledProcessError

APP_ID = "zerotier-qt"
APP_NAME = "ZeroTier-Qt"
APP_VERSION = "0.9"

HOME_DIR = str(QStandardPaths.standardLocations(QStandardPaths.StandardLocation.HomeLocation)[0])
CONFIG_DIR = os.path.join(
  str(QStandardPaths.standardLocations(QStandardPaths.StandardLocation.GenericConfigLocation)[0]),
  APP_ID
)
AUTH_FILE = os.path.join(CONFIG_DIR, "authtoken.secret")
authtoken = None

# ============ CONTROLLER ==================
def get_token() -> str:
  global authtoken
  if authtoken is not None:
    return authtoken
  if os.getuid() == 0:
    authtoken = open("/var/lib/zerotier-one/authtoken.secret").read().strip()
    return authtoken
  else:
    if os.path.isfile(".zeroTierOneAuthToken"):
      authtoken = open(os.path.join(HOME_DIR, ".zeroTierOneAuthToken")).read().strip()
      return authtoken
    authtoken = open(AUTH_FILE).read().strip()
    return authtoken

def get_status():
  status = check_output(["zerotier-cli", f"-T{get_token()}", "status"]).decode()
  status = status.split()
  return status

def manage_service(action: str):
  try:
    check_output(["systemctl", action, "zerotier-one"])
  except CalledProcessError as error:
    QMessageBox.warning(
      None,
      "Error",
      f'Something went wrong: "{error}"'
    )

def change_config(network_id: str, config: str, value):
  # zerotier-cli only accepts int values
  value = int(value)
  try:
    check_output(
      ["zerotier-cli", f"-T{get_token()}", "set", network_id, f"{config}={value}",],
      stderr=STDOUT,
    )
  except CalledProcessError as error:
    error = error.output.decode().strip()
    QMessageBox.warning(
      None,
      "Failed to change config",
      f'Error: "{error}"'
    )

def is_on_network(network_id):
  currently_joined = False
  for network in get_networks_info():
    if currently_joined:
      break
    currently_joined = network["nwid"] == network_id
  return currently_joined

def join_network(network_id):
  try:
    if is_on_network(network_id):
      QMessageBox.information(
        None,
        QApplication.applicationDisplayName(),
        "You are already a member of this network.",
      )
      return False
    check_call(["zerotier-cli", f"-T{get_token()}", "join", network_id])
    return True
  except CalledProcessError:
    QMessageBox.warning(
      None,
      QApplication.applicationDisplayName(),
      "Invalid network ID",
    )
    return False

def get_network_name_by_id(network_id):
  networks = get_networks_info()
  for network in networks:
    if network_id == network["nwid"]:
      return network["name"]

# TODO: describe data structure
def get_networks_info():
  return json.loads(check_output(["zerotier-cli", f"-T{get_token()}", "-j", "listnetworks"]))

def get_peers_info():
  return json.loads(check_output(["zerotier-cli", f"-T{get_token()}", "-j", "peers"]))

def get_interface_state(interface):
  interfaceInfo = json.loads(check_output(["ip", "--json", "address"]).decode())
  for info in interfaceInfo:
    if info["ifname"] == interface:
      state = info["operstate"]
      break
  return state # pyright: ignore

def leave_network(networkId, networkName=None):
  answer = QMessageBox.question(
    None,
    "Leave Network",
    f"Are you sure you want to "
    f'leave "{networkName}"\n(ID: {networkId})?',
  )
  if answer == QMessageBox.StandardButton.Yes:
    try:
      check_call(["zerotier-cli", f"-T{get_token()}", "leave", networkId])
      return True
    except CalledProcessError:
      QMessageBox.warning(
        None,
        QApplication.applicationDisplayName(),
        "Failed to leave network.",
      )
      return False
  else:
    return False

def toggle_interface(interfaceName):
  state = get_interface_state(interfaceName)

  if state.lower() == "down":
    try:
      check_call(
        ["pkexec", "ip", "link", "set", interfaceName, "up"]
      )
      return True
    except CalledProcessError:
      return False
  else:
    try:
      check_call(
        ["pkexec", "ip", "link", "set", interfaceName, "down"]
      )
      return True
    except CalledProcessError:
      return False

def get_service_status():
  data = check_output(
    ["systemctl", "show", "zerotier-one", "--property=ActiveState,UnitFileState"], universal_newlines=True
  ).split("\n")
  formatted_data = {}
  for entry in data:
    key_value = entry.split("=", 1)
    if len(key_value) == 2:
      formatted_data[key_value[0]] = key_value[1]

  return formatted_data

def setup_auth_token():
  if not os.path.isfile("/var/lib/zerotier-one/authtoken.secret"):
    allowed_to_start_service = QMessageBox.question(
      None,
      "No authtoken found",
      textwrap.dedent(
        """\
        No authtoken.secret file has been found in
        "/var/lib/zerotier-one". This usually means you
        never started the zerotier-one service.
        Do you wish to start it now?
        """
      )
    )
    if allowed_to_start_service == QMessageBox.StandardButton.Yes:
      manage_service("start")
    else:
      os._exit(0)
  if os.getuid() == 0:
    return
  if not os.path.isfile(AUTH_FILE):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    answer = QMessageBox.question(
      None,
      "Missing Local Authtoken",
      textwrap.dedent(f"""\
        This user doesn't have ZeroTier-One Authtoken file.
        Choosing «Yes» will ask you for password to
        copy the authtoken.secret from
        /var/lib/zerotier-one/
        to
        {CONFIG_DIR}

        «No» will exit the program.
        """),
    )
    if answer == QMessageBox.StandardButton.Yes:
      try:
        check_output([
          "pkexec", "bash", "-c",
          f"""
          cp /var/lib/zerotier-one/authtoken.secret {AUTH_FILE} &&
          chown {os.getuid()}:{os.getgid()} {AUTH_FILE}""",
        ], stderr=STDOUT)
      except CalledProcessError as error:
        if error.returncode == 127:
          os._exit(1)
        QMessageBox.critical(
          None,
          "Operation Failed",
          "Failed to copy authtoken.secret.\n\n"
          f"Command Output:\n {error.output.decode().strip()}")
        os._exit(1)
    else:
      os._exit(1)

# ============ DIALOGS =====================
def about_window():
  QMessageBox.about(
      None,
      "About",
      f"""
      <b>ZeroTier Version {get_status()[3]}<br>
      {QApplication.applicationDisplayName()} Version {QApplication.applicationVersion()}</b><br>
      Qt front-end for ZeroTier One<br>
      Created by Vsevolod «Damglador» Stopchanskyi<br>
      Based on zerotier-gui by Tomás Ralph<br>
      Licensed under GPL-3.0<br>
      <a href="https://github.com/Damglador/zerotier-qt">
          https://github.com/Damglador/zerotier-qt
      </a>
      """
  )

def networkinfo(networkIndex: int, parent: QWidget=None): # pyright: ignore[reportArgumentType]
  dlg = QDialog(parent)
  dlg.setWindowTitle("Network Info")
  layout = QFormLayout(dlg)
  currentNetworkInfo = get_networks_info()[networkIndex]

  allowDefault  = QCheckBox(dlg)
  allowGlobal   = QCheckBox(dlg)
  allowManaged  = QCheckBox(dlg)
  allowDNS      = QCheckBox(dlg)

  allowDefault.setChecked(currentNetworkInfo["allowDefault"])
  allowGlobal.setChecked(currentNetworkInfo["allowGlobal"])
  allowManaged.setChecked(currentNetworkInfo["allowManaged"])
  allowDNS.setChecked(currentNetworkInfo["allowDNS"])

  allowDefault.stateChanged.connect(
    lambda state: change_config(currentNetworkInfo["id"], "allowDefault", allowDefault.isChecked()))
  allowGlobal.stateChanged.connect(
    lambda state: change_config(currentNetworkInfo["id"], "allowGlobal", allowGlobal.isChecked()))
  allowManaged.stateChanged.connect(
    lambda state: change_config(currentNetworkInfo["id"], "allowManaged", allowManaged.isChecked()))
  allowDNS.stateChanged.connect(
    lambda state: change_config(currentNetworkInfo["id"], "allowDNS", allowDNS.isChecked()))

  layout.addRow(QLabel("Name:"), QLabel(currentNetworkInfo["name"]))
  layout.addRow(QLabel("Network ID:"), QLabel(currentNetworkInfo["id"]))
  try:
    # first widget
    layout.addRow(QLabel("Assigned Addresses:"), QLabel(currentNetworkInfo["assignedAddresses"][0]))

    # subsequent widgets
    for address in currentNetworkInfo["assignedAddresses"][1:]:
      layout.addRow("", QLabel(address))
  except IndexError:
    layout.addRow(QLabel("Assigned Addresses:"), QLabel("-"))
  layout.addRow(QLabel("Status:"), QLabel(currentNetworkInfo["status"]))
  layout.addRow(QLabel("State:"), QLabel(get_interface_state(currentNetworkInfo["portDeviceName"])))
  layout.addRow(QLabel("Type:"), QLabel(currentNetworkInfo["type"]))
  layout.addRow(QLabel("Device:"), QLabel(currentNetworkInfo["portDeviceName"]))
  layout.addRow(QLabel("Bridge:"), QLabel("True" if currentNetworkInfo["bridge"] else "False"))
  layout.addRow(QLabel("MAC Address:"), QLabel(currentNetworkInfo["mac"]))
  layout.addRow(QLabel("MTU:"), QLabel(str(currentNetworkInfo["mtu"])))
  layout.addRow(QLabel("DHCP:"), QLabel("True" if currentNetworkInfo["dhcp"] else "False"))
  layout.addRow(QLabel("Default Route:"), allowDefault)
  layout.addRow(QLabel("Global IP:"), allowGlobal)
  layout.addRow(QLabel("Managed IP:"), allowManaged)
  layout.addRow(QLabel("DNS Configuration:"), allowDNS)
  for label in dlg.findChildren(QLabel):
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    # label.setStyleSheet("font-size: 16px")

  dlg.setLayout(layout)
  dlg.adjustSize() # otherwise dialog will be a big square when resize is applied
  dlg.resize(int(dlg.width() * 1.1), dlg.height())
  closeBtn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
  closeBtn.clicked.connect(dlg.close)
  layout.addWidget(closeBtn)
  dlg.exec()

class PeersList(QDialog):
  def __init__(self, parent: QWidget = None): # pyright: ignore
    super().__init__(parent)
    self.setWindowTitle("Peers Info")
    columns = ["ZT Address", "Version", "Role", "Latency"]
    self.table = Table(self, columns)

    self.resize(500, 300)

    self.buttonBox = QDialogButtonBox()
    self.refreshBtn = self.buttonBox.addButton("Refresh", QDialogButtonBox.ButtonRole.ActionRole)
    self.refreshBtn.setIcon(QIcon.fromTheme("view-refresh"))
    self.refreshBtn.clicked.connect(self.refresh)
    self.pathsBtn = self.buttonBox.addButton("Show Paths", QDialogButtonBox.ButtonRole.ActionRole)
    self.pathsBtn.setToolTip("Show paths for the selected peer")
    self.pathsBtn.setIcon(QIcon.fromTheme("show-all-effects"))
    self.pathsBtn.clicked.connect(self.peerpaths)
    self.closeBtn = self.buttonBox.addButton(QDialogButtonBox.StandardButton.Close)
    self.closeBtn.clicked.connect(self.close)
    layout = QVBoxLayout(self)
    layout.addWidget(self.table)
    layout.addWidget(self.buttonBox)
    self.setLayout(layout)
    self.refresh()
    self.setMinimumWidth(     int(self.table.header().length() + 100)      )
    self.setMinimumHeight(min(int(self.table.header().height() + 100), 300))
  def refresh(self):
    # outputs info of peers in json format
    peersData = get_peers_info()
    # get peers information in a list of tuples
    peers = []
    for peerPosition in range(len(peersData)):
      peers.append(
        (
          str(peersData[peerPosition]["address"]),
          str(peersData[peerPosition]["version"]).replace("-1.-1.-1", "-"),
          str(peersData[peerPosition]["role"]),
          str(peersData[peerPosition]["latency"]),
        )
      )
    self.table.populate(peers)
  def peerpaths(self):
    peerpaths = PeerPaths(peerIndex=self.table.indexOfTopLevelItem(self.table.currentItem()), parent=self)
    peerpaths.show()

class PeerPaths(QDialog):
  def __init__(self, peerIndex, parent: QWidget = None): # pyright: ignore
    super().__init__(parent)
    self.peerIndex = peerIndex
    self.setWindowTitle("Peer Paths")
    columns = [
      "Address",
      "Active",
      "Expired",
      "Last Receive",
      "Last Send",
      "Preferred",
      "Trusted Path ID"
    ]
    self.table = Table(self, columns)
    self.label = QLabel()
    self.label.setStyleSheet("font-size: 14px; font-weight: bold;")
    self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    self.buttonBox = QDialogButtonBox()
    self.refreshBtn = self.buttonBox.addButton("Refresh", QDialogButtonBox.ButtonRole.ActionRole)
    self.refreshBtn.setIcon(QIcon.fromTheme("view-refresh"))
    self.refreshBtn.clicked.connect(self.refresh)
    self.closeBtn = self.buttonBox.addButton(QDialogButtonBox.StandardButton.Close)
    self.closeBtn.clicked.connect(self.close)
    layout = QVBoxLayout(self)
    layout.addWidget(self.label)
    layout.addWidget(self.table)
    layout.addWidget(self.buttonBox)
    self.setLayout(layout)
    self.refresh()
    self.setMinimumWidth(     int(self.table.header().length() + 100)      )
    self.setMinimumHeight(min(int(self.table.header().height() + 100), 300))
  def refresh(self):
    # get peers information in a list of tuples
    paths = []
    # outputs info of paths in json format
    pathsData = get_peers_info()[self.peerIndex]["paths"]
    label = f"Paths for peer {get_peers_info()[self.peerIndex]["address"]}"
    self.label.setText(label)
    self.setWindowTitle(label)

    # get paths information in a list of tuples
    for pathPosition in range(len(pathsData)):
      paths.append(
        (
          str(pathsData[pathPosition]["address"]),
          str(pathsData[pathPosition]["active"]),
          str(pathsData[pathPosition]["expired"]),
          str(pathsData[pathPosition]["lastReceive"]),
          str(pathsData[pathPosition]["lastSend"]),
          str(pathsData[pathPosition]["preferred"]),
          str(pathsData[pathPosition]["trustedPathId"]),
        )
      )
    self.table.populate(paths)

class Table(QTreeWidget):
  def __init__(self, parent, columns: list):
    super().__init__(parent)
    self.columns = columns
    self.setColumnCount(len(columns))
    self.setHeaderLabels(columns)

    self.setRootIsDecorated(False) # hide the tree-indicating lines
    self.setStyleSheet("font-size: 16px")
    # Resize columns to content size
    for i in range(len(columns)):
      self.resizeColumnToContents(i)

    # Implement copying
    # self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
    copy_action = QAction(
      text="Copy",
      icon=QIcon.fromTheme("edit-copy"),
      shortcut=QKeySequence(QKeySequence.StandardKey.Copy),
      parent=self
    )
    copy_action.triggered.connect(lambda: QApplication.clipboard().setText(
        self.currentItem().text(self.currentColumn())
    ))
    self.addAction(copy_action)
    self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

  def populate(self, content: list[list[str]]):
    self.clear()
    for row in range(len(content)):
      self.insertTopLevelItem(row, QTreeWidgetItem(content[row]))
    for i in range(self.columnCount()):
      self.resizeColumnToContents(i)

class MainWindow(QMainWindow):
  def __init__(self):
    super().__init__()
    mainLayout = QVBoxLayout()
    centralWidget = QWidget()
    centralWidget.setLayout(mainLayout)
    self.setCentralWidget(centralWidget)

    topSubLayout = QHBoxLayout()
    mainLayout.addLayout(topSubLayout)

    joinLbl = QLabel("Join a Network:")
    topSubLayout.addWidget(joinLbl)
    self.joinTextBox = QLineEdit(placeholderText="Network ID", clearButtonEnabled=True)
    self.joinTextBox.returnPressed.connect(self.call_join_network)
    topSubLayout.addWidget(self.joinTextBox)
    joinBtn = QPushButton()
    joinBtn.setIcon(QIcon.fromTheme("dialog-ok"))
    joinBtn.setToolTip("Join")
    joinBtn.clicked.connect(self.call_join_network)
    topSubLayout.addWidget(joinBtn)

    tableColumns = ["ID", "Name", "Status", "Interface"]
    self.networksTable = Table(centralWidget, tableColumns)
    mainLayout.addWidget(self.networksTable)

    # self.setMinimumWidth(     int(self.networksTable.header().length() + 100)      )
    # self.setMinimumHeight(min(int(self.networksTable.header().height() + 100), 300))

    bottomSubLayout = QHBoxLayout()
    mainLayout.addLayout(bottomSubLayout)

    peersBtn = QPushButton("Show Peers")
    peersBtn.setIcon(QIcon.fromTheme("show-all-effects"))
    peersBtn.clicked.connect(self.call_peerslist)
    topSubLayout.addWidget(peersBtn)

    refreshBtn = QPushButton("Refresh")
    refreshBtn.setIcon(QIcon.fromTheme("view-refresh"))
    refreshBtn.setToolTip("Refresh networks list")
    refreshBtn.clicked.connect(self.refresh_networks)
    topSubLayout.addWidget(refreshBtn)

    aboutBtn = QPushButton("About")
    aboutBtn.setIcon(QIcon.fromTheme("help-about"))
    aboutBtn.clicked.connect(about_window)
    topSubLayout.addWidget(aboutBtn)

    leaveAction = QAction(
      text="Leave Network",
      icon=QIcon.fromTheme("application-exit-symbolic"),
      parent=self.networksTable)
    leaveAction.triggered.connect(self.call_leave_network)
    self.networksTable.addAction(leaveAction)

    toggleAction = QAction(
      # I would like to make text and icon dynamic, but Idk how
      text="Toggle Interface",
      icon=QIcon.fromTheme("adjustlevels"), # media-playlist-shuffle
      parent=self.networksTable
    )
    toggleAction.triggered.connect(self.call_toggle_interface)
    self.networksTable.addAction(toggleAction)

    infoAction = QAction(
      text="Info",
      icon=QIcon.fromTheme("help-info"),
      parent=self.networksTable
    )
    infoAction.triggered.connect(lambda: self.call_networkinfo())
    self.networksTable.addAction(infoAction)

    # To enable/disable the service
    self.serviceCheckBox = QCheckBox()
    self.serviceCheckBox.clicked.connect(self.enable_disable_service)
    bottomSubLayout.addWidget(self.serviceCheckBox)
    serviceLabel = QLabel("ZeroTier Service")
    bottomSubLayout.addWidget(serviceLabel)
    # To start/stop the service
    self.serviceBtn = QPushButton()
    self.serviceBtn.clicked.connect(self.start_stop_service)
    bottomSubLayout.addWidget(self.serviceBtn)
    self.update_service_status()

    bottomSubLayout.addStretch()

    self.statusLabel = QLabel(textInteractionFlags=Qt.TextInteractionFlag.TextSelectableByMouse)
    bottomSubLayout.addWidget(self.statusLabel)

    # TODO: open https://central.zerotier.com/network/NETWORKID to go directly to network's page
    #       the issue is old central and new central have seperate networks,
    #       so it needs to know which belongs where
    oldcentralBtn = QPushButton("Old Central")
    oldcentralBtn.setIcon(QIcon.fromTheme("zerotier-central-old"))
    oldcentralBtn.setToolTip("Open ZeroTier Legacy Central in your browser")
    oldcentralBtn.clicked.connect(lambda: QDesktopServices.openUrl("https://my.zerotier.com"))
    bottomSubLayout.addWidget(oldcentralBtn)
    newcentralBtn = QPushButton("New Central")
    newcentralBtn.setIcon(QIcon.fromTheme("zerotier-central-new"))
    newcentralBtn.setToolTip("Open ZeroTier New Central in your browser")
    newcentralBtn.clicked.connect(lambda: QDesktopServices.openUrl("https://central.zerotier.com"))
    bottomSubLayout.addWidget(newcentralBtn)

    self.refresh_networks()

  def call_networkinfo(self):
    networkinfo(self.networksTable.indexOfTopLevelItem(self.networksTable.currentItem()))

  def start_stop_service(self):
    status = get_service_status()
    if status["ActiveState"] == "active":
      manage_service("stop")
    else:
      print("Starting service")
      manage_service("start")
    self.update_service_status()
    return
  def enable_disable_service(self):
    status = get_service_status()
    if status["UnitFileState"] == "enabled":
      print("Disabling service")
      manage_service("disable")
    else:
      print("Enabling service")
      manage_service("enable")
    self.update_service_status()
    return
  def update_service_status(self):
    status = get_service_status()
    # Set checkbox state
    if status["UnitFileState"] == "enabled":
      self.serviceCheckBox.setChecked(True)
      self.serviceCheckBox.setToolTip("Disable ZeroTier Service")
    else:
      self.serviceCheckBox.setChecked(False)
      self.serviceCheckBox.setToolTip("Enable ZeroTier Service")
    # Set button state
    if status["ActiveState"] == "active":
      self.serviceBtn.setIcon(QIcon.fromTheme("media-playback-pause"))
      self.serviceBtn.setToolTip("Stop ZeroTier Service")
    else:
      self.serviceBtn.setIcon(QIcon.fromTheme("media-playback-start"))
      self.serviceBtn.setToolTip("Start ZeroTier Service")
  def call_peerslist(self):
    peerslist = PeersList(self)
    peerslist.show()

  def call_toggle_interface(self):
    if toggle_interface(self.networksTable.currentItem().text(3)):
      self.refresh_networks()
  def call_leave_network(self):
    if leave_network(self.networksTable.currentItem().text(0), self.networksTable.currentItem().text(1)):
      self.refresh_networks()
  def call_join_network(self):
    # Refresh networks only if join was successful
    if join_network(self.joinTextBox.text()):
      self.refresh_networks()
      self.joinTextBox.clear()
      QTimer.singleShot(1000, self.refresh_networks)
      QTimer.singleShot(5000, self.refresh_networks)

  def refresh_networks(self):
    status = get_status()
    self.statusLabel.setText(f"Your ID: {status[2]} Status: {status[4]}")

    self.networksTable.clear()
    networks = []
    # outputs info of networks in json format
    networkData = get_networks_info()

    # gets networks information in a list of tuples
    for networkPosition in range(len(networkData)):
      interfaceState = get_interface_state(
        networkData[networkPosition]["portDeviceName"]
      )
      isDown: bool = interfaceState.lower() == "down"
      networks.append(
        (
          str(networkData[networkPosition]["id"]),
          str(networkData[networkPosition]["name"] if networkData[networkPosition]["name"] else "Unknown Name"),
          str(networkData[networkPosition]["status"]),
          str(networkData[networkPosition]["portDeviceName"]),
          isDown,
        )
      )
    # Custom implementation of populate() to get rows disabled
    for row in range(len(networks)):
      # [:-1] prevents type errors from the last bool by not including it
      self.networksTable.insertTopLevelItem(row, QTreeWidgetItem(networks[row][:-1]))
      if networks[row][-1]:
        for column in range(self.networksTable.columnCount()):
          self.networksTable.topLevelItem(row).setForeground(column, QBrush(QColor("gray")))  # pyright: ignore[reportOptionalMemberAccess]
    for i in range(self.networksTable.columnCount()):
      self.networksTable.resizeColumnToContents(i)

if __name__ == "__main__":
  app = QApplication()
  app.setApplicationName(APP_ID)
  app.setDesktopFileName(APP_ID)
  app.setApplicationDisplayName(APP_NAME)
  app.setApplicationVersion(APP_VERSION)

  QApplication.setWindowIcon(QIcon.fromTheme(QApplication.applicationName()))

  # Check if zerotier-one is installed
  if shutil.which("zerotier-cli") is None:
    QMessageBox.critical(
      None,
      "No zerotier-cli",
      "zerotier-cli is not installed or is not in PATH.\n"
      f"Ensure that it's available before running {APP_NAME}.",
    )
    os._exit(127)
  # Check if service is running
  if not get_service_status()["ActiveState"] == "active":
    answer = QMessageBox.question(
      None,
      "Start Service",
      "The 'zerotier-one' service isn't running.\n\n"
      "Do you wish to start it now?",
    )
    if answer == QMessageBox.StandardButton.Yes:
      manage_service("start")
    else:
      os._exit(1)

  # Ensure token is available
  setup_auth_token()

  try:
    check_output(["zerotier-cli", f"-T{get_token()}", "listnetworks"], stderr=STDOUT)
  # in case the command throws an error
  except CalledProcessError as error:
    # Can't connect to the service
    if error.returncode == 1:
      QMessageBox.critical(
        None,
        "Error",
        "The service is active, but zerotier-cli can't connect to it.\n\n"
        f"Command Output:\n {error.output.decode().strip()}",
      )
    QMessageBox.critical(
      None,
      "Error",
      "zerotier-cli exited with an unknown error.\n\n"
      f"Command Output:\n {error.output.decode().strip()}",
    )
    os._exit(1)
  signal.signal(signal.SIGINT, signal.SIG_DFL)
  mainwindow = MainWindow()
  mainwindow.show()
  sys.exit(app.exec())
