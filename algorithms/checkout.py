def checkout(detections, config, my_class_names):
    counter = 0
    for det in detections:
        class_idx = int(det[5].item())  # Class index is the 5th element
        if class_idx in my_class_names:  # is in my list?
            counter += 1  # Increment the counter for this class
    return (counter*config['avg_processing_time'])/config['num_lanes']