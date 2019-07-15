from extronlib_pro import (
    event,
    File,
    Wait,
)

import calendar
import datetime
import json

from keyboard import Keyboard
from scrolling_table import ScrollingTable
from gs_tools import GetRandomHash

DEBUG = False
if not DEBUG:
    print = lambda *a, **k: None


# UserInput *********************************************************************
class UserInputClass:
    '''
    A one-time setup of the buttons/popups and the programmer can easily grab info from the user like so:

    Get an integer/float/text from the user: UserInput.get_keyboard('popupname', callback=CallbackFunction)
    Get a calendar data as a datetime.datetime object: UserInput.get_date(**kwargs)
    etc...
    '''
    _instances = []  # hold all instances so that instances can request each other to update

    def __init__(self, TLP):
        self._TLP = TLP

        self._kb_feedback_btn = None
        self._kb_text_feedback = None
        self._kb_callback = None
        self._instances.append(self)

        self._list_popup_name = ''

    def set_file_explorer_parameters(self, d):
        for key, value in d.items():
            method = getattr(self._dirNav, key)
            method(value)

    def setup_file_explorer(self,
                            lblCurrentDirectory=None,
                            btnScrollUp=None,
                            btnScrollDown=None,
                            lvlScrollFeedback=None,
                            lblScrollText=None,
                            btnNavUp=None,

                            lblMessage=None,
                            btnClosePopup=None,
                            popupName=None,
                            limitStringLen=25,
                            btnSubmit=None,
                            ):

        self._file_explorer_lblMessage = lblMessage
        self._file_explorer_popupName = popupName
        self._btnSubmit = btnSubmit

        self._dirNav = DirectoryNavigationClass(
            lblCurrentDirectory,
            btnScrollUp,
            btnScrollDown,
            lvlScrollFeedback,
            lblScrollText,
            btnNavUp,
            limitStringLen=limitStringLen,
            lblMessage=lblMessage,
        )

        self._file_explorer_filename = None
        self._file_explorer_filepath = None
        self._file_explorer_getFileCallback = None

        self._dirNav.FileSelected = self._file_explorer_fileSelectedCallback
        self._dirNav.FileHeld = self._file_explorer_fileHeldCallback

        if btnClosePopup:
            @event(btnClosePopup, 'Released')
            def btnClosePopupEvent(button, state):
                btnClosePopup.Host.HidePopup(self._file_explorer_popupName)

    def _file_explorer_fileSelectedCallback(self, dirNav, path, passthru=None):
        self._file_explorer_filepath = path
        self._file_explorer_filename = path.split('/')[-1]

        if callable(self._file_explorer_getFileCallback):
            self._file_explorer_getFileCallback(self, path, self._file_explorer_passthru)

        if self._file_explorer_feedback_btn is not None:
            self._file_explorer_feedback_btn.SetText(self._file_explorer_filename)

        if self._file_explorer_popupName is not None:
            self._TLP.HidePopup(self._file_explorer_popupName)

    def _file_explorer_fileHeldCallback(self, dirNav, filepath):
        print('_file_explorer_fileHeldCallback(dirNav={}, filepath={})'.format(dirNav, filepath))

        def DirNavActionCallback(input, value, passthru):
            filepath = passthru['filepath']

            if 'Delete' in value:
                if self._dirNav.IsFile(filepath):
                    File.DeleteFile(filepath)
                    self._dirNav.UpdateData()

                elif self._dirNav.IsDirectory(filepath):
                    File.DeleteDirRecursive(filepath)
                    self._dirNav.UpdateData()

            elif 'Make New Directory' == value:
                self.make_new_directory(
                    data=None,  # internal file system
                    callback=None,
                    passthru=None,
                    makeDir=True,
                    # whether to actually create the dir, False will just return the new path to the user, True will actually create the dir in the internal filesystem
                )

            elif 'Make New File' == value:
                self.make_new_file(
                    data=None,  # internal file system
                    callback=None,
                    feedback_btn=None,
                    passthru=None,
                    extension=None,  # '.json', '.dat', etc...
                    keyboardPopupName=None,
                )

        options = []
        if self._dirNav.AllowMakeNewFolder():
            options.append('Make New Directory')

        if self._dirNav.AllowMakeNewFile():
            options.append('Make New File')

        if self._dirNav.AllowDelete() and (self._dirNav.IsFile(filepath) or self._dirNav.IsDirectory(filepath)):
            options.append('Delete this {}'.format(self._dirNav.GetType(filepath)))

        self.get_list(
            options=options,  # list()
            callback=DirNavActionCallback,
            # function - should take 2 params, the UserInput instance and the value the user submitted
            feedback_btn=None,
            passthru={'filepath': filepath},  # any object that you want to pass thru to the callback
            message='Choose an action.',
            sort=True,
        )

    def file_explorer_register_row(self, *args, **kwargs):
        '''
        Example:
        for rowNumber in range(0, 7+1):
            file_explorer_register_rowObject.RegisterRow(
                rowNumber=rowNumber,
                btnIcon=Button(ui, 2000+rowNumber),
                btnSelection=Button(ui, 1000+rowNumber, PressFeedback='State'),
        )
        '''
        self._dirNav.RegisterRow(*args, **kwargs)

    def get_file(self,
                 data=None,
                 callback=None,
                 feedback_btn=None,
                 passthru=None,
                 message=None,
                 submitText='Submit',
                 submitCallback=None,  # (button, state),
                 startingDir=None
                 ):

        self._dirNav.SetShowFiles(True)

        if startingDir is not None:
            self._dirNav.SetCurrentDirectory(startingDir)

        if data is None:
            data = File.ListDirWithSub()

        self._dirNav.UpdateData(data)
        self._file_explorer_getFileCallback = callback
        self._file_explorer_feedback_btn = feedback_btn
        self._file_explorer_passthru = passthru

        if self._file_explorer_lblMessage is not None and message is not None:
            self._file_explorer_lblMessage.SetText(message)

        if self._btnSubmit:
            if submitCallback is None:
                self._btnSubmit.SetVisible(False)
            else:
                self._btnSubmit.SetText(submitText)
                self._btnSubmit.SetVisible(True)

                @event(self._btnSubmit, 'Released')
                def self_btnSubmitEvent(button, state):
                    submitCallback(button, state)

        def SubCallback(dirNavObject, value, passthru=None):
            self._TLP.HidePopup(self._file_explorer_popupName)
            callback(self, value, self._file_explorer_passthru)

        self._dirNav.FileSelected = SubCallback

        if self._file_explorer_popupName is not None:
            Wait(0.1, lambda: self._TLP.ShowPopup(self._file_explorer_popupName))

    def make_new_directory(self,
                           data=None,
                           callback=None,
                           passthru=None,
                           makeDir=False,
                           # whether to actually create the dir, False will just return the new path to the user, True will actually create the dir in the internal filesystem
                           ):
        if data is None:
            data = File.ListDirWithSub()

        self._dirNav.SetShowFiles(False)

        def getNewDirNameCallback(input, value, passthru3=None):
            newFolderName = value
            currentDir = self._dirNav.GetDir()
            File.MakeDir(currentDir + '/' + newFolderName)
            self._dirNav.UpdateData()

        popup = self._kb_other_popups.get('AlphaNumeric', self._kb_popup_name)

        self.get_keyboard(
            kb_popup_name=popup,
            callback=getNewDirNameCallback,
            # function - should take 2 params, the UserInput instance and the value the user submitted
            feedback_btn=None,
            password_mode=False,
            text_feedback=None,  # button()
            passthru=None,  # any object that you want to also come thru the callback
            message='Enter a name for the new directory.',
        )

    def make_new_file(self,
                      data=None,  # list of filePath as str, or None means use the IPCP internal file system
                      callback=None,
                      feedback_btn=None,
                      passthru=None,
                      extension=None,  # '.json', '.dat', etc...
                      keyboardPopupName=None,
                      ):
        '''Use this method to create a new filePath and let the user choose the name and which directory to save it in
        returns: path to the new file. THe user will have to use File(path, mode='wt') to actually write data to the file
        return type: str (example: '/folder1/subfolder2/filename.txt')
        '''

        self._dirNav.SetShowFiles(False)

        if keyboardPopupName is None:
            keyboardPopupName = self._kb_popup_name

        if extension is None:
            extension = '.dat'

        def newFileDirectoryCallback(input, value, passthru2):
            print('newFileDirectoryCallback(input={}, value={}, passthru2={})'.format(input, value, passthru2))
            if callable(callback):
                value = value + passthru2

                callback(self, value, passthru)

        def newFileNameCallback(input, value, passthru3=None):
            print('newFileNameCallback(input={}, value={}, passthru3={})'.format(input, value, passthru3))
            value = value + extension

            # let the user choose which directory to save this file to
            self.get_directory(
                data=None,
                callback=newFileDirectoryCallback,
                feedback_btn=None,
                passthru=value,
                message='Choose where to save {}'.format(value),
            )

        self.get_keyboard(
            kb_popup_name=keyboardPopupName,
            callback=newFileNameCallback,
            # function - should take 2 params, the UserInput instance and the value the user submitted
            feedback_btn=None,
            password_mode=False,
            text_feedback=None,  # button()
            passthru=None,  # any object that you want to also come thru the callback
            message='Enter a new name for the file.',
        )

    def get_directory(self,
                      data=None,
                      callback=None,
                      feedback_btn=None,
                      passthru=None,
                      message=None,
                      ):
        self._dirNav.SetShowFiles(False)

        if data is None:
            data = File.ListDirWithSub()

        if message is None:
            message = 'Select a folder'

        self._dirNav.UpdateData(data)
        self._dirNav.FileSelected = None  # dont do anything when a file is selected. A file should never be selected anyway.
        self._dirNav.UpdateMessage(message)

        if self._btnSubmit:

            @event(self._btnSubmit, 'Released')
            def btnSubmitEvent(button, state):
                if callable(callback):
                    callback(self, self._dirNav.GetDir(), passthru)
                self._btnSubmit.Host.HidePopup(self._file_explorer_popupName)

            self._btnSubmit.SetText('Select this folder')
            self._btnSubmit.SetVisible(True)

            if self._file_explorer_popupName is not None:
                Wait(0.1, lambda: self._TLP.ShowPopup(self._file_explorer_popupName))

        else:
            raise Exception('"get_directory" requires "setup_file_explorer()" with btnSubmit parameter')

    def SetupCalendar(self, *a, **k):
        return self.setup_calendar(*a, **k)

    def setup_calendar(self,
                       calDayNumBtns,
                       # list of extronlib.ui.Button where .ID is int() where the first int is the first day of the first week. Assuming 5 weeks of 7 days
                       calDayAgendaBtns=None,
                       calBtnNext=None,  # button that when pressed will show the next month
                       calBtnPrev=None,  # button that when pressed will show the previous month
                       calBtnCancel=None,  # button when presses will hide the modal
                       calLblMessage=None,  # Button or Label
                       calLblMonthYear=None,
                       calPopupName=None,
                       startDay=None,
                       maxAgendaWidth=None,  # limit the num of characters on an adgenda. to prevent it word-wrapping

                       ):
        '''
        This func must be called before self.get_date()
        :param calDayNumBtns:
        :param calDayAgendaBtns:
        :param calBtnNext:
        :param calBtnPrev:
        :param calBtnCancel:
        :param calLblMessage:
        :param calLblMonthYear:
        :param calPopupName:
        :param startDay: int > None assumes 6=sunday
        :param maxAgendaWidth:
        :return:
        '''

        # Save args
        self._calDayNumBtns = calDayNumBtns
        self._calDayAgendaBtns = calDayAgendaBtns
        self._calBtnNext = calBtnNext
        self._calBtnPrev = calBtnPrev
        self._calBtnCancel = calBtnCancel
        self._calLblMessage = calLblMessage
        self._calLblMonthYear = calLblMonthYear
        self._calPopupName = calPopupName
        self._maxAgendaWidth = maxAgendaWidth

        calendar.setfirstweekday(6)  # Start calendar on Sunday

        # Create attributes
        self._wait__calDisplayMonth = Wait(1, self._calDisplayMonth)
        self._calendarCurrentDatetimeChanges = None
        if startDay is None:
            startDay = 6  # sunday
        self._calObj = calendar.Calendar(startDay)

        self._currentYear = 0
        self._currentMonth = 0
        self._currentDatetime = datetime.datetime.now()
        self._calEvents = [
            # {'datetime': dt,
            # 'name': 'name of event',
            # 'meta': {'Room Name': 'Room1',
            #          'Device Name': 'Room2',
            #           }
            # }
        ]
        self._calCallback = None
        self._dtMap = {}
        self._calHeldEvent = None

        # Hide/Cancel button
        if self._calBtnCancel is not None:
            @event(self._calBtnCancel, 'Released')
            def calBtnCancelEvent(button, state):
                if self._calPopupName is not None:
                    self._TLP.HidePopup(self._calPopupName)

        # Next/Prev buttons
        @event(self._calBtnNext, 'Released')
        def CalBtnNextEvent(button, state):
            self._currentMonth += 1
            if self._currentMonth > 12:
                self._currentYear += 1
                self._currentMonth = 1

            dt = datetime.datetime(year=self._currentYear, month=self._currentMonth, day=1)
            self._calDisplayMonth(dt)
            print('self._currentMonth=', self._currentMonth)

            if callable(self._calendarCurrentDatetimeChanges):
                self._calendarCurrentDatetimeChanges(self, dt)

        @event(self._calBtnPrev, 'Released')
        def CalBtnPrevEvent(button, state):
            self._currentMonth -= 1
            if self._currentMonth < 1:
                self._currentYear -= 1
                self._currentMonth = 12

            dt = datetime.datetime(year=self._currentYear, month=self._currentMonth, day=1)
            self._calDisplayMonth(dt)
            print('self._currentMonth=', self._currentMonth)

            if callable(self._calendarCurrentDatetimeChanges):
                self._calendarCurrentDatetimeChanges(self, dt)

        # Day/Agenda buttons
        @event(self._calDayNumBtns, 'Released')
        @event(self._calDayAgendaBtns, 'Released')
        def calDayNumBtnsEvent(button, state):
            pass

        # Init the button states
        for btn in self._calDayNumBtns:
            btn.SetState(0)
        for btn in self._calDayAgendaBtns:
            btn.SetState(0)

        # Load previous data
        self._LoadCalData()

        # Set the 6th week buttons to not visible
        for btn in self._calDayNumBtns + self._calDayAgendaBtns:
            if btn.ID % 100 >= 35:
                btn.SetVisible(False)

    @property
    def CalendarCurrentDatetimeChanges(self):
        return self._calendarCurrentDatetimeChanges

    @CalendarCurrentDatetimeChanges.setter
    def CalendarCurrentDatetimeChanges(self, func):
        self._calendarCurrentDatetimeChanges = func

    def GetDate(self, *a, **k):
        return self.get_date(*a, **k)

    def get_date(self,
                 popupName=None,
                 callback=None,
                 # function - should take 2 params, the UserInput instance and the value the user submitted
                 feedback_btn=None,
                 passthru=None,  # any object that you want to pass thru to the callback
                 message=None,
                 startMonth=None,
                 startYear=None,
                 ):
        '''
        The programmer must call self.setup_calendar() before calling this method.
        :param popupName:
        :param callback:
        :param feedback_btn:
        :param passthru:
        :param message:
        :param startMonth:
        :param startYear:
        :return:
        '''

        self._calCallback = callback

        if self._calLblMessage is not None:
            if message is None:
                self._calLblMessage.SetText('Select a date')
            else:
                self._calLblMessage.SetText(message)

        # Populate the calendar info
        now = datetime.datetime.now()
        if startMonth is None:
            startMonth = now.month

        if startYear is None:
            startYear = now.year

        self._currentYear = startYear
        self._currentMonth = startMonth

        self._calDisplayMonth(datetime.datetime(year=startYear, month=startMonth, day=1))

        # Show the calendar
        if popupName is not None:
            self._TLP.ShowPopup(popupName)

        @event(self._calDayNumBtns, 'Released')
        @event(self._calDayAgendaBtns, 'Released')
        def calDayNumBtnsEvent(button, state):
            if callable(self._calCallback):
                dt = self._GetDatetimeFromButton(button)
                self._calCallback(self, dt)
                self._currentDatetime = dt

    def CalOffsetTimedelta(self, delta):
        '''
        Change the calendar by delta time.
        For example if I am currently looking at info for today and I want to see next week's info,
            I would call UserInput.CalOffsetTimedelta(datetime.timedelta(days=7))
            This would cause the UI to update to show next weeks info.
        :param delta: datetime.timedelta object
        :return:
        '''
        if self._currentDatetime is None:
            self._currentDatetime = datetime.datetime.now()

        self._currentDatetime += delta

        return self._currentDatetime

    def GetCalCurrentDatetime(self):
        '''
        return a datetime.datetime object of the info currently being displayed.
        :return:
        '''
        return self._currentDatetime

    def _GetDatetimeFromButton(self, button):
        for date in self._dtMap:
            if button in self._dtMap[date]:
                return date

    def UpdateMonthDisplay(self, dt=None):
        '''
        The programmer can call this to update the buttons with info for the month contained in dt
        :param dt: datetime.datetime object
        :return:
        '''
        if dt is None:
            dt = self.GetCalCurrentDatetime()

        for instance in self._instances:
            instance._calDisplayMonth(dt)

    def _GetWeekOfMonth(self, dt):
        weeks = calendar.monthcalendar(dt.year, dt.month)
        for index, week in enumerate(weeks):
            if dt.day in week:
                return index + 1

    def _calDisplayMonth(self, dt=None):
        # date = datetime.datetime object
        # this will update the TLP with data for the month of the datetime.date

        if dt is None:
            dt = self._currentDatetime

        self._currentDatetime = dt

        self._dtMap = {}

        self._calLblMonthYear.SetText(dt.strftime('%B %Y'))

        # Set the 6th week buttons to not visible
        # for btn in self._calDayNumBtns + self._calDayAgendaBtns:
        #     if btn.ID % 100 >= 35:
        #         btn.SetVisible(False)

        monthDates = list(self._calObj.itermonthdates(dt.year, dt.month))
        for index, date in enumerate(monthDates):
            if index >= len(self._calDayNumBtns):
                continue

            btnDayNum = self._calDayNumBtns[index]
            btnDayAgenda = self._calDayAgendaBtns[index]

            # Save the datetime and map it to the buttons for later use
            self._dtMap[date] = [btnDayNum, btnDayAgenda]

            if date.month != self._currentMonth:  # Not part of the month

                newState = 1
                newText = date.strftime('%d ')

            else:  # is part of the current month
                weekNum = self._GetWeekOfMonth(date)
                if weekNum >= 6:
                    # This is part of this month and is in the 6th week, show it
                    if not btnDayNum.Visible:
                        btnDayNum.SetVisible(True)
                    if not btnDayAgenda.Visible:
                        btnDayAgenda.SetVisible(True)

                newState = 0
                newText = date.strftime('%d ')

            agendaText = self._GetAgendaText(date)

            # btnDayNum
            if btnDayNum.State != newState:
                btnDayNum.SetState(newState)

            if btnDayNum.Text != newText:
                btnDayNum.SetText(newText)

            # btnDayAgenda
            if btnDayAgenda.State != newState:
                btnDayAgenda.SetState(newState)

            if btnDayAgenda.Text != agendaText:
                btnDayAgenda.SetText(agendaText)

        else:
            # these buttons are past the current month, set to visible false
            while index <= 41:
                btnDayNum = self._calDayNumBtns[index]
                btnDayAgenda = self._calDayAgendaBtns[index]

                btnDayNum.SetVisible(False)
                btnDayAgenda.SetVisible(False)

                index += 1

    def _GetAgendaText(self, date):
        result = ''

        for item in self._calEvents:
            dt = item['datetime']
            if date.year == dt.year:
                if date.month == dt.month:
                    if date.day == dt.day:
                        name = item['name']
                        string = '{} - {}\n'.format(dt.strftime('%I:%M%p'), name)

                        # Make sure the string isnt too long
                        if self._maxAgendaWidth is not None:
                            if len(string) > self._maxAgendaWidth:
                                string = string[:self._maxAgendaWidth - 4] + '...\n'

                        result += string

        return result

    def GetAgendaFromDatetime(self, date):
        '''
        Returns a list of eventDicts that are happening on the date

        eventDict looks like:
        {
        'datetime': dt, #datetime.datetime object representing the time the event is happening
        'name': 'Name Of The Event', #str representing the name of the event
        'meta': {'Room Number': 'Room 101'}, #dict with any custom values that the user may want to hold about the event. For example a room number.
        }

        :param date: datetime.date or datetime.datetime
        :return: list like [{eventDict1, eventDict2, ...]
        '''

        result = []

        for item in self._calEvents:
            dt = item['datetime']
            if date.year == dt.year:
                if date.month == dt.month:
                    if date.day == dt.day:
                        name = item['name']
                        result.append(item)

        return result

    def GetCalEventByID(self, ID):
        for event in self._calEvents.copy():
            if event.get('ID', None) == ID:
                return event

    def GetAllCalendarEvents(self):
        '''
        eventDict looks like:
        {
        'datetime': dt, #datetime.datetime object representing the time the event is happening
        'name': 'Name Of The Event', #str representing the name of the event
        'meta': {'Room Number': 'Room 101'}, #dict with any custom values that the user may want to hold about the event. For example a room number.
        }
        :return: list of all eventDicts
        '''
        return self._calEvents.copy()

    def AddCalendarEvent(self,
                         startDT=None,
                         name=None,
                         metaDict=None,
                         endDT=None,
                         ID=None,
                         _delayUpdate=True,
                         # weather to update the display immediately or wait for 1 second after last update
                         ):
        '''
        Add an event to the calendar
        :param startDT: datetime.
        :param endDT: datetime.datetime
        :param name: str
        :param metaDict: {}
        :param ID: str
        :param _delayUpdate: bool
        :return:
        '''
        if metaDict is None:
            metaDict = {}

        if ID is None:
            ID = GetRandomHash()

        newEvent = {
            'datetime': startDT,
            'name': name,
            'meta': metaDict,
            'Start Time': startDT,
            'End Time': endDT,
            'ID': ID,  # assign a unique id to each event
        }

        for event in self._calEvents.copy():
            if event['ID'] == newEvent['ID']:
                if event == newEvent:
                    break  # ignore this duplicate
                else:
                    # this event is being updated
                    self._calEvents.remove(event)
        else:
            # add the event normally
            self._calEvents.append(newEvent)

            self._SaveCalData()
            self._currentDatetime = startDT

            if _delayUpdate:
                self._wait__calDisplayMonth.Restart()
            else:
                self._calDisplayMonth()

    def _SaveCalData(self):
        # Write the data to a file
        saveItems = []

        for item in self._calEvents:
            dt = item['datetime']
            saveItem = {
                'datetime': GetDatetimeKwargs(dt),
                'name': item['name'],
                'meta': item['meta'],
                'Start Time': GetDatetimeKwargs(item.get('Start Time', None)),
                'End Time': GetDatetimeKwargs(item.get('End Time', None)),
                'ID': item.get('ID', None),
            }
            saveItems.append(saveItem)

        with File('calendar.json', mode='wt') as file:
            file.write(json.dumps(saveItems, indent=4))
            file.close()

    def _LoadCalData(self):
        if not File.Exists('calendar.json'):
            self._calEvents = []
            return

        with File('calendar.json', mode='rt') as file:
            saveItems = json.loads(file.read())
            file.close()

            for saveItem in saveItems:
                dt = datetime.datetime(**saveItem['datetime'])

                loadItem = {
                    'datetime': dt,
                    'name': saveItem['name'],
                    'meta': saveItem['meta'],
                    'Start Time': datetime.datetime(**saveItem.get('Start Time', None)),
                    'End Time': datetime.datetime(**saveItem.get('End Time', None)),
                    'ID': saveItem.get('ID', None)
                }

                self._calEvents.append(loadItem)

    def GetCalEvents(self, dt=None, ID=None):
        '''
        return list of eventDicts happening at a specific datetime.datetime

        eventDict looks like:
        {
        'datetime': dt, #datetime.datetime object representing the time the event is happening
        'name': 'Name Of The Event', #str representing the name of the event
        'meta': {'Room Number': 'Room 101'}, #dict with any custom values that the user may want to hold about the event. For example a room number.
        }
        :param dt: datetime.datetime
        :return: list
        '''
        result = []
        if dt is not None:
            for item in self._calEvents:
                dataDT = item['datetime']
                if dt.year == dataDT.year:
                    if dt.month == dataDT.month:
                        if dt.day == dataDT.day:
                            if isinstance(dt, datetime.datetime):
                                if dt.hour is not 0:
                                    if dt.hour == dataDT.hour:
                                        if dt.minute is not 0:
                                            if dt.minute == dataDT.minute:
                                                result.append(item)
                                        else:
                                            result.append(item)
                                else:
                                    result.append(item)
                            else:  # probably a datetime.date object
                                result.append(item)

        elif ID is not None:
            for item in self._calEvents:
                if item.get('ID', None) == ID:
                    result.append(item)

        return result

    def HoldThisEvent(self, eventDict):
        '''
        This class can hold one eventDict for the programmer.
        :param eventDict: dict or None
        :return:
        '''
        self._calHeldEvent = eventDict

    def GetHeldEvent(self):
        '''
        Returns the held eventDict
        :return: eventDict or None
        '''
        return self._calHeldEvent.copy() if self._calHeldEvent else None

    def TrashHeldEvent(self):
        '''
        Deletes the held event from memory.
        :return:
        '''
        self.DeleteEvent(self._calHeldEvent)
        self._calHeldEvent = None

    def DeleteEventByID(self, ID):
        print('862 DeleteEventByID(', ID)
        for event in self._calEvents.copy():
            if event.get('ID') == ID:
                print('860 removing event=', event)
                self._calEvents.remove(event)
                self._wait__calDisplayMonth.Restart()

    def DeleteEvent(self, eventDict):
        '''
        Deletes the specified eventDict
        :param eventDict:
        :return:
        '''
        print('DeleteEvent(', eventDict)
        if eventDict in self._calEvents:
            self._calEvents.remove(eventDict)
        else:
            raise Exception('Exception in DeleteEvent\neventDict not in self._calEvents')

        self._SaveCalData()
        self.UpdateMonthDisplay()

    def SetupList(self, *a, **k):
        return self.setup_list(*a, **k)

    def setup_list(self,
                   list_popup_name,  # str()
                   list_btn_hide,  # Button object
                   list_btn_table,  # list() of Button objects
                   list_btn_scroll_up=None,  # Button object
                   list_btn_scroll_down=None,  # Button object
                   list_label_message=None,  # Button/Label object
                   list_label_scroll=None,  # Button/Label object
                   list_level_scroll=None,

                   ):

        self._list_popup_name = list_popup_name
        self._list_table = ScrollingTable()

        if list_level_scroll is not None:
            self._list_table.register_scroll_updown_level(list_level_scroll)

        if list_label_message is not None:
            self._list_table.register_scroll_updown_label(list_label_scroll)

        if list_btn_scroll_up:
            self._list_table.register_scroll_up_button(list_btn_scroll_up)

        if list_btn_scroll_down:
            self._list_table.register_scroll_down_button(list_btn_scroll_down)

        self._list_callback = None
        self._list_label_message = list_label_message

        # Setup the ScrollingTable
        for btn in list_btn_table:

            # Add an event handler for the table buttons
            @event(btn, 'Released')
            def list_btn_event(button, state):
                print('list_btn_event')
                print('self._list_passthru=', self._list_passthru)
                print('button=', button)
                print('button.Text=', button.Text)

                # If a button with no text is selected. Do nothing.
                if button.Text == '':
                    print('button.Text == ''\nPlease select a button with text')
                    return

                # Set text feedback
                if self._list_feedback_btn:
                    self._list_feedback_btn.SetText(button.Text)

                # do callback
                if self._list_callback:
                    if self._list_passthru is not None:
                        self._list_callback(self, button.Text, self._list_passthru)
                    else:
                        self._list_callback(self, button.Text)

                self._TLP.HidePopup(self._list_popup_name)

            # Register the btn with the ScrollingTable instance
            row_number = list_btn_table.index(btn)
            self._list_table.register_row_buttons(row_number, btn)

        # Setup Scroll buttons
        if list_btn_scroll_up:
            if not list_btn_scroll_up._repeatTime:
                list_btn_scroll_up._repeatTime = 0.1

            @event(list_btn_scroll_up, ['Pressed', 'Repeated'])
            def list_btn_scroll_upEvent(button, state):
                self._list_table.scroll_up()

        if list_btn_scroll_down:
            if not list_btn_scroll_down._repeatTime:
                list_btn_scroll_down._repeatTime = 0.1

            @event(list_btn_scroll_down, ['Pressed', 'Repeated'])
            def list_btn_scroll_downEvent(button, state):
                self._list_table.scroll_down()

        # Hide button
        @event(list_btn_hide, 'Released')
        def list_btn_hideEvent(button, state):
            self.HidePopup()

    def HidePopup(self):
        # hides popups for all types
        for name in [self._list_popup_name, self._kb_popup_name] + list(self._kb_other_popups.values()):
            print('name=', name)
            self._TLP.HidePopup(name)

    def GetList(self, *a, **k):
        return self.get_list(*a, **k)

    def get_list(self,
                 options=None,  # list()
                 callback=None,
                 # function - should take 2 params, the UserInput instance and the value the user submitted
                 feedback_btn=None,
                 passthru=None,  # any object that you want to pass thru to the callback
                 message=None,
                 sort=False,
                 highlight=None,
                 ):
        self._list_highlight = highlight or None
        self._list_callback = callback
        self._list_feedback_btn = feedback_btn
        self._list_passthru = passthru

        # Update the table with new data
        self._list_table.clear_all_data()

        # try to sort the options
        if sort is True:
            try:
                options.sort()
            except:
                pass

        for option in options:
            self._list_table.add_new_row_data({'Option': option})

        # highlight some options if applicable
        self._list_table.ClearAllStateRules()
        if self._list_highlight is not None:
            for text in self._list_highlight:
                self._list_table.AddSelectedTextStateRule(text, 1)

        if self._list_label_message:
            if message:
                self._list_label_message.SetText(message)
            else:
                self._list_label_message.SetText('Select an item from the list.')

        # Show the list popup
        self._TLP.ShowPopup(self._list_popup_name)

    def SetupKeyboard(self, *a, **k):
        return self.setup_keyboard(*a, **k)

    def setup_keyboard(self,
                       kb_popup_name,  # str() #default popup name
                       kb_btn_submit,  # Button()
                       kb_btn_cancel=None,  # Button()
                       kb_other_popups={},
                       # {'Integer': 'User Input - Integer', 'Float': 'User Input - Float', 'AlphaNumeric': 'User Input - AlphaNumeric'}

                       KeyIDs=None,  # list()
                       BackspaceID=None,  # int()
                       ClearID=None,  # int()
                       SpaceBarID=None,  # int()
                       ShiftID=None,  # int()
                       SymbolID=None,
                       FeedbackObject=None,  # object with .SetText() method
                       kb_btn_message=None,
                       kb_class=None,
                       kb_class_kwargs=None,
                       ):

        self._kb_btn_cancel = kb_btn_cancel
        self._kb_popup_name = kb_popup_name
        self._kb_other_popups = kb_other_popups
        self._kb_btn_message = kb_btn_message

        @event(kb_btn_submit, 'Released')
        def kb_btn_submitEvent(button, state):
            string = self._kb_Keyboard.GetString()
            print('kb_btn_submitEvent\n button.ID={}\n state={}\n string={}'.format(button.ID, state, string))

            self._TLP.HidePopup(self._kb_popup_name)

            if self._kb_callback:
                if self._kb_passthru:
                    self._kb_callback(self, string, self._kb_passthru)
                else:
                    self._kb_callback(self, string)

            if self._kb_feedback_btn:
                self._kb_feedback_btn.SetText(string)

        if self._kb_btn_cancel:
            @event(self._kb_btn_cancel, 'Released')
            def kb_btn_cancelEvent(button, state):
                self.HidePopup()

        if kb_class is None:
            kb_class = Keyboard

        if kb_class_kwargs is None:
            kb_class_kwargs = {}

        self._kb_Keyboard = kb_class(
            TLP=self._TLP,
            KeyIDs=KeyIDs,  # list()
            BackspaceID=BackspaceID,  # int()
            ClearID=ClearID,  # int()
            SpaceBarID=SpaceBarID,  # int()
            ShiftID=ShiftID,  # int()
            SymbolID=SymbolID,
            FeedbackObject=FeedbackObject,  # object with .SetText() method
            **kb_class_kwargs
        )

    @property
    def KeyboardObject(self):
        return self._kb_Keyboard

    def SetKeyboardText(self, text):
        self._kb_Keyboard.SetString(text)
        if self._kb_text_feedback:
            self._kb_text_feedback.SetText(text)

    def GetKeyboard(self, *a, **k):
        return self.get_keyboard(*a, **k)

    def get_keyboard(self,
                     kb_popup_name=None,
                     kb_popup_timeout=0,
                     callback=None,
                     # function - should take 2 params, the UserInput instance and the value the user submitted
                     feedback_btn=None,  # button to assign submitted value
                     password_mode=False,  # mask your typing with '****'
                     text_feedback=None,  # button() to show text as its typed
                     passthru=None,  # any object that you want to also come thru the callback
                     message=None,
                     allowCancel=True,  # set to False to force the user to enter input
                     ):

        if allowCancel is True:
            self._kb_btn_cancel.SetVisible(True)
        else:
            self._kb_btn_cancel.SetVisible(False)

        if kb_popup_name:
            self._kb_popup_name = kb_popup_name

        if message:
            if self._kb_btn_message:
                self._kb_btn_message.SetText(message)
        else:
            if self._kb_btn_message:
                self._kb_btn_message.SetText('Please enter your text.')

        self._kb_Keyboard.SetPasswordMode(password_mode)

        if text_feedback:
            self._kb_text_feedback = text_feedback  # button to show text as it is typed
            self._kb_Keyboard.SetFeedbackObject(self._kb_text_feedback)

        self._kb_callback = callback  # function accepts 2 params; this UserInput instance and the value submitted
        self._kb_feedback_btn = feedback_btn  # button to assign submitted value
        self._kb_passthru = passthru

        self._kb_Keyboard.ClearString()

        self._TLP.ShowPopup(self._kb_popup_name, kb_popup_timeout)

    def setup_boolean(self,
                      bool_popup_name,  # str()

                      bool_btn_true,  # Button()
                      bool_btn_false,  # Button()
                      bool_btn_cancel=None,  # Button()

                      bool_btn_message=None,
                      bool_btn_long_message=None,
                      bool_btn_true_explaination=None,
                      bool_btn_false_explanation=None,
                      ):
        self._bool_callback = None
        self._bool_true_text = 'Yes'
        self._bool_false_text = 'No'

        self._bool_popup_name = bool_popup_name

        self._bool_btn_true = bool_btn_true
        self._bool_btn_false = bool_btn_false
        self._bool_btn_cancel = bool_btn_cancel

        self._bool_btn_message = bool_btn_message
        self._bool_btn_long_message = bool_btn_long_message
        self._bool_btn_true_explaination = bool_btn_true_explaination
        self._bool_btn_false_explanation = bool_btn_false_explanation

        @event(self._bool_btn_true, 'Released')
        @event(self._bool_btn_false, 'Released')
        def _bool_btn_event(button, state):
            if button == self._bool_btn_true:
                if self._bool_callback:
                    if self._bool_passthru:
                        self._bool_callback(self, True, self._bool_passthru)
                    else:
                        self._bool_callback(self, True)

                    if self._bool_feedback_btn:
                        self._bool_feedback_btn.SetText(self._bool_true_text)

            elif button == self._bool_btn_false:
                if self._bool_callback:
                    if self._bool_passthru:
                        self._bool_callback(self, False, self._bool_passthru)
                    else:
                        self._bool_callback(self, False)

                    if self._bool_feedback_btn:
                        self._bool_feedback_btn.SetText(self._bool_false_text)

            button.Host.HidePopup(self._bool_popup_name)

        if self._bool_btn_cancel:
            @event(self._bool_btn_cancel, 'Released')
            def _bool_btn_cancelEvent(button, state):
                _bool_btn_event(button, state)

    def get_boolean(self,
                    callback=None,
                    # function - should take 2 params, the UserInput instance and the value the user submitted
                    feedback_btn=None,
                    passthru=None,  # any object that you want to also come thru the callback
                    message=None,
                    long_message=None,
                    true_message=None,
                    false_message=None,
                    true_text=None,
                    false_text=None,
                    ):
        self._bool_callback = callback
        self._bool_passthru = passthru
        self._bool_true_text = true_text
        self._bool_false_text = false_text
        self._bool_feedback_btn = feedback_btn

        if message:
            self._bool_btn_message.SetText(message)
        else:
            self._bool_btn_message.SetText('Are you sure?')

        if true_text:
            self._bool_btn_true.SetText(true_text)
        else:
            self._bool_btn_true.SetText('Yes')

        if false_text:
            self._bool_btn_false.SetText(false_text)
        else:
            self._bool_btn_false.SetText('No')

        if long_message:
            self._bool_btn_long_message.SetText(long_message)
        else:
            self._bool_btn_long_message.SetText('')

        if true_message:
            self._bool_btn_true_explaination.SetText(true_message)
        else:
            self._bool_btn_true_explaination.SetText('')

        if false_message:
            self._bool_btn_false_explanation.SetText(false_message)
        else:
            self._bool_btn_false_explanation.SetText('')

        self._bool_btn_true.Host.ShowPopup(self._bool_popup_name)


