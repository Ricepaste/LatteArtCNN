import torch
import time
import os
import copy
from torchvision import datasets, transforms
import torch.optim as optim
from torch.optim import lr_scheduler
from torchvision.io import read_image
import torchvision.models as models
from torchvision.models import EfficientNet_B1_Weights
from torch.utils.tensorboard import SummaryWriter

# TODO dataLoader's label need to custom

writer = SummaryWriter('runs/efficientnet_b1')

# 同時含訓練/評估


def train_model(model, criterion, optimizer, scheduler, num_epochs=25):
    since = time.time()

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0
    best_loss = 10000

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch, num_epochs - 1))
        print('-' * 10)

        # Each epoch has a training and validation phase
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()  # Set model to training mode
            else:
                model.eval()   # Set model to evaluate mode

            running_loss = 0.0
            running_corrects = 0

            # 逐批訓練或驗證
            for inputs, labels in dataloaders[phase]:
                inputs = inputs.to(device)
                labels *= 4
                labels = labels.to(device)

                # zero the parameter gradients
                optimizer.zero_grad()

                # 訓練時需要梯度下降
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    outputs = outputs.float()

                    outputs = outputs.squeeze(1)
                    labels = labels.float()
                    loss = criterion(outputs, labels)

                    print(outputs, labels)
                    print('loss:\n', loss)

                    # 訓練時需要 backward + optimize
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                # 統計損失
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
            if phase == 'train':
                scheduler.step()

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]

            if phase == 'train':
                writer.add_scalar('training loss', epoch_loss, epoch)
                writer.add_scalar('training accuracy', epoch_acc, epoch)
            elif phase == 'val':
                writer.add_scalar('validation loss', epoch_loss, epoch)
                writer.add_scalar('validation accuracy', epoch_acc, epoch)

            print('{} Loss: {:.4f} Acc: {:.4f}'.format(
                phase, epoch_loss, epoch_acc))

            # 如果是評估階段，且準確率創新高即存入 best_model_wts
            if phase == 'val' and\
                    (epoch_acc >= best_acc or epoch_loss <= best_loss):
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())

        print()

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(
        (time_elapsed // 60), (time_elapsed % 60)))
    print(f'Best val Acc: {best_acc:4f}')

    # 載入最佳模型
    model.load_state_dict(best_model_wts)
    return model


# 訓練資料進行資料增補，驗證資料不需要
data_transforms = {
    'train': transforms.Compose([
        # transforms.Resize(256),  # null
        transforms.RandomResizedCrop(224),  # 資料增補 224
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        # transforms.Normalize([0.485, 0.456, 0.406],
        #                      [0.229, 0.224, 0.225])
    ]),
    'val': transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        # transforms.Normalize([0.485, 0.456, 0.406],
        #                      [0.229, 0.224, 0.225])
    ]),
}

# 準備資料集匯入器
# 使用 ImageFolder 可方便轉換為 dataset
data_dir = '.\\main\\cropPhoto'
image_datasets = {x: datasets.ImageFolder(os.path.join(data_dir, x),
                                          data_transforms[x])
                  for x in ['train', 'val']}
dataloaders = {x: torch.utils.data.DataLoader(image_datasets[x],
                                              batch_size=8,
                                              shuffle=True,
                                              num_workers=0)
               for x in ['train', 'val']}
dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'val']}
print(dataset_sizes)

for i, x in dataloaders['train']:
    print(i.shape)
    print(x)
    print(x.data)

# Step 1: Initialize model with the best available weights
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
weights = EfficientNet_B1_Weights.DEFAULT
model = models.efficientnet_b1(weights=weights)

# Step 2: Initialize the inference transforms
# 資料強化還沒有做，需要研究原轉換函數內容
preprocess = weights.transforms()
# print(preprocess)

# freeze all the parameters in the old model
for param in model.parameters():
    param.requires_grad = False

# print the model structure to see the last layer
# print('old top layer:', model._modules['classifier'], sep='\n')

# change the last layer of the model to fit our problem
model._modules['classifier'] = torch.nn.Sequential(
    # torch.nn.Dropout(p=0.2, inplace=False),
    torch.nn.Linear(1280, 1))

# print('new top layer for transfer learning',
#       model._modules['classifier'], sep='\n')

# 使用MSE作為損失函數，reduction='mean'表示計算均值，功能不明
criterion = torch.nn.MSELoss(reduction='mean')

# 定義優化器為隨機梯度下降，學習率為0.001，動量為0.9
optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9)
model = model.to(device)

# 每7個執行週期，學習率降 0.1
exp_lr_scheduler = lr_scheduler.StepLR(
    optimizer, step_size=7, gamma=0.1)

model = train_model(model, criterion, optimizer,
                    exp_lr_scheduler, num_epochs=200)

# ------------------------------train done--------------------------------

# start evaluating the model
model.eval()

# Step 3: Apply inference preprocessing transforms
img = read_image(".\\main\\cropPhoto\\cropPhotocrop_2.jpg")
batch = preprocess(img).unsqueeze(0).to(device)

# Step 4: Use the model and print the predicted category
# prediction = model(batch).squeeze(0).softmax(0)
prediction = model(batch).squeeze(0)
class_id = prediction.argmax().item()
score = prediction[class_id].item()
category_name = weights.meta["categories"][class_id]
print(f"{category_name}: {100 * score:.1f}%")

print(prediction.detach().cpu().numpy())
for i in range(prediction.detach().cpu().numpy().shape[0]):
    print(weights.meta["categories"][i])


# if __name__ == "__main__":
#     main()
