import numpy as np
from puff import Puff
data = [[260.916,   63.486],
[268.831,   324.685],
[276.746,   421.646],
[340.068,   448.359],
[303.46,    508.712],
[448.901,   546.309],
[325.227,   635.354],
[359.855,   714.506],
[303.46,    832.243],
[370.739,   812.455],
[411.304,   734.293],
[529.041,   735.283],
[571.585,   616.556],
[563.67,    458.253],
[561.691,   393.943],
[529.041,   300.940],
[390.527,   247.513],
[419.219,   150.552]]



data = np.array(data) // 4 - [20, 0]

def uniform(points, size):
    xs = np.random.uniform(0.15*size[0], size[0]*.85, points)
    ys = np.random.uniform(0.15*size[1], size[1]*.85, points)
    return np.transpose([xs, ys]).astype(int)

class Model():

    def __init__(self, **kargs): #d, dt, dx, dy, t_max, x_max, y_max, puffs, sequestration = 1, refresh=20):
        self.d = kargs.get('d', 20)
        self.dt = kargs.get('dt', .05)
        self.dx = kargs.get('dx', 166)
        self.dy = kargs.get('dy', 166)
        self.t_max = kargs.get('t_max', 1000)
        self.x_max = kargs.get('x_max', 40000)
        self.y_max = kargs.get('y_max', 40000)
        self.sequestration = kargs.get('sequestration', 1.0)
        self.stop_early = kargs.get('stop_early', False)
        self.refresh = kargs.get('refresh', 50)

        maxDt = self.dx**2*self.dy**2/( 2*self.d*(self.dx**2+self.dy**2) )
        if self.dt > maxDt:
            print("ALERT: time step too large for mesh, setting to %s" % maxDt)
            self.dt = maxDt

        self.nx = len(np.arange(0, self.x_max+self.dx, self.dx))
        self.ny = len(np.arange(0, self.y_max+self.dy, self.dy))
        self.nt = len(np.arange(0, self.t_max+self.dt, self.dt))

        puffs = kargs.get('puffs', 30)
        if isinstance(puffs, int):
            self.genPuffs(puffs)
        else:
            self.puffs = puffs
            self.puffCount = len(puffs)

    def finished(self):
        return all([p.finished() for p in self.puffs])
        
        
    def genPuffs(self, n):
        self.puffCount = n
        self.puffs = [Puff(a, b) for a, b in uniform(n, [self.nx, self.ny])]

    def export(self, fname):
        # x y amplitude openDuration 
        d = np.zeros([len(self.puffs), 5])
        for i, p in enumerate(self.puffs):
            d[i] = [p.x, p.y, p.amplitude, p.timeToOpen, p.openDuration]

        np.savetxt(fname, d)
        
    def handlePuffs(self, dt):
        for p in self.puffs:
            if p.finished():
                continue
            valAtT = self.u[p.x, p.y]
            v = p.update(dt, valAtT)
            self.u[p.x, p.y] += v

    def run(self, im):

        #convert units to micron
        
        d = self.d  * 1e-6 #/ (1e-3) # micron ** 2 per second
        dt = self.dt * 1e-3
        dx = self.dx * 1e-6
        dy = self.dy * 1e-6
        t_max = self.t_max * 1e-3
        x_max = self.x_max * 1e-6
        y_max = self.y_max * 1e-6

        s = d*dt/(dy*dx)

        x = np.arange(0,x_max+dx,dx)
        y = np.arange(0,y_max+dy,dy) 
        t = np.arange(0,t_max+dt,dt)
        r = len(t)
        c = len(y)
        d = len(x)
        self.u = im.copy()
        for n in range(0,r-1): # time
            u = self.u[1:-1, 1:-1] + s * (self.u[2:, 1:-1] - 4*self.u[1:-1, 1:-1] + self.u[:-2, 1:-1] + self.u[1:-1, 2:] + self.u[1:-1, :-2])
            u *= self.sequestration
            u[:, 0] = u[:, 1]
            u[:, -1] = u[:, -2]
            u[0, :] = u[1, :]
            u[-1, :] = u[-2, :]
            
            self.u[1:-1, 1:-1] = u.copy()
            self.handlePuffs(self.dt)
            yield self.u
            if self.stop_early and self.finished():
                break
            
d = 20 # um**2/s

models = {'Science Signaling': Model(d=d, dt=.01, dx=50, dy=50, t_max=1000, x_max=8000, y_max=12000, puffs=[Puff(*p) for p in data], refresh=100), 
        'Sample': Model(d=d, dt=.05, dx=100, dy=100, t_max=4000, x_max=10000, y_max=10000, puffs=10, refresh=20),
        'Empty': Model(puffs=30)}

import pickle, os
def load_models():
    global models
    if os.path.exists('models.p'):
        newModels = pickle.load(open('models.p', 'rb'))
        models.update(newModels)

def save_models():
    modelsNew = {k:v for k, v in models.items() if k not in ('Science Sampling', 'Sample')}
    pickle.dump(models, open('models.p', 'wb'))

def save_model(name, model):
    global models
    models[name] = model

load_models()

def showMovie(mov):
    import pyqtgraph as pg
    app = pg.Qt.QtGui.QApplication([])
    im = pg.ImageView()
    im.setImage(mov)
    im.show()
    return app, im