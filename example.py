# Reaction-Diffusion Simulation Using Gray-Scott Model
# https://en.wikipedia.org/wiki/Reaction-diffusion_system
# http://www.labri.fr/perso/nrougier/teaching/numpy/numpy.html#
# FB - 20160130

'''
Set rows to removable
fix empty row at all times
'''

import random
import numpy as np
import threading
from qtpy import QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.console import ConsoleWidget
from gen import models, uniform

DEFAULT_PARAMS = [['Bacteria 1', (0.16, 0.08, 0.035, 0.065)],
    ['Bacteria 2', (0.14, 0.06, 0.035, 0.065)],
    ['Coral', (0.16, 0.08, 0.060, 0.062)],
    ['Fingerprint', (0.19, 0.05, 0.060, 0.062)],
    ['Spirals', (0.10, 0.10, 0.018, 0.050)],
    ['Spirals Dense', (0.12, 0.08, 0.020, 0.050)],
    ['Spirals Fast', (0.10, 0.16, 0.020, 0.050)],
    ['Unstable', (0.16, 0.08, 0.020, 0.055)],
    ['Worms 1', (0.16, 0.08, 0.050, 0.065)],
    ['Worms 2', (0.16, 0.08, 0.054, 0.063)],
    ['Zebrafish', (0.16, 0.08, 0.035, 0.060)]]

class PuffTable(pg.TableWidget):
    def __init__(self):
        pg.TableWidget.__init__(self)
        self.setEditable(True)
        self.cellChanged.connect(self.changedCell)
        self.puffs = []

    def changedCell(self, a):
        if self.item(a, 0) is None or self.item(a, 1) is None or self.item(a, 2) is None:
            return
        self.puffs[a].x = self.item(a, 0).value
        self.puffs[a].y = self.item(a, 1).value
        self.puffs[a].calcium = self.item(a, 2).value


    def addPuff(self, puff):
        self.puffs.append(puff)
        self.updateTable()

    def updateTable(self):
        data = [[p.x, p.y, p.calcium] for p in self.puffs]
        self.setData(data)
        self.setHorizontalHeaderLabels(["X", "Y", "Calcium"])

    def setPuffs(self, puffs):
        self.removeAll()
        self.puffs = puffs
        self.updateTable()

    def getPuffs(self):
        return self.puffs

    def removeAll(self):
        self.puffs = []
        self.setData([])

class Puff:
    def __init__(self, x, y, calcium=1):
        self.x = int(x)
        self.y = int(y)
        self.calcium = calcium
        self.open = False
        self.openSteps = 0

    def update(self, val):
        if self.finished():
            return
        if self.open:
            self.openSteps += 1
        if val > 30:
            self.open = False

    def finished(self):
        return not self.open and self.openSteps > 5

