import numpy as np
import pyqtgraph as pg
import random

arr = np.loadtxt('out/results.txt')

openDurations = arr[:, -1]
a, b = np.histogram(openDurations, 50)
pg.plot(x=b, y=a, stepMode=True, title="Puff Open Duration (ms)")

openTimes = arr[:, -2]
a, b = np.histogram(openTimes, 50)
pg.plot(x=b, y=a, stepMode=True, title="Puff Time To Open (ms)")

pg.Qt.QtWidgets.qApp.exec_()