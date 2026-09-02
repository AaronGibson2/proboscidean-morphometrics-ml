import os
import torch
import numpy as np
from pathlib import Path
from bioencoder.core import utils
import bioencoder

bioencoder.configure(
    root_dir="../bioencoder_wd",
    run_name="proboscidean_v1",
    create=True
)

# Load the trained model
ckpt_path = "../bioencoder_wd/weights/proboscidean_v1/first/swa"
backbone = "timm_resnet50"

model = utils.build_model(backbone, second_stage=False, num_classes=None, 
                          ckpt_pretrained=ckpt_path).cuda()
model.eval()

# Load all images and extract embeddings
from torchvision import transforms
from PIL import Image

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

image_dir = "../segmented_teeth"
embeddings = []
labels = []
filenames = []

for class_folder in sorted(Path(image_dir).iterdir()):
    if not class_folder.is_dir():
        continue
    for img_path in sorted(class_folder.glob("*.jpg")):
        img = Image.open(img_path).convert("RGB")
        tensor = transform(img).unsqueeze(0).cuda()
        with torch.no_grad():
            emb = model(tensor)
        embeddings.append(emb.cpu().numpy().flatten())
        labels.append(class_folder.name)
        filenames.append(img_path.stem)

embeddings = np.array(embeddings)
print(f"Embeddings shape: {embeddings.shape}")
print(f"Labels: {set(labels)}")

# Check for NaN
if np.isnan(embeddings).any():
    print("NaN detected — replacing with 0")
    embeddings = np.nan_to_num(embeddings)

# PCA first to reduce dimensions
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

pca = PCA(n_components=10)
embeddings_pca = pca.fit_transform(embeddings)

# t-SNE
tsne = TSNE(n_components=2, perplexity=5, random_state=42)
embeddings_2d = tsne.fit_transform(embeddings_pca)

# Plot with bokeh
from bokeh.plotting import figure, show, output_file
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.palettes import Category10

unique_labels = sorted(set(labels))
colors = Category10[max(3, len(unique_labels))]
color_map = {label: colors[i] for i, label in enumerate(unique_labels)}

source = ColumnDataSource(dict(
    x=embeddings_2d[:, 0].tolist(),
    y=embeddings_2d[:, 1].tolist(),
    label=labels,
    filename=filenames,
    color=[color_map[l] for l in labels]
))

p = figure(width=900, height=700, title="Proboscidean M3 — BioEncoder Embeddings (t-SNE)",
           tools="pan,wheel_zoom,box_zoom,reset,hover")

p.circle("x", "y", size=12, color="color", legend_field="label",
         alpha=0.8, source=source)

p.add_tools(HoverTool(tooltips=[("Specimen", "@filename"), ("Site", "@label")]))
p.legend.location = "top_left"

output_file("../proboscidean_tsne_plot.html")
show(p)
print("\nPlot saved to proboscidean_tsne_plot.html — open it in your browser!")