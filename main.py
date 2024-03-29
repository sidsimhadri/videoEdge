import argparse
import numpy as np
import cv2
import torch
from algorithms.gas import gas
from algorithms.checkout import checkout
from algorithms.parking import parking
import threading
import time
import requests
from config_manager import ConfigManager

algos= {
        "gas": gas,
        "checkout": checkout,
        "parking": parking
}
feeds= {
    "mp4": {"gas": "./videos/gas.mp4",
            "parking": "./videos/parking.mov",
            "checkout": "./videos/checkout.mp4",},
    "camera": 0}
stream = []
stream_lock = threading.Lock()

def register_with_server(url, client_info):
    try:
        response = requests.post(f"{url}/client", json=client_info)
        print("Server response status code:", response.status_code)
        print("Raw server response:", response.text)  # This line prints the raw response
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to register with server: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error during registration: {e}")
        return None
    except ValueError as e:
        print(f"JSON decoding error: {e}, Response: '{response.text}'")
        return None

def safe_ping_server(client_id, frequency, url):
    while True:
        time.sleep(frequency)
        with stream_lock:
            if stream:
                value = sum(stream) / len(stream)
                stream.clear()
                try:
                    response = requests.post(f"{url}/client/ping", json={"clientId": client_id,"value": value})
                    print(f"Sent to API: {response.text}") 
                except requests.RequestException as e:
                    print(f"Failed to send data: {e}")


# TODO fix this broken function and use
def filter_detections_by_zone(detections, coordinates):
    filtered_detections = []
    for detection in detections:
        x, y = detection[:2]
        if any(abs(x - coord[0]) < 10 and abs(y - coord[1]) < 10 for coord in coordinates):
            filtered_detections.append(detection)
    return filtered_detections

#not necessary in production, only for demo
def display_results(results):
    frame_with_results = np.squeeze(results.render())
    frame_bgr = cv2.cvtColor(frame_with_results, cv2.COLOR_RGB2BGR)
    cv2.imshow('Vehicle Detection', frame_bgr)
    cv2.waitKey(1)

config_manager = ConfigManager()

def main(feed, algorithm, config, frequency, url, name):
    ##########comment out this codeblock for local development######################
    client_info = {"name": name, "type": algorithm, "configuration": config}
    client_id = register_with_server(url, client_info)
    if client_id is None:
        print("Failed to register client. Exiting.")
        return
    #################################################################################
    ping_thread = threading.Thread(target=safe_ping_server, args=(client_id, frequency, url,))
    ping_thread.daemon = True
    ping_thread.start()
    model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
    if feed == "mp4":
        feedObj = feeds[feed][algorithm]
    else:
        feedObj = feeds[feed]
    cap = cv2.VideoCapture(feedObj)
    configObj = config_manager.get_config(algorithm, config)
    if not cap.isOpened():
        print("Error: Unable to stream.")
        return
    while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Unable to read frame. Exiting.")
                break
            # Convert frame to the RGB format that PyTorch expects
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            my_class_names = {idx: name for idx, name in model.names.items() if name in configObj['search']}
            results = model(frame_rgb)
            #dont display results in prod
            display_results(results)
            detections = model(frame_rgb).xyxy[0]
            curWaitTime = algos[algorithm](detections, configObj, my_class_names)
            #dont print in prod, just broadcast
            print(curWaitTime)
            with stream_lock:
                stream.append(curWaitTime)
            if feed == "mp4":
                #loop to simulate camera for testing
                if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    cap.release()
    cv2.destroyAllWindows()

feed_options = ['mp4', 'camera']
algo_options = ['gas', 'parking', 'checkout']
config_options = {'gas': ['default', 'heavy'], 'parking':['default'], 'checkout':['default']}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process video feeds based on site type, video feed, and site configuration.")
    parser.add_argument("site_type", choices=algo_options,  help="The site type to process.")
    parser.add_argument("feed", choices=feed_options,  help="The type of feed to process (mp4 or camera).")
    parser.add_argument("name",  help="Name of the client instance")
    parser.add_argument("--frequency", type=int, default=10, help="API update frequency in seconds (optional).")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8080", help="URL to post to (optional).")
    args = parser.parse_args()
    config = config_options.get(args.site_type, ['default'])[0] # Selects the first config option as default

    main(feed=args.feed, algorithm=args.site_type, config=config, frequency=args.frequency, url=args.url, name=args.name)