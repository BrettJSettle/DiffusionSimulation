import numpy as np
import random

OPEN_DURATION = 200

class Puff:
	OPEN_RATE = 5
	def __init__(self, x, y, amplitude=1):
		self.x = int(x)
		self.y = int(y)
		self.amplitude = amplitude
		self.open = False
		self.openDuration = 0.
		self.timeToOpen = 0.
		self.concentrations = []
		self.pToggle = Puff.OPEN_RATE
		self.closeTime = random.expovariate(1/OPEN_DURATION)

	def finished(self):
		return self.open == False and self.openDuration > 0

	def tryToggleOpen(self, dt, concentration):
		if np.random.random() < (np.exp(1 + concentration) * self.pToggle * 1e-4 * dt):
			self.open = not self.open

	def update(self, dt, concentration):
		self.concentrations.append(concentration)
		val = 0
		if self.open:
			self.openDuration += dt
			val = self.amplitude * 4
			if self.openDuration >= self.closeTime:
				self.open = False
			#self.tryToggleOpen(dt, concentration)
		elif self.openDuration == 0:
			self.tryToggleOpen(dt, concentration)
			if not self.open:
				self.timeToOpen += dt
		#self.pToggle *= 1.000001

		return val