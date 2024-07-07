#!/usr/bin/env python3
import os
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
import threading
import subprocess
import web_server  # Import the web_server module
import check_wifi  # Import the check_wifi module

AGENT_PATH = "/test/agent"

class BluetoothAgent(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName("org.bluez", bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, AGENT_PATH)

    @dbus.service.method("org.bluez.Agent1", in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        print(f"Passkey: {passkey} Entered: {entered}")

    @dbus.service.method("org.bluez.Agent1", in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print(f"RequestConfirmation: {passkey}")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print(f"AuthorizeService: {uuid}")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print(f"RequestAuthorization: {device}")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print(f"RequestPinCode: {device}")
        return "0000"

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print(f"RequestPasskey: {device}")
        return dbus.UInt32(123456)

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Release(self):
        print("Release")

def register_agent():
    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), "org.bluez.AgentManager1")
    manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
    manager.RequestDefaultAgent(AGENT_PATH)
    print("Agent registered")

def make_discoverable():
    bus = dbus.SystemBus()
    adapter_path = "/org/bluez/hci0"
    adapter = dbus.Interface(bus.get_object("org.bluez", adapter_path), "org.freedesktop.DBus.Properties")
    adapter.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(1))
    print("Device is now discoverable")

def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    agent = BluetoothAgent()
    register_agent()
    make_discoverable()
    if not check_wifi.is_connected():
        check_wifi.start_access_point()
    threading.Thread(target=web_server.start_flask_server).start()
    mainloop = GLib.MainLoop()
    mainloop.run()

if __name__ == "__main__":
    main()
