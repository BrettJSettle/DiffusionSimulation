import random
import numpy as np
import threading
from qtpy import QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.console import ConsoleWidget
from gen import models, uniform, save_model, Model, save_models, HIDDEN_AMPLITUDE, AMPLITUDE
from puff import Puff


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
        self.puffs[a].amplitude = self.item(a, 2).value

    def addPuff(self, puff):
        self.puffs.append(puff)
        self.updateTable()

    def updateTable(self):
        data = [[p.x, p.y, p.amplitude] for p in self.puffs]
        self.setData(data)
        self.setHorizontalHeaderLabels(["X", "Y", "Amplitude"])

    def setPuffs(self, puffs):
        self.removeAll()
        self.puffs = puffs
        self.updateTable()

    def getPuffs(self):
        return self.puffs

    def removeAll(self):
        self.puffs = []
        self.setData([])

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(centralWidget)
        self.running = False

        self._makeMenuBar()

        self.imageview = pg.ImageView()
        self.imageview.view.setAutoPan(False)
        self.imageview.setMinimumWidth(650)
        self.console = ConsoleWidget()
        self.console.setMaximumWidth(400)
        self.optionsWidget = QtWidgets.QWidget()

        def errCall(err, a):
            self.running = False
            self.imageview.setHistogramRange(0, 2)
            self.imageview.setLevels(0, 2)
        np.seterrcall(errCall)
        np.seterr(over='call')

        opsL = QtWidgets.QFormLayout()
        header = QtWidgets.QLabel("Diffusion Simulation")
        opsL.addRow(header)
        self.optionsWidget.setMaximumWidth(600)
        self.optionsWidget.setMinimumWidth(400)
        self.top_left_label = pg.LabelItem("", justify='right')
        self.imageview.ui.graphicsView.addItem(self.top_left_label)

        def timeChanged(m, b):
            self.top_left_label.setText("Frame %d, %s ms" % (m, m * self.dtSpin.value() * self.refreshSpin.value()))

        self.imageview.sigTimeChanged.connect(timeChanged)
        def viewKeyPress(ev):
            pg.ViewBox.keyPressEvent(self.imageview.view, ev)

        self.imageview.view.keyPressEvent = viewKeyPress

        def saveModel():
            puffs = self.puffs
            model = self.getModel()
            model.puffs = puffs
            name = QtWidgets.QInputDialog.getText(self, "Enter a model name", "Enter a model name")
            if name is not None and len(name) > 0:
                save_model(name, m)

        self.startButton = QtWidgets.QPushButton("Start")
        self.startButton.pressed.connect(self.start)
        self.saveModelButton = QtWidgets.QPushButton("Save Model")
        self.saveModelButton.pressed.connect(saveModel)
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        buttonBox = QtWidgets.QWidget()
        buttonLayout = QtWidgets.QGridLayout()
        buttonLayout.addWidget(self.progressBar, 0, 0, 1, 3)
        buttonLayout.addWidget(self.saveModelButton, 1, 0)
        buttonLayout.addWidget(self.startButton, 1, 1)
        buttonBox.setLayout(buttonLayout)

        self.imageWidget = self._makeImageWidget()
        self.modelWidget = self._makeModelWidget()
        self.puffWidget = self._makePuffWidget()

        separator = QtWidgets.QWidget()
        sepLayout = QtWidgets.QHBoxLayout()
        self.infoLabel = QtWidgets.QLabel()
        sepLayout.addWidget(self.infoLabel)
        sepLayout.addStretch()
        separator.setLayout(sepLayout)

        def modelSelected():
            data = combo.currentData()
            self.widthSpin.setValue(data.x_max)
            self.heightSpin.setValue(data.y_max)
            self.timeSpin.setValue(data.t_max)
            self.dxSpin.setValue(data.dx)
            self.dySpin.setValue(data.dy)
            self.dtSpin.setValue(data.dt)
            self.dSpin.setValue(data.d)

            self.sequesterSpin.setValue(data.sequestration)
            puffs = data.puffs
            self.pointSpin.setValue(len(puffs))
            self.puffTable.setPuffs(puffs)
            self.refreshSpin.setValue(data.refresh)
        
        combo = QtWidgets.QComboBox()
        combo.currentIndexChanged.connect(modelSelected)

        for a, b in models.items():
            combo.addItem(a, b)
        opsL.addRow("Saved Models", combo)
        opsL.addRow(self.imageWidget)
        opsL.addRow(self.puffWidget)
        opsL.addRow(self.modelWidget)
        opsL.addRow(separator)
        opsL.addRow(buttonBox)
        self.optionsWidget.setLayout(opsL)

        self.console.localNamespace.update({'self': self, 'set': self.imageview.setImage})
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.console, 0, 0)
        layout.addWidget(self.imageview, 0, 1)
        layout.addWidget(self.optionsWidget, 0, 2)
        centralWidget.setLayout(layout)
        self.resize(1850, 600)

        self.mouse = [0, 0]

        self.imageview.scene.sigMouseMoved.connect(self.mouseMoved)
        self.imageview.mousePressEvent = self.mousePressed

        self.puffs = []

        self.scatter = pg.ScatterPlotItem(brush=pg.mkBrush(255, 255, 0))
        self.scatter.sigClicked.connect(self.mousePressed)

        self.imageview.view.addItem(self.scatter)
        self.imageview.view.setMenuEnabled(False)

    def _makeMenuBar(self):
        m = self.menuBar()
        fileMenu = m.addMenu("File")
        self.saveResultsAction = fileMenu.addAction("Save Results", self.saveResults)
        fileMenu.addAction("Save Movie", lambda : np.savetxt("movie.txt", self.imageview.image))
        plotMenu = m.addMenu("Plot")

        def plotTTO():
            vals = [p.timeToOpen for p in self.puffTable.puffs]
            a, b = np.histogram(vals, 50)
            pg.plot(x=b, y=a, stepMode=True, title="Puff Time To Open (ms)")

        def plotOD():
            vals = [p.openDuration for p in self.puffTable.puffs]
            a, b = np.histogram(vals, 50)
            pg.plot(x=b, y=a, stepMode=True, title="Puff Open Duration (ms)")

        def plotPuffs():
            self.plotItem = pg.PlotWidget()
            for p in self.puffs:
                self.plotItem.addItem(pg.PlotDataItem(p.concentrations))
            self.plotItem.show()


        plotMenu.addAction("Plot Time To Open", plotTTO)
        plotMenu.addAction("Plot Open Duration", plotOD)
        plotMenu.addAction("Plot Puffs", plotPuffs)
        

        m.addAction("Quit", self.close)

    def saveResults(self):
        fname = QtWidgets.QFileDialog.getSaveFileName(self, "Save model results")
        fname = str(fname if type(fname) != tuple else fname[0])
        if fname != '':
            self.model.export(fname)

    def getModel(self):
        dt = self.dtSpin.value()
        dx = self.dxSpin.value()
        dy = self.dySpin.value()
        x_max = self.widthSpin.value()
        y_max = self.heightSpin.value()
        t_max = self.timeSpin.value()
        puffs = self.puffTable.puffs
        sequestration = self.sequesterSpin.value()
        d = self.dSpin.value()
        refresh = self.refreshSpin.value()
        stop_early = self.stopEarlyCheck.isChecked()
        return Model(d=d, dt=dt, dx=dx, dy=dy, t_max=t_max, x_max=x_max, y_max=y_max, puffs=puffs, sequestration=sequestration, refresh=refresh, stop_early=stop_early) 

    def mouseMoved(self, point):
        mouse = self.imageview.getImageItem().mapFromScene(point)
        self.mouse = [int(mouse.x()), int(mouse.y())]

    def mousePressed(self, ev):
    
        if isinstance(ev, pg.ScatterPlotItem):
            pt = ev.ptsClicked[0]
            for p in self.puffs:
                if p.x == int(pt.pos().x()) and p.y == int(pt.pos().y()):
                    p.open = not p.open

        elif ev.button() == 2:
            if hasattr(self, 'selectedPoint'):
                print(self.selectedPoint)
            puffs = 0
            for p in self.puffs:
                d = np.linalg.norm(np.subtract(self.mouse, [p.x, p.y]))
                if puffs == 0 and d < 1:
                    return
            self.puffTable.addPuff(Puff(self.mouse[0], self.mouse[1]))
        self.generate(image=False)

    def closeEvent(self, ev):
        print("Saving models...")
        save_models()

    def _makeImageWidget(self):
        w = QtWidgets.QGroupBox("Model Settings")
        layout = QtWidgets.QFormLayout()
        self.widthSpin = QtWidgets.QSpinBox()
        self.widthSpin.setRange(0, 50000)
        self.widthSpin.setValue(10000)
        self.heightSpin = QtWidgets.QSpinBox()
        self.heightSpin.setRange(0, 50000)
        self.heightSpin.setValue(10000)
        self.timeSpin = QtWidgets.QDoubleSpinBox()
        self.timeSpin.setRange(0, 10000)
        self.timeSpin.setDecimals(2)
        self.timeSpin.setValue(2000)

        self.dxSpin = QtWidgets.QSpinBox()
        self.dxSpin.setRange(0, 1000)
        self.dxSpin.setValue(100)
        self.dySpin = QtWidgets.QSpinBox()
        self.dySpin.setRange(0, 1000)
        self.dySpin.setValue(100)
        self.dtSpin = QtWidgets.QDoubleSpinBox()
        self.dtSpin.setDecimals(4)
        self.dtSpin.setValue(.01)

        imageGenStyle = QtWidgets.QWidget()
        l = QtWidgets.QHBoxLayout()
        self.randomRadio = QtWidgets.QRadioButton("Random [0, .05)")
        self.randomRadio.setChecked(True)
        self.onesRadio = QtWidgets.QRadioButton("Ones")
        l.addWidget(self.randomRadio)
        l.addWidget(self.onesRadio)
        imageGenStyle.setLayout(l)

        layout.addRow("Width (micron)", self.widthSpin)
        layout.addRow("Height (micron)", self.heightSpin)
        layout.addRow("Time (ms)", self.timeSpin)
        layout.addRow("X Grid Size (micron)", self.dxSpin)
        layout.addRow("Y Grid Size (micron)", self.dySpin)
        layout.addRow("Time Step (ms)", self.dtSpin)

        layout.addRow(imageGenStyle)
        w.setLayout(layout)
        return w

    def _makePuffWidget(self):
        w = QtWidgets.QGroupBox("Puff Settings")
        layout = QtWidgets.QFormLayout()
        self.pointSpin = QtWidgets.QSpinBox()
        self.pointSpin.setRange(1, 1000)
        self.puffTable = PuffTable()

        self.minPuffSpin = QtWidgets.QSpinBox()
        self.minPuffSpin.setValue(0)

        def generatePuffs():
            m = self.getModel()
            m.genPuffs(self.pointSpin.value(), amplitude=AMPLITUDE)

            m.genPuffs(self.minPuffSpin.value(), amplitude=HIDDEN_AMPLITUDE, reset=False)

            self.puffTable.setPuffs(m.puffs)

        genPointsButton = QtWidgets.QPushButton("Generate Points")
        genPointsButton.pressed.connect(generatePuffs)
        generateButton = QtWidgets.QPushButton("Generate")
        generateButton.pressed.connect(self.generate)
        buttonBox = QtWidgets.QWidget()
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(genPointsButton)
        buttonLayout.addWidget(generateButton)
        buttonBox.setLayout(buttonLayout)

        layout.addRow("Puff Sites", self.pointSpin)
        layout.addRow("Hidden Sites", self.minPuffSpin)
        layout.addRow(self.puffTable)
        layout.addRow(buttonBox)
        w.setLayout(layout)
        return w

    def _makeModelWidget(self):
        widg = QtWidgets.QGroupBox("Model Settings")
        layout = QtWidgets.QFormLayout()

        self.dSpin = QtWidgets.QDoubleSpinBox()
        self.dSpin.setRange(0, 1000)
        self.dSpin.setValue(20)
        self.sequesterSpin = QtWidgets.QDoubleSpinBox()
        self.sequesterSpin.setRange(0, 1)
        self.sequesterSpin.setDecimals(4)
        self.sequesterSpin.setValue(.95)
        self.refreshSpin = QtWidgets.QSpinBox()
        self.refreshSpin.setRange(1, 1000)
        self.refreshSpin.setValue(100)
        self.stopEarlyCheck = QtWidgets.QCheckBox()
        self.stopEarlyCheck.setChecked(True)

        layout.addRow("Diffusion Coefficient (micron**2 / s)", self.dSpin)
        layout.addRow("Sequestration Coefficient", self.sequesterSpin)
        layout.addRow("Interval Refresh Rate", self.refreshSpin)
        layout.addRow("Quit when all puffs close", self.stopEarlyCheck)
        widg.setLayout(layout)
        return widg

    def generate(self, image=True):
        m = self.getModel()

        if image:
            self.Z = np.zeros((m.nx+2,m.ny+2), dtype=np.float64)
            z = self.Z[1:-1,1:-1]
            if self.onesRadio.isChecked():
                z += 1
            elif self.randomRadio.isChecked():
                z += 0.05*np.random.random((m.nx,m.ny))

        self.puffs = []
        points = []
        sizes = []
        colors = []
        for puff in self.puffTable.puffs:
            if image:
                puff.openDuration = 0
            points.append([puff.x+.5, puff.y+.5])
            sizes.append(puff.amplitude)
            colors.append((255, 255, 0) if not puff.open else (255, 0, 0))

        pens = [pg.mkPen(pen) for pen in colors]
        brushes = [pg.mkBrush(brush) for brush in colors]
        self.puffs = self.puffTable.puffs

        if len(self.puffs) > 0:
            sizes = 5 + 4 * (np.array(sizes) / np.max(sizes))
            self.scatter.setPoints(pos=points, size=sizes, pen=pens, brush=brushes)
        if image:
            self.showImage(self.Z)

    def start(self):
        if not self.running and self.startButton.text() == 'Stop':
            self.startButton.setText("Start")
            return
        if self.running:
            self.running = False
            return
        
        self.model = self.getModel()
        m = self.model
        refreshRate = self.refreshSpin.value()
        frames = (m.nt) // refreshRate + 1
        movie = np.zeros([frames, m.nx+2, m.ny+2])

        movie[0] = self.imageview.getImageItem().image
        i = 1
        p = 0
        self.startButton.setText("Stop")
        self.running = True
        for im in m.run(movie[0]):
            if not self.running:
                break
            if i % refreshRate == 0:
                movie[i // refreshRate] = im
            
            if (100 * i) // m.nt > p:
                p = (100 * i) // m.nt
                self.progressBar.setValue(p)
            QtWidgets.qApp.processEvents()
            i += 1

        self.progressBar.setValue(100)
        self.showImage(movie)

        self.running = False
        self.startButton.setText("Start")
        self.saveResultsAction.setEnabled(True)

    def keyPressEvent(self, ev):
        if ev.text() == 'c':
            from pyqtgraph.console import ConsoleWidget
            self.console = ConsoleWidget()
            self.console.localNamespace['self'] = self
            self.console.show()

    def closeEvent(self, ev):
        QtWidgets.QWidget.closeEvent(self, ev)
        self.running = False

    def showImage(self, V, **kargs):
        self.imageview.setImage(V, autoLevels=False, **kargs)
        self.imageview.setLevels(0, min(1.5, 1.5 * V.max()))
        self.imageview.setHistogramRange(0, 2)

    def openPuff(self, puff, clicked=False):
        if clicked and self.running:
            return
        puff.open = not puff.open

if __name__ == '__main__':
  app = QtWidgets.QApplication([])
  mw = MainWindow()
  mw.show()
  app.exec_()