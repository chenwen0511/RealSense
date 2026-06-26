# RealSense `.bag` 数据包说明

本文档整理 D435i 录制数据包 `data/20260530_151155.bag` 的检查结果，以及 Depth / Color 内参 **K** 为何不同。

---

## 一、检查 bag 包内容

### 1.1 脚本

仓库提供 [`scripts/inspect_bag.py`](scripts/inspect_bag.py)，用于查看 RealSense 专有 `.bag`（**不是** ROS bag）中包含的流、分辨率、内参 K、时长与帧数。

```bash
cd ~/stephen/RealSense

# 快速查看：设备信息、流、分辨率、K、时长
python3 scripts/inspect_bag.py data/20260530_151155.bag

# 扫描整包统计各流帧数（约十几秒）
python3 scripts/inspect_bag.py data/20260530_151155.bag --count-frames

# JSON 输出
python3 scripts/inspect_bag.py data/20260530_151155.bag --count-frames --json
```

可选参数：

| 参数 | 说明 |
|------|------|
| `bag` | `.bag` 路径，默认 `data/20260530_151155.bag` |
| `--count-frames` | 回放整包并统计各流帧数 |
| `--max-frames N` | 仅扫描前 N 组帧（快速测试） |
| `--json` | 以 JSON 打印 |

### 1.2 `20260530_151155.bag` 实测结果

| 项目 | 内容 |
|------|------|
| 文件大小 | **1.8 GB** |
| 时长 | **约 41.4 s** |
| 设备 | Intel RealSense **D435I** |
| 序列号 | 349622073221 |
| 固件 | 5.15.1.55 |
| USB | 3.2 |

**包含的数据流（仅 2 路，无 IMU）：**

| 流 | 格式 | 分辨率 | FPS | 帧数 | 内参（fx, fy, cx, cy） |
|----|------|--------|-----|------|------------------------|
| **depth** | Z16（16 位深度，单位 mm） | 640×480 | 30 | 1240 | 386.95, 386.95, 318.68, 233.52 |
| **color** | RGB8 | 640×480 | 30 | 1240 | 607.10, 606.40, 328.24, 252.88 |

说明：

- 1240 帧 ≈ 41.3 s × 30 fps，与时长一致。
- **未录制** 加速度计 / 陀螺仪（IMU）流。
- Depth 与 Color 的 **K 不同**（见第二节）。

### 1.3 回放与使用

- **GUI**：`realsense-viewer` → Open bag 回放。
- **代码**：`pyrealsense2` 使用 `config.enable_device_from_file("xxx.bag", repeat_playback=False)`。
- RGB-D 融合时建议对回放 pipeline 使用 **`rs.align(rs.stream.color)`**，使 depth 与 color 像素对齐（见 2.3 节）。

---

## 二、为什么 Depth 的 K 与 Color 的 K 不同？

### 2.1 结论（一句话）

Depth K 和 Color K **本来就应该不同**：D435i 是 **两套物理相机**（立体 IR 算深度 + 独立 RGB），镜头与光心不同，内参不会相同；使用时靠 **外参 R、T + align**，而不是让两个 K 相等。

### 2.2 硬件结构

| 模块 | 作用 |
|------|------|
| 左 / 右 **红外（IR）** | 立体匹配计算深度 |
| **RGB 彩色相机** | 单独一颗传感器，拍摄彩色图 |

- **Depth 的 K**：描述 **深度图 / 立体几何** 对应的相机模型（与 IR 立体相关）。
- **Color 的 K**：描述 **RGB 镜头** 自己的成像模型。

本包中虽均为 **640×480** 输出，但只是各自缩放/裁剪后的分辨率，**不是**同一镜头、同一像素网格。

```
[左 IR] —— [右 IR]  →  立体深度  →  K_depth
              \
               [RGB]  →  另一套镜头  →  K_color
```

### 2.3 分辨率相同 ≠ 内参相同

SDK 可将 depth、color 都设为 640×480，但：

- Depth：由 IR 视差得到，按深度相机内参解释像素；
- Color：由 RGB 传感器按自己的内参成像。

因此 **输出尺寸可以一样，fx、fy、cx、cy 仍可差很多**（本包中 depth fx≈387，color fx≈607）。

### 2.4 正确用法：外参 + 对齐

不能把 `K_depth` 当成 `K_color`。需要：

1. **外参**：RGB 相对深度（或 IR）的旋转 **R**、平移 **T**（设备出厂标定，保存在相机内）。
2. **对齐（align）**：将 depth 重投影到 color 像素平面。

```python
import pyrealsense2 as rs

align = rs.align(rs.stream.color)
aligned_frames = align.process(frames)
# 之后同一像素 (u,v) 上的 color 与 depth 对应同一条视线
```

| 场景 | 建议使用的内参 |
|------|----------------|
| 仅在深度图上做 3D / 测距 | **depth K** |
| 在彩色像素上取 3D、RGB-D 融合、上色 | **align 后** 使用 **color K**（或对齐后的深度图） |

### 2.5 与本 bag 的关系

`20260530_151155.bag` 仅含 **depth + color**（无 IMU），两路 640×480@30：

- 做 RGB-D、点云上色：playback 时加 **`rs.align(rs.stream.color)`**。
- 只在深度图空间处理：用 **depth K** 即可。

---

## 三、相关文件

| 文件 | 说明 |
|------|------|
| `data/20260530_151155.bag` | 示例录制（约 1.8 GB，勿提交 git） |
| `scripts/inspect_bag.py` | bag 检查脚本 |
| [README.md](README.md) | D435i 安装与 Python 取流说明 |
