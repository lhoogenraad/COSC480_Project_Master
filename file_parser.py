from PIL import Image, ImageTk, ImageEnhance
import numpy as np
# import matplotlib.pyplot as plt
import sys, getopt, os
import time
import tkinter as tk
import xml.etree.ElementTree as ET
from xml.dom import minidom
import cv2


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