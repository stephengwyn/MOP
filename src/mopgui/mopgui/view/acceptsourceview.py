__author__ = "David Rusk <drusk@uvic.ca>"

import wx


class AcceptSourceDialog(wx.Dialog):
    TITLE = "Accept Source"
    MINOR_PLANET_NUMBER = "Minor planet number: "
    PROVISIONAL_NAME = "Provisional name: "
    DISCOVERY_ASTERISK = "Discovery asterisk: "
    NOTE1 = "Note 1: "
    NOTE2 = "Note 2: "
    DATE_OF_OBS = "Date of observation: "
    RA = "Right ascension: "
    DEC = "Declination: "
    OBS_MAG = "Observed magnitude: "
    BAND = "Band: "
    OBSERVATORY_CODE = "Observatory code: "
    OK_BTN = "Ok"
    CANCEL_BTN = "Cancel"

    def __init__(self, parent, provisional_name, date_of_obs, ra, dec,
                 note1_choices=None, note2_choices=None):
        super(AcceptSourceDialog, self).__init__(parent, title=self.TITLE)

        self.provisional_name = provisional_name
        self.date_of_obs = date_of_obs
        self.ra_str = str(ra)
        self.dec_str = str(dec)

        self.note1_choices = note1_choices if note1_choices is not None else []
        self.note2_choices = note2_choices if note2_choices is not None else []

        self._init_ui()

    def _init_ui(self):
        self.minor_planet_num_label = wx.StaticText(self, label=self.MINOR_PLANET_NUMBER)
        self.minor_planet_num_text = wx.TextCtrl(self)

        self.provisional_name_label = wx.StaticText(self, label=self.PROVISIONAL_NAME)
        self.provision_name_text = wx.StaticText(self, label=self.provisional_name)

        self.discovery_asterisk_cb = wx.CheckBox(self, label=self.DISCOVERY_ASTERISK,
                                                 style=wx.ALIGN_RIGHT)

        self.note1_label = wx.StaticText(self, label=self.NOTE1)
        self.note1_combobox = wx.ComboBox(self, choices=self.note1_choices, style=wx.CB_READONLY,
                                          name=self.NOTE1)

        self.note2_label = wx.StaticText(self, label=self.NOTE2)
        self.note2_combobox = wx.ComboBox(self, choices=self.note2_choices, style=wx.CB_READONLY,
                                          name=self.NOTE2)

        self.date_of_obs_label = wx.StaticText(self, label=self.DATE_OF_OBS)
        self.date_of_obs_text = wx.StaticText(self, label=self.date_of_obs)

        self.ra_label = wx.StaticText(self, label=self.RA)
        self.ra_text = wx.StaticText(self, label=self.ra_str)

        self.dec_label = wx.StaticText(self, label=self.DEC)
        self.dec_text = wx.StaticText(self, label=self.dec_str)

        self.obs_mag_label = wx.StaticText(self, label=self.OBS_MAG)
        self.obs_mag_text = wx.TextCtrl(self)

        self.band_label = wx.StaticText(self, label=self.BAND)
        self.band_text = wx.TextCtrl(self)

        self.observatory_code_label = wx.StaticText(self, label=self.OBSERVATORY_CODE)
        self.observatory_code_text = wx.TextCtrl(self)

        self.ok_button = wx.Button(self, label=self.OK_BTN, name=self.OK_BTN)
        self.cancel_button = wx.Button(self, label=self.CANCEL_BTN, name=self.CANCEL_BTN)

        self._do_layout()

    def _get_vertical_widget_list(self):
        return [self._create_horizontal_pair(self.minor_planet_num_label, self.minor_planet_num_text),
                self._create_horizontal_pair(self.provisional_name_label, self.provision_name_text),
                self.discovery_asterisk_cb,
                (0, 0), # blank space
                self._create_horizontal_pair(self.note1_label, self.note1_combobox),
                self._create_horizontal_pair(self.note2_label, self.note2_combobox),
                (0, 0), # blank space
                self._create_horizontal_pair(self.date_of_obs_label, self.date_of_obs_text),
                self._create_horizontal_pair(self.ra_label, self.ra_text),
                self._create_horizontal_pair(self.dec_label, self.dec_text),
                self._create_horizontal_pair(self.obs_mag_label, self.obs_mag_text),
                self._create_horizontal_pair(self.band_label, self.band_text),
                self._create_horizontal_pair(self.observatory_code_label, self.observatory_code_text),
                (0, 0)  # blank space
        ]

    def _do_layout(self):
        vsizer = wx.BoxSizer(wx.VERTICAL)
        for widget in self._get_vertical_widget_list():
            vsizer.Add(widget, proportion=0, flag=wx.ALL, border=5)

        vsizer.Add(self._create_horizontal_pair(self.ok_button, self.cancel_button,
                                                flag=wx.ALL, border=5),
                   flag=wx.ALIGN_CENTER)

        # Extra border padding
        bordersizer = wx.BoxSizer(wx.VERTICAL)
        bordersizer.Add(vsizer, flag=wx.ALL, border=20)

        self.SetSizerAndFit(bordersizer)

    def _create_horizontal_pair(self, widget1, widget2, flag=0, border=0):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(widget1, flag=flag, border=border)
        hsizer.Add(widget2, flag=flag, border=border)
        return hsizer
