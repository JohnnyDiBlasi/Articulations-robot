"""
This is a kind of dummy script that was taken from the Beauty Project's PY script: 
(That script was one that mimics one state-action pair of the Beauty robot's actions.
It mimics commands from the rl model's controller to select a pipette, collect attract/repellent solution
and drop it on the plate at a particular location (that the controller determines) before returning to
its home position.)
THIS Dummy Script will: mimics one state-action pair of the robot's actions. It mimics commands from the rl model's controller to
select a brush or marker, collects paint (if applicable), and move to make a mark on the canvas area at a particular location 
(that the controller determines) before returning to its home position. 
"""

from tensorflow import keras
from tensorflow.keras import backend as K
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Conv2D, Conv2DTranspose, Flatten, Input, Dense, Dropout, Lambda, Reshape, MaxPooling2D, LSTM, Reshape
# from tensorflow.keras.models importkdl,kkk'sdee
import os
import sys
import serial
import threading
import cv2
import time
from time import sleep
import numpy as np
import gphoto2 as gp
import argparse
import random
import math

# sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(os.path.join(os.path.dirname(__file__), "/Users/designuser/Documents/GitHub/uArm-Python-SDK"))

from uarm.wrapper import SwiftAPI

def loadImg(s, read_as_float32=False, gray=False):
    if read_as_float32:
        img = cv2.imread(s).astype(np.float32) / 255
    else:
        img = cv2.imread(s)
    if gray:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img

def setupCamera(target="Memory card"):
    # Open Camera Connection
    camera = gp.Camera()
    camera.init()

    #get Configuration tree
    config = camera.get_config()

    #Find the Capture target Config item
    capture_target = config.get_child_by_name("capturetarget")

    # set value to Memory Card (default) or Internal RAM
    # value = capture_target.get_value()
    capture_target.set_value(target)
    # set config
    camera.set_config(config)

    return camera


# configure the Serial port
def serial_connect(port, baudrate=9600, timeout=1):
    ser = serial.Serial(
        # port='/dev/ttyS1',\
        port=port, 
        baudrate=baudrate, 
        parity=serial.PARITY_NONE, 
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=timeout, 
    )
    print("Connected to: " + ser.portstr)
    return ser


