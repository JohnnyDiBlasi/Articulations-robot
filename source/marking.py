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
