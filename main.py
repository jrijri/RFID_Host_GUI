#!/usr/bin/python3
import pathlib
import tkinter as tk
from tkinter import END
import tkinter.ttk as ttk
import pygubu
import usb.core
import serial

PROJECT_PATH = pathlib.Path(__file__).parent
PROJECT_UI   = PROJECT_PATH / "RFID_interface.ui"
zStatus      = {'ReadError'    : ('red', 'Erreur de lecture'),
                'WriteError'   : ('red', "Erreur d'écriture"),
                'USBError'     : ('red', "Lecteur non connecté"),
                'NotConnected' : ('yellow', 'Non connecté'),
                'NoCard'       : ('yellow', 'Pas de carte'),
                'Processing'   : ('orange', "Transaction en cours"),
                'GoodCard'     : ('green', "Carte lue"),
                'GoodWrite'    : ('green', "Carte écrite"),
                'Connected'    : ('green', 'Connecté')}

def updateEntryText(zEntry, szText):
  zEntry.delete(0, END)
  zEntry.insert(0, szText)

class RfidInterfaceApp:
  zData       = {None: (None, None, None)}                           # Tag data
  bRead       = False                                                # Lock the read mode
  bWrite      = False                                                # Lock the write mode
  zSerial     = None                                                 # Set the serial monitor

  def __init__(self, master=None):
    self.builder = builder = pygubu.Builder()
    builder.add_resource_path(PROJECT_PATH)
    builder.add_from_file(PROJECT_UI)
    # Main widget
    self.mainwindow   = builder.get_object("toplevel1", master)
    self.entReference = builder.get_object('entRef', master)
    self.entAddress   = builder.get_object('entAddress', master)
    self.entOwner     = builder.get_object('entOwner', master)
    self.entTagID     = builder.get_object('entTagID', master)
    self.canvaState   = builder.get_object("canStatus", master)
    self.lblStatus    = builder.get_object("lblStatus", master)
    self.butRead      = builder.get_object("butRead", master)
    self.butWrite     = builder.get_object("butWrite", master)
    
    builder.connect_callbacks(self)
    zUSBDevice  = usb.core.find(idVendor = 0x2E8A, idProduct = 0x0005)         # Look for the RPi pico
    if zUSBDevice is None:
      self.setStatus('USBError')
    else:
      try:
        self.setStatus('Processing')
        self.zSerial = serial.Serial('/dev/ttyACM0', timeout = 1)              # timeout needed for readline use
        self.zSerial.flush()
        self.zSerial.write(b'*IDN?\n')
        szLines = self.getReplies()                                            # Get the replies from the RPi
        self.setStatus('Connected')                                            # Just used to set the green oval
        self.lblStatus.config(text = szLines[1])
      except:
        self.setStatus('USBError')

  def getReplies(self):
    szLines = []
    szMsg   = ''
    while not 'Done' in szMsg:
      szMsg = str(self.zSerial.readline().strip())
      #print('> {}'.format(szMsg))
      if len(szMsg) > 7:                                                   # Check if this isn't an empty line
        szLines.append(szMsg.replace("b'", "").replace("'", ""))           # Build the list of the reply
    return(szLines)


  def setStatus(self, szStatus):
    self.canvaState.create_oval(29, 29, 1, 1, width = 1, fill = zStatus[szStatus][0])
    self.lblStatus.config(text = zStatus[szStatus][1])
    self.canvaState.update()

  def run(self):
    self.mainwindow.mainloop()

  def readData(self):
    self.setStatus('Processing')
    self.bRead  = not self.bRead
    if not self.bRead:
      self.butRead.configure(relief = tk.RAISED, text = "  Lecture ")
      return
    else:
      self.butRead.configure(relief = tk.SUNKEN, text = "En lecture")
      updateEntryText(self.entReference, ' ')                                  # Clear the entries
      updateEntryText(self.entAddress,   ' ')
      updateEntryText(self.entOwner,     ' ')
      self.zSerial.flushInput()                                                # Flush the flow first
      self.zSerial.write(b'READ\n')                                            # Set the Read mode
      szLines = self.getReplies()
      for szLine in szLines:
        if 'Tag' in szLine:
          iTag = int(szLine.split('=')[1].strip(' ').strip("'"))               # The Tag value
          updateEntryText(self.entTagID, str(iTag))                            # Display the tag value
          if iTag == -1:
            self.setStatus('NoCard')
            break                                                              # Exit the for loop if no card
        self.setStatus('GoodCard')
        szDisplay = "".join(cChar for cChar in szLine if cChar.isprintable() and cChar != "." and cChar != "'")
        if 'Engine' in szLine:
          updateEntryText(self.entReference, szDisplay.split('Engine')[1].strip())
        if 'Address' in szLine:
          updateEntryText(self.entAddress,   szDisplay.split('Address')[1].strip())
        if 'Owner' in szLine:
          updateEntryText(self.entOwner,     szDisplay.split('Owner')[1].strip())
    self.butRead.configure(relief = tk.RAISED, text = "  Lecture ")            # Exit the read mode
    self.bRead = False
        

  def writeTag(self):
    self.setStatus('Processing')
    self.bWrite  = not self.bWrite
    if not self.bWrite:
      self.butWrite.configure(relief = tk.RAISED, text = "Mise à jour")
      return
    else:
      self.butWrite.configure(relief = tk.SUNKEN, text = "  Ecriture ")
      szEngine  = self.entReference.get()
      szAddress = self.entAddress.get()
      szOwner   = self.entOwner.get()
      szMsg = "Engine {engine}#Address {address}#Owner {owner}\n".format(engine = szEngine, address = szAddress, owner = szOwner)
      szMsg = bytes(szMsg, 'utf-8')
      #print('> {}'.format(szMsg))
      #self.zSerial.flush()                                                     # Flush the flow first
      self.zSerial.write(b'WRITE\n')                                           # Set the Write mode
      self.zSerial.write(szMsg)                                                # Message is a string, fields splitted by '\r\n'
      #print('Sent < {}'.format(szMsg))
      self.getReplies()                                                        # Get the RPi messages
    self.butWrite.configure(relief = tk.RAISED, text = "Mise à jour")
    self.bWrite = False
    self.setStatus('GoodWrite')

  def quitApp(self):
    quit()


if __name__ == "__main__":
  app = RfidInterfaceApp()
  app.run()
