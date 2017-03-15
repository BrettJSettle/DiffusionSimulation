import numpy as np
import sys
import argparse

def parseArgs():
	parser = argparse.ArgumentParser()
	args = sys.argv[1:]
	parser.add_argument("-x", type=int,
					help="width")
	parser.add_argument("-y", type=int,
					help="width")
	parser.add_argument('-c', type=int, help="puff count", default=5)
	parser.add_argument("-d", type=float,
					help="Diffusion Coefficient")

	args = dict(parser.parse_args()._get_kwargs())
	DEFAULTS = {'c': 10, 'd': .012, 'x':100, 'y':100}
	for arg in DEFAULTS:
		if args[arg] is None and arg in DEFAULTS:
			args[arg] = DEFAULTS[arg]
	size = [args.pop('x')]
	if args['y'] != None and args['y'] > 1:
		size.append(args.pop('y'))
	args['im'] = tuple(size)
	return {k:v for k, v in args.items() if v is not None}

class Puff:
	RELEASE = 7.0
	def __init__(self, x, y):
		self.x = int(x)
		self.y = int(y)
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

class DiffusionSimulation:
	def __init__(self, d, im=(100,100), iterations=50000, iterSize=50):
		if type(im) == tuple:
			self.shape = im
			self.initialImage = np.random.random([i + 1 for i in im]).astype(np.float64) * .1
		else:
			self.shape = im.shape
			self.initialImage = im.astype(np.float64)

		self.t = iterations
		self.iterSize = iterSize or 1
		self.a = d

		self.puffs = []
		self.u_1 = self.initialImage.copy()

		self.F = self.a*1./1.**2

	def reset(self):
		self.u_1 = self.initialImage.copy()

	def run(self):
		p = 0
		pn = 0
		movie = np.array([self.u_1.copy()])
		np.random.choice(self.puffs).open = True
			
		for i in np.arange(self.t):
			self.handlePuffs()
			try:
				self.step()
			except:
				if len(movie) > 1000:
					break
			if i % self.iterSize == 0:
				movie = np.vstack([movie, [self.u_1.copy()]])

			pn = int(100 * i / float(self.t))
			if pn > p:

				print("%d%%" % pn)
				p = pn
		return movie

	def handlePuffs(self):
		for p in self.puffs:
			try:
				v = self.u_1[p.x, p.y]
			except:
				v = self.u_1[p.x]
			p.update(v)
			if p.open:
				try:
					self.u_1[p.x, p.y] += puff.RELEASE
				except:
					self.u_1[p.x] += puff.RELEASE

	def step(self):
		dx = 1
		u = np.zeros_like(self.u_1, dtype=np.float64)           # unknown u at new time level
		
		if len(self.shape) > 1:
			u[1:-1, 1:-1] = self.u_1[1:-1, 1:-1] + self.a  * (
				(self.u_1[2:, 1:-1] - 2*self.u_1[1:-1, 1:-1] + self.u_1[:-2, 1:-1])/(dx**2)
				+ (self.u_1[1:-1, 2:] - 2*self.u_1[1:-1, 1:-1] + self.u_1[1:-1, :-2])/(dx**2) )
			u[0, :] = 0
			u[self.shape[0], :] = 0
			u[:, 0] = 0
			u[:, self.shape[1]] = 0

		else:
			for i in np.arange(1, self.shape[0]):
				u[i] = self.u_1[i] + self.F*(self.u_1[i-1] - 2*self.u_1[i] + self.u_1[i+1])
			u[0] = 0
			u[self.shape[0]] = 0
		
		# Update self.u_1 before next step
		self.u_1[:]= u

if __name__ == '__main__':
	args = parseArgs()
	puffCount = args.pop('c')
	diff = DiffusionSimulation(**args)
	for i in range(puffCount):
		x = np.random.randint(diff.shape[0])
		y = np.random.randint(diff.shape[1]) if len(diff.shape) > 1 else 0
		puff = Puff(x, y)
		diff.puffs.append(puff)
	movie = diff.run()
	

	import pyqtgraph as pg
	app = pg.Qt.QtGui.QApplication([])
	im = pg.ImageView()
	im.setImage(movie)
	im.show()
	app.exec_()