def main():
    print(__doc__)

    prevTime = 0
    # default =  30 minutes = 1800 seconds
    INTERVAL = args.interval

    callback_obj = gp.check_result(gp.use_python_logging())

    # establish connectino with digital camera
    camera = setupCamera()

    # === INITIALIZE ARM ===
    swift = SwiftAPI(filters={"hwid": "USB VID:PID=2341:0042"})

    sleep(2)
    print("Device info: ")
    print(swift.get_device_info())
    swift.waiting_ready()
    # normal mode:
    swift.set_mode(0)

    # Get the Initial position of the arm.
    position = swift.get_position(wait=True)
    print("Robot arm's initial position: ")
    print(position)

    # Set arm to home position
    # HOME = (100, 0, 20)
    HOME = (200, 0, -10)
    swift.set_buzzer(1000, 0.5)
    swift.set_wrist(90)
    print("moving arm to home position...")
    pos_status = swift.set_position(*HOME, speed=100, wait=True)
    print("pos_status: ", pos_status)
    sleep(1)

    # === INITIALIZE SERIAL COMMUNICATION WITH ARDUINO ===
    # syringe_pump_serial = serial_connect("/dev/cu.usbmodem1441201", 19200, timeout=10)
    syringe_pump_serial = serial_connect("/dev/cu.usbmodem201", 19200, timeout=10)
    syringe_pump_serial.reset_output_buffer()

    # Serial Reader Thread
    class SerialReaderThread(threading.Thread):
        def run(self):
            while True:
                # Read output from ser
                output = syringe_pump_serial.readline().decode("ascii")
                print(output)
    
    serial_reader = SerialReaderThread()
    serial_reader.start()

    # Put the Stepper to SLEEP:
    syringe_pump_serial.write(b"S\n")

    # === COORDINATES & AMOUNTS ===
    # paint brush tip location coords (for the pipette: y should be -127 or less)
    tip_coords = (
        (149.1, -161.4, -87.2),
        (149.1, -160.5, -87.2), 
        (149.1, -159.6, -87.2),
    )

    tip_idx = 0

    # Paint and paintbrush and/or marker and/or pen locations and amountss (pressure)
    black = {
        "slow-thin": (
            {"concentration": "high", "pressure": 10, "location": (240.5, -149.41, 25)},
            {"concentration": "low", "pressure": 10, "location": (240.5, -165.41, 25)},
            {"concentration": "high", "pressure": 1, "location": (240.5, -149.41, 25)},
            {"concentration": "low", "pressure": 1, "location": (240.5, -165.41, 25)},
        ),
        "slow-thick": (
            {"concentration": "high", "pressure": 10, "location": (240.5, -181.41, 25)},
            {"concentration": "low", "pressure": 10, "location": (240.5, -197.41, 25)},
            {"concentration": "high", "pressure": 1, "location": (240.5, -181.41, 25)},
            {"concentration": "low", "pressure": 1, "location": (240.5, -197.41, 25)},
        ),
        "fast-thin": (
            {"concentration": "high", "pressure": 10, "location": (256.5, -149.41, 25)},
            {"concentration": "low", "pressure": 10, "location": (256.5, -165.41, 25)},
            {"concentration": "high", "pressure": 1, "location": (256.5, -149.41, 25)},
            {"concentration": "low", "pressure": 1, "location": (256.5, -165.41, 25)},
        ), 
        "fast-thick": (
            {"concentration": "high", "pressure": 10, "location": (256.5, -181.41, 25)},
            {"concentration": "low", "pressure": 10, "location": (256.5, -197.41, 25)},
            {"concentration": "high", "pressure": 1, "location": (256.5, -171.41, 25)},
            {"concentration": "low", "pressure": 1, "location": (256.5, -197.41, 25)},
        ),
    }
    green = {
        "slow-thin": (
            {"concentration": "high", "pressure": 10, "location": (172.5, -129.41, -5)},
            {"concentration": "low", "pressure": 10, "location": (172.5, -145.41, -5)},
            {"concentration": "high", "pressure": 1, "location": (172.5, -129.41, -5)},
            {"concentration": "low", "pressure": 1, "location": (172.5, -145.41, -5)},
        ),
        "slow-thick": (
            {"concentration": "high", "pressure": 10, "location": (172.5, -161.41, -5)},
            {"concentration": "low", "pressure": 10, "location": (172.5, -177.41, -5)},
            {"concentration": "high", "pressure": 1, "location": (172.5, -161.41, -5)},
            {"concentration": "low", "pressure": 1, "location": (172.5, -177.41, -5)},
        ), 
        "fast-thin": (
            {"concentration": "high", "pressure": 10, "location": (188.5, -129.41, -5)},
            {"concentration": "low", "pressure": 10, "location": (188.5, -145.41, -5)},
            {"concentration": "high", "pressure": 1, "location": (188.5, -129.41, -5)},
            {"concentration": "low", "pressure": 1, "location": (188.5, -145.41, -5)},
        ), 
        "fast-thick": (
            {"concentration": "high", "pressure": 10, "location": (188.5, -161.41, -5)},
            {"concentration": "low", "pressure": 10, "location": (188.5, -177.41, -5)},
            {"concentration": "high", "pressure": 1, "location": (188.5, -161.41, -5)},
            {"concentration": "low", "pressure": 1, "location": (188.5, -177.41, -5)},
        ), 
    }

    # Plate location -> CHANGING to Canvas Location (center)
    canvas_coords = ((265, 0, -17), (266, 0, -17))

    # Trash location 
    trash_coords = (270, -175, 50)

    # === LOAD WORLD MODEL ===
    print("loading world model...")

    # AI Model stuff removed for now - ONLY Robotic Arm Control for now..

    # === CAPTURE IMAGES, DO MODEL PREDICTION & CONTROLLER ACTIONS ===
    # main program loop
    # capture a frame and show it to the rl model
    # (make sure camera is set to 1:1 ratio & check the dimensions of the frames to confirm)
    # then get an action from the model's controller
    # actions consist of location and attract/repellent (including amount and concentration)
    # can also be "null" or "None" action (i.e. do nothing)
    try:
        while True:
            timestr = time.strftime("%Y%m%d-%H%M%S")
            currTime = time.time()

            # === IMAGE CAPTURE ===
            # with a DSLR/Mirrorless camera

            ### -- grab an image, show it to the world model and get an action --
            if currTime - prevTime >= INTERVAL:
                prevTime = currTime
                print("Capturing image...")
                file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
                print(
                    "Camera file path: {0}/{1}".format(file_path.folder, file_path.name)
                )
                # Rename the file with a timestamp
                if file_path.name.lower().endswith(".jpg"):
                    new_filename = "{}.jpg".format(timestr)
                target = os.path.join("./captures", new_filename)
                print("Copying image to", target)
                camera_file = camera.file_get(
                    file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL
                )
                camera_file.save(target)
                print("image saved")
                # load in image
                img = loadImg(target)
                img_array = loadImg(target, gray=True)
                #img_array = cv2.imread(img_path)

                #resize
                #img_array = cv2.imread(img)
                #img_array = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
                img_array = cv2.resize(img_array, (img_height, img_width), interpolation=cv2.INTER_AREA)
                img_array = img_array.reshape(-1, img_height, img_width, 1)

                # show image to world model & get action
                # this will inlcude the plate coords and the attractant/repellent to drop

                ### --- run the image through the models --- ###

                print("showing image to world model and getting next action...")

                font = cv2.FONT_HERSHEY_PLAIN # cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(img, "Capturing image and showing it to world model...", (10, 450), font, 1, (255, 255, 0), 1, cv2.LINE_AA)
                
                # predictions by each piece of the model
                #z = encoder.predict(img_array) # encode image
                print("predicted z: ")
                #print(z)

                # show predicted image
                #decoded_img = decoder.predict(np.array([z[0][0]]))
                #decoded_img = decoder.predict(np.array(z))
                #decoded_img_reshaped = decoded_img.reshape(img_height, img_width)
                # show image full screen
                cv2.namedWindow("Articulations", cv2.WINDOW_NORMAL)
                cv2.setWindowProperty("Articulations", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                cv2.imshow("Articulations", img_array)

                #z = z.reshape(-1, 1, 2048) # reshape for rnn
                #zprime = rnn.predict(z) # make prediction (of future image/state)
                #z_and_zprime = np.reshape(np.concatenate((z[0][0], zprime[0][0])), (1, z_len*2))[None,:,:] # concat for controller
                #action = ctrl.predict(z_and_zprime) # controller returns an action

                # World Model Results
                print("z (encoder): ", 3.14)
                print("z' (rnn prediction): ", 6.28)
                print("action: ", 2)

                cv2.putText(img, "z (encoder): " + str(3.14), (10, 470), font, 1, (255, 255, 0), 1, cv2.LINE_AA)
                cv2.putText(img, "z' (rnn prediction): " + str(6.28), (10, 490), font, 1, (255, 255, 0), 1, cv2.LINE_AA)
                cv2.putText(img, "action: " + str(2), (10, 510), font, 1, (255, 255, 0), 1, cv2.LINE_AA)


                # To Simulate the Controller Making Predictions: Random Action
                # action = np.randint(0,8)

                sleep(1)
                
                cv2.putText(img, "taking action... ", (10, 530), font, 1, (255, 255, 0), 1, cv2.LINE_AA)


                print("moving arm into place...")
                swift.set_buzzer(1500, 0.25)
                swift.set_buzzer(1500, 0.25)
                # Move arm to paint brush location and pick it up
                swift.set_position(
                    tip_coords[tip_idx][0], 
                    tip_coords[tip_idx][1], 
                    z=15.24, 
                    speed=20,
                    timeout=30,
                    wait=True,
                )
                # current brush/pen location
                swift.set_position(
                    z=tip_coords[tip_idx][2] + 19, speed=20, timeout=30, wait=True
                )
                # acquire brush
                swift.set_position(
                    z=tip_coords[tip_idx][2] + 9, speed=2, wait=True
                )
                # acquire brush... slowly
                swift.set_position(
                    z=tip_coords[tip_idx][2] + 4, speed=2, timeout=30, wait=True
                )
                # acquire bursh
                swift.set_position(
                    z=tip_coords[tip_idx][2], speed=1, timeout=30, wait=True
                )
                # acquire brush... got it
                sleep(1)
                swift.set_position(
                    z=tip_coords[tip_idx]][2] + 60, speed=2, timeout=30, wait=True
                )
                # go back up
                sleep(0.1)
                swift.set_position(z=35.24, speed=50, timeout=30, wait=True)
                sleep(1)

                # increment brush location
                tip_idx += 1

                # move arm to location of mark making selected by RL controller
                curr_solution_loc = black["fast-thin"][0]["location"]
                print("moving black paint to make mark on canvas")
                swift.set_position(
                    x=curr_solution_loc[0],
                    y=curr_solution_loc[1], 
                    z=40,
                    speed=200,
                    timeout=30,
                    wait=True,
                )
                # current paint - black or green
                swift.set_position(z=curr_solution_loc[2] + 19, speed=20, timeout=30, wait=True)
                swift.set_position(z=curr_solution_loc[2] + 9, speed=3, timeout=30, wait=True)
                swift.set_position(
                    z=curr_solution_loc[2] + 4, speed=3, timeout=30, wait=True
                )
                # get closer
                swift.set_position(
                    z=curr_solution_loc[2], speed=3, timeout=30, wait=True
                )
                # To DO: need to CONTROL the BRUSH Gripper
                # extract paint
                syringe_pump_serial.write(b"s\n")





if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--interval",
        type=int,
        required=False,
        default=1800,
        help="timelapse interval (default=1800 seconds (30 minutes))",
    )
    args = parser.parse_args()

    print(" ")
    sys.exit(main())



