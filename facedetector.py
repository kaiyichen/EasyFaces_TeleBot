import cv2

def convert(image):
  imagePath = image

  image = cv2.imread(imagePath)
  gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

  faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
  faces = faceCascade.detectMultiScale(
          gray,
          scaleFactor=1.1,
          minNeighbors=8,
          minSize=(30, 30),
          maxSize=(512, 512)
  )

  print("[INFO] Found {0} Faces!".format(len(faces)))

  cropped_faces = []
  counter = 0
  for (x, y, w, h) in faces:
    roi_color = image[y:y + h, x:x + w]
    roi_color_resize = cv2.resize(roi_color, (512, 512))
    cropped_faces.append(cv2.imencode('.png', roi_color_resize)[1].tostring())
    counter += 1

  return cropped_faces

 

