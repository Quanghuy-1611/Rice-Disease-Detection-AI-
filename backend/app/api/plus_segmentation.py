"""Compact DeepLabV3+ lesion segmenter for the Plus leaf-disease branch."""

from torch import nn
from torch.nn import functional as F
from torchvision import models


def conv_bn_relu(in_channels: int, out_channels: int, kernel: int,
                 dilation: int = 1) -> nn.Sequential:
    padding = (kernel // 2) * dilation
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, kernel, padding=padding,
                  dilation=dilation, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True),
    )


class DeepLabV3Plus(nn.Module):
    """MobileNetV3 encoder, ASPP at stride 16, low-level stride 4 decoder."""

    def __init__(self):
        super().__init__()
        self.encoder = models.mobilenet_v3_large(weights=None).features
        self.aspp = nn.ModuleList([
            conv_bn_relu(112, 64, 1),
            conv_bn_relu(112, 64, 3, dilation=3),
            conv_bn_relu(112, 64, 3, dilation=6),
            conv_bn_relu(112, 64, 3, dilation=9),
        ])
        self.context = conv_bn_relu(112, 64, 1)
        self.aspp_project = conv_bn_relu(320, 128, 1)
        self.low_project = conv_bn_relu(24, 32, 1)
        self.decoder = nn.Sequential(
            conv_bn_relu(160, 96, 3),
            conv_bn_relu(96, 64, 3),
            nn.Conv2d(64, 1, 1),
        )

    def forward(self, image):
        low = None
        x = image
        for index, layer in enumerate(self.encoder):
            x = layer(x)
            if index == 3:
                low = x
            if index == 12:
                break
        pooled = self.context(F.adaptive_avg_pool2d(x, 1))
        pooled = F.interpolate(pooled, size=x.shape[-2:], mode="bilinear", align_corners=False)
        high = self.aspp_project(torch_cat([branch(x) for branch in self.aspp] + [pooled]))
        high = F.interpolate(high, size=low.shape[-2:], mode="bilinear", align_corners=False)
        logits = self.decoder(torch_cat([high, self.low_project(low)]))
        return F.interpolate(logits, size=image.shape[-2:], mode="bilinear", align_corners=False)


def torch_cat(parts):
    # Import locally keeps this module easy to load alongside different torch builds.
    import torch
    return torch.cat(parts, dim=1)