class DirectoryNavigationClass:
    def __init__(self,
                 lblCurrentDirectory=None,
                 btnScrollUp=None,
                 btnScrollDown=None,
                 lvlScrollFeedback=None,
                 lblScrollText=None,
                 btnNavUp=None,
                 limitStringLen=25,
                 lblMessage=None,
                 ):

        self._lblMessage = lblMessage
        self._limitStringLen = limitStringLen
        self._btnNavUp = btnNavUp
        self._lblCurrentDirectory = lblCurrentDirectory

        self._table = ScrollingTable()
        self._table.set_table_header_order(['entry', 'folderIcon'])
        if btnScrollUp is not None:
            self._table.register_scroll_up_button(btnScrollUp)
            btnScrollUp._repeatTime = 0.1
            btnScrollUp._holdTime = 0.2

            @event(btnScrollUp, ['Pressed', 'Repeated'])
            def btnScrollUpEvent(button, state):
                print('btnScrollUpEvent', state)
                self._table.scroll_up()

        if btnScrollDown is not None:
            self._table.register_scroll_down_button(btnScrollDown)
            btnScrollDown._repeatTime = 0.1
            btnScrollDown._holdTime = 0.2

            @event(btnScrollDown, ['Pressed', 'Repeated'])
            def btnScrollDownEvent(button, state):
                self._table.scroll_down()

        if btnNavUp is not None:
            @event(btnNavUp, 'Released')
            def btnNavUpEvent(button, state):
                self.NavigateUp()

        if lvlScrollFeedback is not None:
            self._table.register_scroll_updown_level(lvlScrollFeedback)

        if lblScrollText is not None:
            self._table.register_scroll_updown_label(lblScrollText)

        self._data = {
            # [
            # '/rootfile1',
            # '/rootfile2',
            # '/rootFolder3/file3a',
            # '/rootFolder3/file3b',
            # '/rootFolder3/folder3c/file3c1',
            # '/rootFolder3/folder3c/file3c2',
            # ]
        }
        self._currentDirectory = '/'

        self._waitUpdateTable = Wait(0.1, self._UpdateTable)
        self._waitUpdateTable.Cancel()

        self._table.CellTapped = self._CellTapped
        self._fileSelectedCallback = None

        self._table.CellHeld = self._CellHeld
        self._fileHeldCallback = None

        self._allowChangeDirectory = True
        self._allowMakeNewFile = True
        self._allowMakeNewFolder = True
        self._showCurrentDirectory = True
        self._allowDelete = True

        self._directoryLock = '/'  # dont allow the user to go higher than this dir
        self._showFiles = True

    def SetShowFiles(self, state):
        self._showFiles = state
        self._UpdateTable()

    def SetCurrentDirTextLen(self, length):
        length = int(length)
        self._limitStringLen = length

    def SetDirectoryLock(self, dir):
        self._directoryLock = dir
        self.SetCurrentDirectory(dir)

    def SetCurrentDirectory(self, dir):
        self._currentDirectory = dir
        self._UpdateTable()

    def RegisterRow(self, rowNumber, btnIcon, btnSelection):
        if btnIcon._holdTime is None:
            btnIcon._holdTime = 1
        self._table.register_row_buttons(rowNumber, btnSelection, btnIcon)

    def NavigateUp(self):
        if self._currentDirectory != '/':
            dropDir = self._currentDirectory.split('/')[-2] + '/'
            self._currentDirectory = self._currentDirectory.replace(dropDir, '')
            self._waitUpdateTable.Restart()

    def UpdateData(self, newData=None):
        print('UpdateData(newData={})'.format(newData))
        if newData == None:
            newData = File.ListDirWithSub()
        self._data = newData
        self._UpdateTable()

    def _CurrentDirIsValid(self):
        if not self._currentDirectory.endswith('/'):
            return False

        for item in self._data:
            if self._currentDirectory in item:
                return True

        return False

    def _UpdateTable(self):
        print('DirectoryNavigationClass._UpdateTable()')
        try:
            # Verify the self._currentDirectory is valid
            print('_UpdateTable self._currentDirectory=', self._currentDirectory)
            print('_UpdateTable self._directoryLock=', self._directoryLock)
            if self._directoryLock not in self._currentDirectory:
                self._currentDirectory = self._directoryLock

            if not self._CurrentDirIsValid():
                self._currentDirectory = self._directoryLock

            print('_UpdateTable self._allowChangeDirectory=', self._allowChangeDirectory)
            print('_UpdateTable self._btnNavUp.Visible=', self._btnNavUp.Visible)
            print('_UpdateTable self._btnNavUp=', self._btnNavUp)

            if self._allowChangeDirectory is True:
                if self._currentDirectory == self._directoryLock:
                    if self._btnNavUp.Visible is True:
                        print('self._btnNavUp.SetVisible(False)')
                        self._btnNavUp.SetVisible(False)
                else:
                    if self._btnNavUp.Visible is False:
                        print('self._btnNavUp.SetVisible(True)')
                        self._btnNavUp.SetVisible(True)
            else:
                if self._btnNavUp.Visible is True:
                    print('else self._btnNavUp.SetVisible(False)')
                    self._btnNavUp.SetVisible(False)

            print('_UpdateTable self._lblCurrentDirectory=', self._lblCurrentDirectory)
            print('_UpdateTable self._showCurrentDirectory=', self._showCurrentDirectory)
            if self._showCurrentDirectory is True:
                if self._lblCurrentDirectory.Visible is False:
                    print('self._lblCurrentDirectory.SetVisible(True)')
                    self._lblCurrentDirectory.SetVisible(True)
            else:
                if self._lblCurrentDirectory.Visible is True:
                    print('self._lblCurrentDirectory.SetVisible(False)')
                    self._lblCurrentDirectory.SetVisible(False)

            # Update the table with data
            self._table.freeze(True)

            print('_UpdateTable self._data=', self._data)
            if self._data is not None:
                # Add missing data
                currentData = []
                for item in self._data:
                    print('item=', item)
                    # Determine if the item is a folder or file
                    if item.startswith(self._currentDirectory):  # only deal with items in the current directory
                        print('item.startswith(self._currentDirectory)')
                        if self.IsInCurrentDirectory(item):
                            print('self.IsInCurrentDirectory(item)')
                            itemMinusCurrent = item[len(self._currentDirectory):]
                            if itemMinusCurrent is not '':
                                print('itemMinusCurrent is not ""')

                                if self.IsFile(item):
                                    folderIcon = ' '
                                    if not self._showFiles:
                                        continue

                                elif self.IsDirectory(item):
                                    folderIcon = '\xb1'
                                    itemMinusCurrent = itemMinusCurrent[
                                                       :-1]  # chop off the extra '/' at the end of directories

                                else:
                                    folderIcon = '?'

                                data = {'entry': str(itemMinusCurrent), 'folderIcon': folderIcon, }
                                if not self._table.has_row(data):
                                    self._table.add_new_row_data(data)
                                currentData.append(data)

                # remove leftover data
                print('_UpdateTable currentData=', currentData)
                print('_UpdateTable self._table.get_row_data()', self._table.get_row_data())
                for row in self._table.get_row_data():
                    if row not in currentData:
                        self._table.delete_row(row)

                # Sort with the folders at the top
                self._table.sort_by_column_list([1, 0], reverse=True)

                self._table.freeze(False)

            # Update the current directory label
            if self._lblCurrentDirectory is not None:
                if self._data is not None:
                    self._lblCurrentDirectory.SetText(self._currentDirectory, limitLen=self._limitStringLen,
                                                      elipses=True, justify='Right')
                else:
                    self._lblCurrentDirectory.SetText('<No Data>')

        except Exception as e:
            print('Exeption DirectoryNavigationClass._UpdateTable\n', e)
            print('item=', item)

    def IsFile(self, filepath):
        print('IsFile(filepath={})'.format(filepath))
        name = filepath.split('/')[-1]
        if name == '':
            print('IsFile return False')
            return False

        for item in self._data:
            if name in item:
                if name == item.split('/')[-1]:
                    print('IsFile return True')
                    return True

        print('IsFile return False')
        return False

    def IsDirectory(self, path):
        print('IsDirectory(path={})'.format(path))
        # path may end in '/' or may not
        # examples path='TEST1026', path='TEST1026/', path='image.png'(return False)
        for item in self._data:
            if item.endswith('/'):
                # item is a directory
                if item.endswith(path):
                    print('IsDirectory return True')
                    return True
                else:
                    name = path.split('/')[-1]
                    if name == item.split('/')[-2]:
                        # '/Farm_Network_Profiles/TEST1026/'.split('/') = ['', 'Farm_Network_Profiles', 'TEST1026', '']
                        print('IsDirectory return True')
                        return True

        print('IsDirectory return False')
        return False

    def IsInCurrentDirectory(self, filepath):
        # Return true if the item is in the current directory
        # Return false if it is in a super/sub directory
        print('IsInCurrentDirectory filepath=', filepath)

        if filepath.startswith(self._currentDirectory):
            pathMinusCurrent = filepath[len(self._currentDirectory):]
            print('IsInCurrentDirectory pathMinusCurrent=', pathMinusCurrent)
            print('self.IsDirectory({})='.format(filepath), self.IsDirectory(filepath))
            print('self.IsFile({})='.format(filepath), self.IsFile(filepath))

            if self.IsDirectory(filepath):
                print('IsInCurrentDirectory IsDirectory')
                print("len(pathMinusCurrent.split('/'))=", len(pathMinusCurrent.split('/')))
                if len(pathMinusCurrent.split('/')) <= 2:
                    return True
                else:
                    return False
            elif self.IsFile(filepath):
                print('IsInCurrentDirectory IsFile')
                print("len(pathMinusCurrent.split('/'))=", len(pathMinusCurrent.split('/')))
                if len(pathMinusCurrent.split('/')) == 1:
                    return True
                else:
                    return False

        return False

    def GetType(self, name):
        if self.IsFile(name):
            return 'File'
        elif self.IsDirectory(name):
            return 'Directory'

    def ChangeDirectory(self, newDir):
        if not newDir.endswith('/'):
            newDir += '/'

        self._currentDirectory = newDir

    def _CellTapped(self, table, cell):
        print(
            'DirectoryNavigationClass._CellTapped(table={}, cell={})\nself._fileSelectedCallback={}'.format(table, cell,
                                                                                                            self._fileSelectedCallback))
        row = cell.get_row()
        value = self._table.get_cell_value(row, 0)
        path = self._currentDirectory + value
        if value == '':
            return

        print('value=', value)
        print('path=', path)
        if self.IsDirectory(path):
            self.ChangeDirectory(path + '/')
            self._waitUpdateTable.Restart()

        elif self.IsFile(path):
            if callable(self._fileSelectedCallback):
                self._fileSelectedCallback(self, self._currentDirectory + value)

    def _CellHeld(self, table, cell):
        # This is used for providing the user with more options like: Deleting a file/folder, Creating a new file/folder...
        print('DirectoryNavigationClass._CellHeld(table={}, cell={})\nself._fileHeldCallback={}'.format(table, cell,
                                                                                                        self._fileHeldCallback))
        value = cell.get_value()
        path = self._currentDirectory + value
        # path might be a filepath or directory
        if callable(self._fileHeldCallback):
            self._fileHeldCallback(self, path)

    def GetDir(self):
        return self._currentDirectory

    @property
    def FileSelected(self):
        return self._fileSelectedCallback

    @FileSelected.setter
    def FileSelected(self, func):
        # func should be a function that accetps this dir nav object itself and the selected value
        self._fileSelectedCallback = func

    @property
    def FileHeld(self):
        return self._fileHeldCallback

    @FileHeld.setter
    def FileHeld(self, func):
        # func should be a function that accetps this dir nav object itself and the selected value
        self._fileHeldCallback = func

    def UpdateMessage(self, msg):
        if self._lblMessage is not None:
            self._lblMessage.SetText(msg)

    def AllowChangeDirectory(self, state):
        self._allowChangeDirectory = state
        self._UpdateTable()

    def GetAllowChangeDirectory(self):
        return self._allowChangeDirectory

    def AllowMakeNewFile(self, state=None):
        if state == None:
            return self._allowMakeNewFile
        else:
            self._allowMakeNewFile = state
            self._UpdateTable()

    def AllowMakeNewFolder(self, state=None):
        if state == None:
            return self._allowMakeNewFolder
        else:
            self._allowMakeNewFolder = state
            self._UpdateTable()

    def AllowDelete(self, state=None):
        if state == None:
            return self._allowDelete
        else:
            self._allowDelete = state
            self._UpdateTable()

    def ShowCurrentDirectory(self, state=None):
        if state == None:
            return self._showCurrentDirectory
        else:
            self._showCurrentDirectory = state
            self._UpdateTable()


def GetDatetimeKwargs(dt):
    '''
    This converts a datetime.datetime object to a dict.
    This is useful for saving a datetime.datetime object as a json string
    :param dt: datetime.datetime
    :return: dict
    '''
    if dt is None:
        return None

    d = {'year': dt.year,
         'month': dt.month,
         'day': dt.day,
         'hour': dt.hour,
         'minute': dt.minute,
         'second': dt.second,
         'microsecond': dt.microsecond,
         }
    return d
