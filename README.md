# Jetson Orin NX 安装 Intel RealSense D435i

在 **NVIDIA Jetson Orin NX**（Ubuntu 22.04 / JetPack 6.x）上安装 **Intel RealSense D435i** 的完整步骤。

- 官方 SDK：<https://github.com/realsenseai/librealsense>
- Jetson 说明：<https://github.com/realsenseai/librealsense/blob/master/doc/installation_jetson.md>

## 方案说明

| 项目 | 本指南采用 |
|------|------------|
| 安装方式 | 源码编译 |
| USB 后端 | **RSUSB**（用户态 libusb，`-DFORCE_RSUSB_BACKEND=ON`） |
| 内核 | **不**安装 `librealsense2-dkms`，**不**打 L4T 内核补丁 |
| GPU | 可选 `-DBUILD_WITH_CUDA=ON`（JetPack 已装 CUDA 时启用） |

Jetson 使用自定义内核，DKMS 模块容易失败；RSUSB 路线无需改内核，与 JetPack 冲突最少，适合先跑通设备。

> 若需要更高性能或多机同步，可改用官方 **Native 后端 + 内核补丁**（`scripts/patch-realsense-ubuntu-L4T.sh`），见 [installation_jetson.md](https://github.com/realsenseai/librealsense/blob/master/doc/installation_jetson.md)。

---

## 环境要求

- **硬件**：Jetson Orin NX；Intel RealSense **D435i**
- **系统**：Ubuntu 22.04（L4T 36.x / JetPack 6.x）
- **连接**：**USB 3.0 数据线 + USB 3.0 口**（USB2 可能认到设备但帧率/稳定性差）
- **磁盘**：源码编译约需 1～2 GB 空间
- **时间**：首次编译约 **20～40 分钟**（视 `nproc` 而定）

### 安装前检查

```bash
# 系统与 Jetson 信息
cat /etc/os-release
jetson_release    # 可选，需安装 jetson-stats

# CUDA（启用 BUILD_WITH_CUDA 时需要）
nvcc --version
# 若提示 command not found，再试：
/usr/local/cuda/bin/nvcc --version

# 相机是否被 USB 识别（先插上 D435i）
lsusb | grep -i intel
# 期望类似：8086:0b3a Intel Corp. Intel(R) RealSense(TM) Depth Camera 435i
```

### 本机实测环境（2026-05-29）

在 `~/stephen/RealSense` 目录下执行检查命令的实际输出记录，供对照与排错。

<details>
<summary>终端输出（点击展开）</summary>

```text
$ cat /etc/os-release
PRETTY_NAME="Ubuntu 22.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.5 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
...

$ jetson_release
Software part of jetson-stats 4.3.2 - (c) 2024, Raffaello Bonghi
Jetpack missing!
 - Model: NVIDIA Jetson Orin NX Engineering Reference Developer Kit Super
 - L4T: 36.4.7
NV Power Mode[0]: MAXN_SUPER
Hardware:
 - P-Number: p3767-0000
 - Module: NVIDIA Jetson Orin NX (16GB ram)
Platform:
 - Distribution: Ubuntu 22.04 Jammy Jellyfish
 - Release: 5.15.148-tegra
jtop:
 - Version: 4.3.2
 - Service: Active
Libraries:
 - CUDA: 12.6.85
 - cuDNN: 9.3.0.75
 - TensorRT: 10.3.0.30
 - VPI: 3.2.4
 - Vulkan: 1.3.204
 - OpenCV: 4.10.0 - with CUDA: YES

$ nvcc --version
bash: nvcc: command not found

$ lsusb | grep -i intel
Bus 002 Device 003: ID 8086:0b3a Intel Corp. Intel(R) RealSense(TM) Depth Camera 435i

# 配置 ~/.bashrc 中的 CUDA PATH 后（见下文）
$ echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
$ echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
$ source ~/.bashrc

$ nvcc --version
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2024 NVIDIA Corporation
Built on Tue_Oct_29_23:53:06_PDT_2024
Cuda compilation tools, release 12.6, V12.6.85
Build cuda_12.6.r12.6/compiler.35059454_0
```

</details>

| 检查项 | 本机结果 | 说明 |
|--------|----------|------|
| 操作系统 | Ubuntu **22.04.5** LTS | 符合本指南要求 |
| 板型 | Jetson **Orin NX 16GB**（p3767-0000） | 与文档目标平台一致 |
| L4T | **36.4.7** | 对应 JetPack **6.x** 一代 |
| `jetson_release` 显示 Jetpack missing | 多为 jetson-stats **元数据未写入**，不代表未装 JetPack | CUDA 12.6 / TensorRT 10.3 等已列出，可视为 JetPack 组件在机 |
| CUDA 运行时 | **12.6.85**（jetson_release） | GPU 栈已就绪 |
| `nvcc` | **12.6.85**（已写入 `~/.bashrc` 并验证） | PATH 已配置，编译 librealsense 可用 `-DBUILD_WITH_CUDA=ON` |
| D435i USB | **已识别**（`8086:0b3a`，Bus 002） | 线材与 USB3 正常，可进入 SDK 编译安装 |

### 针对本机的安装建议

1. **可以直接按本文档安装 SDK**  
   系统版本、板型、相机 USB 均已满足；硬件侧无需再排查。

2. **`nvcc: command not found` 不等于没装 CUDA**  
   Jetson 上常见情况是已安装 `cuda-toolkit-12-6`，但 shell 未加载 CUDA 路径。编译前执行：

   ```bash
   export PATH=/usr/local/cuda/bin:$PATH
   export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
   nvcc --version   # 应显示 12.6.x
   ```

   若需长期生效，写入 `~/.bashrc`（**本机已执行并验证**）：

   ```bash
   echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
   echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
   source ~/.bashrc
   nvcc --version
   ```

   本机验证输出：

   ```text
   nvcc: NVIDIA (R) Cuda compiler driver
   Cuda compilation tools, release 12.6, V12.6.85
   ```

   之后编译 librealsense 请使用 **`-DBUILD_WITH_CUDA=ON`**（新开终端也会自动加载 PATH）。

3. **若未配置 PATH**  
   可临时用 `-DBUILD_WITH_CUDA=OFF` 安装，**不影响** D435i 取流；本机 PATH 已就绪，无需关闭 CUDA。

4. **`Jetpack missing!` 可忽略**（就本安装而言）  
   以 L4T 36.4.7 + CUDA 12.6 为准即可；若需确认，可用 NVIDIA SDK Manager 或 `dpkg -l | grep nvidia-jetpack` 查看。

5. **电源模式**  
   当前为 `MAXN_SUPER`，有利于 USB3 与多路流稳定，安装与测试阶段保持即可。

6. **建议的 cmake 选择（本机）**  
   - **当前状态**：`nvcc` 12.6.85 可用 → 编译时 **务必** 加 `-DBUILD_WITH_CUDA=ON`  
   - 新开的终端若 `nvcc` 又找不到，先执行 `source ~/.bashrc` 再编译

---


## 一、更新系统

```bash
sudo apt update && sudo apt upgrade -y
```

---

## 二、安装编译依赖

```bash
sudo apt install -y \
  git cmake build-essential \
  libusb-1.0-0-dev libssl-dev pkg-config \
  libgtk-3-dev libglfw3-dev libgl1-mesa-dev libglu1-mesa-dev
```

若需要 **Python 绑定**，额外安装：

```bash
sudo apt install -y python3-dev
```

---

## 三、克隆 librealsense 源码

```bash
cd ~
git clone https://github.com/realsenseai/librealsense.git
cd librealsense
```

推荐使用稳定标签（与 D400 系列固件兼容，且官方标明支持 JetPack 6.0）：

```bash
git checkout v2.56.5
```

---

## 四、配置 udev 规则（必做）

普通用户访问 RealSense USB 设备需要 udev 权限。

> **注意路径**：以下命令必须在 **librealsense 源码目录** 内执行（含 `config/` 子目录），不要在 `RealSense` 项目根目录执行，否则会报 `cannot stat 'config/99-realsense-libusb.rules'`。

```bash
cd ~/stephen/RealSense/librealsense   # 按你的实际克隆路径调整

sudo cp config/99-realsense-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

插上相机后重新插拔一次，或注销再登录，使规则生效。

也可使用仓库脚本（效果等价）：

```bash
./scripts/setup_udev_rules.sh
```

---

## 五、编译并安装

### 5.1 推荐配置（含 Python）

在 `librealsense` 目录下：

```bash
mkdir -p build && cd build

cmake .. \
  -DFORCE_RSUSB_BACKEND=ON \
  -DBUILD_WITH_CUDA=ON \
  -DBUILD_EXAMPLES=ON \
  -DBUILD_GRAPHICAL_EXAMPLES=ON \
  -DBUILD_PYTHON_BINDINGS=ON \
  -DCHECK_FOR_UPDATES=OFF \
  -DCMAKE_BUILD_TYPE=Release

make -j$(nproc)
sudo make install
sudo ldconfig
```

### 5.2 CMake 参数说明

| 参数 | 说明 |
|------|------|
| `FORCE_RSUSB_BACKEND=ON` | 使用 RSUSB 用户态后端，**不依赖** RealSense 内核模块，Jetson 推荐 |
| `BUILD_WITH_CUDA=ON` | 使用 GPU 加速部分处理；CUDA 报错时可改为 `OFF`，不影响基本取流 |
| `BUILD_EXAMPLES=ON` | 编译 `rs-*` 命令行工具 |
| `BUILD_GRAPHICAL_EXAMPLES=ON` | 编译带 GUI 的示例；纯 SSH 无桌面时可设为 `OFF` |
| `BUILD_PYTHON_BINDINGS=ON` | 生成 `pyrealsense2`；建议首次 cmake 即开启 |
| `CHECK_FOR_UPDATES=OFF` | **Jetson 推荐关闭**；默认 ON 会在编译时从 GitHub 拉取 libcurl，网络不稳易失败 |

**不要**在 Jetson 上安装或使用 `librealsense2-dkms`。

### 5.3 无桌面 / 无 Python 时的精简配置

```bash
cmake .. \
  -DFORCE_RSUSB_BACKEND=ON \
  -DBUILD_WITH_CUDA=ON \
  -DBUILD_EXAMPLES=ON \
  -DBUILD_GRAPHICAL_EXAMPLES=OFF \
  -DCHECK_FOR_UPDATES=OFF \
  -DCMAKE_BUILD_TYPE=Release
```

### 5.4 CUDA 编译失败时

确认 JetPack 已安装 CUDA 后重试；仍失败可先关闭 CUDA 完成安装：

```bash
cd ~/librealsense/build
rm -rf *
cmake .. \
  -DFORCE_RSUSB_BACKEND=ON \
  -DBUILD_WITH_CUDA=OFF \
  -DBUILD_EXAMPLES=ON \
  -DCHECK_FOR_UPDATES=OFF \
  -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install && sudo ldconfig
```

### 5.5 清理后重新编译

```bash
cd ~/librealsense
rm -rf build
mkdir build && cd build
# 重新执行 cmake 与 make
```

---

## 六、验证安装

### 6.1 命令行枚举设备

```bash
rs-enumerate-devices
```

应列出 D435i 及固件版本等信息。

### 6.2 RealSense Viewer（有桌面时）

```bash
realsense-viewer
```

在 Viewer 中确认以下流正常：

- **Depth**（深度）
- **Color**（RGB）
- **IMU**（陀螺仪 / 加速度计，D435i 特有）

### 6.3 Python 测试

> **Jetson + RSUSB 注意**：D435i 若用 `pipeline.start(config)` 且 **不显式指定流**，SDK 会默认同时开 Depth + Color + **IMU**，在本机 RSUSB 后端下常出现 `Frame didn't arrive within 5000`。请**显式配置**分辨率与帧率（见下方脚本）。

```bash
python3 << 'EOF'
import pyrealsense2 as rs

pipeline = rs.pipeline()
config = rs.config()

# 必须显式指定流（Jetson RSUSB 推荐 640x480@30）
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

pipeline.start(config)
frames = pipeline.wait_for_frames(timeout_ms=10000)

depth = frames.get_depth_frame()
color = frames.get_color_frame()
print("Depth:", depth.get_width(), "x", depth.get_height())
print("Color:", color.get_width(), "x", color.get_height())

pipeline.stop()
print("OK")
EOF
```

仅测深度时可只开 depth 流：

```python
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
```

---

## 七、一键安装脚本

以下脚本与上文步骤等价（含 Python 绑定；无图形环境可将 `BUILD_GRAPHICAL_EXAMPLES` 改为 `OFF`）：

```bash
set -e

sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  git cmake build-essential python3-dev \
  libusb-1.0-0-dev libssl-dev pkg-config \
  libgtk-3-dev libglfw3-dev libgl1-mesa-dev libglu1-mesa-dev

cd ~
if [ ! -d librealsense ]; then
  git clone https://github.com/realsenseai/librealsense.git
fi
cd librealsense
git fetch --tags
git checkout v2.56.5

sudo cp config/99-realsense-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

mkdir -p build && cd build
cmake .. \
  -DFORCE_RSUSB_BACKEND=ON \
  -DBUILD_WITH_CUDA=ON \
  -DBUILD_EXAMPLES=ON \
  -DBUILD_GRAPHICAL_EXAMPLES=ON \
  -DBUILD_PYTHON_BINDINGS=ON \
  -DCHECK_FOR_UPDATES=OFF \
  -DCMAKE_BUILD_TYPE=Release

make -j$(nproc)
sudo make install
sudo ldconfig

echo "安装完成。请插上 D435i 后运行： rs-enumerate-devices 或 realsense-viewer"
```

---

## 八、常见问题

### 1. 找不到设备 / `rs-enumerate-devices` 无输出

- 确认 `lsusb` 能看到 Intel RealSense（`8086:0b3a` 等为 D435 系列）
- 更换 **USB 3.0** 线与口，避免经过无源 USB Hub
- 重新执行第四节 udev 规则，并**重新插拔**相机
- 检查权限：`groups`（udev 规则通常已加入 `plugdev` 等组）

### 2. Python 报错 `Frame didn't arrive within 5000`（本机已遇到）

**现象**：`rs-enumerate-devices` 正常，但 Python `pipeline.start(config)` 后 `wait_for_frames()` 超时。

**原因**：RSUSB 后端 + D435i 默认 pipeline 会同时启用 **IMU**，在本机实测会导致长时间无帧；显式只开 Depth/Color 则正常。

**修复**：显式 `enable_stream`（见第六节 Python 测试脚本），例如：

```python
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
```

本机验证结果：

| 配置 | 结果 |
|------|------|
| 默认 `start(config)`（含 IMU） | 超时失败 |
| 仅 Depth 640×480@30 | 成功 |
| Depth + Color 640×480@30 | 成功 |
| Depth + IMU | 超时失败 |

**IMU**：RSUSB 下 Python pipeline 取 IMU 可能不稳定；可先用 `realsense-viewer` 查看 IMU，或后续改用 **Native 内核后端**（需 L4T 内核补丁）。

**其他检查**：

- 确认无其他程序占用相机（关闭 `realsense-viewer`）
- 适当增大超时：`wait_for_frames(timeout_ms=10000)`
- 固件偏旧（本机 5.15.1.55，推荐 5.17.0.10）一般不影响取流，可按需用 `rs-fw-update` 升级

### 3. 编译到 80%+ 失败：无法 clone `libcurl`（本机已遇到）

典型报错：

```text
error: RPC failed; curl 92 HTTP/2 stream 0 was not closed cleanly: CANCEL (err 8)
Failed to clone repository: 'https://github.com/curl/curl.git'
```

**原因**：`CHECK_FOR_UPDATES=ON`（默认）会在编译 `realsense-viewer` 时通过 ExternalProject 从 GitHub 下载 libcurl；网络或 HTTP/2 不稳定时会中断。

**推荐修复**（关闭 Viewer 在线更新检查，不影响相机功能）：

```bash
cd ~/stephen/RealSense/librealsense/build   # 按实际路径

cmake .. \
  -DFORCE_RSUSB_BACKEND=ON \
  -DBUILD_WITH_CUDA=ON \
  -DBUILD_EXAMPLES=ON \
  -DBUILD_GRAPHICAL_EXAMPLES=ON \
  -DBUILD_PYTHON_BINDINGS=ON \
  -DCHECK_FOR_UPDATES=OFF \
  -DCMAKE_BUILD_TYPE=Release

make -j$(nproc)
sudo make install && sudo ldconfig
```

**备选**（若仍想保留更新检查）：配置 git 使用 HTTP/1.1 后重试 `make`：

```bash
git config --global http.version HTTP/1.1
git config --global http.postBuffer 524288000
rm -rf build/libcurl
make -j$(nproc)
```

### 4. udev 规则复制失败

```text
cp: cannot stat 'config/99-realsense-libusb.rules': No such file or directory
```

当前目录不对。先 `cd` 到 librealsense 源码根目录（含 `config/` 文件夹），再执行第四节命令。

### 5. 编译报错缺少头文件或库

- 重新执行第二节安装全部依赖
- 删除 `build` 目录后从第五节重新 `cmake` / `make`

### 6. CUDA / CMake 报错

- 运行 `nvcc --version` 确认 CUDA 来自 JetPack
- 将 `-DBUILD_WITH_CUDA=OFF` 后重新编译（相机仍可正常使用）

### 7. `realsense-viewer` 无法打开窗口

- 需在本地桌面或配置 `DISPLAY` 的 X11 转发
- 无显示环境时仅用 `rs-enumerate-devices` 与 Python/C++ API 即可

### 8. 固件与 SDK 版本

- D400 系列建议使用 SDK **v2.56.5** 及对应固件，见 [固件说明](https://dev.realsenseai.com/docs/firmware-updates)
- 可用 `rs-fw-update` 查看/更新固件（谨慎操作，按官方文档进行）

---

## 九、其他安装方式（可选）

### Debian 包（更省事，版本可能较旧）

JetPack ≥ 5.0.2 时，可按官方 [distribution_linux.md](https://github.com/realsenseai/librealsense/blob/master/doc/distribution_linux.md) 配置 apt 源后安装：

```bash
sudo apt-get install librealsense2-utils librealsense2-dev
```

若 apt 版本过旧或 Jetson 上异常，仍建议回到本文 **源码 + RSUSB** 方案。

### ROS 2

若需 ROS 2 Humble 驱动，在本文 SDK 安装成功后，再安装 `realsense2_camera` 功能包并编写 launch 文件（可单独补充文档）。

---

## 参考

- [librealsense GitHub](https://github.com/realsenseai/librealsense)
- [Release v2.56.5](https://github.com/realsenseai/librealsense/releases/tag/v2.56.5)（支持 JetPack 6.0）
- [Jetson 安装文档](https://github.com/realsenseai/librealsense/blob/master/doc/installation_jetson.md)
- 本仓库简要笔记：[doumao.md](./doumao.md)
