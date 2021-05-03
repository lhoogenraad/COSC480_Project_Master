from PIL import Image, ImageTk, ImageEnhance
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from PIL import Image
import sys, getopt, os
import time
import tkinter as tk
import xml.etree.ElementTree as ET
from xml.dom import minidom
import cv2
print('starting file parser')

# Code adopted from run_labeller.py
# There will be a lot of adopted/inspired code from run_labller.py
def read_labels(folder):
    x = []

    for _, _, files in os.walk(folder):
        for file in files:
            extension = os.path.splitext(file)[1]
            if extension.lower() == '.xml':
                image_path = os.path.join(folder, file)
                x.append(image_path)
        break

    return x

# Finds all xml files and splits them into files that have
# been labelled and haven't been labelled
def find_labelled(file):
    labelled = []
    unlabelled = []
    #i is the iteration we are on
    # xml_file_name is the name of the xml file we are messing
    # around with
    for i, xml_file_name in enumerate(file):
        try:
            xml_tree = ET.parse(xml_file_name)
            xml_root = xml_tree.getroot()

            for object in xml_root.findall('object'):
                object_name = object.find('name').text

                if object_name != 'sheepface':
                    continue

                subobjFound = False
                for subobj in object.findall('subobj'):
                    subobjFound = True
                    break

                break

            if subobjFound:
                labelled.append(xml_file_name)
            else:
                unlabelled.append(xml_file_name)

        except:
            print("Failed to parse label file for %s." % xml_file_name)

    return labelled, unlabelled

def getXMLFile(filepath):
    xmltree = ET.parse(filepath)
    root = xmltree.getroot()
    return root

# Our current working directory.
currentdir = os.getcwd()
# The path to the file containing all the labels
labelsfile = read_labels(os.path.join(currentdir, "labels"))
# All the label xml files that have been labelled.
labelled = find_labelled(labelsfile)[0]

# The layout of the inputs we want to give the cnn file are such:
# We want 2 arrays, one of input images, and one of the labels.
# I haven't determined the dimensions of the image array
# For the labels array, each index will contain a 6 length array, determining,
# in order, the locations of the left eye, right eye, left nose, right nose,
# left mouth, right mouth.
# If any of the labels aren't present for the given image, a value of -1 should be given.
# (These dimensions may change based on what information we need for the labels e.g. x and y coords
# of mouth and nose labels)

img = Image.open('2020_06/ims/1022.18_315.jpg')


tree = ET.parse(labelled[0])
root = tree.getroot()

x1 = 0
y1 = 0
x2 = 0
y2 = 0

# iterate through xml tree
for node in root:
    # Find node named object
    if node.tag == 'object':
        for obj_child in node:
            # Find the bndbox node inside the object node
            if obj_child.tag == 'bndbox':
                # Extract the dimensions of the bndbx for the purposes of cropping the
                # image around the face of the sheep
                for bb in obj_child:
                    if bb.tag == 'xmin':
                       x1 = int(bb.text)
                    elif bb.tag == 'ymin':
                        y1 = int(bb.text)
                    elif bb.tag == 'xmax':
                        x2 = int(bb.text)
                    elif bb.tag == 'ymax':
                        y2 = int(bb.text)


img_cropped = img.crop((x1, y1, x2, y2))

plt.imshow(img)
plt.imshow(img_cropped)
plt.show()
