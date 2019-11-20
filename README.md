

## START

### Clone this file
```bashrc
$ git clone https://github.com/buiduchanh/TF_yolov3.git
```

## Train your own dataset

### 1. Prepare Dataset
Two files are required as follows:

- [`dataset.txt`](https://github.com/buiduchanh/TF_yolov3/tree/master/data/dataset/voc_train.txt): 

```
xxx/xxx.jpg 18.19,6.32,424.13,421.83,20 323.86,2.65,640.0,421.94,20 
xxx/xxx.jpg 48,240,195,371,11 8,12,352,498,14
# image_path x_min, y_min, x_max, y_max, class_id  x_min, y_min ,..., class_id 
# make sure that x_max < width and y_max < height
```

- [`class.names`](https://github.com/buiduchanh/TF_yolov3/tree/master/data/classes/coco.names):

```
person
bicycle
car
...
toothbrush
```

### 2. Caculate Anchor

We provided file *kmeans.py* for caculate the anchor like [`coco_anchor.txt`](https://github.com/buiduchanh/TF_yolov3/blob/master/data/anchors/coco_anchors.txt)

### 3. Change config
```
Then edit your `./core/config.py` to make some necessary configurations

```bashrc
__C.YOLO.CLASSES                = "./data/classes/voc.names"
__C.TRAIN.ANNOT_PATH            = "./data/dataset/voc_train.txt"
__C.TEST.ANNOT_PATH             = "./data/dataset/voc_test.txt"

If you want to use MobileNetV2 as backbone instead of Darknet53 just set the parameters in config same as below
__C.YOLO.BACKBONE_MOBILE        = True
__C.YOLO.GT_PER_GRID            = 3
```
Here are two kinds of training method: 

### 4. Training

```bashrc
$ python train.py
$ tensorboard --logdir ./data
```
## Result

We will update this result asap

## Other Implementations

[-**`YOLOv3目标检测有了TensorFlow实现，可用自己的数据来训练`**](https://mp.weixin.qq.com/s/cq7g1-4oFTftLbmKcpi_aQ)<br>

[-**`Stronger-yolo`**](https://github.com/Stinky-Tofu/Stronger-yolo)<br>

[- **`Implementing YOLO v3 in Tensorflow (TF-Slim)`**](https://itnext.io/implementing-yolo-v3-in-tensorflow-tf-slim-c3c55ff59dbe)

[- **`YOLOv3_TensorFlow`**](https://github.com/wizyoung/YOLOv3_TensorFlow)

[- **`Object Detection using YOLOv2 on Pascal VOC2012`**](https://fairyonice.github.io/Part_1_Object_Detection_with_Yolo_for_VOC_2014_data_anchor_box_clustering.html)

[-**`Understanding YOLO`**](https://hackernoon.com/understanding-yolo-f5a74bbc7967)

