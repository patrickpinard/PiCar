
from gpiozero import LED, PWMLED, Button
import time

PIN = Button(18, pull_up = True)
A1 = LED(6)
A2 = LED(13)
B1 = LED(20)
B2 = LED(21)


p1 = PWMLED(12)
p2 = PWMLED(26)

def init():
	stop()
	speed(50,50)

def forward():
	A1.on()
	A2.off()
	B1.on()
	B2.off()


def stop():
	A1.off()
	A2.off()
	B1.off()
	B2.off()

def reverse():
	A1.off()
	A2.on()
	B1.off()
	B2.on()

def left():
	A1.on()
	A2.off()
	B1.off()
	B2.off()

def right():
	A1.off()
	A2.off()
	B1.on()
	B2.off()

	'''
	Adjust the speed of the motor
	PWMB : 0 - 100
	PWMB : 0 -100
	'''
def speed(PWMA,PWMB):
	p1.value = PWMA / 500
	p2.value = PWMB / 500

while True:
	try:
		print("Test the motor")
		init()
		print ("Set the motor forward for 2s")
		forward()
		time.sleep(2)
		print("Set the motor turn left for 1s")
		left()
		time.sleep(1)
		print("Set the motor turn right for 1s")
		right()
		time.sleep(1)
		print("Set the motor stop")
		stop()
		time.sleep(5)
	except KeyboardInterrupt:
		print("Ending program")
		break