class MainWindow(QtWidgets.QWidget):
    sigStepCompleted = QtCore.Signal(int, object)
    sigFinished = QtCore.Signal()
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.paused = False
        self.inLoop = False
        self.movie = []

        self.imageview = pg.ImageView()
        self.imageview.view.setAutoPan(False)
        #self.imageview.setAutoRange(False)
        self.imageview.setMinimumWidth(650)
        self.console = ConsoleWidget()
        self.console.setMaximumWidth(400)
        self.optionsWidget = QtWidgets.QWidget()

        opsL = QtWidgets.QFormLayout()
        header = QtWidgets.QLabel("Diffusion Simulation")
        opsL.addRow(header)
        self.optionsWidget.setMaximumWidth(300)

        self.modelWidget = self._makeModelWidget()

        params = QtWidgets.QGroupBox("Parameters")
        paramLayout = QtWidgets.QFormLayout()
        paramCombo = QtWidgets.QComboBox()
        self.duSpin = QtWidgets.QDoubleSpinBox()
        self.dvSpin = QtWidgets.QDoubleSpinBox()
        self.fSpin = QtWidgets.QDoubleSpinBox()
        self.kSpin = QtWidgets.QDoubleSpinBox()
        self.duSpin.setDecimals(4)
        self.dvSpin.setDecimals(4)
        self.fSpin.setDecimals(4)
        self.kSpin.setDecimals(4)
        self.duSpin.setSingleStep(.001)
        self.dvSpin.setSingleStep(.001)
        self.kSpin.setSingleStep(.001)
        self.fSpin.setSingleStep(.001)

        def setValues():
            Du, Dv, F, k = paramCombo.currentData()
            self.duSpin.setValue(Du)
            self.dvSpin.setValue(Dv)
            self.fSpin.setValue(F)
            self.kSpin.setValue(k)

        paramCombo.currentIndexChanged.connect(setValues)
        for a, b in DEFAULT_PARAMS:
            paramCombo.addItem(a, b)
        paramLayout.addRow(paramCombo)
        paramLayout.addRow("Du", self.duSpin)
        paramLayout.addRow("Dv", self.dvSpin)
        paramLayout.addRow("F", self.fSpin)
        paramLayout.addRow("k", self.kSpin)
        params.setLayout(paramLayout)

        self.iterSpin = QtWidgets.QSpinBox()
        self.iterSpin.setRange(1, 30000)
        self.iterSpin.setValue(10000)
        self.refreshSpin = QtWidgets.QSpinBox()
        self.refreshSpin.setRange(2, 100)
        self.refreshSpin.setValue(30)

        self.startButton = QtWidgets.QPushButton("Start")
        self.startButton.pressed.connect(self.start)
        self.sigFinished.connect(self.finished)
        self.pauseButton = QtWidgets.QPushButton("Pause")
        self.pauseButton.pressed.connect(self.pause)
        buttonBox = QtWidgets.QWidget()
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(self.startButton)
        buttonLayout.addWidget(self.pauseButton)
        buttonBox.setLayout(buttonLayout)

        self.modelWidget = self._makeModelWidget()

        separator = QtWidgets.QWidget()
        sepLayout = QtWidgets.QHBoxLayout()
        self.infoLabel = QtWidgets.QLabel()
        sepLayout.addWidget(self.infoLabel)
        sepLayout.addStretch()
        separator.setLayout(sepLayout)

        self.lightSpin = QtWidgets.QSpinBox()
        self.lightSpin.setRange(1, 1000)
        self.lightSpin.setValue(20)

        opsL.addRow(self.modelWidget)
        opsL.addRow(params)
        opsL.addRow("Iterations", self.iterSpin)
        opsL.addRow("Refresh Rate", self.refreshSpin)
        opsL.addRow("Light Duration", self.lightSpin)
        opsL.addRow(separator)
        opsL.addRow(buttonBox)
        self.optionsWidget.setLayout(opsL)

        self.console.localNamespace.update({'self': self, 'set': self.imageview.setImage})
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.console, 0, 0)
        layout.addWidget(self.imageview, 0, 1)
        layout.addWidget(self.optionsWidget, 0, 2)
        self.setLayout(layout)
        self.resize(1250, 600)

        self.sigStepCompleted.connect(self.stepCompleted)

        self.mouse = [0, 0]

        self.imageview.scene.sigMouseMoved.connect(self.mouseMoved)
        #self.imageview.mousePressEvent = self.mousePressed

        self.puffs = []

        self.scatter = pg.ScatterPlotItem(brush=pg.mkBrush(255, 0, 0))
        self.scatter.sigClicked.connect(self.mousePressed)

        self.imageview.view.addItem(self.scatter)

        self.crosshair = pg.CrosshairROI(size=(2, 2), translateSnap=[1, 1])

        self.imageview.view.addItem(self.crosshair)
        self.crosshair.removeHandle(0)
        pen = pg.mkPen(width=2)
        self.crosshair.setPen(pen)

    def mouseMoved(self, point):
        mouse = self.imageview.getImageItem().mapFromScene(point)
        self.mouse = [mouse.x(), mouse.y()]

    def mousePressed(self, ev):
        colors = []
        for p in self.puffs:
            d = np.linalg.norm(np.subtract(self.mouse, [p.x, p.y]))
            if d < 2:
                self.openPuff(p, clicked=True)
                #return
            if p.open:
                colors.append(pg.mkPen(255, 255, 0))
            else:
                colors.append(pg.mkPen(255, 0, 0))
        #colors = np.array(colors)
        self.scatter.setPen(colors)
    def _makeModelWidget(self):
        widg = QtWidgets.QGroupBox("Model")
        layout = QtWidgets.QFormLayout()
        self.widthSpinner = QtWidgets.QSpinBox()
        self.widthSpinner.setRange(0, 2000)
        self.widthSpinner.setValue(256)
        self.heightSpinner = QtWidgets.QSpinBox()
        self.heightSpinner.setRange(0, 2000)
        self.heightSpinner.setValue(256)
        self.pointSpinner = QtWidgets.QSpinBox()
        self.pointSpinner.setRange(1, 1000)

        self.puffTable = PuffTable()

        def genPoints():
            points = uniform(self.pointSpinner.value(), [self.widthSpinner.value(), self.heightSpinner.value()])
            puffs = [Puff(p[0], p[1]) for p in points]
            self.puffTable.setPuffs(puffs)

        genPointsButton = QtWidgets.QPushButton("Generate Points")
        genPointsButton.pressed.connect(genPoints)
        generateButton = QtWidgets.QPushButton("Generate")
        generateButton.pressed.connect(self.generate)

        def modelSelected():
            data = combo.currentData()
            self.widthSpinner.setValue(data.size[0])
            self.heightSpinner.setValue(data.size[1])
            puffs = [Puff(p[0], p[1]) for p in data.getPoints()]
            self.pointSpinner.setValue(len(puffs))
            self.puffTable.setPuffs(puffs)
        
        combo = QtWidgets.QComboBox()
        combo.currentIndexChanged.connect(modelSelected)

        for a, b in models.items():
            combo.addItem(a, b)

        layout.addRow("Model", combo)
        layout.addRow("Width", self.widthSpinner)
        layout.addRow("Height", self.heightSpinner)
        layout.addRow("# of Points", self.pointSpinner)
        layout.addRow(self.puffTable)
        buttonBox = QtWidgets.QWidget()
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(genPointsButton)
        buttonLayout.addWidget(generateButton)
        buttonBox.setLayout(buttonLayout)
        layout.addRow(buttonBox)
        widg.setLayout(layout)
        return widg


    def generate(self):
        w = self.widthSpinner.value()
        h = self.heightSpinner.value()

        self.Z = np.zeros((w+2,h+2), [('U', np.double), ('V', np.double)])
        U, V = self.Z['U'], self.Z['V']
        u,v = U[1:-1,1:-1], V[1:-1,1:-1]

        self.puffs = []
        points = []
        sizes = []
        for puff in self.puffTable.puffs:
            points.append([puff.x+.5, puff.y+.5])
            sizes.append(puff.calcium)

        self.puffs = self.puffTable.puffs

        sizes = 2 + 4 * (np.array(sizes) / np.max(sizes))

        self.scatter.setPoints(pos=points, size=sizes)
        u += 0.05*np.random.random((w,h))
        v += 0.05*np.random.random((w,h))
        
        self.showImage(V)
        

    def finished(self):
        self.pauseButton.setText("Pause")
        self.startButton.setText("Start")
        self.inLoop = False

    def start(self):
        self.inLoop = False

        while hasattr(self, 'diffThread') and self.diffThread.isAlive():
            QtWidgets.qApp.processEvents()
            self.diffThread.join()

        if self.startButton.text() == 'Start':
            self.diffThread = threading.Thread(None, self.loop)
            self.diffThread.start()

        self.startButton.setText("Start" if self.startButton.text() == 'Stop' else "Stop")

    def pause(self):
        self.paused = not self.paused
        self.pauseButton.setText("Unpause" if self.paused else "Pause")

    def closeEvent(self, ev):
        QtWidgets.QWidget.closeEvent(self, ev)
        self.inLoop = False

    def getArgs(self):
        args = {}
        args['steps'] = self.iterSpin.value()
        args['Du'] = self.duSpin.value()
        args['Dv'] = self.dvSpin.value()
        args['F'] = self.fSpin.value()
        args['k'] = self.kSpin.value()
        return args

    def showImage(self, V, **kargs):
        V = V.copy()[1:-1, 1:-1]
        #V = np.divide(V - V.min(), V.max() - V.min())
        self.imageview.setImage(V, levels=[0, .5], autoLevels=False, **kargs)
        self.imageview.setLevels(0., 0.5)

    def stepCompleted(self, i, V):
        for p in self.puffs:
            v = V[p.x, p.y]
            p.update(v)
            if p.open:
                V[p.x+1, p.y+1] += p.calcium

        if i % self.refreshSpin.value() == 0:
            self.showImage(V)

    def openPuff(self, puff, clicked=False):
        if clicked and self.inLoop:
            return
        self.Z['U'][puff.x+1, puff.y+1] = 0.50 if not puff.open else np.random.random()*.05
        self.Z['V'][puff.x+1, puff.y+1] = 0.25 if not puff.open else np.random.random()*.05

        puff.open = not puff.open
        self.showImage(self.Z['V'], autoRange=False)

    def loop(self):
        
        if self.inLoop:
            return

        self.inLoop = True
        if self.imageview.image is None:
            return
        self.scatter.hide()
        w = self.widthSpinner.value()
        h = self.heightSpinner.value()

        U, V = self.Z['U'], self.Z['V']
        u,v = U[1:-1,1:-1], V[1:-1,1:-1]

        p = 0
        args = self.getArgs()
        Du = args['Du']
        Dv = args['Dv']
        F = args['F']
        k = args['k']
        steps = args['steps']
        self.movie = []

        i = 0
        while True:
            if self.paused:
                continue
            if i >= steps or not self.inLoop:
                break
            Lu = (U[0:-2,1:-1] +
                  U[1:-1,0:-2] - 4*U[1:-1,1:-1] + U[1:-1,2:] +
                                   U[2:  ,1:-1] )
            Lv = (V[0:-2,1:-1] +
                  V[1:-1,0:-2] - 4*V[1:-1,1:-1] + V[1:-1,2:] +
                                   V[2:  ,1:-1] )
            uvv = u*v*v
            u += (Du*Lu - uvv +  F   *(1-u))
            v += (Dv*Lv + uvv - (F+k)*v)

            pn = 100 * (i + 1) / steps # percent completed
            if pn > p + 2:
                p = pn
                self.infoLabel.setText("%" + str(p).zfill(2))

            self.sigStepCompleted.emit(i, V)
            self.movie.append(V.copy())


            i += 1
        self.scatter.setVisible(True)
        self.inLoop = False
        self.sigFinished.emit()

if __name__ == '__main__':
  app = QtWidgets.QApplication([])
  mw = MainWindow()
  mw.show()
  app.exec_()