import os
import queue
import re
import time
import threading

import cv2
import face_recognition as face_recognition
import numpy as np
import requests


class VideoCapture:
    """
    class to capture buffered less video
    """

    def __init__(self, name):
        self.cap = cv2.VideoCapture(name)
        self.q = queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    def _reader(self):
        """
        read frames as soon as they are available, keeping only most recent one
        :return:
        """
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait()  # discard previous (unprocessed) frame
                except queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
        return self.q.get()


video_capture = VideoCapture(0)

know_face_encodings = []
know_face_names = []
know_faces_filenames = []

for (dirpath, dirnames, filenames) in os.walk('assets/img/users'):
    know_faces_filenames.extend(filenames)
    break

for filename in know_faces_filenames:
    face = face_recognition.load_image_file('assets/img/users' + filename)
    know_face_names.append(re.sub("[0-9]", '', filename[:-4]))
    know_face_encodings.append(face_recognition.face_encodings(face)[0])

face_locations = []
face_encodings = []
face_names = []
process_this_frame = True

while True:
    frame = video_capture.read()

    # process every frame only one time
    if process_this_frame:
        # Find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)

        # Initialize an array for the name of the detected users
        face_names = []

        # Initialize json to export
        json_to_export = {}

        for face_encoding in face_encodings:
            # See if the face is a match for the know face(s)
            matches = face_recognition.compare_faces(know_face_encodings, face_encoding)
            name = "Unknown"

            # use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(know_face_encodings, face_encoding)
            best_match_index = np.argmin()

            if matches[best_match_index]:
                name = know_face_names[best_match_index]
                # prepare json data
                json_to_export['name'] = name
                json_to_export['hour'] = f'{time.localtime().tm_hour}:{time.localtime().tm_min}'
                json_to_export[
                    'date'] = f'{time.localtime().tm_year}-{time.localtime().tm_mon}-{time.localtime().tm_mday}'
                json_to_export['picture_array'] = frame.tolist()

                r = requests.post(url='<host:port>/receive_data', json=json_to_export)
                print("Status: ", r.status_code)

            face_names.append(name)

    process_this_frame = not process_this_frame

    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

        # Draw a label with a name below the face
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    # Display the resulting image
    cv2.imshow('Video', frame)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release handle to the webcam
video_capture.release()
cv2.destroyAllWindows()
