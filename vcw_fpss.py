import sys,os
sys.path.append(os.path.join(os.getcwd(), '.'))
import aditofpython.aditofpython as tof
import numpy as np
import cv2 as cv
import argparse
from enum import Enum
import csv
import matplotlib.pyplot as plt
import time
from time import perf_counter
# import sys

WINDOW_NAME_DEPTH = "Display Depth"
WINDOW_NAME_COLOR = "Display Color"
configFile = "aditofpython/tof-viewer_config.json"


class ModesEnum(Enum):
    MODE_NEAR = 0
    MODE_MEDIUM = 1
    MODE_FAR = 2

def get_data(data_list, data):
    raw_data = data[1:len(data)-1]
    # print (raw_data)
    data_con = raw_data.split(", ")
    # print (data_con)

    
    for i in data_con :
        i_int = int(float (i))
        data_list.append(i_int)
    y_axis = data_list
    x_axis = [x for x in range (len(y_axis))]

    plt.plot(x_axis, y_axis)
    plt.show()

    plt.close()
    
if __name__ =="__main__":
    system = tof.System()

    cameras = []
    status = system.getCameraListAtIp(cameras,"10.42.0.1")
    if not status:
        print("system.getCameraList() failed with status: ", status)
    status = cameras[0].setControl("initialization_config", configFile)
    if not status:
        print("cameras[0].setControl() failed with status: ", status)
        
    status = cameras[0].initialize()
    if not status:
        print("cameras[0].initialize() failed with status: ", status)

    modes = []
    status = cameras[0].getAvailableModes(modes)
    if not status:
        print("system.getAvailableModes() failed with status: ", status)

    status = cameras[0].setMode(modes[ModesEnum.MODE_MEDIUM.value])
    if not status:
        print("cameras[0].setMode() failed with status: ", status)

    print (f"\nstatus {status} setMode\n")

    types = []
    status = cameras[0].getAvailableFrameTypes(types)
    if not status:
        print("system.getAvailableFrameTypes() failed with status: ", status)

    print (f"\nstatus {status}getavailableframetype {types} \n")

    status = cameras[0].setFrameType(types[0]) # types[2] is 'mp_pcm' type.
    
    print (f"\nstatus {status} the error is{cameras[0].setFrameType(types[0])}\n ")
    
    if not status:
        print("cameras[0].setFrameType() failed with status:", status)
    
    status = cameras[0].start()
    if not status:
        print("cameras[0].start() failed with status:", status)
   
    camDetails = tof.CameraDetails()
    status = cameras[0].getDetails(camDetails)
    if not status:
        print("system.getDetails() failed with status: ", status)

    # Enable noise reduction for better results
    smallSignalThreshold = 100
    cameras[0].setControl("noise_reduction_threshold", str(smallSignalThreshold))

    camera_range = 5000
    bitCount = 9
    frame = tof.Frame()

    max_value_of_IR_pixel = 2 ** bitCount - 1
    distance_scale_ir = 255.0 / max_value_of_IR_pixel
    distance_scale = 255.0 / camera_range

    # Time -initial
    prev_frame_time = 0
    new_frame_time = 0

    pre_fps = 0
    smoothing = 0.9
    
    before_get_data = 0
    after_get_data = 0

    ir_prev_time = 0
    ir_aft_time = 0
    
    dp_prev_time = 0
    
    # Data stamps -initial
    save_fps = []
    save_time = []

    while True:
        # Capture frame-by-frame
        status = cameras[0].requestFrame(frame)
        if not status:
            print("cameras[0].requestFrame() failed with status: ", status)

        # Capture depth -frame -time
        dp_prev_time = time.perf_counter()
        depth_data = frame.getData("depth")
        after_get_data = perf_counter()
        dp_time = after_get_data - dp_prev_time
        
        # Capture ir -frame -time
        ir_prev_time = time.perf_counter()
        ir_data = frame.getData("ir")
        ir_aft_time = time.perf_counter()
        ir_time = ir_aft_time -ir_prev_time
        
        # Capture processing -time
        total_time = dp_time - ir_time
        display_total_time = "Processing Time: " + str(total_time)

        # Latency 
        latency = after_get_data - before_get_data
        before_get_data = after_get_data
        # latency = int(latency)


        depth_map = np.array(depth_data, dtype="uint16", copy=False)
        ir_map = np.array(ir_data, dtype="uint16", copy=False)

        new_shape = (int(depth_map.shape[0] / 2), depth_map.shape[1])
        depth_map = np.resize(depth_map, new_shape)
        depth_map = cv.flip(depth_map, 1)
        distance_map = depth_map
        depth_map = distance_scale * depth_map
        depth_map = np.uint8(depth_map)
        depth_map = cv.applyColorMap(depth_map, cv.COLORMAP_RAINBOW)

        # ir_map = ir_map[0: int(ir_map.shape[0] / 2), :]
        # ir_map = distance_scale_ir * ir_map
        # ir_map = np.uint8(ir_map)
        # ir_map = cv.flip(ir_map, 1)
        # ir_map = cv.cvtColor(ir_map, cv.COLORMAP_RAINBOW)


        # result = cv.addWeighted(ir_map, 0.4, depth_map, 0.6, 0)
    
        new_frame_time=perf_counter()

        acutal = 1 / (new_frame_time-prev_frame_time)
        prev_frame_time = new_frame_time

        fps = (pre_fps * smoothing) + (acutal * (1-smoothing))
        pre_fps = fps

        display_fps = "FPS: " + str(int(fps))

        save_fps.append(fps)
        save_time.append(total_time)

        # print (f"\nthe latency is : {latency}\n")
        print (f"FPS: {int(fps)}")
        print(display_total_time)
        
        cv.putText(depth_map, display_fps, (7, 30), cv.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv.LINE_8)
        cv.putText(depth_map, display_total_time, (7, 60), cv.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv.LINE_8)
        # cv.putText(depth_map, display_fps, (7, 90), cv.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv.LINE_8)
        
        cv.namedWindow(WINDOW_NAME_DEPTH, cv.WINDOW_AUTOSIZE)
        cv.imshow(WINDOW_NAME_DEPTH, depth_map)

        if cv.waitKey(1) >= 0:
            break
    
    # Fps data
    with open ("fps-log.txt","w") as file :
        file.write(str(save_fps))

    with open ("fps-log.txt","r") as file :
        fps_data = file.read()
    fps_data_list = []
    

    # Time data
    with open ("time-log.txt","w") as file :
        file.write(str(save_time))
    with open ("time-log.txt","r") as file :
        time_data = file.read()
    time_data_list = []

    get_data(fps_data_list, fps_data)
    get_data(time_data_list, time_data)
    


    




    
    




