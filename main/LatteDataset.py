from torch.utils.data.dataset import Dataset
import pandas as pd
import random
import numpy as np
import os
from PIL import Image
import cv2


class TonyLatteDataset(Dataset):
    def __init__(self, root, transform, x):
        # --------------------------------------------
        # Initialize paths, transforms, and so on
        # --------------------------------------------
        self.transform = transform
        self.root = root

        # 讀取每個label的抽樣機率
        arr = pd.read_csv('./LabelTool/label_probability.csv', header=None)
        arr = np.array(arr.values).flatten().tolist()

        # Load image path and annotations
        files = os.listdir(root+"\\images")
        self.imgs = ['{}\\images\\{}'.format(
            root, filename) for filename in files]

        files = os.listdir(root+"\\labels")
        for i in range(len(files)):
            files[i] = files[i].replace('jpg', 'txt')
        self.lbls = ['{}\\labels\\{}'.format(
            root, filename) for filename in files]

        if (x == 'train'):
            assert len(self.imgs) == len(
                self.lbls), 'images & labels mismatched length!'

            Sum_of_every_label = [0 for i in range(11)]
            # 讀取label，並統計每個label的數量
            for i in range(len(self.imgs)):
                with open(self.lbls[i], 'r') as f:
                    # 對讀取的label進行四捨五入
                    lbl = int(np.round(float(f.read())))
                    Sum_of_every_label[lbl] += 1
            print("Amount of every label:")
            print(Sum_of_every_label)

            stratify_imgs = []
            stratify_lbls = []
            Sum_of_every_label_stratified = [0 for i in range(11)]
            # 讀取label，並依照抽樣機率進行抽樣
            for i in range(len(self.imgs)):
                with open(self.lbls[i], 'r') as f:
                    # 對讀取的label進行四捨五入
                    lbl = int(np.round(float(f.read())))
                    thd = random.random()
                    if (thd <= arr[lbl]):
                        stratify_imgs.append(self.imgs[i])
                        stratify_lbls.append(self.lbls[i])
                        Sum_of_every_label_stratified[lbl] += 1
            print("Amount of every label after stratified:")
            print(Sum_of_every_label_stratified)

            self.imgs = stratify_imgs
            self.lbls = stratify_lbls

        assert len(self.imgs) == len(
            self.lbls), 'images & labels mismatched length!'

    def __getitem__(self, index):
        # --------------------------------------------
        # 1. Read from file (using numpy.fromfile, PIL.Image.open)
        # 2. Preprocess the data (torchvision.Transform)
        # 3. Return the data (e.g. image and label)
        # --------------------------------------------

        # # 定期重新抽樣資料庫
        # if (index != 0 and index % 10 == 0):
        #     self.restratify()

        imgpath = self.imgs[index]
        img = Image.open(imgpath).convert('RGB')
        with open(self.lbls[index], 'r') as f:
            lbl = float(f.read())

        # 4. 雙邊濾波
        open_cv_image = np.array(img)
        # Convert RGB to BGR
        open_cv_image = open_cv_image[:, :, ::-1].copy()
        open_cv_image = cv2.bilateralFilter(open_cv_image, 20, 50, 100)
        img = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)

        # lbl = int(self.lbls[index])
        if self.transform is not None:
            img = self.transform(img)

        # print(self.imgs[index], lbl)
        return img, lbl

    def __len__(self):
        # --------------------------------------------
        # Indicate the total size of the dataset
        # --------------------------------------------
        return len(self.imgs)

    def restratify(self):
        # 定期重新抽樣資料庫
        # 讀取每個label的抽樣機率
        arr = pd.read_csv('./LabelTool/label_probability.csv', header=None)
        arr = np.array(arr.values).flatten().tolist()

        # Load image path and annotations
        files = os.listdir(self.root+"\\images")
        self.imgs = ['{}\\images\\{}'.format(
            self.root, filename) for filename in files]

        files = os.listdir(self.root+"\\labels")
        for i in range(len(files)):
            files[i] = files[i].replace('jpg', 'txt')
        self.lbls = ['{}\\labels\\{}'.format(
            self.root, filename) for filename in files]

        assert len(self.imgs) == len(
            self.lbls), 'images & labels mismatched length!'

        Sum_of_every_label = [0 for i in range(11)]
        # 讀取label，並統計每個label的數量
        for i in range(len(self.imgs)):
            with open(self.lbls[i], 'r') as f:
                # 對讀取的label進行四捨五入
                lbl = int(np.round(float(f.read())))
                Sum_of_every_label[lbl] += 1
        print("Amount of every label:")
        print(Sum_of_every_label)

        stratify_imgs = []
        stratify_lbls = []
        Sum_of_every_label_stratified = [0 for i in range(11)]
        # 讀取label，並依照抽樣機率進行抽樣
        for i in range(len(self.imgs)):
            with open(self.lbls[i], 'r') as f:
                # 對讀取的label進行四捨五入
                lbl = int(np.round(float(f.read())))
                thd = random.random()
                if (thd <= arr[lbl]):
                    stratify_imgs.append(self.imgs[i])
                    stratify_lbls.append(self.lbls[i])
                    Sum_of_every_label_stratified[lbl] += 1
        print("Amount of every label after stratified:")
        print(Sum_of_every_label_stratified)

        self.imgs = stratify_imgs
        self.lbls = stratify_lbls

        assert len(self.imgs) == len(
            self.lbls), 'images & labels mismatched length!'
