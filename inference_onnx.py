import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image

import os
import argparse
import warnings
import time

import onnxruntime
from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropImage
from src.utility import parse_model_name
warnings.filterwarnings('ignore')

def process_border_crop(img, bbox):
    x_min, y_min, width, height = bbox

    # Thêm viền đen vào ảnh ban đầu
    if x_min < 0 or y_min < 0:
        border_size = 256
    img_with_border = cv2.copyMakeBorder(img, border_size, border_size, border_size, border_size, cv2.BORDER_CONSTANT, value=[0, 0, 0])

    # Tính toán lại tọa độ của bounding box trên ảnh có viền
    x_min += border_size
    y_min += border_size

    # Cắt vùng ảnh cần thiết từ ảnh có viền
    cropped_img = img_with_border[y_min:y_min+height, x_min:x_min+width]
    return cropped_img

def process_crop_image_size(image, bounding_box, width_resize, height_resize):
    x1, y1, x2, y2 = bounding_box
    height_crop = y2 - y1
    width_crop = x2 - x1
    h_image = int(image.shape[0])
    w_image = int(image.shape[1])

    if height_crop < height_resize: 
        if width_crop < width_resize:
            x1_new = ((x2+x1)//2) - width_resize//2
            x2_new = ((x2+x1)//2) + width_resize//2
            y1_new = ((y2+y1)//2) - height_resize//2
            y2_new = ((y2+y1)//2) + height_resize//2
        else:
            x1_new = x1
            x2_new = x2
            y1_new = ((y2+y1)//2) - width_crop//2
            y2_new = ((y2+y1)//2) + width_crop//2
    else:
        if width_crop < width_resize:
            x1_new = ((x2+x1)//2) - height_crop//2
            x2_new = ((x2+x1)//2) + height_crop//2
            y1_new = y1
            y2_new = y2
        else:
            if height_crop > width_crop:
                x1_new = ((x2+x1)//2) - height_crop//2
                x2_new = ((x2+x1)//2) + height_crop//2
                y1_new = y1
                y2_new = y2
            else:
                x1_new = x1
                x2_new = x2
                y1_new = ((y2+y1)//2) - width_crop//2
                y2_new = ((y2+y1)//2) + width_crop//2
    if x1_new < 0 or y1_new < 0 or x2_new > w_image or y2_new > h_image:
        border_size = width_resize
        img_with_border = cv2.copyMakeBorder(image, border_size, border_size, border_size, border_size, cv2.BORDER_CONSTANT, value=[0, 0, 0])
        # Tính toán lại tọa độ của bounding box trên ảnh có viền
        x1_new += border_size
        x2_new += border_size
        y1_new += border_size
        y2_new += border_size
        # Cắt vùng ảnh cần thiết từ ảnh có viền
        image_crop = img_with_border[y1_new:y2_new, x1_new:x2_new]
    else:
        image_crop = image[y1_new:y2_new, x1_new:x2_new]
    # print(y1,y2,x1,x2)
    image_crop_resize = cv2.resize(image_crop, (width_resize,height_resize))

    return image_crop_resize


path = "/home/maicg/Downloads/msg-1329751329-12096" #khong co .jpg

def to_input(pil_rgb_image):
    np_img = np.array(pil_rgb_image, dtype = np.float32)
    # np_img = ((np_img / 255.) - 0.5) / 0.5
    # np_img = np_img / 255.
    try:
        np_img = np_img.swapaxes(1, 2).swapaxes(0, 1)
    except:
        print('error')
        return None
    np_img = np.reshape(np_img, [1, 3, 80, 80])
    
    # tensor = torch.tensor([brg_img.transpose(2,0,1)]).float()
    return np_img

def load_model_onnx(file_name):
    session = onnxruntime.InferenceSession(file_name, providers=['CUDAExecutionProvider'])
    return session

def take_image(image):
    height, width = image.shape[:2]
    if height / width != 4 / 3:
        if width > height:
            new_width = height * 3 // 4

            # Tính toán vị trí cắt
            x_offset = (width - new_width) // 2
            if x_offset < 0:
                x_offset = 0

            # Cắt ảnh
            cropped_image = image[:, x_offset:x_offset+new_width, :]
            cv2.imwrite('new_image.jpg', cropped_image)
            toado = [0, x_offset]
            return cropped_image, toado
        else:
            new_height = width * 4 // 3

            # Tính toán vị trí cắt
            y_offset = (height - new_height) // 2
            if y_offset < 0:
                y_offset = 0
            cropped_image = image[y_offset:y_offset+new_height, :, :]
            cv2.imwrite('new_image.jpg', cropped_image)
            toado = [y_offset, 0]
            return cropped_image, toado

app = FaceAnalysis(providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
img = ins_get_image(path)
faces = app.get(img)
rimg = app.draw_on(img, faces)
cv2.imwrite("./t1_output.jpg", rimg)

for face in faces:
    bbox = face.bbox.astype(np.int)
    x, y, x2, y2 = bbox
    cv2.rectangle(img, (x, y), (x2, y2), (0, 255, 0), 2)
    image = cv2.imread(path + ".jpg")
    img_crop = process_crop_image_size(image, bbox, 1800,1800)
    cv2.imshow('img_crop', img_crop)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

cv2.imshow('Faces', img)
cv2.waitKey(0)
cv2.destroyAllWindows()

print(x, y, x2, y2)



height, width = image.shape[:2]
d_org_x2 = width - x2
d_org_y2 = height - y2
print(d_org_x2)

if x<d_org_x2:
    x_start = 0
    x_end = x2 + x
else:
    x_start = x - d_org_x2
    x_end = width

if y < d_org_y2:
    y_start = 0
    y_end = y2 + y
else:
    y_start = y - d_org_y2
    y_end = height


crop_img = image[y_start:y_end, x_start:x_end]

new_bbox_x = x - x_start
new_bbox_y = y - y_start
new_bbox_width = x2 -x
new_bbox_height = y2 -y

cv2.imshow('crop', crop_img)
cv2.waitKey(0)
cv2.destroyAllWindows()

process_image, toado = take_image(crop_img)
new_bbox_x = new_bbox_x - toado[1]
new_bbox_y = new_bbox_y - toado[0]

cv2.imshow('process_crop', process_image)
cv2.waitKey(0)
cv2.destroyAllWindows()

def test(image, model_dir, device_id):
    # model_test = AntiSpoofPredict(device_id)
    image_cropper = CropImage()
    # image_bbox = model_test.get_bbox(image)
    # print("image_bbox: ", image_bbox)
    image_bbox = [new_bbox_x, new_bbox_y, new_bbox_width, new_bbox_height]
    print("image_bbox: ", image_bbox)
    prediction = np.zeros((1, 3))
    test_speed = 0
    # sum the prediction from single model's result
    for model_name in os.listdir(model_dir):
        path_model = os.path.join(model_dir,model_name)
        h_input, w_input, model_type, scale = parse_model_name(model_name)
        param = {
            "org_img": image,
            "bbox": image_bbox,
            "scale": scale,
            "out_w": w_input,
            "out_h": h_input,
            "crop": True,
        }
        if scale is None:
            param["crop"] = False
        img = image_cropper.crop(**param)
        cv2.imshow('image_crop', img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        print("shape: ", img.shape)
        print(h_input, w_input, model_type, scale)
        input = to_input(img)
        start = time.time()
        session = load_model_onnx(path_model)
        results = session.run(['output'], {'input': input})
        rs = results[0]
        softmax_x = np.exp(rs) / np.sum(np.exp(rs), axis=1, keepdims=True)
        print(softmax_x)
        prediction += softmax_x
        test_speed += time.time()-start

    # draw result of prediction
    label = np.argmax(prediction)
    value = prediction[0][label]/2
    if label == 1:
        print("Image '{}' is Real Face. Score: {:.2f}.".format("image_name", value))
        result_text = "RealFace Score: {:.2f}".format(value)
        color = (255, 0, 0)
    else:
        print("Image '{}' is Fake Face. Score: {:.2f}.".format("image_name", value))
        result_text = "FakeFace Score: {:.2f}".format(value)
        color = (0, 0, 255)
    print("Prediction cost {:.2f} s".format(test_speed))
    cv2.rectangle(
        image,
        (image_bbox[0], image_bbox[1]),
        (image_bbox[0] + image_bbox[2], image_bbox[1] + image_bbox[3]),
        color, 2)
    cv2.putText(
        image,
        result_text,
        (image_bbox[0], image_bbox[1] - 5),
        cv2.FONT_HERSHEY_COMPLEX, 0.5*image.shape[0]/1024, color)
    
    cv2.imwrite("results.jpg", image)


if __name__ == "__main__":
    desc = "test"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        "--device_id",
        type=int,
        default=0,
        help="which gpu id, [0/1/2/3]")
    parser.add_argument(
        "--model_dir",
        type=str,
        default="./onnx_cu",
        help="model_lib used to test")
    parser.add_argument(
        "--image_name",
        type=str,
        default="image_F1.jpg",
        help="image used to test")
    args = parser.parse_args()
    test(process_image, args.model_dir, args.device_id)


