import os
import cv2
import hashlib
import subprocess
import multiprocessing

BASH_SCRIPT = "./noided.sh"
FRAMES_DIR = "frames"
FRAMES_EXT = ".jpg"

def basename_to_int(filename):
    return int(os.path.splitext(os.path.basename(filename))[0])

def calc_hist(image_path):
    file = cv2.imread(image_path)
    hist = cv2.calcHist(file, [2], None, [256], [0, 256])

    return hist

def compare_hist(hist1, hist2):
    return cv2.compareHist(hist1, hist2, cv2.HISTCMP_BHATTACHARYYA)

def get_file_hash(file_path):
    hash = hashlib.md5()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            hash.update(chunk)

    return hash.hexdigest()

def extract_frames(video_path):
    video = cv2.VideoCapture(video_path)
    success, frame = video.read()
    count = 0
    
    while success:
        cv2.imwrite(os.path.join(FRAMES_DIR, f"{count}{FRAMES_EXT}"), frame)
        success, frame = video.read()
        count += 1

def delete_duped_frames(frame_arr):
    histograms = {}

    for i in range(len(frame_arr)):
        item = frame_arr[i]

        if item not in histograms:
            frame_path = os.path.join(FRAMES_DIR, item)
            histograms[item] = calc_hist(frame_path)
        
        h1 = histograms.get(item)

        for j in range(i + 1, len(frame_arr)):
            item2 = frame_arr[j]
            frame2_path = os.path.join(FRAMES_DIR, item2)

            if item2 not in histograms:
                histograms[item2] = calc_hist(frame2_path)
            
            h2 = histograms[item2]
            # compareHist returns a float from 0 to 1
            # 0 means equal, 1 means unequal
            # 0.0; 0.0001; ... ; 0.999; 1.0
            hist = compare_hist(h1, h2)
            
            if hist < 0.3:
                try:
                    os.remove(frame2_path)

                except OSError:
                    pass # XD

def init():
    is_noided = subprocess.run(BASH_SCRIPT).returncode
    video_path = None
    expected_md5 = None
    calculated_md5 = None

    if is_noided > 0:
        print(f"something wrong with {BASH_SCRIPT}.")
        exit(1)

    with open(BASH_SCRIPT, "r") as file:
        content = file.readlines()
        video_path = content[2].strip().split('#')[-1]
        expected_md5 = content[1].strip().split("#")[-1]

    calculated_md5 = get_file_hash(video_path)

    if expected_md5 != calculated_md5:
        print(f"file hashes don't match. expected '{expected_md5}' calculated '{calculated_md5}'.")
        exit(1)
    
    extract_frames(video_path)

def main():
    files = sorted(os.listdir(FRAMES_DIR), key=basename_to_int)
    cpu_count = os.cpu_count()
    chunk_size = len(files) // cpu_count
    remaining = len(files) % cpu_count
    start_index = 0
    end_index = chunk_size
    processes = []

    for i in range(cpu_count):
        if i == cpu_count - 1:
            end_index += remaining
        
        process = multiprocessing.Process(target=delete_duped_frames, args=(files[start_index:end_index],))
        process.start()
        processes.append(process)

        start_index = end_index
        end_index += chunk_size
    
    for i in processes:
        i.join()
    
if __name__ == "__main__":
    init()
    main()