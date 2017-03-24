import numpy as np
import random

OPEN_DURATION = 100

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
		duration = min(1, amplitude) * OPEN_DURATION
		self.closeTime = min(300, random.expovariate(1/duration))

	def finished(self):
		return self.open == False and self.openDuration > 0

	def tryToggleOpen(self, dt, concentration):
		if np.random.random() < (np.exp(1 + 20 * concentration) * self.pToggle * 1e-5 * dt):
			self.open = not self.open

	def update(self, dt, concentration):
		self.concentrations.append(concentration)
		val = 0
		if self.open:
			self.openDuration += dt
			val = 5 * self.amplitude * dt
			if self.openDuration >= self.closeTime:
				self.open = False
				print("Puff closes at %d" % (self.timeToOpen + self.openDuration))
			#self.tryToggleOpen(dt, concentration)
		elif self.openDuration == 0:
			self.tryToggleOpen(dt, concentration)
			if not self.open:
				self.timeToOpen += dt
			else:
				print("Puff opens at %d, will remain open for %d" % (self.timeToOpen, self.closeTime))

		return val