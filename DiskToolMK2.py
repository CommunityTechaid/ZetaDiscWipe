#!/usr/bin/python3
# Usage:
#   DiskToolMK2.py
#
# Options:
#   None at the moment
#
# Description:
#   A python GUI to help volunteers wipe discs on zeta
#
# Caveats:
#   - Relies on physical hardware in zeta
#
# TODO:
#   - Everything
#
# Author:
#   tom.cronin@communitytechaid.org.uk
#
##################################################

from dataclasses import dataclass, MISSING
from datetime import datetime
import subprocess
import re
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout,
                             QHBoxLayout, QLabel, QGridLayout, QGroupBox,
                             QLineEdit, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt


@dataclass
class Disk:
    position: str = None
    bay_port_number: int = None
    dev_path: str = "/path/to/dev"
    size: int = None
    make: str = "Make"
    model: str = "Model"
    serial: str = "Serial"
    health: str = "Unknown"
    cta_id: int = None
    wipe_status: str = "Unknown"
    cert_path: str = None

    def reset(self):
        # Function to reset values to defaults set above
        for name, field in self.__dataclass_fields__.items():
            # Skip resetting positiona and bay info as this won't change
            # after initialization
            if name not in {"position", "bay_port_number"}:
                if field.default != MISSING:
                    setattr(self, name, field.default)
                else:
                    setattr(self, name, field.default_factory())


class DiskWidgetGroup(QWidget):
    def __init__(self, disk_object):
        QWidget.__init__(self)

        self.do = disk_object
        self.make = QLabel(self.do.make)
        self.model = QLabel(self.do.model)
        self.size = QLabel(self.do.size)
        self.health = QLabel(self.do.health)
        self.wipe_status = QLabel(self.do.wipe_status)
        self.serial = QLabel(self.do.serial)

        self.check_health_button = QPushButton("Check")
        self.check_health_button.clicked.connect(self.health_check)

        self.start_wipe_button = QPushButton("Wipe")
        self.start_wipe_button.clicked.connect(self.start_wipe)

        self.cta_id_input = QLineEdit(self.do.cta_id)
        self.cta_id_input.returnPressed.connect(self.start_wipe_button.click)

        layout = QGridLayout()
        self.setLayout(layout)
        groupbox = QGroupBox(self.do.position)
        inner = QGridLayout()

        layout.addWidget(groupbox)

        inner.addWidget(QLabel("Make:"), 0, 0,)
        inner.addWidget(self.make, 0, 1, 1, 2)
        inner.addWidget(QLabel("Model:"), 1, 0)
        inner.addWidget(self.model, 1, 1)
        inner.addWidget(QLabel("Size:"), 2, 0)
        inner.addWidget(self.size, 2, 1)
        inner.addWidget(QLabel("Serial:"), 3, 0)
        inner.addWidget(self.serial, 3, 1)
        inner.addWidget(QLabel("Health:"), 4, 0)
        inner.addWidget(self.health, 4, 1)
        inner.addWidget(self.check_health_button, 4, 2)
        inner.addWidget(QLabel("Wipe status:"), 5, 0)
        inner.addWidget(self.wipe_status, 5, 1)
        inner.addWidget(QLabel("CTA ID:"), 6, 0)
        inner.addWidget(self.cta_id_input, 6, 1)
        inner.addWidget(self.start_wipe_button, 6, 2)
        groupbox.setLayout(inner)

    def health_check(self):
        self.check_health_button.setEnabled(False)
        time_to_wait = 0
        skdump_info = subprocess.run(['sudo', 'skdump', self.do.dev_path],
                                     text=True,
                                     capture_output=True)
        self_test_search = re.search('Short Self-Test Polling Time: ([0-9]+)',
                                     skdump_info.stdout)
        if self_test_search:
            short_test_time = self_test_search.group(1)
        else:
            short_test_time = 0

        if short_test_time > time_to_wait:
            time_to_wait = short_test_time

        self.health.setText("Testing")

        run_test = subprocess.run(['sudo',
                                   'sktest',
                                   self.do.dev_path,
                                   'short'],
                                  text=True,
                                  capture_output=True)

        test_outcome = "FAILED"

        if test_outcome == "PASSED":
            self.health.setText("Healthy")
            disk.health = "Healthy"
            self.health.setStyleSheet("background-color: lightgreen;\
                                            border: 1px solid black")
            self.update()
        elif test_outcome == "FAILED":
            self.health.setText("Unhealthy")
            disk.health = "Unhealthy"
            self.health.setStyleSheet("background-color: red;\
                                            border: 1px solid black")
            self.update()

    def start_wipe(self):
        self.start_wipe_button.setEnabled(False)
        inputNumber = self.cta_id_input.text()
        if inputNumber.isdigit():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setWindowTitle("CTA ID")
            msg.setText("You've entered "+str(inputNumber)+" as the ID.")
            msg.setInformativeText("Do you want to proceed and wipe this drive under this ID?")
            return_value = msg.exec_()

            if return_value == 16384:
                self.wipe_status.setText("Wiping")
                disk.wipe_status = "Wiping"
                self.update()
                # Spawn nwipe
                nwipe_outcome = "FAILED"

                if nwipe_outcome == "PASSED":
                    self.wipe_status.setText("WIPED")
                    disk.wipe_status = "Wiped"
                    self.wipe_status.setStyleSheet("background-color: lightgreen;\
                                                    border: 1px solid black")
                    self.update()
                elif nwipe_outcome == "FAILED":
                    self.wipe_status.setText("FAILED")
                    disk.wipe_status = "FAILED"
                    self.wipe_status.setStyleSheet("background-color: red;\
                                                    border: 1px solid black")
                    self.update()

            else:
                self.start_wipe_button.setEnabled(True)

        else:
            self.start_wipe_button.setEnabled(True)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setText(inputNumber+"is not a valid CTA ID")
            msg.setWindowTitle("CTA ID Warning")
            msg.exec_()

        # self.start_wipe_button.setText(self.cta_id_input.text())


