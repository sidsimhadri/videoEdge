def gas(detections, config , my_class_names):
    counters = {value: 0 for value in my_class_names.values()}
    #FOR EACH DETECTION IN CURRENT FRAME!!!
    for det in detections:
        class_idx = int(det[5].item())  # Class index is the 5th element
        if class_idx in my_class_names:  # is in my list?
            class_name = my_class_names[class_idx]
            counters[class_name] += 1  # Increment the counter for this class
    return total_wait_time(counters, config)

def total_wait_time(counters, config):
    total_wait_time = 0
    for vehicle in counters:
        if vehicle in config['fill_times']:
            total_wait_time += counters[vehicle] * config['fill_times'][vehicle]
    return total_wait_time/config["pump_count"] 