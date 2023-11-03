import time
import RPi.GPIO as GPIO

servo = 13
# Set up the GPIO pin to control the servo motor
GPIO.setmode(GPIO.BCM)
GPIO.setup(servo, GPIO.OUT)

# Create a PWM object on the GPIO pin
pwm = GPIO.PWM(servo, 50)
pwm.start(0)

try:
    while True:
        angle = int(input("Enter Degrees: "))
        duty = (angle/18)+2.5
        print(angle,' ',duty)
        # Rotate the servo motor to 0 degrees
        pwm.ChangeDutyCycle(duty)
        time.sleep(0.1)

except KeyboardInterrupt:
    pass

finally:
    # Stop the PWM object and clean up the GPIO
    pwm.stop()
    GPIO.cleanup()