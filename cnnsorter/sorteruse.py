import torch
import glob
import os
import shutil
import platform
from torch.autograd import Variable
from PIL import Image
import numpy as np
from multiprocessing import Process, cpu_count
import cnnsorter.sortercnn as sorter  # Assuming this is a custom module you've created
from datetime import datetime, date

# Get the path of the current directory
dir_path = os.path.dirname(os.path.realpath(__file__))

# Prediction function
def prediction(img_path, transformer, model, classes):
    image = Image.open(img_path)
    image_tensor = transformer(image).float()
    image_tensor = image_tensor.unsqueeze_(0)

    if torch.cuda.is_available():
        image_tensor.cuda()
    input = Variable(image_tensor)
    output = model(input)
    index = output.data.numpy().argmax()
    pred = classes[index]
    return pred

def sort(images_path, classes, model, filtered_save_dir):
    for image in images_path:
        if prediction(image, sorter.transformer, model, classes) == classes[0]:
            print("[+] Passed:", os.path.basename(image))
            shutil.move(image, filtered_save_dir)
        else:
            print("[-] Failed:", os.path.basename(image))
            os.remove(image)

def run_sorter():
    print("BINARY SORT STARTED")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    cores = cpu_count()
    images_path = glob.glob(os.path.join(os.getcwd(), 'datacollection', 'images', '*'))
    images_paths = np.array_split(images_path, cores)
    filtered_save_dir = os.path.join(dir_path, 'filtered')
    if not os.path.isdir(filtered_save_dir):
        os.mkdir(filtered_save_dir)

    # Categories
    classes = ['nanostructure', 'not']

    # Find the best state/model
    model_paths = glob.glob(os.path.join(dir_path, '*.model'))
    models = [os.path.basename(model) for model in model_paths]
    model_dates = [datetime.strptime(model[:10], '%Y-%m-%d').date() for model in models]
    datediff_dict = {abs(date.today() - model_date): model_date for model_date in model_dates}
    res = str(datediff_dict[min(datediff_dict.keys())])
    accuracy = 0
    for model in model_paths:
        if res in model and int(model[-8:-6]) > accuracy:
            best_model = model
            accuracy = int(model[-8:-6])
    checkpoint = torch.load(os.path.join(dir_path, best_model), map_location=device)

    # Load the model
    model = sorter.SorterCNN(num_classes=2)
    model.load_state_dict(checkpoint)
    model.eval()

    if platform.system() == 'Linux':
        sort(images_path, classes, model, filtered_save_dir)
    else:
        processes = []
        for i in range(cores):
            p = Process(target=sort, args=(images_paths[i], classes, model, filtered_save_dir))
            p.start()
            processes.append(p)

        for process in processes:
            process.join()

    print("PRELIMINARY SORTING FINISHED")

# Entry point of the script
if __name__ == "__main__":
    run_sorter()