def get_disk_info(disk_object):
    # Function to poll hardware and update given object properties
    time = str(datetime.now())
    disk_object.serial = time

    bay_number = disk_object.bay_port_number
    disk_object.dev_path = get_disk_path(bay_number)
    disk_object.make = get_disk_make(bay_number)
    disk_object.model = get_disk_model(bay_number)
    disk_object.size = get_disk_size(bay_number)

    disk_object.serial = get_disk_serial(disk_object.dev_path)


def get_disk_path(bay_number):
    # Take position, parse lsscsi output and return path
    lsscsi_info = subprocess.run(['lsscsi', '-b'],
                                 text=True,
                                 capture_output=True)
    line = re.search('\['+str(bay_number)+':.+?\\n',
                     lsscsi_info.stdout).group(0)
    path = re.search('/dev/[a-z]{3}', line).group(0)
    return path


def get_disk_make(bay_number):
    # Take position, parse lsscsi output and return model name
    lsscsi_info = subprocess.run(['lsscsi', '-c'],
                                 capture_output=True,
                                 text=True,
                                 )
    line = re.search('scsi'+str(bay_number)+'.+?\\n.+?\\n',
                     lsscsi_info.stdout).group(0)
    model = re.search('(?<=Vendor: )(.+?)(?=Model:)', line).group(0).rstrip()
    return model


def get_disk_model(bay_number):
    # Take position, parse lsscsi output and return model name
    lsscsi_info = subprocess.run(['lsscsi', '-c'],
                                 capture_output=True,
                                 text=True,
                                 )
    line = re.search('scsi'+str(bay_number)+'.+?\\n.+?\\n',
                     lsscsi_info.stdout).group(0)
    model = re.search('(?<=Model: )(.+?)(?=Rev:)', line).group(0).rstrip()
    return model


def get_disk_size(bay_number):
    # Take position, parse lsscsi output and return human readable size
    lsscsi_info = subprocess.run(['lsscsi', '-bs'],
                                 capture_output=True,
                                 text=True,
                                 )
    # group 1 as the group 0 is the matching group and 1 is the capturing group
    size = re.search('\['+str(bay_number)+':.+?\s+\/dev\/[a-z]{3}\s+(.+?)\\n',
                     lsscsi_info.stdout).group(1)
    return size


def get_disk_serial(dev_path):
    # Take dev_path, parse skdump output and return serial
    skdump_info = subprocess.run(['sudo', 'skdump', dev_path],
                                 text=True,
                                 capture_output=True)
    # group 1 as the group 0 is the matching group and 1 is the capturing group
    serial_search = re.search('Serial:\s\[(.+)\]\\n', skdump_info.stdout)
    if serial_search:
        serial = serial_search.group(1)
    else:
        serial = "Unknown"
    return serial


# def disk_refresh(w):


# Bay ATA port numbers, as determined via lsscsi
# ---------
# | 8 | 6 |
# ---------
# | 4 | 7 |
# ---------
# | 5 | 9 |
# ---------

top_left = Disk("Top Left", 0)
top_right = Disk("Top Right", 0)
mid_left = Disk("Middle left", 0)
mid_right = Disk("Middle Right", 0)
bottom_left = Disk("Bottom Left", 0)
bottom_right = Disk("Bottom Right", 0)

disk_list = [top_left, top_right,
             mid_left, mid_right,
             bottom_left, bottom_right]


app = QApplication([])
window = QWidget()

# Sort out header with info
header = QHBoxLayout()
header_text = QLabel("Welcome to CTAZeta")
# header_text.setAlignment(Qt.AlignCenter)
header.addWidget(header_text)

# Sort out body
main = QGridLayout()
main.addLayout(header, 0, 0, 1, 2, Qt.AlignCenter)

# Initiate disk stuff
# test = Disk("Top Left", 0)
# disk_list = [test]

for disk in disk_list:
    get_disk_info(disk)
    main.addWidget(DiskWidgetGroup(disk))

row_count = main.rowCount()

footer = QHBoxLayout()
footer_text = QLabel("Footer refresh")
footer.addWidget(footer_text)
main.addLayout(footer, row_count+1, 0, 1, 2, Qt.AlignCenter)

window.setLayout(main)
window.show()
app.exec()
