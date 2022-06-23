# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys
import traceback
from itertools import islice
from datetime import datetime
import csv

from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QApplication, QWidget, QTableWidgetItem
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader

import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_qtagg import (
        FigureCanvasQTAgg as FigureCanvas,
        NavigationToolbar2QT as NavigationToolbar)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

class Dialog(QWidget):
    def __init__(self):
        super(Dialog, self).__init__()
        self.load_ui()
        self.ui.CloseButton.clicked.connect(self.closeWindow)
        self.setPlot()

    def load_ui(self):
        loader = QUiLoader()
        path = os.fspath(Path(__file__).resolve().parent / "dialog.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

    def setPlot(self):
        fig = plt.figure(2)
        self.canvas = FigureCanvas(fig)
        self.ui.MPLVL.addWidget(self.canvas)
        self.canvas.draw()
        self.toolbar = NavigationToolbar(self.canvas, self, coordinates=True)
        self.ui.MPLVL.addWidget(self.toolbar)

    def closeWindow(self):
        plt.close(plt.figure(2))
        self.close()

    def clearLayout(self, layout):
        for i in reversed(range(layout.count())): 
            layout.itemAt(i).widget().setParent(None)

class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.load_ui()
        self.setBindings()
        self.setPlot()
        self.workingDirectory = os.path.expanduser('~')
        self.dialog = None

    def load_ui(self):
        loader = QUiLoader()
        path = os.fspath(Path(__file__).resolve().parent / "main.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

    def setBindings(self):
        self.ui.LoadDataButton.clicked.connect(self.loadData)
        self.ui.AnalyseButton.clicked.connect(self.analyseCurrentFile)
        self.ui.AnalyseButton.setEnabled(False)
        self.ui.SaveFileButton.clicked.connect(self.saveFile)

        self.ui.PCPS_RButton.clicked.connect(lambda: self.plot(self.CVInsight_output, self.CVInsight_events, self.canvas, variable='PCPS'))
        self.ui.PS_RButton.clicked.connect(lambda: self.plot(self.CVInsight_output, self.CVInsight_events, self.canvas, variable='PS'))
        self.ui.HR_RButton.clicked.connect(lambda: self.plot(self.CVInsight_output, self.CVInsight_events, self.canvas, variable='HR'))
        self.ui.SPO2_RButton.clicked.connect(lambda: self.plot(self.CVInsight_output, self.CVInsight_events, self.canvas, variable='SPO2'))

        self.ui.PCPS_RButton.setEnabled(False)
        self.ui.PS_RButton.setEnabled(False)
        self.ui.HR_RButton.setEnabled(False)
        self.ui.SPO2_RButton.setEnabled(False)

        self.ui.OpenPlotButton.clicked.connect(self.showPlot)
        self.ui.OpenPlotButton.setEnabled(False)

    def setPlot(self):
        fig = plt.figure(1)
        self.canvas = FigureCanvas(fig)
        self.ui.MPLVL.addWidget(self.canvas)
        self.canvas.draw()
        self.toolbar = NavigationToolbar(self.canvas, self, coordinates=True)
        self.ui.MPLVL.addWidget(self.toolbar)

    def loadData(self):
        # Disable buttons and return to default selection
        self.ui.AnalyseButton.setEnabled(False)
        self.ui.PCPS_RButton.setChecked(True)
        self.ui.PCPS_RButton.setEnabled(False)
        self.ui.PS_RButton.setEnabled(False)
        self.ui.HR_RButton.setEnabled(False)
        self.ui.SPO2_RButton.setEnabled(False)
        self.ui.OpenPlotButton.setEnabled(False)

        # Select patient directory containing CVInsight files
        prev = str(self.ui.DirectoryLineEdit.text())
        data_directory = str(QtWidgets.QFileDialog.getExistingDirectory(self, 'Open Data Directory', self.workingDirectory))
        self.ui.DirectoryLineEdit.setText(data_directory)

        if str(self.ui.DirectoryLineEdit.text()) == '':
            self.ui.DirectoryLabel.setText('No data loaded.')
        else:
            # Load files and set working directory
            self.workingDirectory = data_directory.rsplit('/',1)[0]
            self.ui.AnalyseButton.setEnabled(True)

            self.currentID = data_directory.split('/')[-1]
            data_files = os.listdir(data_directory)
            try:
                for file in data_files:
                    if 'data.txt' in file:
                        data_file = file
                    elif 'eventlog.txt' in file:
                        log_file = file

                # Read CVInsight files
                self.CVInsight_output = self.read_CVInsight_output(data_directory + '/' + data_file)
                self.CVInsight_events = self.read_CVInsight_eventlog(data_directory + '/' + log_file)

                # Create index for CVInsight_events
                for t, timed_event in enumerate(self.CVInsight_events['Event']):
                    try:
                        self.CVInsight_events['Index'].append(self.CVInsight_output['Timestamp'].index(self.CVInsight_events['Timestamps'][t]))
                    except Exception as e:
                        self.CVInsight_events['Index'].append(np.nan)
                    # print('    | ', self.CVInsight_events['Timestamps'][t], '\t', self.CVInsight_events['Event'][t], '\t', self.CVInsight_events['Index'][t])

                # Find dialysis start and end times
                dialysis_start_time = ""
                dialysis_end_time = ""
                for t, timed_event in enumerate(self.CVInsight_events['Event']):
                    event = timed_event.upper()
                    if (('HD' in event) or ('DIALYSIS' in event)) and ('START' in event):
                        dialysis_start_time = self.CVInsight_events['Timestamps'][t]
                    elif (('HD' in event) or ('DIALYSIS' in event)) and (('COMPLETE' in event) or ('END' in event)):
                        dialysis_end_time   = self.CVInsight_events['Timestamps'][t]
                
                if dialysis_start_time == "":
                    dialysis_start_time = self.CVInsight_events['Timestamps'][0]

                if dialysis_end_time == "":
                    dialysis_end_time = self.CVInsight_events['Timestamps'][-1]
                
                dialysis_start_time_index = self.CVInsight_output['Timestamp'].index(dialysis_start_time)
                dialysis_end_time_index = self.CVInsight_output['Timestamp'].index(dialysis_end_time)

                self.CVInsight_events['dialysis_start_time'] = dialysis_start_time
                self.CVInsight_events['dialysis_end_time'] = dialysis_end_time
                self.CVInsight_output['dialysis_start_time_index'] = dialysis_start_time_index
                self.CVInsight_output['dialysis_end_time_index'] = dialysis_end_time_index

                # Plot PCPS By Default
                self.plot(self.CVInsight_output, self.CVInsight_events, self.canvas, variable='PCPS')

                # Enable Radio Buttons
                self.ui.PCPS_RButton.setEnabled(True)
                self.ui.PS_RButton.setEnabled(True)
                self.ui.HR_RButton.setEnabled(True)
                self.ui.SPO2_RButton.setEnabled(True)

                self.ui.OpenPlotButton.setEnabled(True)

                self.ui.DirectoryLabel.setText(data_directory + '<br>└─ ' \
                    + data_file + '<br>└─ ' \
                    + log_file)

            except Exception as e:
                self.ui.DirectoryLabel.setText('Error reading *_data.txt and *_eventlog.txt from' + data_directory)
                print(traceback.format_exc())

    def analyseCurrentFile(self):
        patient_id = self.currentID

        # CVInsight data records are in 1 second intervals.
        # Thus, the index of the arrays correspond to the time in seconds.

        # Calculate HD time
        dialysis_start_time = self.CVInsight_events['dialysis_start_time']
        dialysis_end_time = self.CVInsight_events['dialysis_end_time']
        dialysis_start_time_index = self.CVInsight_output['dialysis_start_time_index']
        dialysis_end_time_index = self.CVInsight_output['dialysis_end_time_index']

        HD_time_seconds = dialysis_end_time_index - dialysis_start_time_index
        HD_time = HD_time_seconds/60.0

        # Calculate pulse strength mean, std, max, min
        ps_mean = np.nanmean(self.CVInsight_output['Pulse Strength'][dialysis_start_time_index:dialysis_end_time_index+1])
        ps_max  = np.nanmax (self.CVInsight_output['Pulse Strength'][dialysis_start_time_index:dialysis_end_time_index+1])
        ps_min  = np.nanmin (self.CVInsight_output['Pulse Strength'][dialysis_start_time_index:dialysis_end_time_index+1])
        ps_std  = np.nanstd (self.CVInsight_output['Pulse Strength'][dialysis_start_time_index:dialysis_end_time_index+1])

        # Calculate PCPS ≤ -10 ... -60
        pcps_l10 = 0
        pcps_l20 = 0
        pcps_l30 = 0
        pcps_l40 = 0
        pcps_l50 = 0
        pcps_l60 = 0

        for val in self.CVInsight_output['% Change Pulse Strength'][dialysis_start_time_index:dialysis_end_time_index+1]:
            if ~np.isnan(val):
                if val <= -10: pcps_l10 += 1
                if val <= -20: pcps_l20 += 1
                if val <= -30: pcps_l30 += 1
                if val <= -40: pcps_l40 += 1
                if val <= -50: pcps_l50 += 1
                if val <= -60: pcps_l60 += 1

        pcps_l10 = pcps_l10/float(HD_time_seconds) * 100
        pcps_l20 = pcps_l20/float(HD_time_seconds) * 100
        pcps_l30 = pcps_l30/float(HD_time_seconds) * 100
        pcps_l40 = pcps_l40/float(HD_time_seconds) * 100
        pcps_l50 = pcps_l50/float(HD_time_seconds) * 100
        pcps_l60 = pcps_l60/float(HD_time_seconds) * 100

        # Calculate time to min pulse strength
        tt_min_ps = np.nanargmin(self.CVInsight_output['Pulse Strength'][dialysis_start_time_index:dialysis_end_time_index+1]) + 1
        tt_min_ps = tt_min_ps/60.0

        # Calculate time to PCPS ≤ -10 ... -60
        tt_pcps_l10 = np.nan
        tt_pcps_l20 = np.nan
        tt_pcps_l30 = np.nan
        tt_pcps_l40 = np.nan
        tt_pcps_l50 = np.nan
        tt_pcps_l60 = np.nan
        for i, val in enumerate(self.CVInsight_output['% Change Pulse Strength'][dialysis_start_time_index:dialysis_end_time_index+1]):
            if ~np.isnan(val):
                if val <= -10: tt_pcps_l10 = (i+1)/60.0
                if val <= -20: tt_pcps_l20 = (i+1)/60.0
                if val <= -30: tt_pcps_l30 = (i+1)/60.0
                if val <= -40: tt_pcps_l40 = (i+1)/60.0
                if val <= -50: tt_pcps_l50 = (i+1)/60.0
                if val <= -60: tt_pcps_l60 = (i+1)/60.0

        # Calculate heart rate mean, std, max, min
        hr_mean = np.nanmean(self.CVInsight_output['Pulse Rate (BPM)'][dialysis_start_time_index:dialysis_end_time_index+1])
        hr_max  = np.nanmax (self.CVInsight_output['Pulse Rate (BPM)'][dialysis_start_time_index:dialysis_end_time_index+1])
        hr_min  = np.nanmin (self.CVInsight_output['Pulse Rate (BPM)'][dialysis_start_time_index:dialysis_end_time_index+1])
        hr_std  = np.nanstd (self.CVInsight_output['Pulse Rate (BPM)'][dialysis_start_time_index:dialysis_end_time_index+1])

        # Calculate time to min heart rate
        tt_min_hr = np.nanargmin(self.CVInsight_output['Pulse Rate (BPM)'][dialysis_start_time_index:dialysis_end_time_index+1]) + 1
        tt_min_hr = tt_min_hr/60.0

        # Calculate time to max heart rate
        tt_max_hr = np.nanargmax(self.CVInsight_output['Pulse Rate (BPM)'][dialysis_start_time_index:dialysis_end_time_index+1]) + 1
        tt_max_hr = tt_max_hr/60.0

        # Calculate SpO2
        spo2_min = np.nanmin(self.CVInsight_output['% SpO2'][dialysis_start_time_index:dialysis_end_time_index+1])

        # Calculate time to min SpO2
        tt_min_spo2 = np.nanargmin(self.CVInsight_output['% SpO2'][dialysis_start_time_index:dialysis_end_time_index+1])
        tt_min_spo2 = tt_min_spo2/60.0

        # Calculate area under PCPS curve
        auc = 0
        auc_negonly = 0
        auc_posonly = 0

        for val in self.CVInsight_output['% Change Pulse Strength'][dialysis_start_time_index:dialysis_end_time_index+1]:
            if ~np.isnan(val):
                auc += val
                if val < 0:
                    auc_negonly += val
                elif val > 0:
                    auc_posonly += val

        # Populate table
        table = self.ui.ResultsTable
        currentRowPosition = table.rowCount()
        table.insertRow(currentRowPosition)

        table.setItem(currentRowPosition, 0, QTableWidgetItem(str(self.currentID)))
        table.setItem(currentRowPosition, 1, QTableWidgetItem(str(HD_time)))
        table.setItem(currentRowPosition, 2, QTableWidgetItem(str(ps_mean)))
        table.setItem(currentRowPosition, 3, QTableWidgetItem(str(ps_std)))
        table.setItem(currentRowPosition, 4, QTableWidgetItem(str(ps_min)))
        table.setItem(currentRowPosition, 5, QTableWidgetItem(str(ps_max)))
        table.setItem(currentRowPosition, 6, QTableWidgetItem(str(pcps_l10)))
        table.setItem(currentRowPosition, 7, QTableWidgetItem(str(pcps_l20)))
        table.setItem(currentRowPosition, 8, QTableWidgetItem(str(pcps_l30)))
        table.setItem(currentRowPosition, 9, QTableWidgetItem(str(pcps_l40)))
        table.setItem(currentRowPosition, 10, QTableWidgetItem(str(pcps_l50)))
        table.setItem(currentRowPosition, 11, QTableWidgetItem(str(pcps_l60)))
        table.setItem(currentRowPosition, 12, QTableWidgetItem(str(tt_min_ps)))
        table.setItem(currentRowPosition, 13, QTableWidgetItem(str(tt_pcps_l10)))
        table.setItem(currentRowPosition, 14, QTableWidgetItem(str(tt_pcps_l20)))
        table.setItem(currentRowPosition, 15, QTableWidgetItem(str(tt_pcps_l30)))
        table.setItem(currentRowPosition, 16, QTableWidgetItem(str(tt_pcps_l40)))
        table.setItem(currentRowPosition, 17, QTableWidgetItem(str(tt_pcps_l50)))
        table.setItem(currentRowPosition, 18, QTableWidgetItem(str(tt_pcps_l60)))
        table.setItem(currentRowPosition, 19, QTableWidgetItem(str(hr_mean)))
        table.setItem(currentRowPosition, 20, QTableWidgetItem(str(hr_std)))
        table.setItem(currentRowPosition, 21, QTableWidgetItem(str(hr_min)))
        table.setItem(currentRowPosition, 22, QTableWidgetItem(str(hr_max)))
        table.setItem(currentRowPosition, 23, QTableWidgetItem(str(tt_min_hr)))
        table.setItem(currentRowPosition, 24, QTableWidgetItem(str(tt_max_hr)))
        table.setItem(currentRowPosition, 25, QTableWidgetItem(str(spo2_min)))
        table.setItem(currentRowPosition, 26, QTableWidgetItem(str(tt_min_spo2)))
        table.setItem(currentRowPosition, 27, QTableWidgetItem(str(auc)))
        table.setItem(currentRowPosition, 28, QTableWidgetItem(str(auc_negonly)))
        table.setItem(currentRowPosition, 29, QTableWidgetItem(str(auc_posonly)))

    def saveFile(self):
        path, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save CSV', self.workingDirectory, 'CSV (*.csv)')
        if ok:
            columns = range(self.ui.ResultsTable.columnCount())
            header = [self.ui.ResultsTable.horizontalHeaderItem(column).text()
                      for column in columns]
            with open(path, 'w') as csvfile:
                writer = csv.writer(
                    csvfile, dialect='excel', lineterminator='\n')
                writer.writerow(header)
                for row in range(self.ui.ResultsTable.rowCount()):
                    writer.writerow(
                        self.ui.ResultsTable.item(row, column).text()
                        for column in columns)
            self.ui.SaveFileLabel.setText('Analysis saved to ' + path)
        else:
            self.ui.SaveFileLabel.setText('Analysis not saved.')

    def showPlot(self):
        if self.dialog is None:
            self.dialog = Dialog()
            self.dialog.show()
            if self.ui.PCPS_RButton.isChecked():
                plot_var = 'PCPS'
            elif self.ui.PS_RButton.isChecked():
                plot_var = 'PS'
            elif self.ui.HR_RButton.isChecked():
                plot_var = 'HR'
            elif self.ui.SPO2_RButton.isChecked():
                plot_var = 'SPO2'

            self.plot(self.CVInsight_output, self.CVInsight_events, canvas=self.dialog.canvas, variable=plot_var, fignum=2)
        else:
            self.dialog.close()
            self.dialog = None
            self.showPlot()

    def plot(self, CVInsight_output, CVInsight_events, canvas, variable='PCPS', fignum=1):

        if variable == 'PCPS':
            plot_var = '% Change Pulse Strength'
        elif variable == 'PS':
            plot_var = 'Pulse Strength'
        elif variable == 'HR':
            plot_var = 'Pulse Rate (BPM)'
        elif variable == 'SPO2':
            plot_var = '% SpO2'
        else:
            plot_var = '% Change Pulse Strength'

        dialysis_start_time = CVInsight_events['dialysis_start_time']
        dialysis_end_time = CVInsight_events['dialysis_end_time']
        dialysis_start_time_index = CVInsight_output['dialysis_start_time_index']
        dialysis_end_time_index = CVInsight_output['dialysis_end_time_index']

        plt.figure(fignum).clear()
        fig = plt.figure(fignum)
        ax = fig.add_subplot(111)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

        plt.plot_date(CVInsight_output['Timestamp'], CVInsight_output[plot_var], ls='-', marker='')
        fig.autofmt_xdate(rotation=30)
        fig.tight_layout()

        plt.fill_between(CVInsight_output['Timestamp'][dialysis_start_time_index:dialysis_end_time_index+1], CVInsight_output[plot_var][dialysis_start_time_index:dialysis_end_time_index+1], alpha=0.5)

        indx   = [CVInsight_output['Timestamp'][e] for e in CVInsight_events['Index'] if ~np.isnan(e)]
        text   = [CVInsight_events['Event'][e] for e, E in enumerate(CVInsight_events['Index']) if ~np.isnan(E)]

        ymin = min(CVInsight_output[plot_var])
        ymax = max(CVInsight_output[plot_var])
        plt.vlines(x=indx, ymin=ymin, ymax=ymax, color = 'red')

        for t, timed_event in enumerate(text):
            plt.text(indx[t], (ymax+ymin)/2, timed_event, rotation=90, verticalalignment='center')

        plt.title(self.currentID)
        plt.tight_layout()

        canvas.draw()

    def read_CVInsight_output(self, datapath):
        datafile = open(datapath, 'r')

        data = {}
        data['Timestamp'] = []
        data['Pulse Rate (BPM)'] = []
        data['% SpO2'] = []
        data['Pulse Rate (Hz)'] = []
        data['% Change Pulse Rate'] = []
        data['Pulse Strength'] = []
        data['% Change Pulse Strength'] = []

        datafile_iterable = iter(enumerate(datafile))

        for l, line in datafile_iterable:
            if l < 7:
                if l == 0:
                    data['Start of Monitoring'] = line.rstrip()
                if l > 2:
                    var = line.split(' = ')[0].rstrip()
                    val = line.split(' = ')[1].rstrip()
                    data[var] = val
            elif l > 10:
                if 'Start of Monitoring' in line:
                    # This means acquisition was reset and continued.
                    # Skip ahead 9 lines.
                    next(islice(datafile_iterable, 9, 9), None)
                else:
                    vals = line.rstrip().split('\t')
                    try:
                        if np.size(vals) == 11:
                            dt = vals[0].split(' ')
                            d  = dt[0].split('/')
                            t  = dt[1].split(':')
                            z  = dt[2]
                            if ('PM' in z) and int(t[0]) != 12: 
                                t[0] = str((int(t[0]) + 12)%24)
                            elif ('AM' in z) and int(t[0]) == 12:
                                t[0] = str(0)
                            data['Timestamp'].append(datetime(int(d[2]), int(d[0]), int(d[1]), int(t[0]), int(t[1]), int(t[2])))

                            data['Pulse Rate (BPM)'].append(float(vals[1]))
                            data['% SpO2'].append(float(vals[2]))
                            data['Pulse Rate (Hz)'].append(float(vals[3]))
                            data['% Change Pulse Rate'].append(float(vals[4]))
                            data['Pulse Strength'].append(float(vals[5]))
                            data['% Change Pulse Strength'].append((float(vals[5])-float(data['Baseline Pulse Strength']))/float(data['Baseline Pulse Strength'])*100)
                    except Exception as e:
                        print('    | ', line.rstrip(), ' ; error: ', e)
            else:
                continue
        
        # Correct clipped non-sensical data points 
        for i, val in enumerate(data['% SpO2']):
            if val > 100: data['% SpO2'][i] = np.nan

        for i, val in enumerate(data['Pulse Rate (BPM)']):
            # limits here are based on lowest and highest HR ever recorded
            if val > 480: data['Pulse Rate (BPM)'][i] = np.nan
            if val < 27:  data['Pulse Rate (BPM)'][i] = np.nan

        datafile.close()
        return data

    def read_CVInsight_eventlog(self, datapath):
        datafile = open(datapath, 'r')
        
        data = {}
        data['Timestamps'] = []
        data['Event'] = []
        data['Index'] = []
        
        for l, line in enumerate(datafile):
            vals = line.rstrip().split('\t')
            try:
                if np.size(vals) == 2:
                    dt = vals[0].split(' ')
                    d  = dt[0].split('/')
                    t  = dt[1].split(':')
                    z  = dt[2]
                    if ('PM' in z) and int(t[0]) != 12: 
                        t[0] = str((int(t[0]) + 12)%24)
                    elif ('AM' in z) and int(t[0]) == 12:
                        t[0] = str(0)
                    data['Timestamps'].append(datetime(int(d[2]), int(d[0]), int(d[1]), int(t[0]), int(t[1]), int(t[2])))
                    data['Event'].append(vals[1])
            except Exception as e:
                print('    | ', line.rstrip(), ' ; error: ', e)
                
        datafile.close()
        return data

if __name__ == "__main__":
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
