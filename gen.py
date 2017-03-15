import numpy as np
data = [[260.916,	63.486],
[268.831,	324.685],
[276.746,	421.646],
[340.068,	448.359],
[303.46,	508.712],
[448.901,	546.309],
[325.227,	635.354],
[359.855,	714.506],
[303.46,	832.243],
[370.739,	812.455],
[411.304,	734.293],
[529.041,	735.283],
[571.585,	616.556],
[563.67,	458.253],
[561.691,	393.943],
[529.041,	300.940],
[390.527,	247.513],
[419.219,	150.552]]


scale = 10. / 360
#size = [400, 850]
size = [786, 1057]
data = np.array(data)# * scale
size = np.array(size)# * scale
#data -= np.min(data, 0) - [1, 1]

data = np.divide(data, 4)
size  = np.divide(size, 4)

points = len(data)

def uniform(points, size):
	xs = np.random.uniform(0, size[0], points)
	ys = np.random.uniform(0, size[1], points)
	return np.transpose([xs, ys])

class Model():
	def __init__(self, points, size):
		self.size = size
		self.points = points
	def getPoints(self):
		if isinstance(self.points, int):
			return uniform(self.points, self.size)
		else:
			return self.points


models = {'Science Signaling': Model(data, size), 'None': Model(0, [0, 0]), '1D': Model(1, [100, 1]), 'Sample': Model(10, [100, 100])}