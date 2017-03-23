import numpy as np
import sys, os
import argparse
from gen import Model, models
from tqdm import *

def parseArgs():
	parser = argparse.ArgumentParser()
	args = sys.argv[1:]
	parser.add_argument("-width", type=int,
					help="width in microns")
	parser.add_argument("-height", type=int,
					help="height in microns")
	parser.add_argument("-dx", type=int,
					help="mesh width")
	parser.add_argument("-dy", type=int,
					help="mesh height")
	parser.add_argument("-t", type=int,
					help="total time to simulate")
	parser.add_argument("-dt", type=int, default=None,
					help="time interval in microseconds")
	parser.add_argument("-s", type=float, default=1.0,
					help="sequestration coefficient")
	parser.add_argument('-p', type=int, default=10,
					help="Sites to generate")
	parser.add_argument("-d", type=float,
					help="Diffusion Coefficient in square microns per second")
	parser.add_argument("-r", type=int,
					help="Refresh rate for result movie. Saves every r frames")
	parser.add_argument('-o', type=str, default="out/results.txt",
					help="output file to save results to")
	parser.add_argument('-n', type=int, default=1,
					help="Number of simulations to run")
	parser.add_argument('--stop-early', action="store_true", default=False,
					help="Stop once all puffs are closed")

	args = dict(parser.parse_args()._get_kwargs())
	
	args['x_max'] = args.pop('width')
	args['y_max'] = args.pop('height')
	args['t_max'] = args.pop('t')
	args['sequestration'] = args.pop('s')
	args['puffs'] = args.pop('p')
	args['refresh'] = args.pop('r')

	return {k:v for k, v in args.items() if v is not None}

if __name__ == '__main__':
	args = parseArgs()
	n = args.pop('n')
	
	##### SETTINGS ###
	n = 40
	args['t_max'] = 2000
	args['puffs'] = 30
	args['stop_early'] = True
	#####

	fname = str(args.pop('o'))
	if not os.path.exists(os.path.dirname(fname)):
		os.mkdir(os.path.dirname(fname))
	if os.path.exists(fname):
		os.remove(fname)
	
	m = Model(**args)
	for i in tqdm(range(n)):
		m.genPuffs(len(m.puffs))
		#np.random.choice(m.puffs).open = True
		#frames = (m.nt) // m.refresh + 1	
		frames = 1
		movie = np.zeros([frames, m.nx+2, m.ny+2])

		movie[0, 1:-1, 1:-1] = np.random.random([m.nx, m.ny]) * .05
		i = 1
		p = 0
		for im in m.run(movie[0]):
			if i % m.refresh == 0:
				movie[0] = im
				#movie[i // m.refresh] = im
			
			if (100 * i) // m.nt > p:
				p = (100 * i) // m.nt
			i += 1

		m.export(open(str(fname), 'wb' if i == 0 else 'ab'))
	'''
	import pyqtgraph as pg
	app = pg.Qt.QtGui.QApplication([])
	im = pg.ImageView()
	im.setImage(movie)
	im.show()
	app.exec_()
	'''