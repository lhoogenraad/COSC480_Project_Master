import file_parser
import os
from PIL import Image
import tensorflow as tf
import numpy as np

data = file_parser.get_inputs()
labels = data[0]
files = data[1]
img_files = []
imgs = []

print(labels)
print(files)

for file in files:
    img_files.append("compressed/" + os.path.basename(os.path.normpath(file))[:-4] + ".jpg")

for img_file in img_files:
    imgs.append(Image.open(img_file))


# All the above code is just sorting out input data #